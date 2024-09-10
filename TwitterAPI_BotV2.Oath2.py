import base64
import hashlib
import json
import os
import secrets
import requests
from urllib.parse import urlencode
import keys
import Gen_Random_Bill_Prompt

# Twitter API endpoints
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWEET_URL = "https://api.twitter.com/2/tweets"

# Your app's client ID (replace with your actual client ID)
CLIENT_ID = "your_client_id_here"

# Read OAuth 2.0 credentials from keys.py
OAUTH2_USER_KEY = keys.oath2_userkey
OAUTH2_SECRET = keys.oath2_secret

def generate_code_verifier():
    return base64.urlsafe_b64encode(os.urandom(30)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier):
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')

def get_authorization_url(code_challenge):
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": "https://example.com/callback",
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": secrets.token_urlsafe(16),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def get_access_token(code, code_verifier):
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": "https://example.com/callback",
        "code_verifier": code_verifier
    }
    auth = (OAUTH2_USER_KEY, OAUTH2_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get access token: {response.text}")

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

def main():
    # Generate PKCE code verifier and challenge
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    # Get authorization URL
    auth_url = get_authorization_url(code_challenge)
    print(f"Please go to this URL to authorize the app: {auth_url}")

    # Get the authorization code from user input
    auth_code = input("Enter the authorization code: ")

    # Exchange authorization code for access token
    token_data = get_access_token(auth_code, code_verifier)
    access_token = token_data["access_token"]

    # Generate tweet text
    tweet_text = Gen_Random_Bill_Prompt.RESULT[0]

    # Create and post the tweet
    tweet_response = create_tweet(access_token, tweet_text)
    print(f"Tweet created successfully: {json.dumps(tweet_response, indent=2)}")

if __name__ == "__main__":
    main()