import os
import sqlite3
import datetime
import logging
import re
from ollama import Client

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bill_importance_collection_local.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up the Ollama client
client = Client(host='http://localhost:10001')
model = 'llama3.1:8b-instruct-q8_0'

# Compile the regex pattern
MUST_KNOW_PATTERN = re.compile(r'\b(President|Public Law)\b', re.IGNORECASE)

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
            SELECT title, importance, latestActionText
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

def get_bill_text_parts_with_summaries(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT text_part, summary
            FROM bill_text
            WHERE congress = ? AND bill_type = ? AND bill_number = ? AND summary IS NOT NULL AND summary != ''
            ORDER BY text_part
        """, (congress, bill_type, bill_number))
        result = cursor.fetchall()
        if result:
            logging.info(f"Retrieved {len(result)} bill text parts with summaries for {congress}.{bill_type}.{bill_number}")
        else:
            logging.warning(f"No bill text parts with summaries found for {congress}.{bill_type}.{bill_number}")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill text parts with summaries: {str(e)}")
        raise

def get_bills_needing_importance(conn_data, conn_text):
    try:
        cursor_data = conn_data.cursor()
        cursor_text = conn_text.cursor()
        
        logging.info("Querying bill_text for bills with summaries")
        cursor_text.execute("""
            SELECT DISTINCT congress, bill_type, bill_number
            FROM bill_text
            WHERE summary IS NOT NULL AND summary != ''
        """)
        bills_with_summaries = cursor_text.fetchall()
        logging.info(f"Found {len(bills_with_summaries)} bills with summaries")
        
        if not bills_with_summaries:
            logging.warning("No bills found with summaries")
            return []
        
        # Log a sample of bills with summaries
        sample_bills = bills_with_summaries[:5]
        logging.info(f"Sample bills with summaries: {sample_bills}")
        
        # Prepare the query to find bills needing importance ratings
        placeholders = ','.join(['(?,?,?)' for _ in bills_with_summaries])
        query = f"""
            SELECT congress, billType, billNumber
            FROM active_bill_list
            WHERE (congress, billType, billNumber) IN ({placeholders})
            AND (importance IS NULL OR importance = '')
        """
        
        # Flatten the list of tuples for the query parameters
        params = [item for sublist in bills_with_summaries for item in sublist]
        
        logging.info("Querying active_bill_list for bills needing importance ratings")
        cursor_data.execute(query, params)
        bills_needing_importance = cursor_data.fetchall()
        
        logging.info(f"Found {len(bills_needing_importance)} bills needing importance ratings")
        
        if not bills_needing_importance:
            logging.warning("No bills found that need importance ratings")
        else:
            # Log a sample of bills needing importance ratings
            sample_bills = bills_needing_importance[:5]
            logging.info(f"Sample bills needing importance ratings: {sample_bills}")
        
        return bills_needing_importance
    
    except sqlite3.Error as e:
        logging.error(f"SQLite error in get_bills_needing_importance: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in get_bills_needing_importance: {str(e)}")
        raise

def update_importance(conn, congress, bill_type, bill_number, importance):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE active_bill_list
            SET importance = ?
            WHERE congress = ? AND billType = ? AND billNumber = ?
        """, (importance, congress, bill_type, bill_number))
        conn.commit()
        logging.info(f"Updated importance for bill {congress}.{bill_type}.{bill_number}")
    except sqlite3.Error as e:
        logging.error(f"Error updating importance: {str(e)}")
        raise

def construct_prompt(congress, bill_type, bill_number, bill_title, bill_text_parts, bill_actions):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    bill_summaries = "\n".join([f"Part {part}: {summary}" for part, summary in bill_text_parts])
    actions_text = "\n".join([f"{date}: {action}" for date, action in bill_actions])
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Today Date: {today_date}
You are a helpful assistant tasked with providing a concise assessment of legislative importance. 
Your response should be a single word chosen from "Must Know", "Important", or "Minimal". 
This assessment should be based on the bill's potential impact on the nation and society, considering its full context and any controversial aspects from an unbiased perspective. 
Information about the current Congress, bill number, title, bill summaries, and actions will be provided. 
Note that any bill actions involving the President are always categorized as "Must Know".
Do not provide any additional context or explanation beyond the single-word response.<|eot_id|>

<|start_header_id|>user<|end_header_id|>
Please assess the importance of the following bill:

<Congress>{congress}</Congress>
<Bill Title>{bill_title}</Bill Title>
<Bill Number>{bill_type}{bill_number}</Bill Number>
<Bill Summaries>
{bill_summaries}
</Bill Summaries>
<Bill Actions>
{actions_text}
</Bill Actions>

Respond with only one word: "Must Know", "Important", or "Minimal".<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>"""
    logging.info(f"Constructed importance prompt for bill {congress}.{bill_type}.{bill_number}")
    return prompt

def generate_content(prompt):
    try:
        response = client.generate(
            model=model,
            prompt=prompt
        )
        logging.info("Generated content from local LLM")
        return response['response'].strip()
    except Exception as e:
        logging.error(f"Error generating content: {str(e)}")
        raise

def process_bill(conn_data, conn_text, congress, bill_type, bill_number):
    try:
        bill_info = get_bill_info(conn_data, congress, bill_type, bill_number)
        if not bill_info:
            logging.warning(f"No bill info found for {congress}.{bill_type}.{bill_number}. Skipping.")
            return False

        bill_title, existing_importance, latest_action_text = bill_info

        if existing_importance:
            logging.info(f"Importance already exists for bill {congress}.{bill_type}.{bill_number}. Skipping.")
            return False

        # Check if "President" or "Public Law" exists in the latestActionText using regex
        if MUST_KNOW_PATTERN.search(latest_action_text):
            importance = "Must Know"
            logging.info(f"Bill {congress}.{bill_type}.{bill_number} involves President or Public Law. Setting importance to 'Must Know'.")
            update_importance(conn_data, congress, bill_type, bill_number, importance)
            return True

        bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)
        bill_text_parts = get_bill_text_parts_with_summaries(conn_text, congress, bill_type, bill_number)

        if not bill_text_parts:
            logging.warning(f"No bill text parts with summaries found for {congress}.{bill_type}.{bill_number}. Skipping.")
            return False

        importance_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, bill_text_parts, bill_actions)
        importance = generate_content(importance_prompt)
        
        if importance not in ["Must Know", "Important", "Minimal"]:
            logging.warning(f"Invalid importance rating '{importance}' for bill {congress}.{bill_type}.{bill_number}. Skipping update.")
            return False

        update_importance(conn_data, congress, bill_type, bill_number, importance)

        logging.info(f"Successfully processed bill {congress}.{bill_type}.{bill_number}")
        return True

    except Exception as e:
        logging.error(f"Error processing bill {congress}.{bill_type}.{bill_number}: {str(e)}")
        return False

def main():
    try:
        logging.info("Starting main function")
        
        active_bill_data_db = os.path.join(script_dir, 'sys_db', 'active_bill_data.db')
        active_bill_text_db = os.path.join(script_dir, 'sys_db', 'active_bill_text.db')

        logging.info(f"Connecting to active_bill_data.db at {active_bill_data_db}")
        conn_data = connect_to_db(active_bill_data_db)
        
        logging.info(f"Connecting to active_bill_text.db at {active_bill_text_db}")
        conn_text = connect_to_db(active_bill_text_db)

        logging.info("Retrieving bills needing importance ratings")
        bills_needing_importance = get_bills_needing_importance(conn_data, conn_text)

        logging.info(f"Processing {len(bills_needing_importance)} bills")
        for i, bill in enumerate(bills_needing_importance, 1):
            congress, bill_type, bill_number = bill
            logging.info(f"Processing bill {i}/{len(bills_needing_importance)}: {congress}.{bill_type}.{bill_number}")

            bill_processed = process_bill(conn_data, conn_text, congress, bill_type, bill_number)
            
            if bill_processed:
                logging.info(f"Successfully processed bill: {congress}.{bill_type}.{bill_number}")
            else:
                logging.warning(f"Failed to process bill: {congress}.{bill_type}.{bill_number}")

        conn_data.close()
        conn_text.close()
        logging.info("Database connections closed")
        logging.info("Main function completed successfully")

    except Exception as e:
        logging.critical(f"Critical error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    logging.info("Script execution started")
    try:
        main()
    except Exception as e:
        logging.critical(f"Unhandled exception in script: {str(e)}")
    logging.info("Script execution completed")