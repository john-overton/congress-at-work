import subprocess
import time
import sys

def run_script(script_path):
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
    except FileNotFoundError:
        print(f"Script not found: {script_path}")

def main():
    scripts = [
        "get_bills.py",
        "get_congress_list.py",
        "get_laws_list.py",
        "get_law_text_urls.py",
        "add_update_bill_text.py",
        "add_update_bill_xml.py",
        "bill_tokenizer_htm_7000.py",
        "bill_tokenizer_xml_nocut_7000.py"
    ]
    
    pause_time = 5  # Time to pause between scripts in seconds

    for script in scripts:
        print(f"Running {script}...")
        run_script(script)
        print(f"Finished {script}. Pausing for {pause_time} seconds...")
        time.sleep(pause_time)

    print("All scripts have been executed.")

if __name__ == "__main__":
    main()