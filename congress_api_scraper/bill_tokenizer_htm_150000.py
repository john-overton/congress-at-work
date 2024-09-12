# This pulls data from html files in bill_text.htm folder creates a unique DB per bill html file, and splits to content of the HTML file into token chunks based on the defined size.
# This is useful for splitting up data into chunks that fit within the context window of certain LLM's
# The 150,000 token size context of this file is to allow chunks to be processed by Anthropics Claude 3.5 Sonnet which has a context of 200,000 tokens

import os
import sqlite3
import re
from bs4 import BeautifulSoup
from datetime import datetime
import nltk
nltk.download('punkt_tab')
from nltk.tokenize import word_tokenize

# constraints
token_max_size = 150000

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill_text (
            congress INTEGER,
            bill_type TEXT,
            bill_number INTEGER,
            tokenized_date TIMESTAMP,
            token_count INTEGER,
            text_part INTEGER,
            bill_text TEXT
        )
    ''')
    conn.commit()
    return conn

def parse_filename(filename):
    pattern = r'(\d+)\.(\w+)\.(\d+)\.(\d{4}-\d{2}-\d{2})\.(\d{4}-\d{2}-\d{2}-\d{4})\.htm'
    match = re.match(pattern, filename)
    if match:
        congress = int(match.group(1))
        bill_type = match.group(2)
        bill_number = int(match.group(3))
        last_action_date = datetime.strptime(match.group(4), '%Y-%m-%d')
        file_gen_date = datetime.strptime(match.group(5), '%Y-%m-%d-%H%M')
        return congress, bill_type, bill_number, last_action_date, file_gen_date
    return None, None, None, None, None

def tokenize_text(text):
    return word_tokenize(text)

def insert_tokens(conn, congress, bill_type, bill_number, tokens):
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    
    # Split tokens into chunks of 150,000 or fewer
    chunk_size = token_max_size
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i+chunk_size]
        token_count = len(chunk)
        text = ' '.join(chunk)
        text_part = i // chunk_size + 1
        
        cursor.execute('''
            INSERT INTO bill_text (congress, bill_type, bill_number, tokenized_date, token_count, text_part, bill_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (congress, bill_type, bill_number, current_time, token_count, text_part, text))
    
    conn.commit()

def process_html_file(html_path, db_path):
    congress, bill_type, bill_number, last_action_date, file_gen_date = parse_filename(os.path.basename(html_path))
    if not all((congress, bill_type, bill_number, last_action_date, file_gen_date)):
        print(f"Skipping {html_path}: Unable to parse filename")
        return

    # Check if DB exists and compare dates
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(tokenized_date) FROM bill_text")
        last_tokenized_date = cursor.fetchone()[0]
        conn.close()

        if last_tokenized_date:
            last_tokenized_date = datetime.fromisoformat(last_tokenized_date)
            if last_tokenized_date >= file_gen_date:
                print(f"Skipping {html_path}: DB is up to date")
                return
        
        # If DB exists but is outdated, delete it
        os.remove(db_path)
        print(f"Deleted outdated DB: {db_path}")

    conn = create_database(db_path)

    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        text = soup.get_text()
        tokens = tokenize_text(text)
        insert_tokens(conn, congress, bill_type, bill_number, tokens)

    conn.close()

def main():
    html_folder = 'bill_text.htm'
    db_folder = 'bill_text.db'

    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    for filename in os.listdir(html_folder):
        if filename.endswith('.htm'):
            html_path = os.path.join(html_folder, filename)
            
            # Extract only the necessary parts for the DB filename
            congress, bill_type, bill_number, _, _ = parse_filename(filename)
            if all((congress, bill_type, bill_number)):
                db_name = f"{congress}.{bill_type}.{bill_number}.db"
                db_path = os.path.join(db_folder, db_name)
                process_html_file(html_path, db_path)
                print(f"Processed {filename} -> {db_name}")
            else:
                print(f"Skipping {filename}: Unable to parse filename")

if __name__ == "__main__":
    main()