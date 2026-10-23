"""Get the Customers List from the TadbirWrapper

Raises:
    RuntimeError: Server error when getting the customers list (500) 
    OR the customers have Duplicity in Customers

Returns:
    Collection : Unique customers.
"""
import datetime
from logger import logger
import requests
from pymongo import MongoClient, errors
from config import setting
from hosts import pin_tadbir_host


def get_database():
    """Getting Database

    Returns:
        Database: Mongo Database
    """
    connection_sting = setting.MONGO_CONNECTION_STRING
    client = MongoClient(connection_sting)
    database = client[setting.MONGO_DATABASE]
    return database

logger.debug("it has been started to log...")

brokerage = get_database()
collection = brokerage[setting.CUSTOMER_COLLECTION]


def getter(size=10, date="2023-01-31"):
    """Getting List of Customers in Actual Date

    Args:
        size (int, optional): Page Size in Pagination of Results. Defaults to 10.
        date (str, optional): Date. Defaults to "2023-01-31".
    """
    temp_req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetCustomerList",
        params={'request.date': date, 'request.pageIndex': 0,
                'request.pageSize': 1},
        timeout=100)
    if temp_req.status_code != 200:
        logger.critical("Http response code: %s", temp_req.status_code)
        raise RuntimeError(f"GetCustomerList count for {date} failed: HTTP {temp_req.status_code}")
    total_records = temp_req.json()["TotalRecords"]
    logger.info("\t  \t  \t  %s \t  \t  \t  %s", date, total_records)
    pages = total_records // size + 1
    for page in range(pages):
        logger.info("Getting Page %d from %d pages", page + 1, pages)
        req = requests.get(
            "https://tadbirwrapper.tavana.net/tadbir/GetCustomerList",
            params={'request.date': date, 'request.pageIndex': page,
                    'request.pageSize': size},
            timeout=100
        )
        if req.status_code != 200:
            logger.critical("Http response code: %s", req.status_code)
            raise RuntimeError(f"GetCustomerList page {page} for {date} failed: HTTP {req.status_code}")
        records = req.json().get("Result") or []
        for record in records:
            if record is None:
                logger.info("Record is empty.")
                continue
            try:
                collection.insert_one(record)
                logger.info("Record %s added to Mongodb", record.get('PAMCode'))
            except errors.DuplicateKeyError as dup_error:
                logger.error("%s", dup_error)
                pam_code = record.get('PAMCode')
                if pam_code is None or isinstance(pam_code, (dict, list)):
                    # a missing or operator-shaped upstream value must never become a Mongo filter
                    logger.error("Duplicate record without a plain PAMCode was not updated")
                    continue
                record.pop('_id', None)  # the failed insert_one stamped a new _id; replace cannot change the stored one
                collection.replace_one({"PAMCode": pam_code}, record, upsert=True)
                logger.info("Record %s was Updated", pam_code)


    logger.info("\n \n \n \t \t All were gotten!!!")
    logger.info("Time of getting List of Customers of %s is: %s", date, datetime.datetime.now())


if __name__ == "__main__":
    pin_tadbir_host()
    today = datetime.date.today()
    logger.info(datetime.datetime.now())

    getter(date=today)
    logger.info("Ending Time of getting List of Registered Customers in Today: %s",
                datetime.datetime.now())
    getter(date=today-datetime.timedelta(1))
    logger.info("Ending Time of getting List of Registered Customers in Yesterday: %s",
                datetime.datetime.now())
