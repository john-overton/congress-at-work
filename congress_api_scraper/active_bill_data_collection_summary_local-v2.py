import os
import sqlite3
import logging
from ollama import Client
from typing import  List, Tuple, Optional

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bill_data_collection_summary_local.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up the Ollama client
client = Client(host='http://localhost:11434')
model = 'deepseek-r1:7b'

# New: Quality control constants
MINIMUM_SUMMARY_LENGTH = 500  # characters
MAXIMUM_SUMMARY_LENGTH = 20000  # characters
REQUIRED_ELEMENTS = [
    'introduced',
    'referred to',
    'section',
    'status'
]

def connect_to_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str
        logging.info(f"Successfully connected to database: {db_path}")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database {db_path}: {str(e)}")
        raise

def get_bill_info(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title
            FROM active_bill_list
            WHERE congress = ? AND billType = ? AND billNumber = ?
        """, (congress, bill_type, bill_number))
        result = cursor.fetchone()
        if result:
            logging.info(f"Retrieved bill info for {congress}.{bill_type}.{bill_number}")
        else:
            logging.warning(f"No bill info found for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill info: {str(e)}")
        raise

def get_bill_url(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT formatted_text_url
            FROM active_bill_urls
            WHERE congress = ? AND billType = ? AND billNumber = ?
        """, (congress, bill_type, bill_number))
        result = cursor.fetchone()
        if result:
            logging.info(f"Retrieved bill URL for {congress}.{bill_type}.{bill_number}")
        else:
            logging.warning(f"No bill URL found for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill URL: {str(e)}")
        raise

def get_bill_actions(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT actionDate, actionText
            FROM bill_actions
            WHERE congress = ? AND billType = ? AND billNumber = ?
            ORDER BY actionDate
        """, (congress, bill_type, bill_number))
        result = cursor.fetchall()
        if result:
            logging.info(f"Retrieved {len(result)} bill actions for {congress}.{bill_type}.{bill_number}")
        else:
            logging.warning(f"No bill actions found for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill actions: {str(e)}")
        raise

def get_bill_text(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT previous_context, bill_text, next_context
            FROM bill_text
            WHERE congress = ? AND bill_type = ? AND bill_number = ?
        """, (congress, bill_type, bill_number))
        result = cursor.fetchone()
        if result:
            logging.info(f"Retrieved bill text for {congress}.{bill_type}.{bill_number}")
        else:
            logging.warning(f"No bill text found for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill text: {str(e)}")
        raise

def get_all_bills(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context, summary
            FROM bill_text
        """)
        result = cursor.fetchall()
        logging.info(f"Retrieved {len(result)} bills from bill_text table")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving all bills: {str(e)}")
        raise

def update_summary(conn, congress, bill_type, bill_number, text_part, summary):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bill_text
            SET summary = ?
            WHERE congress = ? AND bill_type = ? AND bill_number = ? AND text_part = ?
        """, (summary, congress, bill_type, bill_number, text_part))
        conn.commit()
        logging.info(f"Updated summary for bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
    except sqlite3.Error as e:
        logging.error(f"Error updating summary: {str(e)}")
        raise


def validate_summary(summary: str) -> Tuple[bool, str]:
    """
    Validates the generated summary against quality control metrics.
    Returns (is_valid, reason_if_invalid)
    """
    logging.debug(f"Validating summary of length {len(summary)} characters")
    if len(summary) < MINIMUM_SUMMARY_LENGTH:
        logging.debug(f"Summary validation failed: length {len(summary)} below minimum {MINIMUM_SUMMARY_LENGTH}")
        return False, f"Summary too short ({len(summary)} chars)"
    
    if len(summary) > MAXIMUM_SUMMARY_LENGTH:
        logging.debug(f"Summary validation failed: length {len(summary)} exceeds maximum {MAXIMUM_SUMMARY_LENGTH}")
        return False, f"Summary too long ({len(summary)} chars)"
        
    # Check for required content elements
    missing_elements = []
    for element in REQUIRED_ELEMENTS:
        if element.lower() not in summary.lower():
            missing_elements.append(element)
    
    if missing_elements:
        return False, f"Missing required elements: {', '.join(missing_elements)}"
    
    # Check for speculation words
    speculation_words = ['might', 'could', 'maybe', 'perhaps', 'possibly']
    found_speculation = [word for word in speculation_words if word in summary.lower()]
    if found_speculation:
        return False, f"Contains speculation words: {', '.join(found_speculation)}"
        
    return True, "Valid summary"

def construct_prompt(congress: str, bill_type: str, bill_number: str, 
                    bill_title: str, previous_context: str, bill_text: str, 
                    next_context: str, bill_actions: List, text_part: int) -> str:
    """
    Constructs a prompt using the model's defined parameters and structure.
    Includes validation for proper tag usage and content structure.
    """
    prompt = f"""<｜begin▁of▁sentence｜>
Legislative Summary Protocol:
Create a precise factual summary of the provided legislation. Include core provisions, status, and section references. Focus on text part {text_part}.

Requirements:
1 Paragraph: State the bill number, introduction date, and primary purpose
2-5 Paragraphs: Detail the main provisions with section numbers
1 Paragraph: List any economic data, statistical information, or procedural requirements
1 Paragraph: Document the current status and most recent legislative actions

Constraints:
Start immediately with bill details
Use only information from provided text
Follow chronological order
Include specific section references
Exclude speculation and external context
<｜end▁of▁sentence｜>

<｜User｜>
Legislative Document:

Congress: {congress}
Bill Title: {bill_title}
Bill Type and Number: {bill_type}{bill_number}
Text Part: {text_part}

Previous Context:
{previous_context}

Bill Text:
{bill_text}

Next Context:
{next_context}

Bill Actions:
{bill_actions}
<｜end▁of▁sentence｜>

<｜Assistant｜>"""
    
    logging.info(f"Constructed summary prompt for bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
    logging.debug(f"Prompt content: {prompt}")
    
    return prompt

def generate_content_with_retry(prompt: str, max_retries: int = 3) -> Optional[str]:
    """
    Generates content with retry logic and validation.
    Returns validated summary or None if all attempts fail.
    """
    for attempt in range(max_retries):
        try:
            response = client.generate(
                model=model,
                prompt=prompt
            )
            summary = response['response']
            
            # Validate the generated summary
            is_valid, reason = validate_summary(summary)
            if is_valid:
                logging.info(f"Generated valid summary on attempt {attempt + 1}")
                logging.debug(f"Valid summary: {summary}")
                return summary
            else:
                logging.warning(f"Generated invalid summary on attempt {attempt + 1}: {reason}")
                continue
                
        except Exception as e:
            logging.error(f"Error generating content (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise
    
    return None

def process_bill(conn_data: sqlite3.Connection, conn_text: sqlite3.Connection, 
                congress: str, bill_type: str, bill_number: str, text_part: int,
                previous_context: str, bill_text: str, next_context: str, 
                existing_summary: str) -> bool:
    """
    Enhanced bill processing with quality controls and detailed logging.
    """
    logging.debug(f"Starting to process bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
    logging.debug(f"Bill text length: {len(bill_text) if bill_text else 0} characters")
    try:
        if existing_summary:
            logging.debug(f"Existing summary found for bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
            logging.info(f"Skipping bill {congress}.{bill_type}.{bill_number}, text part: {text_part} - summary exists")
            return False

        bill_info = get_bill_info(conn_data, congress, bill_type, bill_number)
        bill_url = get_bill_url(conn_data, congress, bill_type, bill_number)
        bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)

        if not all([bill_info, bill_url, bill_actions]):
            logging.warning(f"Incomplete information for bill {congress}.{bill_type}.{bill_number}")
            return False

        bill_title = bill_info[0]
        summary_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, 
                                       previous_context, bill_text, next_context, 
                                       bill_actions, text_part)
        
        summary = generate_content_with_retry(summary_prompt)
        if summary:
            update_summary(conn_text, congress, bill_type, bill_number, text_part, summary)
            logging.info(f"Successfully processed bill {congress}.{bill_type}.{bill_number}")
            return True
        else:
            logging.error(f"Failed to generate valid summary for bill {congress}.{bill_type}.{bill_number}")
            return False

    except Exception as e:
        logging.error(f"Error processing bill {congress}.{bill_type}.{bill_number}: {str(e)}")
        return False

def main():
    try:
        active_bill_data_db = os.path.join(script_dir, 'sys_db', 'active_bill_data.db')
        active_bill_text_db = os.path.join(script_dir, 'sys_db', 'active_bill_text.db')

        conn_data = connect_to_db(active_bill_data_db)
        conn_text = connect_to_db(active_bill_text_db)

        all_bills = get_all_bills(conn_text)

        for bill in all_bills:
            congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context, existing_summary = bill

            bill_processed = process_bill(conn_data, conn_text, congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context, existing_summary)
            
            if bill_processed:
                logging.info(f"Bill processed: {congress}.{bill_type}.{bill_number}, text part: {text_part}")
            else:
                logging.info(f"Skipped bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")

        conn_data.close()
        conn_text.close()
        logging.info("Database connections closed")

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Script execution started")
    main()
    logging.info("Script execution completed")
