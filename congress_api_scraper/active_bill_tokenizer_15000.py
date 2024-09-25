import os
import sqlite3
import re
from datetime import datetime
import nltk
nltk.download('punkt_tab', quiet=True)
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup

# constraints
token_max_size = 15000
context_size = 500

# Define the paths relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
htm_folder = os.path.join(script_dir, 'active_bill_text_htm')
db_folder = os.path.join(script_dir, 'sys_db')
db_path = os.path.join(db_folder, 'active_bill_text.db')

def create_database():
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
            bill_text TEXT,
            previous_context TEXT,
            next_context TEXT,
            summary TEXT,
            formal_report TEXT,
            appropriations TEXT,
            most_important_facts TEXT,
            most_controversial_facts TEXT,
            prompt_text TEXT,
            prompt_response TEXT
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

def get_context(tokens, part_index, total_parts):
    prev_context = ' '.join(tokens[max(0, part_index*token_max_size - context_size):part_index*token_max_size])
    next_context = ' '.join(tokens[min((part_index+1)*token_max_size, len(tokens)):min((part_index+1)*token_max_size + context_size, len(tokens))])
    return prev_context, next_context

def insert_tokens(conn, congress, bill_type, bill_number, content):
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    
    tokens = tokenize_text(content)
    text_parts = []
    
    for i in range(0, len(tokens), token_max_size):
        text_parts.append(' '.join(tokens[i:i+token_max_size]))
    
    for i, text in enumerate(text_parts, 1):
        prev_context, next_context = get_context(tokens, i-1, len(text_parts))
        cursor.execute('''
            INSERT INTO bill_text (congress, bill_type, bill_number, tokenized_date, token_count, text_part, bill_text, previous_context, next_context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (congress, bill_type, bill_number, current_time, len(text.split()), i, text, prev_context, next_context))
    
    conn.commit()

def process_htm_file(htm_path, conn):
    congress, bill_type, bill_number, last_action_date, file_gen_date = parse_filename(os.path.basename(htm_path))
    if not all((congress, bill_type, bill_number, last_action_date, file_gen_date)):
        print(f"Skipping {htm_path}: Unable to parse filename")
        return

    cursor = conn.cursor()
    cursor.execute('''
        SELECT MAX(tokenized_date) FROM bill_text 
        WHERE congress = ? AND bill_type = ? AND bill_number = ?
    ''', (congress, bill_type, bill_number))
    last_tokenized_date = cursor.fetchone()[0]

    if last_tokenized_date:
        last_tokenized_date = datetime.fromisoformat(last_tokenized_date)
        if last_tokenized_date >= file_gen_date:
            print(f"Skipping {htm_path}: DB entry is up to date")
            return

    # Delete existing entries for this bill
    cursor.execute('''
        DELETE FROM bill_text 
        WHERE congress = ? AND bill_type = ? AND bill_number = ?
    ''', (congress, bill_type, bill_number))
    conn.commit()

    # Read the entire HTML content as a string
    with open(htm_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Extract text content from HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text()

    insert_tokens(conn, congress, bill_type, bill_number, text_content)

def main():
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        print(f"Created database folder: {db_folder}")

    conn = create_database()

    for filename in os.listdir(htm_folder):
        if filename.endswith('.htm'):
            htm_path = os.path.join(htm_folder, filename)
            process_htm_file(htm_path, conn)
            print(f"Processed {filename}")

    conn.close()

if __name__ == "__main__":
    main()