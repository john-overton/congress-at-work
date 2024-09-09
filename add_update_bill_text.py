# This python script pulls the latest HTML bill text based on the bill_url_list.db data.
# It does this by getting the bill URL text, comparing the db action dates against the date of existing files, and then scrapes the URL if data is new.

import os
import sqlite3
from datetime import datetime
import requests
from pathlib import Path

# Database and folder configuration
DB_NAME = "bill_url_list.db"
OUTPUT_FOLDER = "bill_text.htm"

def connect_to_db():
    return sqlite3.connect(DB_NAME)

def get_bill_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT congress, bill_type, bill_number, latest_date, formatted_text_url FROM bill_urls")
    return cursor.fetchall()

def save_html_content(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return True
    return False

def delete_outdated_files(conn):
    cursor = conn.cursor()
    files = os.listdir(OUTPUT_FOLDER)
    for file in files:
        parts = file.split('.')
        if len(parts) >= 5:
            congress, bill_type, bill_number, file_date = parts[:4]
            cursor.execute("""
                SELECT latest_date FROM bill_urls 
                WHERE congress = ? AND bill_type = ? AND bill_number = ?
            """, (congress, bill_type, bill_number))
            result = cursor.fetchone()
            if result:
                db_date = datetime.strptime(result[0], "%Y-%m-%dT%H:%M:%SZ").date()
                file_date = datetime.strptime(file_date, "%Y-%m-%d").date()
                if db_date > file_date:
                    os.remove(os.path.join(OUTPUT_FOLDER, file))
                    print(f"Deleted outdated file: {file}")

def file_exists(congress, bill_type, bill_number, formatted_date):
    for file in os.listdir(OUTPUT_FOLDER):
        parts = file.split('.')
        if len(parts) >= 5:
            if parts[0] == congress and parts[1] == bill_type and parts[2] == bill_number and parts[3] == formatted_date:
                return True
    return False

def main():
    conn = connect_to_db()
    try:
        # Ensure output folder exists
        Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

        # Delete outdated files
        delete_outdated_files(conn)

        # Fetch and save new/updated HTML content
        bill_urls = get_bill_urls(conn)
        for congress, bill_type, bill_number, latest_date, url in bill_urls:
            formatted_date = datetime.strptime(latest_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            
            if not file_exists(congress, bill_type, bill_number, formatted_date):
                current_date = datetime.now().strftime("%Y-%m-%d-%H%M")
                filename = f"{congress}.{bill_type}.{bill_number}.{formatted_date}.{current_date}.htm"
                full_path = os.path.join(OUTPUT_FOLDER, filename)
                
                if save_html_content(url, full_path):
                    print(f"Saved: {filename}")
                else:
                    print(f"Failed to save: {filename}")
            else:
                print(f"File already exists for {congress}.{bill_type}.{bill_number}.{formatted_date}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()