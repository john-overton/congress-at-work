# This python script pulls the latest HTML bill text based on the bill_url_list.db data.
# It does this by getting the bill URL text, comparing the db action dates against the date of existing files, and then scrapes the URL if data is new.

import os
import sqlite3
from datetime import datetime
import requests
from pathlib import Path
import logging
import time
import sys

# Delay constants
DELAY_BETWEEN_CALLS = 1  # 1 second delay between API calls
RETRY_DELAY = 60  # 60 second retry delay on connection error

# Configure Loggins
log_file = os.path.join(os.getcwd(), "congress_api_scraper", "Logs", "add_update_bill_text.log")
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database and folder configuration
DB_NAME = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "bill_url_list.db")
OUTPUT_FOLDER = "bill_text_htm"

# Get the directory of the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def connect_to_db():
    db_path = os.path.join(SCRIPT_DIR, DB_NAME)
    if not os.path.exists(db_path):
        logging.error(f"Database file not found: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def get_bill_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT congress, bill_type, bill_number, latest_date, formatted_text_url FROM bill_urls")
    return cursor.fetchall()

def save_html_content(url, filename):
    try:
        logging.info(f"Attempting to fetch URL: {url}")
        response = requests.get(url, timeout=30)  # Add a timeout
        response.raise_for_status()  # Raise an exception for bad status codes
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logging.info(f"Successfully saved content to {filename}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch or save URL {url}. Error: {str(e)}")
        return False

def delete_outdated_files(conn):
    cursor = conn.cursor()
    output_dir = os.path.join(SCRIPT_DIR, OUTPUT_FOLDER)
    files = os.listdir(output_dir)
    for file in files:
        parts = file.split('.')
        if len(parts) >= 5:
            congress, bill_type, bill_number, file_date = parts[:4]
            cursor.execute("""
                SELECT latest_date FROM bill_urls 
                WHERE congress = ? AND bill_type = ? AND bill_number = ?
            """, (congress, bill_type, bill_number))
            result = cursor.fetchone()
            if result:
                db_date = datetime.strptime(result[0], "%Y-%m-%dT%H:%M:%SZ").date()
                file_date = datetime.strptime(file_date, "%Y-%m-%d").date()
                if db_date > file_date:
                    os.remove(os.path.join(output_dir, file))
                    logging.info(f"Deleted outdated file: {file}")

def file_exists(congress, bill_type, bill_number, formatted_date):
    output_dir = os.path.join(SCRIPT_DIR, OUTPUT_FOLDER)
    for file in os.listdir(output_dir):
        parts = file.split('.')
        if len(parts) >= 5:
            if parts[0] == congress and parts[1] == bill_type and parts[2] == bill_number and parts[3] == formatted_date:
                return True
    return False

def main():
    logging.info("Starting HTM Bill Scraper")
    conn = connect_to_db()
    try:
        # Ensure output folder exists
        output_dir = os.path.join(SCRIPT_DIR, OUTPUT_FOLDER)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory: {output_dir}")

        # Delete outdated files
        delete_outdated_files(conn)

        # Fetch and save new/updated HTML content
        bill_urls = get_bill_urls(conn)
        logging.info(f"Found {len(bill_urls)} bills to process")
        for congress, bill_type, bill_number, latest_date, url in bill_urls:
            formatted_date = datetime.strptime(latest_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            
            if not file_exists(congress, bill_type, bill_number, formatted_date):
                current_date = datetime.now().strftime("%Y-%m-%d-%H%M")
                filename = f"{congress}.{bill_type}.{bill_number}.{formatted_date}.{current_date}.htm"
                full_path = os.path.join(output_dir, filename)
                
                if save_html_content(url, full_path):
                    logging.info(f"Saved: {filename}")
                else:
                    logging.error(f"Failed to save: {filename}")
                
                time.sleep(DELAY_BETWEEN_CALLS)
            
            else:
                logging.info(f"File already exists for {congress}.{bill_type}.{bill_number}.{formatted_date}")

    except Exception as e:
        logging.exception("An unexpected error occurred:")
    finally:
        conn.close()

    logging.info("HTM Bill Scraper completed")

if __name__ == "__main__":
    main()