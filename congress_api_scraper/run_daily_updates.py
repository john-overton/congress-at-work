import subprocess
import time
import sys
import logging
from datetime import datetime, timedelta
import os
import run_daily_list

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(os.path.join(os.getcwd(), "congress_api_scraper", "Logs", "daily_updates.log")),
                        logging.StreamHandler()
                    ])

# Set Active Hours
ACTIVE_HOURS_START = 7  # Start of active hours (7 AM)
ACTIVE_HOURS_END = 23  # End of active hours (7 PM)
RUN_INTERVAL = 3600 # Restart interval time

def is_active_hours():
    """Check if current time is within active hours."""
    current_hour = datetime.now().hour
    return ACTIVE_HOURS_START <= current_hour < ACTIVE_HOURS_END

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

def run_script(script_name):
    script_path = os.path.join(current_dir, script_name)
    try:
        logging.info(f"Starting execution of {script_name}")
        start_time = time.time()
        result = subprocess.run([sys.executable, script_path], 
                                check=True, 
                                capture_output=True, 
                                text=True)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"Successfully executed {script_name}")
        logging.info(f"Execution time: {execution_time:.2f} seconds")
        logging.info(f"Output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"Errors/Warnings:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {script_name}: {e}")
        logging.error(f"Error output:\n{e.stderr}")
    except FileNotFoundError:
        logging.error(f"Script not found: {script_name}")

def run_all_scripts():
    scripts = run_daily_list.SCRIPT_LIST
    
    pause_time = 5  # Time to pause between scripts in seconds

    logging.info(f"Starting script execution sequence at {datetime.now()}")
    
    for script in scripts:
        logging.info(f"Preparing to run {script}")
        run_script(script)
        logging.info(f"Finished {script}. Pausing for {pause_time} seconds...")
        time.sleep(pause_time)

    logging.info(f"All scripts have been executed. Sequence completed at {datetime.now()}")


def main():
    logging.info("Scheduler started. Daily update scripts will run hourly between 7 AM and 7 PM.")
    
    while True:
        if is_active_hours():
            run_all_scripts()
            
            # Calculate next run time
            interval = RUN_INTERVAL
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
            time.sleep(1800)  # Sleep for 30 minutes and check again

if __name__ == "__main__":
    main()