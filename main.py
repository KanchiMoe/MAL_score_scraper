from src.page_scrape import PageScrape
from src.sql import *
from src.colours import *
import logging
import requests
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
ROOT_URL = "https://myanimelist.net/anime/6547/Angel_Beats/stats"
MAX_OFFSET = 600

def GetURL():
    ColourTest()
    offset = 0

    while offset <= MAX_OFFSET:
        current_url = f"{ROOT_URL}?show={offset}"
        logging.info(f"Current stats page URL: {current_url}")
        member = PageScrape(current_url)

        if not member:
            msg = f"No more data. Exiting."
            logging.critical(msg)
            raise RuntimeError(msg)

        for member in member:
            DBStart(member)

        time.sleep(60)
        logging.info("Sleeping for 60 seconds...")
        offset += 75


if __name__ == "__main__":
    GetURL()
