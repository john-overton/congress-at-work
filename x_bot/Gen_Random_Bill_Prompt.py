# This script pulls a random set of text from an existing dataset
# This is version 1.4

import sqlite3
import os

# Use os.path.join to create a platform-independent path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, '..', 'congress_api_scraper', 'congress_bills.db')

print(f"Script directory: {SCRIPT_DIR}")
print(f"Database path: {DB_PATH}")
print(f"Database file exists: {os.path.exists(DB_PATH)}")
print(f"Database file is absolute path: {os.path.isabs(DB_PATH)}")
print(f"Absolute path to database: {os.path.abspath(DB_PATH)}")

def select_rand_bill_info():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
                        SELECT	
                            concat('On ',latestActiondate, ' ', type, ' ',number, ' of the ', congress, 'th Congress was ', lower(latestActionText))
                        FROM Bills 
                        ORDER BY RANDOM() LIMIT 1
                        ''')
        result = cursor.fetchone()
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


'''
# Uncomment this section to see results from script

RESULT = select_rand_bill_info()

if RESULT:
    print(RESULT[0])
else:
    print("Failed to retrieve data from the database.")
'''
