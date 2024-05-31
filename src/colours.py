import logging


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

OKGREEN = "\033[92m"
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
WARNING = '\033[93m'
FAIL = '\033[91m'
RESET = "\033[0;0m"

def ColourTest():
    logging.debug(f"{OKGREEN}OKGREEN{RESET}")
    logging.debug(f"{OKBLUE}OKBLUE{RESET}")
    logging.debug(f"{OKCYAN}OKCYAN{RESET}")
    logging.debug(f"{WARNING}WARNING{RESET}")
    logging.debug(f"{FAIL}FAIL{RESET}")
