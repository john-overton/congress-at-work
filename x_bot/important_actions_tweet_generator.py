import os
import sqlite3
import datetime
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import sys
import time
import secrets
import re

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
parent_dir = os.path.dirname(script_dir)

# Set up logging
log_dir = os.path.join(script_dir, 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'important_actions_tweet_generator.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Construct the path to the keys.py file
keys_path = os.path.join(parent_dir, 'keys', 'keys.py')

# Add the directory containing keys.py to sys.path
sys.path.append(os.path.dirname(keys_path))

# Import the gg_key from keys.py
from keys import gg_key

# Configure the Google Generative AI
try:
    genai.configure(api_key=gg_key)
    logging.info("Google Generative AI configured successfully")
except Exception as e:
    logging.error(f"Failed to configure Google Generative AI: {str(e)}")
    raise

# Set up the model
generation_config = {
    "temperature": 0.75,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 7500,
}

safety_settings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]

try:
    model = genai.GenerativeModel(model_name="gemini-1.5-flash",
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)
    logging.info("Generative model initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize generative model: {str(e)}")
    raise

def connect_to_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str
        logging.info(f"Successfully connected to database: {db_path}")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database {db_path}: {str(e)}")
        raise

def get_must_know_bills(conn, days=30):
    cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT congress, billType, billNumber, title, importance
            FROM active_bill_list
            WHERE importance = 'Must Know'
            AND latestActionDate >= ?
            AND tweet_created = 0
        """, (cutoff_date.isoformat(),))
        result = cursor.fetchall()
        logging.info(f"Retrieved {len(result)} 'Must Know' bills from the last {days} days with tweet_created = 0")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving 'Must Know' bills: {str(e)}")
        raise

def get_bill_actions(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT actionDate, actionText
            FROM bill_actions
            WHERE congress = ? AND billType = ? AND billNumber = ?
            ORDER BY actionDate DESC
        """, (congress, bill_type, bill_number))
        result = cursor.fetchall()
        logging.info(f"Retrieved {len(result)} bill actions for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill actions: {str(e)}")
        raise

def find_bill_file(bill_text_dir, congress, bill_type, bill_number):
    logging.info(f"Bill text directory is: {bill_text_dir}")
    logging.debug(f"Looking for bill file: {congress}.{bill_type}.{bill_number}")
    for filename in os.listdir(bill_text_dir):
        if filename.endswith('.htm'):
            # This regex pattern is more flexible and will match variations in naming
            pattern = rf"{congress}\.{bill_type}\.{bill_number}\."
            if re.search(pattern, filename):
                return os.path.join(bill_text_dir, filename)
    logging.warning(f"No bill file found for {congress}.{bill_type}.{bill_number}")
    return None

def get_bill_text(bill_file):
    if bill_file is None:
        logging.warning("No bill file found")
        return "Bill text not available"
    try:
        with open(bill_file, 'r', encoding='utf-8') as file:
            content = file.read()
        logging.info(f"Retrieved bill text from {bill_file}")
        return content
    except IOError as e:
        logging.error(f"Error reading bill text file {bill_file}: {str(e)}")
        return "Error reading bill text"

def construct_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    bill_text_preview = bill_text[:15] if bill_text else "N/A"
    bill_actions_preview = bill_actions[:15] if bill_actions else "N/A"
    
    prompt = f"""
    <Instructions>
    As an unbiased reporter, provide a short report about the recent important actions and key facts of this legislation.
    The report should be 4-5 paragraphs long.
    Do not include a title in the response.
    Focus on the most recent and significant developments, and provide key, important facts from the bill text.
    Always include the section notation of the text if referencing it so that your reader can easily look it up.
    Do not provide any party affiliations of sponsors or co-sponsors.
    </Instructions>
    <Additional Details>
    Today's date is {today_date}. Current sitting President: Joe Biden
    Key action meanings:
    "Presented to President" - This means the legislation has been brought forward to the President's office but the legislation has not yet been signed or vetoed.
    "Signed by President" - This means the legislation has been signed by the president and become public law.
    Bills: A bill is the form used for most legislation, whether permanent or temporary, general or special, public or private. Bills are presented to the President for action when approved in identical form by both the House of Representatives and the Senate.
    Joint Resolutions: Joint resolutions may originate either in the House of Representatives or in the Senate. They are subject to the same procedure as bills, except for joint resolutions proposing amendments to the Constitution.
    Concurrent Resolutions: Matters affecting the operations of both the House of Representatives and Senate are usually initiated by means of concurrent resolutions. They are not presented to the President for action.
    Simple Resolutions: A matter concerning the operation of either the House of Representatives or Senate alone is initiated by a simple resolution. They are not presented to the President for action.
    </Additional Details>

    <Congress>{congress}</Congress>
    <Bill Title>{bill_title}</Bill Title>
    <Bill Number>{bill_type}{bill_number}</Bill Number>
    <Bill Text>
    {bill_text}
    </Bill Text>
    <Bill Actions>
    {bill_actions}
    </Bill Actions>
    """
    logging.info(f"Constructed prompt for bill {congress}.{bill_type}.{bill_number}.  Here is the info included.. Date: {today_date} \ Bill text preview: {bill_text_preview} \ Bill actions preview: {bill_actions_preview}.")
    return prompt

def construct_title_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    bill_text_preview = bill_text[:15] if bill_text else "N/A"
    bill_actions_preview = bill_actions[:15] if bill_actions else "N/A"
    
    prompt = f"""
    <Instructions>
    As an unbiased reporter, provide a concise and informative title for a tweet about the most recent important action and key facts of this legislation.
    The title should be no longer than 100 characters.
    Focus on the most recent and significant developments, or a key important fact from the bill text.
    Do not include any party affiliations of sponsors or co-sponsors.
    </Instructions>
    <Additional Details>
    Today's date is {today_date}. Current sitting President: Joe Biden
    Key action meanings:
    "Presented to President" - This means the legislation has been brought forward to the President's office but the legislation has not yet been signed or vetoed.
    "Signed by President" - This means the legislation has been signed by the president and become public law.
    </Additional Details>

    <Congress>{congress}</Congress>
    <Bill Title>{bill_title}</Bill Title>
    <Bill Number>{bill_type}{bill_number}</Bill Number>
    <Bill Text>
    {bill_text}
    </Bill Text>
    <Bill Actions>
    {bill_actions}
    </Bill Actions>
    """
    logging.info(f"Constructed title prompt for bill {congress}.{bill_type}.{bill_number}")
    return prompt

def construct_hashtag_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    bill_text_preview = bill_text[:15] if bill_text else "N/A"
    bill_actions_preview = bill_actions[:15] if bill_actions else "N/A"
    
    prompt = f"""
    <Instructions>
    As an unbiased reporter, provide 5 relevant hashtags for a tweet about the recent important actions and key facts of this legislation.
    One hashtag should always include the bill number in the format #{{congress}}_{{bill_type}}{{bill_number}} (e.g., #118_S_2024).
    If the bill has become a public law, use the format #PL{{congress}}_{{law_number}} instead (e.g., #PL118_53).
    The other hashtags should be related to the bill's content, recent actions, or key topics.
    Do not include any party affiliations or politician names in the hashtags.
    Provide only the hashtags, separated by spaces, without any additional text or explanation.
    </Instructions>
    <Additional Details>
    Today's date is {today_date}. Current sitting President: Joe Biden
    Key action meanings:
    "Presented to President" - This means the legislation has been brought forward to the President's office but the legislation has not yet been signed or vetoed.
    "Signed by President" - This means the legislation has been signed by the president and become public law.
    </Additional Details>

    <Congress>{congress}</Congress>
    <Bill Title>{bill_title}</Bill Title>
    <Bill Number>{bill_type}{bill_number}</Bill Number>
    <Bill Text>
    {bill_text}
    </Bill Text>
    <Bill Actions>
    {bill_actions}
    </Bill Actions>
    """
    logging.info(f"Constructed hashtag prompt for bill {congress}.{bill_type}.{bill_number}")
    return prompt

def generate_tweet(prompt):
    try:
        response = model.generate_content(prompt)
        logging.info("Generated tweet content from AI model")
        return response.text
    except Exception as e:
        logging.error(f"Error generating tweet content: {str(e)}")
        raise

def generate_title(prompt):
    try:
        response = model.generate_content(prompt)
        logging.info("Generated title content from AI model")
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating title content: {str(e)}")
        raise

def generate_hashtags(prompt, congress, bill_type, bill_number):
    try:
        response = model.generate_content(prompt)
        hashtags = response.text.strip().split()
        
        # Ensure the bill number hashtag is included and in the correct format
        bill_hashtag = f"#{congress}_{bill_type}{bill_number}"
        if not any(h.upper() == bill_hashtag.upper() for h in hashtags):
            if any(h.upper().startswith("#PL") for h in hashtags):
                # If it's a public law, don't add the bill number hashtag
                pass
            else:
                hashtags.insert(0, bill_hashtag)
        
        # Limit to 4 hashtags if more are generated
        hashtags = hashtags[:4]
        
        logging.info(f"Generated hashtags for bill {congress}.{bill_type}.{bill_number}")
        return " ".join(hashtags)
    except Exception as e:
        logging.error(f"Error generating hashtags: {str(e)}")
        raise

def create_tweet_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_bills_tweets (
                bill_index INTEGER PRIMARY KEY,
                congress INTEGER,
                bill_type TEXT,
                bill_number INTEGER,
                tweet_id TEXT UNIQUE,
                tweet_body TEXT,
                tweet_body_len INTEGER,
                tweet_title TEXT,
                hashtags TEXT,
                created_date DATETIME,
                tweeted INTEGER DEFAULT 0,
                tweeted_datetime DATETIME
            )
        ''')
        conn.commit()
        logging.info("Created or confirmed existence of active_bills_tweets table")
    except sqlite3.Error as e:
        logging.error(f"Error creating tweet table: {str(e)}")
        raise

def insert_tweet(conn, congress, bill_type, bill_number, tweet_body, tweet_title, hashtags):
    try:
        cursor = conn.cursor()
        tweet_id = secrets.token_hex(4)
        created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO active_bills_tweets 
            (congress, bill_type, bill_number, tweet_id, tweet_body, tweet_body_len, tweet_title, hashtags, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (congress, bill_type, bill_number, tweet_id, tweet_body, len(tweet_body), tweet_title, hashtags, created_date))
        conn.commit()
        logging.info(f"Inserted tweet for bill {congress}.{bill_type}.{bill_number}")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error inserting tweet: {str(e)}")
        return False

def update_tweet_created(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE active_bill_list
            SET tweet_created = 1
            WHERE congress = ? AND billType = ? AND billNumber = ?
        """, (congress, bill_type, bill_number))
        conn.commit()
        logging.info(f"Updated tweet_created to 1 for bill {congress}.{bill_type}.{bill_number}")
    except sqlite3.Error as e:
        logging.error(f"Error updating tweet_created: {str(e)}")
        raise

def main():
    try:
        active_bill_data_db = os.path.join(parent_dir, 'congress_api_scraper', 'sys_db', 'active_bill_data.db')
        active_bills_tweets_db = os.path.join(script_dir, 'DB', 'active_bills_tweets.db')
        bill_text_dir = os.path.join(parent_dir, 'congress_api_scraper', 'active_bill_text_htm')

        conn_data = connect_to_db(active_bill_data_db)
        conn_tweets = connect_to_db(active_bills_tweets_db)

        create_tweet_table(conn_tweets)

        must_know_bills = get_must_know_bills(conn_data)

        for bill in must_know_bills:
            congress, bill_type, bill_number, bill_title, _ = bill
            bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)
            
            bill_file = find_bill_file(bill_text_dir, congress, bill_type, bill_number)
            bill_text = get_bill_text(bill_file)

            prompt = construct_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions)
            tweet_body = generate_tweet(prompt)
            time.sleep(5) # 5 Seconds between next API Call

            title_prompt = construct_title_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions)
            tweet_title = generate_title(title_prompt)
            time.sleep(5) # 5 Seconds between next API Call

            hashtag_prompt = construct_hashtag_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions)
            hashtags = generate_hashtags(hashtag_prompt, congress, bill_type, bill_number)

            if insert_tweet(conn_tweets, congress, bill_type, bill_number, tweet_body, tweet_title, hashtags):
                update_tweet_created(conn_data, congress, bill_type, bill_number)
                logging.info(f"Successfully processed bill {congress}.{bill_type}.{bill_number}")
            else:
                logging.warning(f"Failed to insert tweet for bill {congress}.{bill_type}.{bill_number}")

            time.sleep(30)  # Wait for 30 seconds before processing the next bill

        conn_data.close()
        conn_tweets.close()
        logging.info("Database connections closed")

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Script execution started")
    main()
    logging.info("Script execution completed")