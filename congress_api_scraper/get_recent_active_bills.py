# This script functions similar to the get_active_bills_base.py
# EACH TIME THIS SCRIPT RUNS IT WILL PULL UPDATES FROM THE LAST 4 DAYS AND INSERT OR UPDATE THEM

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
LOG_FILE = os.path.join(LOG_DIR, "get_recent_active_bills.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_bill_list (
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
        importance TEXT,
        PRIMARY KEY (congress, billNumber, billType)
    )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database structure ensured")

def get_active_congress():
    conn = sqlite3.connect(CONGRESS_DB)
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
    SELECT DISTINCT congress_number
    FROM congress_list
    WHERE session_start_date < ? AND session_end_date IS NULL
    ''', (today,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    else:
        logging.error("No active congress found")
        sys.exit(1)

def fetch_bills(congress, offset=0):
    four_days_ago = datetime.now() - timedelta(days=4)
    now = datetime.now()
    params = {
        "format": "json",
        "offset": offset,
        "limit": 250,  # Maximum allowed by the API
        "fromDateTime": four_days_ago.strftime("%Y-%m-%dT00:00:00Z"),
        "toDateTime": now.strftime("%Y-%m-%dT00:00:00Z"),
        "sort": "updateDate+desc",
        "api_key": API_KEY
    }

    url = f"{API_BASE_URL}/{congress}"
    response = requests.get(url, params=params)
    logging.info(f"API call {url} successful.")
    response.raise_for_status()
    return response.json()["bills"]

def insert_or_update_bills(bills):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    updated_count = 0
    inserted_count = 0
    for bill in bills:
        # Check if the bill already exists
        cursor.execute('''
        SELECT latestActionDate FROM active_bill_list
        WHERE congress = ? AND billNumber = ? AND billType = ?
        ''', (
            bill["congress"],
            bill["number"],
            bill["type"].lower()
        ))

        existing_bill = cursor.fetchone()

        if existing_bill:
            # Update the existing record if the new latestActionDate is more recent
            if existing_bill[0] < bill["latestAction"]["actionDate"]:
                cursor.execute('''
                UPDATE active_bill_list SET
                title = ?, originChamber = ?, originChamberCode = ?, latestActionDate = ?, 
                latestActionText = ?, updateDate = ?, url = ?, 
                actions_updated = 0, importance = NULL, insert_date = CURRENT_TIMESTAMP, tweet_created = 0
                WHERE congress = ? AND billNumber = ? AND billType = ?
                ''', (
                    bill["title"],
                    bill["originChamber"],
                    bill["originChamberCode"],
                    bill["latestAction"]["actionDate"],
                    bill["latestAction"]["text"],
                    bill["updateDate"],
                    bill["url"],
                    bill["congress"],
                    bill["number"],
                    bill["type"].lower()
                ))
                updated_count += 1
        else:
            # Insert the new bill
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
            inserted_count += 1

    conn.commit()
    conn.close()
    return updated_count, inserted_count

def main():
    logging.info("Starting recent bill update process")
    ensure_database()
    total_bills = 0
    total_updated = 0
    total_inserted = 0
    offset = 0
    active_congress = get_active_congress()
    logging.info(f"Active Congress: {active_congress}")

    while True:
        try:
            bills = fetch_bills(active_congress, offset)
            if not bills:
                break

            updated_count, inserted_count = insert_or_update_bills(bills)
            total_updated += updated_count
            total_inserted += inserted_count
            total_bills += len(bills)
            offset += len(bills)

            logging.info(f"Fetched {len(bills)} bills, updated {updated_count}, inserted {inserted_count}. Total processed: {total_bills}")

            if len(bills) < 250:  # If we get less than the maximum, we've reached the end
                break

            time.sleep(1)  # Add a delay to avoid hitting rate limits

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            break

    logging.info(f"Completed. Total bills processed: {total_bills}, updated: {total_updated}, inserted: {total_inserted}")

if __name__ == "__main__":
    main()