# This script pulls a random set of text from an existing dataset
# This is version 1.0

import sqlite3

DB_NAME = "congress_bills.db"

def select_rand_bill_info():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
                    SELECT	
                        concat('On ',latestActiondate, ' ', type, ' ',number, ' of the ', congress, 'th Congress was ', lower(latestActionText))
                    FROM Bills 
                    ORDER BY RANDOM() LIMIT 1
                    ''')
    return cursor.fetchone()

RESULT = select_rand_bill_info()

# To test live in your terminal uncomment the code below
#print(RESULT[0])