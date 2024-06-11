import logging
import os

# DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL")
# DEFAULT_LOG_FORMAT = os.environ.get("LOG_FORMAT")
# logging.getLogger().setLevel(DEFAULT_LOG_LEVEL)
# logging.basicConfig(format=DEFAULT_LOG_FORMAT)

OKGREEN = "\033[92m"
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
WRN = '\033[93m'
CTR = '\033[91m'
RST = "\033[0;0m"

def ColourTest():
    logging.debug(f"{OKGREEN}OKGREEN{RST}")
    logging.debug(f"{OKBLUE}OKBLUE{RST}")
    logging.debug(f"{OKCYAN}OKCYAN{RST}")
    logging.debug(f"{WRN}WARNING{RST}")
    logging.debug(f"{CTR}CRITICAL{RST}")
