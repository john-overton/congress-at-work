import sqlite3
import requests
from datetime import datetime
import logging
import time
import keys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
API_BASE_URL = "https://api.congress.gov/v3/bill"
API_KEY = keys.Key_1
SOURCE_DB = "laws.db"
TARGET_DB = "bill_url_list.db"
TARGET_TABLE = "bill_urls"
DELAY_BETWEEN_CALLS = 1  # 1 second delay between API calls
RETRY_DELAY = 60  # 60 second retry delay on connection error

def create_target_table():
    try:
        conn = sqlite3.connect(TARGET_DB)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TARGET_TABLE} (
                bill_number TEXT,
                bill_type TEXT,
                congress TEXT,
                latest_date TEXT,
                formatted_text_url TEXT,
                PRIMARY KEY (bill_number, bill_type, congress)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def fetch_bill_data(congress, bill_type, bill_number):
    url = f"{API_BASE_URL}/{congress}/{bill_type}/{bill_number}/text"
    params = {
        "format": "json",
        "api_key": API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

def get_latest_formatted_text(text_versions):
    latest_date = None
    latest_url = None
    for version in text_versions:
        date = version.get('date')
        if date:
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            for format in version['formats']:
                if format['type'] == "Formatted Text":
                    if not latest_date or date > latest_date:
                        latest_date = date
                        latest_url = format['url']
    return latest_date.strftime("%Y-%m-%dT%H:%M:%SZ") if latest_date else None, latest_url

def main():
    create_target_table()

    try:
        source_conn = sqlite3.connect(SOURCE_DB)
        source_cursor = source_conn.cursor()
        target_conn = sqlite3.connect(TARGET_DB)
        target_cursor = target_conn.cursor()

        source_cursor.execute("SELECT congress_number, lower(bill_type), bill_number FROM law_list")
        for row in source_cursor.fetchall():
            congress, bill_type, bill_number = row
            bill_data = fetch_bill_data(congress, bill_type, bill_number)
            
            if bill_data and 'textVersions' in bill_data:
                latest_date, formatted_text_url = get_latest_formatted_text(bill_data['textVersions'])
                if latest_date and formatted_text_url:
                    target_cursor.execute('''
                        INSERT OR REPLACE INTO bill_urls 
                        (bill_number, bill_type, congress, latest_date, formatted_text_url)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (bill_number, bill_type, congress, latest_date, formatted_text_url))
                    target_conn.commit()
                    logging.info(f"Inserted/Updated data for bill {bill_type}{bill_number} in congress {congress}")
                else:
                    logging.warning(f"No formatted text URL found for bill {bill_type}{bill_number} in congress {congress}")
            else:
                logging.warning(f"No text versions found for bill {bill_type}{bill_number} in congress {congress}")
            
            # Add delay between API calls
            time.sleep(DELAY_BETWEEN_CALLS)

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if source_conn:
            source_conn.close()
        if target_conn:
            target_conn.close()

if __name__ == "__main__":
    main()