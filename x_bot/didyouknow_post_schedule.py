import sqlite3
import random
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pytz
import x_bot_post

# Set up logging
log_dir = Path("./Logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "didyouknow_post.log"
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database file path
DB_FILE = Path("./DB/didyouknow_tweet.db")

# Configurable start and end times (24-hour format)
START_TIME = "07:00"
END_TIME = "20:00"

# Time zone
TIME_ZONE = 'US/Central'

def get_random_tweet():
    logging.info("Fetching a random tweet from the database")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tweet_id, tweet_text 
        FROM didyouknow_tweet 
        WHERE tweeted = 0 
        ORDER BY RANDOM() 
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()
    
    if result:
        logging.info(f"Retrieved tweet with ID: {result[0]}")
        return result
    else:
        logging.warning("No untweeted posts found in the database")
        return None

def update_tweet_status(tweet_id):
    logging.info(f"Updating tweet status for ID: {tweet_id}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE didyouknow_tweet 
        SET tweeted = 1, tweeted_datetime = ? 
        WHERE tweet_id = ?
    """, (current_time, tweet_id))
    conn.commit()
    conn.close()
    logging.info(f"Tweet status updated for ID: {tweet_id}")

def post_random_tweet():
    tweet_data = get_random_tweet()
    if tweet_data:
        tweet_id, tweet_text = tweet_data
        try:
            x_bot_post.post_tweet(tweet_text)
            update_tweet_status(tweet_id)
            logging.info(f"Successfully posted tweet with ID: {tweet_id}")
        except Exception as e:
            logging.error(f"Error posting tweet: {str(e)}")
    else:
        logging.warning("No tweet available to post")

def is_within_posting_hours(dt):
    start = datetime.strptime(START_TIME, "%H:%M").time()
    end = datetime.strptime(END_TIME, "%H:%M").time()
    return start <= dt.time() < end

def schedule_next_run():
    now = datetime.now(pytz.timezone(TIME_ZONE))
    next_run = now + timedelta(minutes=random.randint(50, 70))
    
    start_time = datetime.strptime(START_TIME, "%H:%M").time()
    end_time = datetime.strptime(END_TIME, "%H:%M").time()
    
    # If next run is after end time, schedule for start time the next day
    if next_run.time() >= end_time:
        next_run = next_run.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0) + timedelta(days=1)
    
    # If next run is before start time, schedule for start time the same day
    elif next_run.time() < start_time:
        next_run = next_run.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
    
    delay = (next_run - now).total_seconds()
    logging.info(f"Scheduling next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    return delay

def run_scheduled_post():
    now = datetime.now(pytz.timezone(TIME_ZONE))
    if is_within_posting_hours(now):
        post_random_tweet()
    schedule_next_run()

def main():
    logging.info(f"Starting the Did You Know Post script (Posting hours: {START_TIME} - {END_TIME} {TIME_ZONE})")
    while True:
        delay = schedule_next_run()
        time.sleep(delay)
        run_scheduled_post()

if __name__ == "__main__":
    main()