"""Get the Firms List from the TadbirWrapper

Raises:
    RuntimeError: Server error when getting the firms list (500)
    OR the firms have Duplicity in Firms

Returns:
    Collection : Unique firms.
"""
import datetime
# import logging
from logger import logger
import requests
from pymongo import MongoClient, errors
from config import setting


with open("/etc/hosts", "a", encoding='utf-8') as file:
    file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    """Getting Database

    Returns:
        Database: Mongo Database
    """
    connection_string = setting.MONGO_CONNECTION_STRING
    client = MongoClient(connection_string)
    database = client[setting.MONGO_DATABASE]
    return database


# logging.basicConfig(
#     encoding="utf-8",
#     format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
#     level=logging.DEBUG,
# )
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
logger.debug("it has been started to log...")


db = get_database()
collection = db[setting.FIRMS_COLLECTION]


def getter(size=10, date="2023-01-31"):
    """Getting List of Customers in Actual Date

    Args:
        size (int, optional): Page Size in Pagination of Results. Defaults to 10.
        date (str, optional): Date. Defaults to "2023-01-31".
    """
    temp_req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetFirmList",
        params={'request.date': date, 'request.pageIndex': 0,
                'request.pageSize': 1},
        timeout=100)
    if temp_req.status_code != 200:
        logger.critical("Http response code: %s", temp_req.status_code)
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
            logger.critical("Http response code: %s", req.status_code)
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
                logger.error("%s", dup_error)
                collection.delete_one({"PAMCode": record.get('PAMCode')})
                collection.insert_one(record)
                logger.info("Record %s was Updated", record.get('PAMCode'))


    logger.info("\n \n \n \t \t All were gotten!!!")
    logger.info("Time of getting List of Firms of %s is: %s",
                date, datetime.datetime.now())


if __name__ == "__main__":
    getter(date='')
    today = datetime.date.today()
    logger.info(datetime.datetime.now())
    getter(date=today)
    logger.info("Ending Time of getting List of Registered Firms in Today: %s",
                datetime.datetime.now())
    getter(date=today-datetime.timedelta(1))
    logger.info("Ending Time of getting List of Registered Firms in Yesterday: %s",
                datetime.datetime.now())

