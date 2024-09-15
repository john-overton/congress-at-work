# Localhost authentication server for Oauth2.0 handshake

import sys
import os
import logging
from flask import Flask, request, redirect, session
import requests
import json
import time
import secrets

# Add the rootdir to the Python path
rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(rootdir)

# Now import keys from the correct location
from keys import keys

# Set up logging
log_dir = os.path.join(os.path.dirname(__file__), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'authentication_server.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
    )

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Set a secret key for session

# Twitter OAuth 2.0 endpoints
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"

# Your app's credentials
CLIENT_ID = keys.caw_oauth2_client_id
CLIENT_SECRET = keys.caw_oauth2_client_secret
REDIRECT_URI = "http://127.0.0.1:3000/oauth/callback"

# File to store tokens
TOKEN_FILE = "x_tokens.json"

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if state != session.get('oauth_state'):
        return 'Invalid state parameter', 400

    code_verifier = session.get('code_verifier')
    if not code_verifier:
        return 'Missing code_verifier', 400

    try:
        # Exchange authorization code for access token
        token_data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier
        }
        auth = (CLIENT_ID, CLIENT_SECRET)
        token_response = requests.post(TOKEN_URL, data=token_data, auth=auth)
        token_response.raise_for_status()

        tokens = token_response.json()
        tokens['expires_at'] = time.time() + tokens['expires_in']

        # Save tokens
        save_tokens(tokens)

        return 'Authorization successful! You can close this window and return to the application.'
    except requests.RequestException as e:
        print(f'Error exchanging code for token: {e}')
        return f'An error occurred during authorization: {str(e)}', 500

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

@app.route('/start_auth')
def start_auth():
    code_verifier = request.args.get('code_verifier')
    code_challenge = request.args.get('code_challenge')
    
    if not code_verifier or not code_challenge:
        return 'Missing code_verifier or code_challenge', 400

    # Store code_verifier in session
    session['code_verifier'] = code_verifier

    # Generate and store state
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state

    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"{AUTH_URL}?{requests.compat.urlencode(auth_params)}"
    
    return redirect(auth_url)

if __name__ == '__main__':
    app.run(port=3000)