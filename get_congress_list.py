import requests
import sqlite3
import time
import keys
import re

# API configuration
API_BASE_URL = "https://api.congress.gov/v3/congress"
API_KEY = keys.Key_1
FORMAT = "json"
LIMIT = 250

# Database configuration
DB_NAME = "congress.db"
TABLE_NAME = "congress_list"

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        congress_number INTEGER,
        congress_name TEXT,
        start_year INTEGER,
        end_year INTEGER,
        session_number INTEGER,
        session_chamber TEXT,
        session_start_date TEXT,
        session_end_date TEXT,
        session_type TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def fetch_data(offset):
    params = {
        "api_key": API_KEY,
        "format": FORMAT,
        "offset": offset,
        "limit": LIMIT
    }
    
    response = requests.get(API_BASE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def extract_congress_number(congress_name):
    match = re.search(r'(\d+)', congress_name)
    if match:
        return int(match.group(1))
    return None

def insert_data(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for congress in data["congresses"]:
        for session in congress["sessions"]:
            cursor.execute(f"""
            INSERT INTO {TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                extract_congress_number(congress_name=congress["name"]),
                congress["name"],
                int(congress["startYear"]),
                int(congress["endYear"]),
                session.get("number", None), # Use None if number is not present
                session["chamber"],
                session["startDate"],
                session.get("endDate", None),  # Use None if endDate is not present
                session["type"]
            ))
    
    conn.commit()
    conn.close()

def main():
    create_database()
    offset = 0
    total_records = 0
    
    while True:
        print(f"Fetching data with offset {offset}...")
        data = fetch_data(offset)
        
        if data is None or not data["congresses"]:
            break
        
        insert_data(data)
        
        records_fetched = len(data["congresses"])
        total_records += records_fetched
        print(f"Inserted {records_fetched} records. Total records: {total_records}")
        
        if records_fetched < LIMIT:
            break
        
        offset += LIMIT
        time.sleep(1)  # Wait for 1 second before the next request
    
    print(f"Data collection complete. Total records inserted: {total_records}")

if __name__ == "__main__":
    main()