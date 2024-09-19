# This script will create the DB active_bills_data.db and pull all activities for the current congressional period.
# EACH TIME THIS SCRIPT RUNS IT WILL TUNCATE THE ACTIVE_BILLS TABLE AND RECREATE THE WHOLE THING

import requests
import sqlite3
from datetime import datetime, timedelta
import sys
import time
import os
import logging

# Add the adjacent 'keys' folder to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keys'))

import keys

# API configuration
API_BASE_URL = "https://api.congress.gov/v3/bill"
API_KEY = keys.Key_1

# Database configuration
DB_NAME = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "active_bill_data.db")
CONGRESS_DB = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "congress.db")

# Logging configuration
LOG_DIR = os.path.join(os.getcwd(), "congress_api_scraper", "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "get_base_active_bills.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Drop the table if it exists
    cursor.execute('DROP TABLE IF EXISTS active_bill_list')
    
    cursor.execute('''
    CREATE TABLE active_bill_list (
        congress INTEGER,
        billNumber TEXT,
        billType TEXT,
        title TEXT,
        originChamber TEXT,
        originChamberCode TEXT,
        latestActionDate TEXT,
        latestActionText TEXT,
        updateDate TEXT,
        url TEXT,
        actions_updated INTEGER DEFAULT 0,
        insert_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        importance TEXT
    )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database created/reset successfully")

def get_active_congress_and_start_date():
    conn = sqlite3.connect(CONGRESS_DB)
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
    SELECT DISTINCT congress_number, session_start_date
    FROM congress_list
    WHERE session_start_date < ? AND session_end_date IS NULL
    ''', (today,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1]
    else:
        logging.error("No active congress found")
        sys.exit(1)

def fetch_bills(congress, offset=0):
    params = {
        "format": "json",
        "offset": offset,
        "limit": 250,  # Maximum allowed by the API
        "sort": "updateDate+desc",
        "api_key": API_KEY
    }

    url = f"{API_BASE_URL}/{congress}"
    response = requests.get(url, params=params)
    logging.info(f"API call {requests.get(url, params=params)} successful.")
    response.raise_for_status()
    return response.json()["bills"]

def insert_or_update_bills(bills):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for bill in bills:
        # Check if the bill already exists
        cursor.execute('''
        SELECT updateDate FROM active_bill_list
        WHERE congress = ? AND billNumber = ? AND billType = ? AND title = ? AND latestActionDate = ?
        ''', (
            bill["congress"],
            bill["number"],
            bill["type"].lower(),
            bill["title"],
            bill["latestAction"]["actionDate"]
        ))

        existing_bill = cursor.fetchone()

        if existing_bill:
            # If the existing bill is older, delete it
            if existing_bill[0] < bill["updateDate"]:
                cursor.execute('''
                DELETE FROM active_bill_list
                WHERE congress = ? AND billNumber = ? AND billType = ? AND title = ? AND latestActionDate = ?
                ''', (
                    bill["congress"],
                    bill["number"],
                    bill["type"].lower(),
                    bill["title"],
                    bill["latestAction"]["actionDate"]
                ))
            else:
                continue  # Skip this bill if it's not newer

        # Insert the new or updated bill
        cursor.execute('''
        INSERT INTO active_bill_list (
            congress, billNumber, billType, title, originChamber, originChamberCode,
            latestActionDate, latestActionText, updateDate, url, actions_updated, insert_date, importance
        ) VALUES (?, ?, lower(?), ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, NULL)
        ''', (
            bill["congress"],
            bill["number"],
            bill["type"],
            bill["title"],
            bill["originChamber"],
            bill["originChamberCode"],
            bill["latestAction"]["actionDate"],
            bill["latestAction"]["text"],
            bill["updateDate"],
            bill["url"]
        ))

    conn.commit()
    conn.close()

def main():
    logging.info("Starting bill update process")
    create_database()
    total_bills = 0
    offset = 0
    active_congress, session_start_date = get_active_congress_and_start_date()
    logging.info(f"Active Congress: {active_congress}, Session Start Date: {session_start_date}")

    session_start_datetime = datetime.strptime(session_start_date, "%Y-%m-%d")

    while True:
        try:
            bills = fetch_bills(active_congress, offset)
            if not bills:
                break

            # Check if the oldest bill in this batch is older than the session start date
            oldest_bill_date = datetime.strptime(bills[-1]["updateDate"], "%Y-%m-%d").replace(tzinfo=None)
            if oldest_bill_date < session_start_datetime:
                logging.info("Reached bills older than the session start date. Stopping the process.")
                break

            insert_or_update_bills(bills)
            total_bills += len(bills)
            offset += len(bills)

            logging.info(f"Fetched and processed {len(bills)} bills. Total: {total_bills}")

            if len(bills) < 250:  # If we get less than the maximum, we've reached the end
                break

            time.sleep(1)  # Add a delay to avoid hitting rate limits

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            break

    logging.info(f"Completed. Total bills fetched and processed: {total_bills}")

if __name__ == "__main__":
    main()