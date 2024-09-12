# This python script pull laws from congress.gov using this API: https://gpo.congress.gov/#/bill/law_list_by_congress_lawType_and_lawNumber
# This is version 1.1

import requests
import sqlite3
import time
from typing import List, Dict, Any
import logging
import json
from collections import deque
import sys
import os

# Add the adjacent 'keys' folder to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keys'))

import keys

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
API_KEY = keys.Key_1
BASE_URL = "https://api.congress.gov/v3/law"
LIMIT = 250  # Maximum allowed by the API
CONGRESS_DB = "congress.db"

# Database configuration
DB_NAME = os.path.join(os.getcwd(), "laws.db")
TABLE_NAME = "law_list"

# Trailing log setup
API_LOG_SIZE = 5
api_log = deque(maxlen=API_LOG_SIZE)

def log_api_call(url: str, params: Dict[str, Any], response: requests.Response):
    try:
        log_entry = {
            'url': url,
            'params': params,
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 200 else response.text
        }
        api_log.append(log_entry)
        
        # Write the current state of the api_log to a file
        with open('api_log.json', 'w') as f:
            json.dump(list(api_log), f, indent=2)
    except Exception as e:
        logging.error(f"Error in log_api_call: {str(e)}")

def create_database():
    # Create necessary tables if they don't exist.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        congress_number INTEGER,
        law_number TEXT,
        type TEXT,
        bill_number TEXT,
        bill_type TEXT,
        title TEXT,
        updateDate TEXT,
        originChamber TEXT,
        PRIMARY KEY (congress_number, law_number, type)
    )
    """)
    
    conn.commit()
    conn.close()

def get_congress_numbers() -> List[int]:
    # Retrieve distinct congress numbers from congress.db.
    conn = sqlite3.connect(CONGRESS_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT congress_number FROM congress_list")
    congress_numbers = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return congress_numbers

def fetch_laws(congress: int, offset: int = 0) -> List[Dict[str, Any]]:
    # Fetch laws data from the API.
    url = f"{BASE_URL}/{congress}"
    params = {
        "api_key": API_KEY,
        "format": "json",
        "offset": offset,
        "limit": LIMIT
    }
    try:
        response = requests.get(url, params=params)
        log_api_call(url, params, response)
        response.raise_for_status()
        data = response.json()
        
        if 'bills' not in data:
            logging.error(f"Unexpected API response structure: {data}")
            raise KeyError("'bills' key not found in API response")
        
        laws = []
        for bill in data['bills']:
            if isinstance(bill, dict) and 'laws' in bill:
                for law in bill['laws']:
                    if isinstance(law, dict):
                        laws.append({
                            'congress': bill.get('congress'),
                            'law_number': law.get('number'),
                            'type': law.get('type'),
                            'bill_number': bill.get('number'),
                            'bill_type': bill.get('type'),
                            'title': bill.get('title', ''),
                            'updateDate': bill.get('updateDate', ''),
                            'originChamber': bill.get('originChamber', '')
                        })
        
        return laws
    except Exception as e:
        logging.error(f"Error in fetch_laws: {str(e)}")
        raise

def insert_laws(laws: List[Dict[str, Any]]):
    # Insert laws data into the SQLite database.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for law in laws:
        try:
            cursor.execute(f"""
            INSERT OR REPLACE INTO {TABLE_NAME} (congress_number, law_number, type, bill_number, bill_type, title, updateDate, originChamber)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                law['congress'],
                law['law_number'],
                law['type'],
                law['bill_number'],
                law['bill_type'],
                law.get('title', ''),
                law.get('updateDate', ''),
                law.get('originChamber', '')
            ))
        except Exception as e:
            logging.error(f"Error inserting law: {law}. Error: {str(e)}")
    
    conn.commit()
    conn.close()

def main():
    try:
        create_database()
        congress_numbers = get_congress_numbers()
        
        for congress in congress_numbers:
            offset = 0
            while True:
                try:
                    laws = fetch_laws(congress, offset)
                    fetched_laws = len(laws)

                    if not laws:
                        break
                    
                    insert_laws(laws)
                    logging.info(f"Inserted {fetched_laws} laws for Congress {congress}, offset {offset}")
                    
                    offset += LIMIT

                    if fetched_laws < LIMIT:
                        break
                
                    time.sleep(1)  # Wait for 1 second before the next request
                except requests.exceptions.RequestException as e:
                    logging.error(f"Network error occurred while processing Congress {congress}, offset {offset}: {str(e)}")
                    time.sleep(60)  # Wait for 1 minute before retrying
                    continue
                except KeyError as e:
                    logging.error(f"Error occurred while processing Congress {congress}, offset {offset}: {str(e)}")
                    break
                except Exception as e:
                    logging.error(f"Unexpected error occurred while processing Congress {congress}, offset {offset}: {str(e)}")
                    break
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting gracefully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in main: {str(e)}")
    finally:
        logging.info("Script execution completed.")

if __name__ == "__main__":
    main()