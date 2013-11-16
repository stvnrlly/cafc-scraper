A scraper for the Federal Circuit Court of Appeals. Will find the day's new cases and email them to specified addresses.

# Setting it up

After cloning, create a file titled `email_addresses.py` to store required information for sending. Or just run the thing and enter the information when prompted.

# Usage

When you hit `python cafc.py`, The script will download the PDF of the new decisions, create a text version, and add new entries to the JSON file. The files are stored in `cafc_cases`.

If you want to scrape more days, change the URL on line 17, though the script currently only deals with one page of results.
