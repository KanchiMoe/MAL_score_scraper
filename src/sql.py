import psycopg2 # type: ignore
from psycopg2.extras import DictCursor # type: ignore
from dotenv import load_dotenv # type: ignore
import logging
import uuid

OKG = "\033[92m"
OKB = '\033[94m'
WRN = "\033[93m"
RST = "\033[0;0m"

load_dotenv()

def DBStart(member):
    with psycopg2.connect() as psql:
        cursor = psql.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM scores WHERE member_id = %s;",
                       (member["id"],))
        is_in_db = cursor.fetchone()

        if is_in_db is not None:
            logging.debug(f"{OKB}ID {member["id"]} is in database.{RST}")
            AlreadyInDB_DiffCheck(member, cursor, data_from_db=is_in_db)  
        else:
            logging.debug(f"ID {member["id"]} is not in database.")
            NewAddToDB(member, cursor)
            ChangeTracking(cursor, member, action="create", field="ALL", old="NULL", new="n/a" )


def NewAddToDB(member, cursor):
    cursor.execute("""
        INSERT INTO scores
        (member_id, member_username, score, status, eps_seen)
        VALUES (%s, %s, %s, %s, %s);  
        """, (member["id"], member["name"], member["score"], member["status"], member["eps_seen"])
        )
    logging.info(f"{OKB}Adding {member["id"]} to database{RST}")

def AlreadyInDB_DiffCheck(member, cursor, data_from_db):
    # Compare values between the member dict and is_in_db
    differences = {}

    for key in member:
        if key in data_from_db and member[key] != data_from_db[key]:
            differences[key] = {"member": member[key], "db": data_from_db[key]}

    if differences:
        logging.debug(f"{WRN}Differences found between database and MAL for {member["id"]}{RST}")
        for key, diff in differences.items():
            logging.debug(f"{WRN}Differences: {key} - from MAL: {diff["member"]}, DB: {diff["db"]}{RST}")
    else:
        logging.debug(f"{OKG}No differences found between database and MAL for {member["id"]}{RST}")


def ChangeTracking(cursor, member, action, field, old, new):
    random_uuid = uuid.uuid4()
    cursor.execute("""
        INSERT INTO change_tracking
        (uuid, user_id, action, field, old_value, new_value)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(random_uuid), member["id"], action.upper(), field, old, new)
        )