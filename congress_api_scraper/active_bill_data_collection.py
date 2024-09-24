import os
import sqlite3
import datetime
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import sys
import time

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
parent_dir = os.path.dirname(script_dir)

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bill_data_collection.log')
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Construct the path to the keys.py file
keys_path = os.path.join(parent_dir, 'keys', 'keys.py')

# Add the directory containing keys.py to sys.path
sys.path.append(os.path.dirname(keys_path))

# Import the Key_1 from keys.py
from keys import gg_key

# Configure the Google Generative AI
try:
    genai.configure(api_key=gg_key)
    logging.info("Google Generative AI configured successfully")
except Exception as e:
    logging.error(f"Failed to configure Google Generative AI: {str(e)}")
    raise

# Set up the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

safety_settings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]

try:
    model = genai.GenerativeModel(model_name="gemini-1.5-flash",
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)
    logging.info("Generative model initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize generative model: {str(e)}")
    raise

def connect_to_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
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
            SELECT *
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
            SELECT bill_text
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
            SELECT congress, bill_type, bill_number, bill_text, summary, full_synopsis
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

def update_synopsis(conn, congress, bill_type, bill_number, synopsis):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bill_text
            SET full_synopsis = ?
            WHERE congress = ? AND bill_type = ? AND bill_number = ?
        """, (synopsis, congress, bill_type, bill_number))
        conn.commit()
        logging.info(f"Updated full synopsis for bill {congress}.{bill_type}.{bill_number}")
    except sqlite3.Error as e:
        logging.error(f"Error updating full synopsis: {str(e)}")
        raise

def construct_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions, is_summary=True):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""
    <Instructions>
    As an unbiased reporter, provide a {'summary' if is_summary else 'full synopsis'} on current actions for the legislation in question. Ensure the output reads like a newspaper column.  Do not provide any party affiliatons of sponsors or co-sponsors. If providing insights chronologically ensure they are in proper order by date. Provide context from the bill text itself if appropriate. If you do reference from the bill text always include section of the text the reference comes from. I will provide a current congress, bill number, title, text, and actions.
    </Instructions>

    <Additional Details>
    Today's date is {today_date}. Current sitting President: Joe Biden
    Key action meanings:
    "Presented to President" - This means the legislation has been brought forward to the President's office but the legislation has not yet been signed or vetoed.
    "Signed by President" - This means the legislation has been signed by the president and become public law.
    </Additional Details>

    <Congress>{congress}</Congress>
    <Bill Title>{bill_title}</Bill Title>
    <Bill Number>{bill_type}{bill_number}</Bill Number>
    <Bill Text>
    {bill_text}
    </Bill Text>
    <Bill Actions>
    {bill_actions}
    </Bill Actions>
    """
    logging.info(f"Constructed {'summary' if is_summary else 'synopsis'} prompt for bill {congress}.{bill_type}.{bill_number}")
    return prompt

def generate_content(prompt):
    try:
        response = model.generate_content(prompt)
        logging.info("Generated content from AI model")
        return response.text
    except Exception as e:
        logging.error(f"Error generating content: {str(e)}")
        raise

def process_bill(conn_data, conn_text, congress, bill_type, bill_number, bill_text, existing_summary, existing_synopsis):
    try:
        # Check if both summary and synopsis already exist
        if existing_summary and existing_synopsis:
            logging.info(f"Skipping bill {congress}.{bill_type}.{bill_number} - summary and synopsis already exist")
            return False  # Indicate that the bill was skipped

        bill_info = get_bill_info(conn_data, congress, bill_type, bill_number)
        bill_url = get_bill_url(conn_data, congress, bill_type, bill_number)
        bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)

        if bill_info and bill_url and bill_actions:
            bill_title = bill_info[0]
            formatted_text_url = bill_url[0]

            # Generate summary if it doesn't exist
            if not existing_summary:
                summary_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions, is_summary=True)
                summary = generate_content(summary_prompt)
                summary_with_url = f"{summary}\n\nSource: {formatted_text_url}"
                update_summary(conn_text, congress, bill_type, bill_number, summary_with_url)

                # Wait for 30 seconds before generating synopsis
                time.sleep(30)

            # Generate full synopsis if it doesn't exist
            if not existing_synopsis:
                synopsis_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, bill_text, bill_actions, is_summary=False)
                synopsis = generate_content(synopsis_prompt)
                synopsis_with_url = f"{synopsis}\n\nSource: {formatted_text_url}"
                update_synopsis(conn_text, congress, bill_type, bill_number, synopsis_with_url)

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
            # Unpack the bill data, ensuring we have the correct number of variables
            congress, bill_type, bill_number, bill_text, existing_summary, existing_synopsis = bill

            bill_processed = process_bill(conn_data, conn_text, congress, bill_type, bill_number, bill_text, existing_summary, existing_synopsis)
            
            # Only wait if the bill was actually processed
            if bill_processed:
                logging.info(f"Waiting for 2 minutes before processing the next bill")
                time.sleep(120)
            else:
                logging.info(f"Skipped waiting period for bill {congress}.{bill_type}.{bill_number}")

        conn_data.close()
        conn_text.close()
        logging.info("Database connections closed")

    except ValueError as ve:
        logging.critical(f"Error unpacking bill data: {str(ve)}. This might be due to an unexpected number of columns in the bill_text table.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Script execution started")
    main()
    logging.info("Script execution completed")