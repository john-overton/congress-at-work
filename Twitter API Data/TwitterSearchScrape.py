import requests
import sqlite3
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time

def create_table():
    conn = sqlite3.connect('gamestop_tweets.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tweets
                 (timestamp TEXT, username TEXT, tweet_body TEXT, hashtags TEXT)''')
    conn.commit()
    conn.close()

def insert_tweet(timestamp, username, tweet_body, hashtags):
    conn = sqlite3.connect('gamestop_tweets.db')
    c = conn.cursor()
    c.execute("INSERT INTO tweets VALUES (?, ?, ?, ?)",
              (timestamp, username, tweet_body, hashtags))
    conn.commit()
    conn.close()

def scrape_tweets():
    cookies = {
        'guest_id_marketing': 'v1%3A172192877915824022',
        'guest_id_ads': 'v1%3A172192877915824022',
        'personalization_id': '"v1_+amlzoLP9e7ORNbfJmdQNg=="',
        'guest_id': '172192877915824022',
        'night_mode': '2',
        'kdt': '0I7H8RtKoEZ0Lq5zHj1OI9YrYKIy5VGID2r20JDO',
        'twid': 'u%3D1685307610621161473',
        'ct0': '99226a80b46cd72e930e9e564fe2f1cf1ca903e4b6cb9a006d155e0a30932c7d22c3aeec2e911dff589a1da440e8cded8446a8cfb9653bc52f55bc4d40f58c98d92c31b107bffa631c8d25ed9f71ff48',
        'auth_token': 'b260224fa40af418704cddecdb00168de864882f',
        'des_opt_in': 'Y',
        'lang': 'en',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Connection': 'keep-alive',
        # 'Cookie': 'guest_id_marketing=v1%3A172192877915824022; guest_id_ads=v1%3A172192877915824022; personalization_id="v1_+amlzoLP9e7ORNbfJmdQNg=="; guest_id=172192877915824022; night_mode=2; kdt=0I7H8RtKoEZ0Lq5zHj1OI9YrYKIy5VGID2r20JDO; twid=u%3D1685307610621161473; ct0=99226a80b46cd72e930e9e564fe2f1cf1ca903e4b6cb9a006d155e0a30932c7d22c3aeec2e911dff589a1da440e8cded8446a8cfb9653bc52f55bc4d40f58c98d92c31b107bffa631c8d25ed9f71ff48; auth_token=b260224fa40af418704cddecdb00168de864882f; des_opt_in=Y; lang=en',
    }

    params = {
        'q': '#GME GME Gamestop #Gamestop',
        'src': 'typed_query',
        'f': 'live',
    }

    response = requests.get('https://x.com/search', params=params, cookies=cookies, headers=headers)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    tweets = soup.find_all('article', {'data-testid': 'tweet'})
    
    with open("output.txt", "w", encoding="utf-8") as a:
        a.write(str(soup))

    for tweet in tweets:
        # Extract timestamp
        time_element = tweet.find('time')
        timestamp = time_element['datetime'] if time_element else ''
        
        # Extract username
        username_element = tweet.find('div', {'data-testid': 'User-Name'})
        username = username_element.text.strip() if username_element else ''
        
        # Extract tweet body
        tweet_body_element = tweet.find('div', {'data-testid': 'tweetText'})
        tweet_body = tweet_body_element.text.strip() if tweet_body_element else ''
        
        # Extract hashtags
        hashtags = ' '.join(re.findall(r'#\w+', tweet_body))
        
        insert_tweet(timestamp, username, tweet_body, hashtags)

def main():
    create_table()
    # url = "https://x.com/search?q=%23GME%20GME%20Gamestop%20%23Gamestop&src=typed_query&f=live"
    
    while True:
        try:
            scrape_tweets()
            print(f"Scraped tweets at {datetime.now()}")
            time.sleep(300)  # Wait for 5 minutes before next scrape
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)  # Wait for 1 minute before retrying

if __name__ == "__main__":
    main()