import requests
import json
from datetime import datetime
import os
from keys import bearer_token

# URL and headers
# Use: https://developer.twitter.com/apitools/api?endpoint=%2F2%2Ftweets%2Fcounts%2Frecent&method=get as reference or help generating url

url = "https://api.twitter.com/2/tweets/counts/recent?query=%23GME%20OR%20GME%20OR%20Gamestop&start_time=2024-09-06T10:00:00.000Z&end_time=2024-09-06T16:00:00.000Z&granularity=minute&search_count.fields=tweet_count"

# Headers with the bearer token
headers = {
    "Authorization": f"Bearer {bearer_token}"
}

# Generate dynamic filename based on current date and time
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join("C:\\temp", f"twitter_data_{timestamp}.json")

# Send the request and get the response
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON content
    json_content = json.loads(response.text)
    
    # Write the JSON content to a file
    with open(output_file, 'w') as f:
        json.dump(json_content, f, indent=4)
    
    print(f"Request completed. JSON output saved to {output_file}")
else:
    print(f"Error: Received status code {response.status_code}")
    print(f"Response: {response.text}")