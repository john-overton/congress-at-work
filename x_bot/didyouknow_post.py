import sqlite3
import logging
from pathlib import Path
import x_bot_post
from datetime import datetime

# Set up logging
log_dir = Path("./Logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "immediate_didyouknow_post.log"
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database file path
DB_FILE = Path("./DB/didyouknow_tweet.db")

def get_random_tweet():
    logging.info("Attempting to fetch a random tweet from the database")
    try:
        if not DB_FILE.exists():
            logging.error(f"Database file not found at {DB_FILE}")
            return None

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
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return None

def update_tweet_status(tweet_id):
    logging.info(f"Attempting to update tweet status for ID: {tweet_id}")
    try:
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
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred while updating tweet status: {e}")
    except Exception as e:
        logging.error(f"Unexpected error occurred while updating tweet status: {e}")

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

def main():
    logging.info("Starting the Immediate Did You Know Post script")
    logging.info(f"Database file path: {DB_FILE.absolute()}")
    post_random_tweet()
    logging.info("Script execution completed")

if __name__ == "__main__":
    main()