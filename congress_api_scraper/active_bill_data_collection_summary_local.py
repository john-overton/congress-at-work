import os
import sqlite3
import datetime
import logging
# import time
from ollama import Client

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bill_data_collection_summary_local.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up the Ollama client
client = Client(host='http://localhost:10001')
model = 'llama3.1:8b-instruct-q8_0'

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
            SELECT congress, bill_type, bill_number, previous_context, bill_text, next_context, summary
            FROM bill_text
        """)
        result = cursor.fetchall()
        logging.info(f"Retrieved {len(result)} bills from bill_text table")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving all bills: {str(e)}")
        raise

def update_summary(conn, congress, bill_type, bill_number, summary):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bill_text
            SET summary = ?
            WHERE congress = ? AND bill_type = ? AND bill_number = ?
        """, (summary, congress, bill_type, bill_number))
        conn.commit()
        logging.info(f"Updated summary for bill {congress}.{bill_type}.{bill_number}")
    except sqlite3.Error as e:
        logging.error(f"Error updating summary: {str(e)}")
        raise

def construct_prompt(congress, bill_type, bill_number, bill_title, previous_context, bill_text, next_context, bill_actions):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an unbiased reporter tasked with summarizing legislation. Provide a detailed 4-5 paragraph summary of the given bill, including current actions and important facts. Follow these guidelines:

- Do not provide a title or helper text like "Here is a summary of [x]..."
- Use plain text without formatting
- Avoid bullet points or lists
- Omit party affiliations of sponsors or co-sponsors
- Present insights chronologically if applicable
- Include section numbers for referenced bill text
- Use the provided information about bill types and key action meanings

Today's date is {today_date}. Current sitting President: Joe Biden

<|eot_id|><|start_header_id|>user<|end_header_id|>
Summarize the following legislation:

Congress: {congress}
Bill Title: {bill_title}
Bill Type and Number: {bill_type}{bill_number}

Previous Context:
{previous_context}

Bill Text:
{bill_text}

Next Context:
{next_context}

Bill Actions:
{bill_actions}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    logging.info(f"Constructed summary prompt for bill {congress}.{bill_type}.{bill_number}")
    return prompt

def generate_content(prompt):
    try:
        response = client.generate(
            model=model,
            prompt=prompt
        )
        logging.info("Generated content from local LLM")
        return response['response']
    except Exception as e:
        logging.error(f"Error generating content: {str(e)}")
        raise

def process_bill(conn_data, conn_text, congress, bill_type, bill_number, previous_context, bill_text, next_context, existing_summary):
    try:
        # Check if summary already exists
        if existing_summary:
            logging.info(f"Skipping bill {congress}.{bill_type}.{bill_number} - summary already exists")
            return False  # Indicate that the bill was skipped

        bill_info = get_bill_info(conn_data, congress, bill_type, bill_number)
        bill_url = get_bill_url(conn_data, congress, bill_type, bill_number)
        bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)

        if bill_info and bill_url and bill_actions:
            bill_title = bill_info[0]
            formatted_text_url = bill_url[0]

            summary_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, previous_context, bill_text, next_context, bill_actions)
            summary = generate_content(summary_prompt)
            # Commenting out summary with URL
            # summary_with_url = f"{summary}\n\nSource: {formatted_text_url}"
            update_summary(conn_text, congress, bill_type, bill_number, summary)

            logging.info(f"Successfully processed bill {congress}.{bill_type}.{bill_number}")
            return True  # Indicate that the bill was processed
        else:
            logging.warning(f"Unable to find complete information for bill {congress}.{bill_type}.{bill_number}")
            return False  # Indicate that the bill was skipped due to incomplete information

    except Exception as e:
        logging.error(f"Error processing bill {congress}.{bill_type}.{bill_number}: {str(e)}")
        return False  # Indicate that the bill processing failed

def main():
    try:
        active_bill_data_db = os.path.join(script_dir, 'sys_db', 'active_bill_data.db')
        active_bill_text_db = os.path.join(script_dir, 'sys_db', 'active_bill_text.db')

        conn_data = connect_to_db(active_bill_data_db)
        conn_text = connect_to_db(active_bill_text_db)

        all_bills = get_all_bills(conn_text)

        for bill in all_bills:
            congress, bill_type, bill_number, previous_context, bill_text, next_context, existing_summary = bill

            bill_processed = process_bill(conn_data, conn_text, congress, bill_type, bill_number, previous_context, bill_text, next_context, existing_summary)
            
            if bill_processed:
                logging.info(f"Bill processed")
                # no timer needed for local llm
                # time.sleep(120)
            else:
                logging.info(f"Skipped waiting period for bill {congress}.{bill_type}.{bill_number}")

        conn_data.close()
        conn_text.close()
        logging.info("Database connections closed")

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Script execution started")
    main()
    logging.info("Script execution completed")