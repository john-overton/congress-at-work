#This pulls bills from the bills API located here: https://gpo.congress.gov/#/bill/bill_list_all and places data into the congress_bills.db
#This is version 1.2

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
DB_NAME = os.path.join(os.getcwd(), "congress_api_scraper", "sys_db", "recent_bill_updates.db")

# Logging configuration
LOG_DIR = os.path.join(os.getcwd(), "congress_api_scraper", "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "get_bill_updates.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Drop the table if it exists
    cursor.execute('DROP TABLE IF EXISTS bills')
    
    cursor.execute('''
    CREATE TABLE bills (
        congress INTEGER,
        number TEXT,
        type TEXT,
        title TEXT,
        originChamber TEXT,
        originChamberCode TEXT,
        latestActionDate TEXT,
        latestActionText TEXT,
        updateDate TEXT,
        url TEXT
    )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database created/reset successfully")

def fetch_bills(offset=0):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    params = {
        "format": "json",
        "offset": offset,
        "limit": 250,  # Maximum allowed by the API
        "fromDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toDateTime": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "updateDate+desc",
        "api_key": API_KEY
    }

    response = requests.get(API_BASE_URL, params=params)
    logging.info(f"API call {requests.get(API_BASE_URL, params=params)} successfull.")
    response.raise_for_status()
    return response.json()["bills"]

def insert_bills(bills):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for bill in bills:
        cursor.execute('''
        INSERT INTO bills (
            congress, number, type, title, originChamber, originChamberCode,
            latestActionDate, latestActionText, updateDate, url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

def check_data_age():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    cursor.execute('''
    SELECT COUNT(*) FROM bills
    WHERE latestActionDate < ?
    ''', (thirty_days_ago,))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

def main():
    logging.info("Starting bill update process")
    create_database()
    total_bills = 0
    offset = 0

    while True:
        try:
            bills = fetch_bills(offset)
            if not bills:
                break

            insert_bills(bills)
            total_bills += len(bills)
            offset += len(bills)

            logging.info(f"Fetched and inserted {len(bills)} bills. Total: {total_bills}")

            if check_data_age():
                logging.info("Detected data older than 30 days. Stopping the process.")
                break

            if len(bills) < 250:  # If we get less than the maximum, we've reached the end
                break

            time.sleep(1)  # Add a delay to avoid hitting rate limits

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")
            break

    logging.info(f"Completed. Total bills fetched and stored: {total_bills}")

if __name__ == "__main__":
    main()