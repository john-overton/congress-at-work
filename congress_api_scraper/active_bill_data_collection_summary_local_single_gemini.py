import os
import sqlite3
import datetime
import logging
from google import genai
import sys

# Get the absolute path of the script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
parent_dir = os.path.dirname(script_dir)

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'active_bill_data_collection_summary_local_single_gemini.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Construct the path to the keys.py file
keys_path = os.path.join(parent_dir, 'keys', 'keys.py')

# Add the directory containing keys.py to sys.path
sys.path.append(os.path.dirname(keys_path))

# Import the gg_key from keys.py
from keys import gg_key

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

def get_total_parts(conn, congress, bill_type, bill_number):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(text_part)
            FROM bill_text
            WHERE congress = ? AND bill_type = ? AND bill_number = ?
        """, (congress, bill_type, bill_number))
        result = cursor.fetchone()
        if result and result[0]:
            logging.info(f"Retrieved total parts ({result[0]}) for bill {congress}.{bill_type}.{bill_number}")
            return result[0]
        logging.warning(f"No parts found for bill {congress}.{bill_type}.{bill_number}")
        return 0
    except sqlite3.Error as e:
        logging.error(f"Error retrieving total parts: {str(e)}")
        raise

def get_bill_next_part(conn, congress=None, bill_type=None, bill_number=None):
    try:
        cursor = conn.cursor()
        if congress and bill_type and bill_number:
            # Get next unsummarized part for specific bill
            cursor.execute("""
                SELECT congress, bill_type, bill_number, text_part,
                       previous_context, bill_text, next_context
                FROM bill_text
                WHERE congress = ? AND bill_type = ? AND bill_number = ?
                AND summary IS NULL
                ORDER BY text_part
                LIMIT 1
            """, (congress, bill_type, bill_number))
        else:
            # Get first unsummarized part of a new bill with multiple parts
            cursor.execute("""
                WITH bills_with_multiple_parts AS (
                    SELECT DISTINCT congress, bill_type, bill_number
                    FROM bill_text
                    WHERE text_part > 1
                ),
                next_part AS (
                    SELECT bt.congress, bt.bill_type, bt.bill_number,
                           MIN(bt.text_part) as next_text_part
                    FROM bill_text bt
                    INNER JOIN bills_with_multiple_parts bmp
                        ON bt.congress = bmp.congress 
                        AND bt.bill_type = bmp.bill_type 
                        AND bt.bill_number = bmp.bill_number
                    WHERE bt.summary IS NULL
                    GROUP BY bt.congress, bt.bill_type, bt.bill_number
                    LIMIT 1
                )
                SELECT bt.congress, bt.bill_type, bt.bill_number, bt.text_part,
                       bt.previous_context, bt.bill_text, bt.next_context
                FROM bill_text bt
                INNER JOIN next_part np
                    ON bt.congress = np.congress
                    AND bt.bill_type = np.bill_type
                    AND bt.bill_number = np.bill_number
                    AND bt.text_part = np.next_text_part
            """)
        result = cursor.fetchone()
        if result:
            logging.info(f"Found bill without summary: {result[0]}.{result[1]}.{result[2]}, text part: {result[3]}")
        else:
            logging.warning("No bills found that have multiple parts (text_part > 1) and need text_part 1 summarized")
        return result
    except sqlite3.Error as e:
        logging.error(f"Error retrieving bill without summary: {str(e)}")
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

def construct_prompt(congress, bill_type, bill_number, bill_title, previous_context, bill_text, next_context, bill_actions, text_part, total_parts):
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""You are a legislative analyst focused on providing precise, factual summaries of specific portions of bills. Your task is to analyze and summarize the provided bill text section, considering its position within the overall legislation. Write a 4-5 paragraph summary that captures the essential facts from the specific text section provided.

If this is the beginning section of the bill (text_part indicates start), include:
- Official title and short title
- Congress number and session
- Bill type and number
- Primary sponsor and total number of co-sponsors
- Committee referrals
- Key definitions and scope

If this is a middle section, focus exclusively on:
- The specific provisions and requirements in the provided bill text
- Any numerical values, deadlines, or specific criteria
- Definitions of new terms introduced in this section
- Cross-references to other sections when explicitly mentioned

If this is the final section (text_part indicates end), include:
- Summary of the specific final provisions
- Most recent legislative actions and their dates
- Current status of the bill
- Implementation timelines if specified

Writing guidelines:
- Write in clear prose without formatting or bullet points
- Use specific section numbers when referencing bill text
- Include precise dates and numerical values
- Maintain chronological order where applicable
- Focus solely on factual content without interpretation
- Exclude party affiliations
- Avoid summarizing sections outside the provided bill text

Today's date is {today_date}.

Please analyze this legislation section:

Congress: {congress}
Bill Title: {bill_title}
Bill Type and Number: {bill_type}{bill_number}
Text Part: {text_part} of {total_parts}

Previous Context:
{previous_context}

Bill Text:
{bill_text}

Next Context:
{next_context}

Bill Actions:
{bill_actions}
"""
    logging.info(f"Constructed summary prompt for bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
    logging.debug(f"Prompt: {prompt}")
    return prompt

def generate_content(prompt):
    try:
        # Initialize the client
        client = genai.Client(api_key=gg_key)
        
        # Stream the response
        print("\nGenerating summary (streaming)...")
        print("-" * 80)
        
        full_response = ""
        response = client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=prompt)
            
        for chunk in response:
            print(chunk.text, end="", flush=True)
            full_response += chunk.text
            
        print("\n" + "-" * 80)
        logging.info("Generated content from Gemini model")
        
        return full_response
    except Exception as e:
        logging.error(f"Error generating content: {str(e)}")
        raise

def process_bill(conn_data, conn_text, congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context):
    try:
        bill_info = get_bill_info(conn_data, congress, bill_type, bill_number)
        bill_url = get_bill_url(conn_data, congress, bill_type, bill_number)
        bill_actions = get_bill_actions(conn_data, congress, bill_type, bill_number)
        total_parts = get_total_parts(conn_text, congress, bill_type, bill_number)

        if bill_info and bill_url and bill_actions and total_parts > 0:
            bill_title = bill_info[0]
            formatted_text_url = bill_url[0]

            print(f"\nProcessing bill {congress}.{bill_type}.{bill_number}, text part: {text_part} of {total_parts}")
            print(f"Title: {bill_title}")
            
            summary_prompt = construct_prompt(congress, bill_type, bill_number, bill_title, previous_context, bill_text, next_context, bill_actions, text_part, total_parts)
            summary = generate_content(summary_prompt)
            update_summary(conn_text, congress, bill_type, bill_number, text_part, summary)

            logging.info(f"Successfully processed bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
            return True
        else:
            logging.warning(f"Unable to find complete information for bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
            return False

    except Exception as e:
        logging.error(f"Error processing bill {congress}.{bill_type}.{bill_number}, text part: {text_part}: {str(e)}")
        return False

def main():
    try:
        active_bill_data_db = os.path.join(script_dir, 'sys_db', 'active_bill_data.db')
        active_bill_text_db = os.path.join(script_dir, 'sys_db', 'active_bill_text.db')

        conn_data = connect_to_db(active_bill_data_db)
        conn_text = connect_to_db(active_bill_text_db)

        # Get the first bill that needs processing
        bill = get_bill_next_part(conn_text)
        
        if bill:
            congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context = bill
            total_parts = get_total_parts(conn_text, congress, bill_type, bill_number)
            print(f"\nProcessing bill {congress}.{bill_type}.{bill_number} ({total_parts} total parts)")
            
            # Process all parts of this bill
            while bill:
                bill_processed = process_bill(conn_data, conn_text, congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context)
                
                if bill_processed:
                    print(f"\nSuccessfully processed bill {congress}.{bill_type}.{bill_number}, text part: {text_part} of {total_parts}")
                    # Get next part of the same bill
                    bill = get_bill_next_part(conn_text, congress, bill_type, bill_number)
                    if bill:
                        congress, bill_type, bill_number, text_part, previous_context, bill_text, next_context = bill
                else:
                    print(f"\nFailed to process bill {congress}.{bill_type}.{bill_number}, text part: {text_part}")
                    break
            
            print(f"\nCompleted processing all parts of bill {congress}.{bill_type}.{bill_number}")
        else:
            print("\nNo bills found that have multiple parts and need summarizing")

        conn_data.close()
        conn_text.close()
        logging.info("Database connections closed")

    except Exception as e:
        logging.critical(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    logging.info("Script execution started")
    main()
    logging.info("Script execution completed")
