import subprocess
import time
import sys
import logging
from datetime import datetime
import os
import automation_run_list

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("script_runner.log"),
                        logging.StreamHandler()
                    ])

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

def main():
    scripts = automation_run_list.run_list
    
    pause_time = 5  # Time to pause between scripts in seconds

    logging.info(f"Starting script execution sequence at {datetime.now()}")
    
    for script in scripts:
        logging.info(f"Preparing to run {script}")
        run_script(script)
        logging.info(f"Finished {script}. Pausing for {pause_time} seconds...")
        time.sleep(pause_time)

    logging.info(f"All scripts have been executed. Sequence completed at {datetime.now()}")

if __name__ == "__main__":
    main()