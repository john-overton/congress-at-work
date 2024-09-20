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

# Configure Logging
log_file = os.path.join(os.getcwd(), "congress_api_scraper", "Logs", "active_bill_htm_scraper.log")
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database and folder configuration
DB_NAME = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "active_bill_data.db")
OUTPUT_FOLDER = "active_bill_text_htm"

# Get the directory of the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def connect_to_db():
    db_path = os.path.join(SCRIPT_DIR, DB_NAME)
    if not os.path.exists(db_path):
        logging.error(f"Database file not found: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def get_active_bill_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT congress, billType, billNumber, latest_date, formatted_text_url FROM active_bill_urls")
    return cursor.fetchall()

def save_html_content(url, filename):
    try:
        logging.info(f"Attempting to fetch URL: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logging.info(f"Successfully saved content to {filename}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch or save URL {url}. Error: {str(e)}")
        return False

def file_exists_and_is_current(congress, billType, billNumber, latest_date):
    output_dir = os.path.join(SCRIPT_DIR, OUTPUT_FOLDER)
    formatted_latest_date = latest_date.split()[0]  # Get YYYY-MM-DD part
    for file in os.listdir(output_dir):
        parts = file.split('.')
        if len(parts) >= 5:
            if parts[0] == congress and parts[1] == billType and parts[2] == billNumber:
                file_date = parts[3]
                if file_date == formatted_latest_date:
                    return True, file
                else:
                    return False, file
    return False, None

def main():
    logging.info("Starting Active Bill HTM Scraper")
    conn = connect_to_db()
    try:
        # Ensure output folder exists
        output_dir = os.path.join(SCRIPT_DIR, OUTPUT_FOLDER)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory: {output_dir}")

        # Fetch and save new/updated HTML content
        active_bill_urls = get_active_bill_urls(conn)
        logging.info(f"Found {len(active_bill_urls)} active bills to process")
        for congress, billType, billNumber, latest_date, url in active_bill_urls:
            # Format the latest_date to be YYYY-MM-DD
            formatted_latest_date = latest_date.split()[0]
            
            is_current, existing_file = file_exists_and_is_current(congress, billType, billNumber, latest_date)
            
            if not is_current:
                if existing_file:
                    old_file_path = os.path.join(output_dir, existing_file)
                    os.remove(old_file_path)
                    logging.info(f"Deleted outdated file: {existing_file}")
                
                current_date = datetime.now().strftime("%Y-%m-%d-%H%M")
                filename = f"{congress}.{billType}.{billNumber}.{formatted_latest_date}.{current_date}.htm"
                full_path = os.path.join(output_dir, filename)
                
                if save_html_content(url, full_path):
                    logging.info(f"Saved: {filename}")
                else:
                    logging.error(f"Failed to save: {filename}")
                
                time.sleep(DELAY_BETWEEN_CALLS)
            
            else:
                logging.info(f"File is current for {congress}.{billType}.{billNumber}.{formatted_latest_date}")

    except Exception as e:
        logging.exception("An unexpected error occurred:")
    finally:
        conn.close()

    logging.info("Active Bill HTM Scraper completed")

if __name__ == "__main__":
    main()