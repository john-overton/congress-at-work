import requests
import sqlite3
import logging
import os
import sys
import time
from datetime import datetime

# Add the adjacent 'keys' folder to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keys'))

import keys

# API configuration
API_BASE_URL = "https://api.congress.gov/v3/bill"
API_KEY = keys.Key_1

# Database configuration
# DB_NAME = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "Bill_Data.db")
ACTIVE_BILLS_DB = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "active_bill_data.db")

# Logging configuration
LOG_DIR = os.path.join(os.getcwd(), "congress_api_scraper", "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "get_bill_actions.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_database():
    conn = sqlite3.connect(ACTIVE_BILLS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bill_actions (
        congress INTEGER,
        billType TEXT,
        billNumber INTEGER,
        actionCode TEXT,
        actionDate DATE,
        actionText TEXT,
        actionType TEXT,
        PRIMARY KEY (congress, billType, billNumber, actionCode, actionDate)
    )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database created/checked successfully")

def get_active_bills():
    conn = sqlite3.connect(ACTIVE_BILLS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT congress, LOWER(billType), billNumber
    FROM active_bill_list
    ORDER BY congress DESC
    ''')
    
    bills = cursor.fetchall()
    conn.close()
    return bills

def fetch_bill_actions(congress, bill_type, bill_number):
    params = {
        "format": "json",
        "api_key": API_KEY
    }

    url = f"{API_BASE_URL}/{congress}/{bill_type}/{bill_number}/actions"
    response = requests.get(url, params=params)
    logging.info(f"API call to {url} successful.")
    response.raise_for_status()
    return response.json()["actions"]

def insert_actions(actions, congress, bill_type, bill_number):
    conn = sqlite3.connect(ACTIVE_BILLS_DB)
    cursor = conn.cursor()

    for action in actions:
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO bill_actions (
                congress, billType, billNumber, actionCode, actionDate, actionText, actionType
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                congress,
                bill_type,
                bill_number,
                action.get("actionCode", ""),
                action["actionDate"],
                action["text"],
                action["type"]
            ))
        except sqlite3.IntegrityError:
            logging.info(f"Skipping duplicate record: {congress}, {bill_type}, {bill_number}, {action.get('actionCode', '')}, {action['actionDate']}")

    conn.commit()
    conn.close()

def main():
    logging.info("Starting bill actions update process")
    create_database()
    active_bills = get_active_bills()
    
    for congress, bill_type, bill_number in active_bills:
        try:
            actions = fetch_bill_actions(congress, bill_type, bill_number)
            insert_actions(actions, congress, bill_type, bill_number)
            logging.info(f"Fetched and inserted actions for {congress} {bill_type}-{bill_number}")
            time.sleep(1)  # Add a delay to avoid hitting rate limits
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data for {congress} {bill_type}-{bill_number}: {e}")

    logging.info("Completed bill actions update process")

if __name__ == "__main__":
    main()