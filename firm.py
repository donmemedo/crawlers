"""_summary_

Raises:
    RuntimeError: _description_

Returns:
    _type_: _description_
"""
import datetime
import logging
import os
import requests
from pymongo import MongoClient, errors


with open("/etc/hosts", "a", encoding='utf-8') as file:
    file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    """_summary_

    Returns:
        _type_: _description_
    """
    connection_string = os.environ.get("DATABASE_URL")
    client = MongoClient(connection_string)
    database = client["brokerage"]
    return database


logging.basicConfig(
    encoding="utf-8",
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.debug("it has been started to log...")


db = get_database()
collection = db["firms"]


def getter(size=10, date="2023-01-31"):
    """_summary_

    Args:
        size (int, optional): _description_. Defaults to 10.
        date (str, optional): _description_. Defaults to "2023-01-31".
    """
    temp_req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetFirmList",
        params={'request.date': date, 'request.pageIndex': 0,
                'request.pageSize': 1},
        timeout=100)
    if temp_req.status_code != 200:
        logging.critical("Http response code: %s", temp_req.status_code)
        total_records = 0
    else:
        total_records = temp_req.json()["TotalRecords"]
    logger.info("\t  \t  \t  %s \t  \t  \t  %s",date,total_records)
    for page in range(0, total_records // 10 + 1):
        logger.info("Getting Page %d from %d pages", page + 1, total_records // 10 + 1)
        req = requests.get(
            "https://tadbirwrapper.tavana.net/tadbir/GetFirmList",
            params={'request.date': date, 'request.pageIndex': page,
                    'request.pageSize': size},
            timeout=100
        )
        if req.status_code != 200:
            logging.critical("Http response code: %s", req.status_code)
            records = ""
        else:
            response = req.json()
            records = response.get("Result")
        for record in records:
            if record is None:
                logger.info("Record is empty.")
                continue
            try:
                collection.insert_one(record)
                logger.info("Record %s added to Mongodb", record.get('PAMCode'))
            except errors.DuplicateKeyError as dup_error:
                logging.error("%s", dup_error)

    logger.info("\n \n \n \t \t All were gotten!!!")
    logger.info("Time of getting List of Firms of %s is: %s",
                date, datetime.datetime.now())


getter(date='')
today = datetime.date.today()
logger.info(datetime.datetime.now())
getter(date=today)
logger.info("Ending Time of getting List of Registered Firms in Today: %s",
            datetime.datetime.now())
