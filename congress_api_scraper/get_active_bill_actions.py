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
ACTIVE_BILLS_DB = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "active_bill_data.db")

# Logging configuration
LOG_DIR = os.path.join(os.getcwd(), "congress_api_scraper", "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "get_active_bill_actions.log")

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
    WHERE actions_updated = 0
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
    return response.json().get("actions", [])

def action_exists(cursor, congress, bill_type, bill_number, action_code, action_date):
    cursor.execute('''
    SELECT 1 FROM bill_actions
    WHERE congress = ? AND billType = ? AND billNumber = ? AND actionCode = ? AND actionDate = ?
    ''', (congress, bill_type, bill_number, action_code, action_date))
    return cursor.fetchone() is not None

def insert_actions(actions, congress, bill_type, bill_number):
    conn = sqlite3.connect(ACTIVE_BILLS_DB)
    cursor = conn.cursor()

    inserted_count = 0
    skipped_count = 0
    error_count = 0

    for action in actions:
        action_code = action.get("actionCode", "")
        action_date = action.get("actionDate", "")
        action_text = action.get("text", "")
        action_type = action.get("type", "")

        if not action_date:
            logging.warning(f"Skipping action with missing date for {congress} {bill_type}-{bill_number}")
            error_count += 1
            continue

        if not action_exists(cursor, congress, bill_type, bill_number, action_code, action_date):
            try:
                cursor.execute('''
                INSERT INTO bill_actions (
                    congress, billType, billNumber, actionCode, actionDate, actionText, actionType
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    congress,
                    bill_type,
                    bill_number,
                    action_code,
                    action_date,
                    action_text,
                    action_type
                ))
                inserted_count += 1
            except sqlite3.IntegrityError:
                logging.warning(f"Integrity error inserting record: {congress}, {bill_type}, {bill_number}, {action_code}, {action_date}")
                error_count += 1
        else:
            skipped_count += 1

    # Update the actions_updated flag in the active_bill_list table
    cursor.execute('''
    UPDATE active_bill_list
    SET actions_updated = 1
    WHERE congress = ? AND billType = ? AND billNumber = ?
    ''', (congress, bill_type, bill_number))

    conn.commit()
    conn.close()
    logging.info(f"Inserted {inserted_count} new actions, skipped {skipped_count} existing actions, and encountered {error_count} errors for {congress} {bill_type}-{bill_number}")

def main():
    logging.info("Starting bill actions update process")
    create_database()
    active_bills = get_active_bills()
    logging.info(f"{len(active_bills)} active bills requiring updates.")
    
    for congress, bill_type, bill_number in active_bills:
        try:
            actions = fetch_bill_actions(congress, bill_type, bill_number)
            insert_actions(actions, congress, bill_type, bill_number)
            logging.info(f"Fetched and inserted actions for {congress} {bill_type}-{bill_number}")
            time.sleep(1)  # Add a delay to avoid hitting rate limits
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data for {congress} {bill_type}-{bill_number}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error processing {congress} {bill_type}-{bill_number}: {e}")

    logging.info("Completed bill actions update process")

if __name__ == "__main__":
    main()