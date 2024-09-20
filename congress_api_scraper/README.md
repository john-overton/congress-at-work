# Congress.gov API and Webpage Scrapers

This folder contains the scripts behind the Congress.gov API and webpage scrapers.

This repo requires Python version 3.7+

1. To get started you will need to acquire an API key from congress.gov: http://gpo.congress.gov/sign-up/

2. Once you have acquired the API key, you will need to create a `keys.py` file in the `keys` folder of the congress-at-work repo.

3. Run the `install_dependencies.py` file within the `congress_api_scraper` folder to install any missing dependencies.

4. To pull data and text for laws, run the `automationV2.py` script
   - **IMPORTANT**: This will pull all laws available online, relevant text, and store it locally. This will require around 1GB of space and will take at least 18-20 hours to complete.

5. To pull data and text for active legislation, run the `run_daily_updates.py` script
   - **IMPORTANT**: This will pull all active legislation within the current congress. There may be thousands of bills pulled, and this could take many hours to complete.