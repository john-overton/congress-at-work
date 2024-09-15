import os
import random
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import run_bot_list

# Variables (you can adjust these as needed)
SCRIPTS_DIRECTORY = Path("./x_bot")  # Current directory
LOG_DIRECTORY = Path("./x_bot/Logs")
LOG_FILE = os.path.join(LOG_DIRECTORY, "schedule_post.log")
SCRIPT_LIST = run_bot_list.SCRIPT_LIST
MIN_INTERVAL = 3600  # Minimum interval between posts in seconds (1 hour)
MAX_INTERVAL = 6600  # Maximum interval between posts in seconds (1 hours 50 minutes)
ACTIVE_HOURS_START = 7  # Start of active hours (7 AM)
ACTIVE_HOURS_END = 23  # End of active hours (6 PM)

# Set up logging
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def is_active_hours():
    """Check if current time is within active hours."""
    current_hour = datetime.now().hour
    return ACTIVE_HOURS_START <= current_hour < ACTIVE_HOURS_END

def run_random_script():
    """Run a random script from the SCRIPT_LIST."""
    script = random.choice(SCRIPT_LIST)
    script_path = os.path.join(SCRIPTS_DIRECTORY, script)
    
    if os.path.exists(script_path):
        try:
            subprocess.run(["python", script_path], check=True)
            logging.info(f"Successfully ran script: {script}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running script {script}: {str(e)}")
    else:
        logging.error(f"Script not found: {script}")

def main():
    logging.info("Starting schedule_post.py")
    
    while True:
        if is_active_hours():
            run_random_script()
            
            # Calculate next run time
            interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
            next_run = datetime.now() + timedelta(seconds=interval)
            logging.info(f"Next script will run at {next_run}")
            
            # Sleep until next run time or until active hours start again
            while datetime.now() < next_run:
                if not is_active_hours():
                    time.sleep(60)  # Check every minute if we're back in active hours
                else:
                    time.sleep(min(60, (next_run - datetime.now()).total_seconds()))
        else:
            logging.info("Outside of active hours. Waiting...")
            time.sleep(3600)  # Sleep for an hour and check again

if __name__ == "__main__":
    main()