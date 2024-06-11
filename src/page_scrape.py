import backoff
from bs4 import BeautifulSoup # type: ignore
import logging
import requests
import time
from src.colours import RST, CTR

@backoff.on_exception(
    backoff.constant, 
    requests.exceptions.RequestException, 
    interval=60, 
    max_tries=5,
    jitter=None,
    giveup=lambda e: e.response.status_code == 200
)
def RequestHandler(requested_url):
    logging.info(f"Requesting {requested_url}")
    response = requests.get(requested_url)
    logging.debug(f"Response status: {response.status_code}")

    if response.status_code == 200:
        return response
    elif response.status_code == 405:
        logging.warn(f"{CTR}We are being rate limited{RST}")
        raise requests.exceptions.RequestException(response=response)
    else:
        msg = f"{CTR}Failed to retrieve page. Page: {requested_url}, status code: {response.status_code}{RST}"
        logging.critical(msg)
        raise RuntimeError(msg)

def PageScrape(url: str):
    response = RequestHandler(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all <tr> tags
    rows = soup.find_all('tr')

    for row in rows:
        # Extract the URL and text from the first cell (Member field)
        member_cell = row.find('td', class_='borderClass')
        member_link = member_cell.find('a')['href'] if member_cell and member_cell.find('a') else "N/A"
        member_name = member_cell.find('a', class_='word-break').text.strip() if member_cell and member_cell.find('a', class_='word-break') else "N/A"

        # Check if the row contains header text or is empty
        if "Member" in member_name or member_name == "N/A":
            continue  # Skip the header row or rows without valid member info

        # Extract relevant information
        cells = row.find_all('td', class_='borderClass')

        # Skip rows that do not contain the expected number of cells
        if len(cells) != 5:
            continue

        # Extract data from the cells
        score = cells[1].text.strip()
        status = cells[2].text.strip()
        eps_seen = cells[3].text.strip()
        activity = cells[4].text.strip()

        # Use member link to make another request
        if member_link != "N/A":
            member_id = GetMemberID(member_link)

        member_raw_dict = {
            "name": member_name,
            "id": member_id,
            "score": score,
            "status": status,
            "eps_seen": eps_seen,
            "activity": activity
        }

        logging.debug(f"Raw dict: {member_raw_dict}") 
        sanatised_dict = SanatiseDict(member_raw_dict)
        logging.debug(f"Sanatised dict: {sanatised_dict}")

        yield(sanatised_dict)

def GetMemberID(member_url):
    time.sleep(1)
    response = RequestHandler(member_url)



    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the desired link on the member page
    report_link = soup.find('a', href=lambda href: href and "modules.php?go=report&type=profile&id=" in href)

    if report_link:
            report_url = report_link['href']
            member_id = report_url.split("id=")[1]
            logging.debug(f"Got member ID: {member_id}")
            return member_id

    else:
        logging.critical(f"Unable to get member ID.")

def SanatiseDict(member_raw_dict):
    raw_eps_seen = member_raw_dict["eps_seen"]

    if raw_eps_seen == "":
        logging.debug("Raw eps is blank. Setting to 0")
        member_raw_dict.update(eps_seen="0")
    elif raw_eps_seen == "- / 13":
        logging.debug("Raw eps is \"-/13\". Setting to 0")
        member_raw_dict.update(eps_seen="0")
    else:
        logging.debug(f"Raw eps is \"{raw_eps_seen}\". Sanatising.")
        member_raw_dict.update(eps_seen=raw_eps_seen.split(" / ")[0])

    return member_raw_dict
