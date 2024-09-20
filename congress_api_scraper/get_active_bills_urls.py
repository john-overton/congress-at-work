import os
import sqlite3
import requests
from datetime import datetime
import logging
import time
import sys

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
parent_dir = os.path.dirname(script_dir)

# Construct the path to the keys.py file
keys_path = os.path.join(parent_dir, 'keys', 'keys.py')

# Add the directory containing keys.py to sys.path
sys.path.append(os.path.dirname(keys_path))

# Import the Key_1 from keys.py
from keys import Key_1

# Set up logging
log_dir = os.path.join(script_dir, "Logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, "active_bill_urls.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
API_BASE_URL = "https://api.congress.gov/v3/bill"
API_KEY = Key_1
DB_PATH = os.path.join(script_dir, "sys_db", "active_bill_data.db")
DELAY_BETWEEN_CALLS = 1  # 1 second delay between API calls

def create_target_table():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_bill_urls (
                congress INTEGER,
                billNumber INTEGER,
                billType TEXT,
                latest_date DATETIME,
                formatted_text_url TEXT,
                formatted_xml_url TEXT,
                pdf_url TEXT,
                insert_date DATETIME,
                PRIMARY KEY (congress, billNumber, billType)
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
        if response.status_code == 200:
            logging.info(f"API call {url} status: {response.status_code}, successful!")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None

def get_latest_formatted_urls(text_versions):
    latest_date = None
    latest_urls = {
        "formatted_text_url": None,
        "formatted_xml_url": None,
        "pdf_url": None
    }
    for version in text_versions:
        date = version.get('date')
        if date:
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            if not latest_date or date > latest_date:
                latest_date = date
                for format in version['formats']:
                    if format['type'] == 'Formatted Text':
                        latest_urls['formatted_text_url'] = format['url']
                    elif format['type'] == 'Formatted XML':
                        latest_urls['formatted_xml_url'] = format['url']
                    elif format['type'] == 'PDF':
                        latest_urls['pdf_url'] = format['url']
    
    return latest_date.strftime("%Y-%m-%d %H:%M:%S") if latest_date else None, latest_urls

def update_active_bill_urls():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT a.congress, a.billNumber, a.billType, a.latestActionDate, 
                   u.latest_date, u.insert_date
            FROM active_bill_list a
            LEFT JOIN active_bill_urls u
            ON a.congress = u.congress AND a.billNumber = u.billNumber AND a.billType = u.billType
        """)
        
        for row in cursor.fetchall():
            congress, bill_number, bill_type, latest_action_date, existing_latest_date, existing_insert_date = row
            
            should_update = False
            if existing_insert_date is None:
                should_update = True
            else:
                latest_action_date = datetime.strptime(latest_action_date, "%Y-%m-%d")
                existing_insert_date = datetime.strptime(existing_insert_date, "%Y-%m-%d %H:%M:%S")
                if latest_action_date > existing_insert_date:
                    should_update = True
                else:
                    logging.info(f"Skipping bill {congress}.{bill_type}.{bill_number}. Latest text already pulled.")
            if should_update:
                # Delete existing row if it's outdated
                if existing_insert_date is not None:
                    cursor.execute("""
                        DELETE FROM active_bill_urls
                        WHERE congress = ? AND billNumber = ? AND billType = ?
                    """, (congress, bill_number, bill_type.lower()))
                
                bill_data = fetch_bill_data(congress, bill_type.lower(), bill_number)
                
                if bill_data and 'textVersions' in bill_data:
                    latest_date, latest_urls = get_latest_formatted_urls(bill_data['textVersions'])
                    if latest_date:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute('''
                            INSERT INTO active_bill_urls 
                            (congress, billNumber, billType, latest_date, formatted_text_url, formatted_xml_url, pdf_url, insert_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (congress, bill_number, bill_type.lower(), latest_date, 
                              latest_urls["formatted_text_url"], 
                              latest_urls["formatted_xml_url"], 
                              latest_urls["pdf_url"],
                              current_time))
                        conn.commit()
                        logging.info(f"Updated data for bill {bill_type}{bill_number} in congress {congress}")
                        time.sleep(DELAY_BETWEEN_CALLS)
                    else:
                        logging.warning(f"No formatted URLs found for bill {bill_type}{bill_number} in congress {congress}")
                        time.sleep(DELAY_BETWEEN_CALLS)
                else:
                    logging.warning(f"No text versions found for bill {bill_type}{bill_number} in congress {congress}")
                    time.sleep(DELAY_BETWEEN_CALLS)            

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def main():
    create_target_table()
    update_active_bill_urls()

if __name__ == "__main__":
    main()