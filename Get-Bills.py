#hello world.  This is a file!
#Adding a new line to see what happens

import requests
import sqlite3
from datetime import datetime, timedelta
import time
import keys

# API configuration
API_BASE_URL = "https://api.congress.gov/v3/bill"
API_KEY = keys.Key_1

# Database configuration
DB_NAME = "congress_bills.db"

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bills (
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

def fetch_bills(offset=0, limit=100):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)  # Fetch bills from the last 30 days

    params = {
        "format": "json",
        "offset": offset,
        "limit": limit,
        "fromDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toDateTime": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "updateDate+desc",
        "api_key": API_KEY
    }

    response = requests.get(API_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()["bills"]

def insert_bills(bills):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for bill in bills:
        cursor.execute('''
        INSERT OR REPLACE INTO bills (
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

def main():
    create_database()
    total_bills = 0
    offset = 0
    limit = 100

    while total_bills < 100:
        try:
            bills = fetch_bills(offset, limit)
            if not bills:
                break

            insert_bills(bills)
            total_bills += len(bills)
            offset += limit

            print(f"Fetched and inserted {len(bills)} bills. Total: {total_bills}")

            if len(bills) < limit:
                break

            time.sleep(1)  # Add a delay to avoid hitting rate limits

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break

    print(f"Completed. Total bills fetched and stored: {total_bills}")

if __name__ == "__main__":
    main()