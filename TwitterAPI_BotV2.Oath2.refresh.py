import base64
import hashlib
import json
import os
import requests
from urllib.parse import urlencode
import keys
import Gen_Random_Bill_Prompt
import time
import webbrowser

# X API endpoints
TOKEN_URL = "https://api.x.com/2/oauth2/token"
TWEET_URL = "https://api.twitter.com/2/tweets"

# Your app's client ID and redirect URI
CLIENT_ID = keys.oauth2_client_id
REDIRECT_URI = "http://127.0.0.1:3000/oauth/callback"

# Read OAuth 2.0 credentials from keys.py
OAUTH2_CLIENT_ID = keys.oauth2_client_id
OAUTH2_CLIENT_SECRET = keys.oauth2_client_secret

# File to store tokens
TOKEN_FILE = "x_tokens.json"

def generate_code_verifier():
    return base64.urlsafe_b64encode(os.urandom(30)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')

def start_authorization(code_verifier, code_challenge):
    auth_url = f"http://127.0.0.1:3000/start_auth?code_verifier={code_verifier}&code_challenge={code_challenge}"
    webbrowser.open(auth_url)
    print("Authorization started. Please check your browser.")
    
    # Wait for the callback server to save the tokens
    while not os.path.exists(TOKEN_FILE):
        time.sleep(1)
    
    # Give it a moment to finish writing
    time.sleep(2)

def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": OAUTH2_CLIENT_ID
    }
    auth = (OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to refresh token: {response.text}")

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def create_tweet(access_token, tweet_text):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {"text": tweet_text}
    response = requests.post(TWEET_URL, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create tweet: {response.text}")

def get_valid_access_token():
    tokens = load_tokens()
    if tokens:
        # Check if the access token has expired (2 hours by default)
        if tokens['expires_at'] <= time.time():
            # Refresh the access token
            new_tokens = refresh_access_token(tokens['refresh_token'])
            new_tokens['expires_at'] = time.time() + new_tokens['expires_in']
            with open(TOKEN_FILE, 'w') as f:
                json.dump(new_tokens, f)
            return new_tokens['access_token']
        else:
            return tokens['access_token']
    return None

def main():
    access_token = get_valid_access_token()

    if not access_token:
        # If we don't have a valid access token, start the authorization process
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)

        start_authorization(code_verifier, code_challenge)
        
        # Load the tokens saved by the callback server
        tokens = load_tokens()
        if not tokens:
            raise Exception("Failed to obtain access token")
        
        access_token = tokens['access_token']

    # Generate tweet text
    tweet_text = Gen_Random_Bill_Prompt.RESULT[0]

    # Create and post the tweet
    tweet_response = create_tweet(access_token, tweet_text)
    print(f"Tweet created successfully: {json.dumps(tweet_response, indent=2)}")

if __name__ == "__main__":
    main()