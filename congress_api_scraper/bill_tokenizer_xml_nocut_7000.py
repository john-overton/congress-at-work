import os
import sqlite3
import re
from datetime import datetime
import nltk
nltk.download('punkt', quiet=True)
from nltk.tokenize import word_tokenize
from xml.etree import ElementTree as ET

# constraints
token_max_size = 7000

# Define the paths relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
xml_folder = os.path.join(script_dir, 'bill_text.xml')
db_folder = os.path.join(script_dir, 'bill_text.db')

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
            bill_text TEXT,
            prompt_text TEXT,
            prompt_response TEXT
        )
    ''')
    conn.commit()
    return conn

def parse_filename(filename):
    pattern = r'(\d+)\.(\w+)\.(\d+)\.(\d{4}-\d{2}-\d{2})\.(\d{4}-\d{2}-\d{2}-\d{4})\.xml'
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

def insert_tokens(conn, congress, bill_type, bill_number, content_blocks):
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    
    text_part = 1
    current_tokens = []
    
    for block in content_blocks:
        block_tokens = tokenize_text(block['text'])
        
        if len(current_tokens) + len(block_tokens) > token_max_size:
            # Insert the current tokens
            text = ' '.join(current_tokens)
            cursor.execute('''
                INSERT INTO bill_text (congress, bill_type, bill_number, tokenized_date, token_count, text_part, bill_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (congress, bill_type, bill_number, current_time, len(current_tokens), text_part, text))
            
            text_part += 1
            current_tokens = block_tokens
        else:
            current_tokens.extend(block_tokens)
        
        # Add closing tag if present
        if block['closing_tag']:
            current_tokens.extend(tokenize_text(block['closing_tag']))
    
    # Insert any remaining tokens
    if current_tokens:
        text = ' '.join(current_tokens)
        cursor.execute('''
            INSERT INTO bill_text (congress, bill_type, bill_number, tokenized_date, token_count, text_part, bill_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (congress, bill_type, bill_number, current_time, len(current_tokens), text_part, text))
    
    conn.commit()

def process_xml_file(xml_path, db_path):
    congress, bill_type, bill_number, last_action_date, file_gen_date = parse_filename(os.path.basename(xml_path))
    if not all((congress, bill_type, bill_number, last_action_date, file_gen_date)):
        print(f"Skipping {xml_path}: Unable to parse filename")
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
                print(f"Skipping {xml_path}: DB is up to date")
                return
        
        # If DB exists but is outdated, delete it
        os.remove(db_path)
        print(f"Deleted outdated DB: {db_path}")

    conn = create_database(db_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    content_blocks = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            content_blocks.append({'text': elem.text.strip(), 'closing_tag': f'</{elem.tag}>'})
        if elem.tail and elem.tail.strip():
            content_blocks.append({'text': elem.tail.strip(), 'closing_tag': None})

    insert_tokens(conn, congress, bill_type, bill_number, content_blocks)

    conn.close()

def main():
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        print(f"Created database folder: {db_folder}")

    for filename in os.listdir(xml_folder):
        if filename.endswith('.xml'):
            xml_path = os.path.join(xml_folder, filename)
            
            # Extract only the necessary parts for the DB filename
            congress, bill_type, bill_number, _, _ = parse_filename(filename)
            if all((congress, bill_type, bill_number)):
                db_name = f"{congress}.{bill_type}.{bill_number}.xml.db"
                db_path = os.path.join(db_folder, db_name)
                process_xml_file(xml_path, db_path)
                print(f"Processed {filename} -> {db_path}")
            else:
                print(f"Skipping {filename}: Unable to parse filename")

if __name__ == "__main__":
    main()