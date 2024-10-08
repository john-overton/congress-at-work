import sqlite3
import logging
from pathlib import Path
import x_bot_post
from datetime import datetime
import os

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
parent_dir = os.path.dirname(script_dir)

# Set up logging
log_dir = os.path.join(script_dir, 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bills_post.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database file path
DB_FILE = Path("./x_bot/DB/active_bills_tweets.db")

def get_random_tweet():
    logging.info("Attempting to fetch a random tweet from the active_bill_tweets table")
    try:
        if not DB_FILE.exists():
            logging.error(f"Database file not found at {DB_FILE}")
            return None

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                bill_index, 
                tweet_title || char(10) || char(10) || tweet_body
            FROM active_bills_tweets 
            WHERE tweeted = 0
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logging.info(f"Retrieved tweet with bill_index: {result[0]}")
            return result
        else:
            logging.warning("No untweeted posts found in the database")
            return None
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return None

def update_tweet_status(bill_index):
    logging.info(f"Attempting to update tweet status for bill_index: {bill_index}")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE active_bills_tweets 
            SET tweeted = 1, tweeted_datetime = ? 
            WHERE bill_index = ?
        """, (current_time, bill_index))
        conn.commit()
        conn.close()
        logging.info(f"Tweet status updated for bill_index: {bill_index}")
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred while updating tweet status: {e}")
    except Exception as e:
        logging.error(f"Unexpected error occurred while updating tweet status: {e}")

def post_random_tweet():
    tweet_data = get_random_tweet()
    if tweet_data:
        bill_index, combined_tweet = tweet_data
        try:
            x_bot_post.post_tweet(combined_tweet)
            update_tweet_status(bill_index)
            logging.info(f"Successfully posted tweet for bill_index: {bill_index}")
        except Exception as e:
            logging.error(f"Error posting tweet: {str(e)}")
    else:
        logging.warning("No tweet available to post")

def main():
    logging.info("Starting the Immediate Active Bill Tweets Post script")
    logging.info(f"Database file path: {DB_FILE.absolute()}")
    post_random_tweet()
    logging.info("Script execution completed")

if __name__ == "__main__":
    main()