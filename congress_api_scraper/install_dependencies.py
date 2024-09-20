import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    print("Installing required dependencies...")
    
    dependencies = [
        "requests",
        "beautifulsoup4",
        "bs4",
        "nltk"
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"{dep} is already installed.")
        except ImportError:
            print(f"Installing {dep}...")
            install(dep)
            print(f"{dep} has been installed successfully.")


    print("All required dependencies have been installed.")

    # Download NLTK data
    print("Downloading NLTK data...")
    import nltk
    nltk.download('punkt_tab', quiet=True)
    print("NLTK data downloaded successfully.")

if __name__ == "__main__":
    main()