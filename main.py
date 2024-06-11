from src.page_scrape import PageScrape
from src.sql import *
from src.colours import *
import logging
import os
import requests
import time

DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL")
DEFAULT_LOG_FORMAT = os.environ.get("LOG_FORMAT")
logging.getLogger().setLevel(DEFAULT_LOG_LEVEL)
logging.basicConfig(format=DEFAULT_LOG_FORMAT)

ROOT_URL = "https://myanimelist.net/anime/6547/Angel_Beats/stats"
MAX_OFFSET = 8000

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

        logging.info("Sleeping for 60 seconds...")
        time.sleep(60)
        offset += 75


if __name__ == "__main__":
    GetURL()
