import logging
import requests
from src.colours import CTR, WRN, RST, OKG, OKC
import time
from bs4 import BeautifulSoup
import psycopg2 # type: ignore
from psycopg2.extras import DictCursor
from dotenv import load_dotenv # type: ignore
import uuid
import uuid
import pytz
from datetime import datetime
import backoff

load_dotenv()

ROOT_URL = "https://myanimelist.net/anime/6547/Angel_Beats/stats"
MAX_OFFSET = 7425
LIST_OF_MEMBERS_NOT_IN_DB = []

logging.getLogger().setLevel(logging.DEBUG)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")



@backoff.on_exception(
    backoff.constant, 
    requests.exceptions.RequestException, 
    interval=60, 
    max_tries=5,
    jitter=None,
    giveup=lambda e: e.response.status_code == 200
)
def RequestHandler(requested_url):
    logging.debug(f"Requesting {requested_url}")
    response = requests.get(requested_url)
    logging.debug(f"Response status: {response.status_code}")

    if response.status_code == 200:
        return response
    elif response.status_code == 405:
        logging.warning(f"{CTR}We are being rate limited{RST}")
        raise requests.exceptions.RequestException(response=response)
    elif response.status_code == 504:
        logging.warning(f"{WRN}Got 504 (gateway timeour). We might be being rate limited, or MAL has an error. Waiting before retrying...")
        raise requests.exceptions.RequestException(response=response)
    else:
        msg = f"{CTR}Failed to retrieve page. Page: {requested_url}, status code: {response.status_code}{RST}"
        logging.critical(msg)
        raise RuntimeError(msg)
    
def SanatiseDict(member_raw_dict):
    raw_eps_seen = member_raw_dict["eps_seen"]

    if raw_eps_seen == "":
        #logging.debug("Raw eps is blank. Setting to 0")
        member_raw_dict.update(eps_seen="0")
    elif raw_eps_seen == "- / 13":
        #logging.debug("Raw eps is \"-/13\". Setting to 0")
        member_raw_dict.update(eps_seen="0")
    else:
        #logging.debug(f"Raw eps is \"{raw_eps_seen}\". Sanatising.")
        member_raw_dict.update(eps_seen=raw_eps_seen.split(" / ")[0])

    return member_raw_dict

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
        # if member_link != "N/A":
        #     member_id = GetMemberID(member_link)

        member_raw_dict = {
            "name": member_name,
            "score": score,
            "status": status,
            "eps_seen": eps_seen,
            "activity": activity
        }

        #logging.debug(f"Raw dict: {member_raw_dict}") 
        sanatised_dict = SanatiseDict(member_raw_dict)
        #logging.debug(f"Sanatised dict: {sanatised_dict}")

        yield(sanatised_dict)

def IsInDB(member):
    if member["name"] == "":
        msg = f"{CTR}Member username is blank. Likely account deleted."
        logging.critical(msg)
        raise RuntimeError(msg)
    

    with psycopg2.connect() as psql:
        cursor = psql.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM scores.scores WHERE member_username = %s;",
                       (member["name"],))
        is_in_db = cursor.fetchone()

        if is_in_db is not None:
            logging.debug(f"USER: {member["name"]} is IN db")
            AlreadyInDB_DiffCheck(member, cursor, data_from_db=is_in_db)  
        else:
            logging.debug(f"USER: {member["name"]} is NOT in db ")
            LIST_OF_MEMBERS_NOT_IN_DB.append(member)

def AlreadyInDB_DiffCheck(raw_member_object, cursor, data_from_db):
    logging.debug(f"Raw DB object: {data_from_db}")
    logging.debug(f"Raw member object: {raw_member_object}")


   
    db_dict = {
        "id": str(data_from_db[0]),
        "name": data_from_db[1],
        "score": data_from_db[2],
        "status": data_from_db[3],
        "eps_seen": data_from_db[4],
    }
    raw_member_object.pop('activity', None)
    member_object = {'id': str(data_from_db[0]), **raw_member_object}



    logging.debug(f"Sanatised DB object: {db_dict}")
    logging.debug(f"Sanatised member object: {member_object}")

    differences = {}

    for each_key in member_object:
        if each_key in db_dict and member_object[each_key] != db_dict[each_key]:
            differences[each_key] = {"member": member_object[each_key], "db": db_dict[each_key]}

    if differences:
        logging.info(f"{WRN}Differences found between MAL and DB for {member_object["name"]}{RST}")

        for key, diff in differences.items():
            logging.debug(f"{WRN}Differences: {key} - from MAL: {diff["member"]}, DB: {diff["db"]}{RST}")


            SQL_UpdateAlreadyInDB(cursor, member_id=member_object["id"], field=key, correct_value=diff["member"], old_value=diff["db"])

    else:
        logging.debug(f"No differences found between database and MAL for {member_object["name"]}")

def SQL_UpdateAlreadyInDB(cursor, member_id, field, correct_value, old_value):
    FieldSafetyCheck(field)
    query = f"""
        UPDATE scores.scores
        SET {field} = %s
        WHERE member_id = %s
        """
    cursor.execute(query, (correct_value, member_id))
    SQL_ChangeTracking(cursor, member_id, action="update", field=field, old=old_value, new=correct_value)

def FieldSafetyCheck(field):
    """
    This is an SQL safety check on the 'field' value, to prevent SQL injections.
    """
    allowed_fields = ["score", "status", "eps_seen"]
    if field not in allowed_fields:
        msg = f"SQL Safety Check - field '{field}' not in list of allowed fields."
        logging.critical(msg)
        raise RuntimeError(msg)

############################################################################################

def ProcessNotInDB():
    logging.debug("")
    logging.debug(f"Number of people not in DB to process: {len(LIST_OF_MEMBERS_NOT_IN_DB)}")

    logging.debug("")
    logging.debug(f"{LIST_OF_MEMBERS_NOT_IN_DB}")


    def GetID(response):
        soup = BeautifulSoup(response.content, 'html.parser') 
        report_link = soup.find('a', href=lambda href: href and "modules.php?go=report&type=profile&id=" in href)

        if report_link:
            report_url = report_link['href']
            member_id = report_url.split("id=")[1]
            logging.debug(f"Got member ID: {member_id}")
            return member_id

        else:
            logging.critical(f"Unable to get member ID.")
            raise RuntimeError(f"Unable to get member ID.")
        

    for member in LIST_OF_MEMBERS_NOT_IN_DB:
        logging.debug(f"Processing: {member}")

        ROOT_URL = "https://myanimelist.net/profile/"
        url = f"{ROOT_URL}{member["name"]}"
        response = RequestHandler(url)
        member_id = GetID(response)

        check = SQL_IsIDInDB(member_id)
        if check == True:
            logging.debug(f"")
            print(f"{OKC}check: {check}{RST}")
            print("Sleeping for 10 ######")
            time.sleep(10)
            SQL_UpdateUsername(member, member_id)
            break

        








        new_member = member

        print(f"OLD {member}")
        new_member.pop('activity', None)
        new_member = {'id': member_id, **new_member}
        print(f"NEW {new_member}")


        with psycopg2.connect() as psql:
            cursor = psql.cursor(cursor_factory=DictCursor)

            SQL_NewToDB(new_member, cursor)

            print("pass to change tracking")
            SQL_ChangeTracking(cursor, member_id=new_member["id"], action="create", field="ALL", old="NULL", new="n/a" )


            print("about to remove from constant")
            print(member)
            LIST_OF_MEMBERS_NOT_IN_DB.remove(member)

            logging.debug("")
            logging.debug(f"PEOPLE REMAINING: {len(LIST_OF_MEMBERS_NOT_IN_DB)}")
            print(LIST_OF_MEMBERS_NOT_IN_DB)
            print("Sleeping for 2")
            time.sleep(2)


def SQL_UpdateUsername(member_object, member_id):


    with psycopg2.connect() as psql:
        cursor = psql.cursor(cursor_factory=DictCursor)
        cursor.execute("""
            SELECT member_username
            FROM users
            WHERE member_id = %s;
            """, (str(member_id),)
        )
        db_data = cursor.fetchone()
        logging.debug(f"ID: {member_id} , Current username: {member_object["name"]}, Old username: {str(db_data[0])}")

        cursor.execute("""
            UPDATE users
            SET member_username = %s
            WHERE member_id = %s
            """, (member_object["name"], member_id)
        )

        cursor.execute("""
            UPDATE scores.scores
            SET member_username = %s
            WHERE member_id = %s
            """, (member_object["name"], member_id)
        )

        random_uuid = uuid.uuid4()
        cursor.execute("""
            INSERT INTO past_usernames
            (uuid, member_id, old_username, new_username, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """, (str(random_uuid), member_id, str(db_data[0]), member_object["name"], datetime.now(pytz.timezone('Europe/London')))
        )
        SQL_ChangeTracking(cursor, member_id=member_id, action="update", field="username", old=str(db_data[0]), new=member_object["name"])
        LIST_OF_MEMBERS_NOT_IN_DB.remove(member_object)
        


    
        














    #### working on the above bit




















def SQL_IsIDInDB(member_id):
    logging.debug(f"Checking if {member_id} is in the database already...")

    with psycopg2.connect() as psql:
        cursor = psql.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM scores.scores WHERE member_id = %s;",
                       (member_id,))
        is_in_db = cursor.fetchone()

        if is_in_db:
            logging.debug(f"{OKC}ID {member_id} IS in the database.{RST}")
            print(f"is in db")
            print(f"{is_in_db}")
            
            return True
        else:
            logging.debug(f"{OKG}ID {member_id} is NOT in the database.{RST}")
            return False

        # if is_in_db is not None:
        #     logging.debug(f"USER: {member["name"]} is IN db")
        #     AlreadyInDB_DiffCheck(member, cursor, data_from_db=is_in_db)  
        # else:
        #     logging.debug(f"USER: {member["name"]} is NOT in db ")
        #     LIST_OF_MEMBERS_NOT_IN_DB.append(member)
        #     #SQL_NewToDB(member, cursor)
        #     #SQL_ChangeTracking(cursor, member_id=member["id"], action="create", field="ALL", old="NULL", new="n/a" )




def SQL_NewToDB(member, cursor):
    cursor.execute("""
        INSERT INTO scores.scores
        (member_id, member_username, score, status, eps_seen)
        VALUES (%s, %s, %s, %s, %s);  
        """, (member["id"], member["name"], member["score"], member["status"], member["eps_seen"])
        )
    cursor.execute("""
        INSERT INTO users
        (member_id, member_username)
        VALUES (%s, %s)
        """, (member["id"], member["name"])
    )
    logging.info(f"Adding {member["id"]} to database")



def SQL_ChangeTracking(cursor, member_id, action, field, old, new):
    random_uuid = uuid.uuid4()
    cursor.execute("""
        INSERT INTO scores.change_tracking
        (uuid, timestamp, member_id, action, field, old_value, new_value)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (str(random_uuid), datetime.now(pytz.timezone('Europe/London')), member_id, action.upper(), field, old, new)
        )
    



MAX_OFFSET_2 = 7425

def GetURL():
    offset = 0
    start_time = time.time()
    print(f"Start time: {start_time}")

    while offset <= MAX_OFFSET_2:
        current_url = f"{ROOT_URL}?show={offset}"
        print(f"Current stats page URL: {current_url}")
        member = PageScrape(current_url)

        

        if not member:
            msg = f"No more data. Exiting."


            logging.critical(msg)
            raise RuntimeError(msg)

        for memberItterator in member:
            #DBStart(member)
            print(f"member: {memberItterator["name"]}")
            IsInDB(memberItterator)

        if LIST_OF_MEMBERS_NOT_IN_DB:
            ProcessNotInDB()


        

        print("Sleeping for 1 second...")
        time.sleep(1)
        offset += 75
        #logging.debug("bar")


    end_time = time.time()  # Record the end time if loop completes
    total_time_seconds = end_time - start_time
    hours, remainder = divmod(total_time_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"Elapsed time: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")



if __name__ == "__main__":
    GetURL()
