import os
import sqlite3
import time
from datetime import datetime
import logging
import secrets
import sys

# Get the current script's directory (x_bot folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

def ensure_directories_exist():
    directories = [os.path.join(current_dir, 'Logs'), os.path.join(current_dir, 'DB')]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Ensure directories exist before setting up logging
ensure_directories_exist()

# Set up logging
log_file = os.path.join(current_dir, 'Logs', 'didyouknow_parameters.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Add the root directory and the keys folder to sys.path
root_dir = os.path.dirname(current_dir)
keys_dir = os.path.join(root_dir, 'keys')
sys.path.extend([root_dir, keys_dir])

# Try to import the API key
try:
    from keys import gg_key
except ImportError:
    logging.error(f"Failed to import gg_key from keys.py. Ensure keys.py is in the correct location: {keys_dir}")
    print(f"Error: Could not import gg_key from keys.py. Please ensure keys.py is in the directory: {keys_dir}")
    sys.exit(1)

# Check if gg_key is defined and not empty
if not gg_key:
    logging.error("gg_key is not defined or is empty in keys.py")
    print("Error: gg_key is not defined or is empty in keys.py")
    sys.exit(1)

# Now that we've confirmed gg_key exists, we can import and configure genai
try:
    import google.generativeai as genai
    genai.configure(api_key=gg_key)
except ImportError:
    logging.error("Failed to import google.generativeai. Make sure it's installed: pip install google-generativeai")
    print("Error: Failed to import google.generativeai. Please install it using: pip install google-generativeai")
    sys.exit(1)
except Exception as e:
    logging.error(f"Error configuring genai: {str(e)}")
    print(f"Error configuring genai: {str(e)}")
    sys.exit(1)

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
    return conn

def create_bill_parameters_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS didyouknow_bill_parameters (
                bill_index INTEGER PRIMARY KEY,
                congress INTEGER,
                bill_type TEXT,
                bill_number INTEGER,
                total_token_size INTEGER,
                total_expected_tweets INTEGER
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error creating bill parameters table: {e}")

def create_tweet_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS didyouknow_tweet (
                bill_index INTEGER,
                tweet_id TEXT UNIQUE,
                tweet_text TEXT,
                created_date DATETIME,
                bill_index_count INTEGER,
                tweeted INTEGER DEFAULT 0,
                tweeted_datetime DATETIME,
                FOREIGN KEY (bill_index) REFERENCES didyouknow_bill_parameters (bill_index)
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error creating tweet table: {e}")

def insert_bill_parameters(conn, congress, bill_type, bill_number, total_token_size, total_expected_tweets):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO didyouknow_bill_parameters 
            (congress, bill_type, bill_number, total_token_size, total_expected_tweets)
            VALUES (?, ?, ?, ?, ?)
        ''', (congress, bill_type, bill_number, total_token_size, total_expected_tweets))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error inserting bill parameters: {e}")
        return None

def insert_tweet(conn, bill_index, tweet_text):
    try:
        cursor = conn.cursor()
        tweet_id = secrets.token_hex(4)
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the current count of tweets for this bill_index
        cursor.execute('SELECT COUNT(*) FROM didyouknow_tweet WHERE bill_index = ?', (bill_index,))
        bill_index_count = cursor.fetchone()[0] + 1
        
        cursor.execute('''
            INSERT INTO didyouknow_tweet 
            (bill_index, tweet_id, tweet_text, created_date, bill_index_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (bill_index, tweet_id, tweet_text, created_date, bill_index_count))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Error inserting tweet: {e}")
        return False

def get_token_count(file_path):
    # This is a placeholder function. In a real-world scenario, you'd use a proper tokenizer.
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return len(content.split())

def process_bill_files():
    bill_params_db = os.path.join(current_dir, 'DB', 'didyouknow_bill_parameters.db')
    conn = create_connection(bill_params_db)
    if conn is not None:
        create_bill_parameters_table(conn)
        
        bill_dir = os.path.join(root_dir, 'congress_api_scraper', 'bill_text_htm')
        if not os.path.exists(bill_dir):
            logging.error(f"Bill directory does not exist: {bill_dir}")
            print(f"Error: Bill directory does not exist: {bill_dir}")
            return

        for filename in os.listdir(bill_dir):
            if filename.endswith('.htm'):
                parts = filename.split('.')
                congress = int(parts[0])
                bill_type = parts[1]
                bill_number = int(parts[2])
                
                # Check if record already exists
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM didyouknow_bill_parameters 
                    WHERE congress = ? AND bill_type = ? AND bill_number = ?
                ''', (congress, bill_type, bill_number))
                
                if cursor.fetchone() is None:
                    file_path = os.path.join(bill_dir, filename)
                    total_token_size = get_token_count(file_path)
                    
                    # New calculation for total_expected_tweets
                    if total_token_size < 500:
                        total_expected_tweets = 2
                    else:
                        total_expected_tweets = total_token_size // 100
                    
                    insert_bill_parameters(conn, congress, bill_type, bill_number, total_token_size, total_expected_tweets)
                    logging.info(f"Processed file: {filename} - Tokens: {total_token_size}, Expected Tweets: {total_expected_tweets}")
                else:
                    logging.info(f"Skipped existing record: {filename}")
        
        conn.close()
    else:
        logging.error("Error: Could not create database connection.")

def generate_tweet(bill_content, bill_type, bill_number):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Generate a did you know tweet that pulls out interesting and unbiased fact(s) out of legislation text provided in html markup below. 
    Remember that the tweet must be 280 characters or less. Include reference information so that someone could find the information if they chose to research it themselves. 
    The reference information should include bill type, bill number, and section within the bill the fact comes from. 
    Create the tweet from any interesting section of this document: {bill_content}"""
    
    for _ in range(5):  # Retry up to 5 times
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"API call failed: {e}. Retrying...")
            time.sleep(5)  # Wait for 5 seconds before retrying
    
    logging.error("Failed to generate tweet after 5 retries.")
    return None

def process_tweets():
    bill_params_db = os.path.join(current_dir, 'DB', 'didyouknow_bill_parameters.db')
    tweet_db = os.path.join(current_dir, 'DB', 'didyouknow_tweet.db')
    
    bill_params_conn = create_connection(bill_params_db)
    tweet_conn = create_connection(tweet_db)
    
    if bill_params_conn is not None and tweet_conn is not None:
        create_tweet_table(tweet_conn)
        
        cursor = bill_params_conn.cursor()
        cursor.execute('SELECT * FROM didyouknow_bill_parameters ORDER BY 1 DESC')
        bills = cursor.fetchall()
        
        for bill in bills:
            bill_index, congress, bill_type, bill_number, _, total_expected_tweets = bill
            
            # Check existing tweets for this bill
            tweet_cursor = tweet_conn.cursor()
            tweet_cursor.execute('SELECT COUNT(*) FROM didyouknow_tweet WHERE bill_index = ?', (bill_index,))
            existing_tweets = tweet_cursor.fetchone()[0]
            
            if existing_tweets < total_expected_tweets:
                # Generate and insert new tweets
                bill_file = f"{congress}.{bill_type}.{bill_number}.*.htm"
                bill_dir = os.path.join(root_dir, 'congress_api_scraper', 'bill_text_htm')
                matching_files = [f for f in os.listdir(bill_dir) if f.startswith(f"{congress}.{bill_type}.{bill_number}.")]
                
                if matching_files:
                    bill_file = os.path.join(bill_dir, matching_files[0])
                    with open(bill_file, 'r', encoding='utf-8') as file:
                        bill_content = file.read()
                    
                    tweet_text = generate_tweet(bill_content, bill_type, bill_number)
                    if tweet_text:
                        if insert_tweet(tweet_conn, bill_index, tweet_text):
                            logging.info(f"Inserted tweet for bill index {bill_index}")
                        else:
                            logging.error(f"Failed to insert tweet for bill index {bill_index}")
                    
                    time.sleep(60)  # Wait 1 second before processing the next tweet
                else:
                    logging.error(f"No matching file found for bill {congress}.{bill_type}.{bill_number}")
            else:
                logging.info(f"All expected tweets generated for bill index {bill_index}")
        
        bill_params_conn.close()
        tweet_conn.close()
    else:
        logging.error("Error: Could not create database connections.")

if __name__ == "__main__":
    process_bill_files()
    process_tweets()
