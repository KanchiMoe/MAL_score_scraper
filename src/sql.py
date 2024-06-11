import psycopg2 # type: ignore
from psycopg2.extras import DictCursor # type: ignore
from dotenv import load_dotenv # type: ignore
import logging
import uuid
import pytz
from datetime import datetime

load_dotenv()

OKG = "\033[92m"
OKB = '\033[94m'
WRN = "\033[93m"
RST = "\033[0;0m"


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
            ChangeTracking(cursor, member_id=member["id"], action="create", field="ALL", old="NULL", new="n/a" )


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
            UpdateAlreadyInDB(cursor, member_id=member["id"], field=key, correct_value=diff["member"], old_value=diff["db"])
    else:
        logging.debug(f"{OKG}No differences found between database and MAL for {member["id"]}{RST}")


def UpdateAlreadyInDB(cursor, member_id, field, correct_value, old_value):
    FieldSafetyCheck(field)

    query = f"""
        UPDATE scores
        SET {field} = %s
        WHERE member_id = %s
        """
    cursor.execute(query, (correct_value, member_id))
    ChangeTracking(cursor, member_id, action="update", field=field, old=old_value, new=correct_value)

def FieldSafetyCheck(field):
    """
    This is an SQL safety check on the 'field' value, to prevent SQL injections.
    """
    allowed_fields = ["score", "status", "eps_seen"]
    if field not in allowed_fields:
        msg = f"SQL Safety Check - field '{field}' not in list of allowed fields."
        logging.critical(msg)
        raise RuntimeError(msg)

def ChangeTracking(cursor, member_id, action, field, old, new):
    random_uuid = uuid.uuid4()
    cursor.execute("""
        INSERT INTO change_tracking
        (uuid, timestamp, member_id, action, field, old_value, new_value)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (str(random_uuid), datetime.now(pytz.timezone('Europe/London')), member_id, action.upper(), field, old, new)
        )
