import base64
import hashlib
import json
import os
import sys
import requests
import time
import webbrowser
import logging
from pathlib import Path
from urllib.parse import urlencode

# Add the rootdir to the Python path
rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(rootdir)

# Now import keys from the correct location
from keys import keys

# X API endpoints
TOKEN_URL = "https://api.x.com/2/oauth2/token"
TWEET_URL = "https://api.twitter.com/2/tweets"

# Your app's client ID and redirect URI
CLIENT_ID = keys.caw_oauth2_client_id
REDIRECT_URI = "http://127.0.0.1:3000/oauth/callback"

# Read OAuth 2.0 credentials from keys.py
OAUTH2_CLIENT_ID = keys.caw_oauth2_client_id
OAUTH2_CLIENT_SECRET = keys.caw_oauth2_client_secret

# File to store tokens
TOKEN_FILE = "x_tokens.json"

# Set up logging
log_dir = Path("./x_bot/Logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "x_bot_post.log"
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def generate_code_verifier():
    logging.info("Generating code verifier")
    return base64.urlsafe_b64encode(os.urandom(30)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    logging.info("Generating code challenge")
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')

def start_authorization(code_verifier, code_challenge):
    logging.info("Starting authorization process")
    auth_url = f"http://127.0.0.1:3000/start_auth?code_verifier={code_verifier}&code_challenge={code_challenge}"
    webbrowser.open(auth_url)
    logging.info("Authorization started. Browser opened.")
    print("Authorization started. Please check your browser.")
    
    while not os.path.exists(TOKEN_FILE):
        time.sleep(1)
    
    time.sleep(2)
    logging.info("Authorization process completed")

def refresh_access_token(refresh_token):
    logging.info("Refreshing access token")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": OAUTH2_CLIENT_ID
    }
    auth = (OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)
    if response.status_code == 200:
        logging.info("Access token refreshed successfully")
        return response.json()
    else:
        logging.error(f"Failed to refresh token: {response.text}")
        raise Exception(f"Failed to refresh token: {response.text}")

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        logging.info("Loading tokens from file")
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    logging.info("No token file found")
    return None

def create_tweet(access_token, tweet_text):
    logging.info("Creating tweet")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {"text": tweet_text}
    response = requests.post(TWEET_URL, headers=headers, json=data)
    if response.status_code == 201:
        logging.info("Tweet created successfully")
        return response.json()
    else:
        logging.error(f"Failed to create tweet: {response.text}")
        raise Exception(f"Failed to create tweet: {response.text}")

def get_valid_access_token():
    logging.info("Getting valid access token")
    tokens = load_tokens()
    if tokens:
        if tokens['expires_at'] <= time.time():
            logging.info("Token expired, refreshing")
            new_tokens = refresh_access_token(tokens['refresh_token'])
            new_tokens['expires_at'] = time.time() + new_tokens['expires_in']
            with open(TOKEN_FILE, 'w') as f:
                json.dump(new_tokens, f)
            return new_tokens['access_token']
        else:
            logging.info("Using existing valid token")
            return tokens['access_token']
    logging.info("No valid token found")
    return None

def post_tweet(tweet_text):
    logging.info(f"Attempting to post tweet: {tweet_text}")
    access_token = get_valid_access_token()

    if not access_token:
        logging.info("No valid access token, starting authorization process")
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)

        start_authorization(code_verifier, code_challenge)
        
        tokens = load_tokens()
        if not tokens:
            logging.error("Failed to obtain access token")
            raise Exception("Failed to obtain access token")
        
        access_token = tokens['access_token']

    tweet_response = create_tweet(access_token, tweet_text)
    logging.info(f"Tweet created successfully: {json.dumps(tweet_response, indent=2)}")
    print(f"Tweet created successfully: {json.dumps(tweet_response, indent=2)}")

# Example usage
if __name__ == "__main__":
    sample_tweet = "**test**, **_test2_**, _test3_, This is a test tweet from the simplified OAuth 2.0 script!"
    post_tweet(sample_tweet)