# cong-scrape
A repository for the scrape engine of congress.gov

This is amazing and something that I really wanted to update for a long timne.


Start with law
(complete) Step 1: Get Congress List
    * DB Format congress.db
        * Table: Congress
    

Step 2:
    * DB Format laws.db
        * Table: Laws
    * Pull list of laws and place into laws.db.laws table: Example CURL: curl -X GET "https://gpo.congress.gov/v3/law/118?format=json&offset=0&limit=100&api_key=[APIKEY]" -H  "accept: application/json" | Example returned payload: {Law_Sample.txt]
    * API Parameters
        congress (integer) -The congress number. For example, the value can be 117.
        format (string) - The data format. Value can be xml or json.
        offset (integer) - The starting record returned. 0 is the first record.
        limit (integer) - The number of records returned. The maximum limit is 250.

Step 2: Pull law text crossed reference from bill number from law