"""Get the Customers List from the TadbirWrapper

Raises:
    RuntimeError: Server error when getting the customers list (500) 
    OR the customers have Duplicity in Customers

Returns:
    Collection : Unique customers.
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
    connection_sting = os.environ.get("DATABASE_URL")
    client = MongoClient(connection_sting)
    database = client["brokerage"]
    return database


def get_customer_list(page_size=10, page_index=0, from_date="2023-01-31"):
    """_summary_

    Args:
        page_size (int, optional): _description_. Defaults to 10.
        page_index (int, optional): _description_. Defaults to 0.
        from_date (str, optional): _description_. Defaults to "2023-01-31".

    Returns:
        _type_: _description_
    """
    req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetCustomerList",
        params={'request.date': from_date, 'request.pageIndex': page_index,
                'request.pageSize': page_size},
        timeout=100
    )
    if req.status_code != 200:
        logging.critical("Http response code: %s", req.status_code)
        return ""
    response = req.json()
    return response.get("Result")


logging.basicConfig(
    encoding="utf-8",
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.debug("it has been started to log...")

brokerage = get_database()
collection = brokerage["customers"]


def getter(size=10, date="2023-01-31"):
    """_summary_

    Args:
        size (int, optional): _description_. Defaults to 10.
        date (str, optional): _description_. Defaults to "2023-01-31".
    """
    temp_req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetCustomerList",
        params={'request.date': date, 'request.pageIndex': 0,
                'request.pageSize': 1},
        timeout=100)
    if temp_req.status_code != 200:
        logging.critical("Http response code: %s", temp_req.status_code)
        total_records = 0
    else:
        total_records = temp_req.json()["TotalRecords"]
    logger.info("\t  \t  \t  %s \t  \t  \t  %s", date, total_records)
    for i in range(0, total_records // 10 + 1):
        logger.info("Getting Page %d from %d pages", i + 1, total_records // 10 + 1)
        records = get_customer_list(size, i, date)
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
    logger.info("Time of getting List of Customers of %s is: %s", date, datetime.datetime.now())


today = datetime.date.today()
logger.info(datetime.datetime.now())

getter(date=today)
logger.info("Ending Time of getting List of Registered Customers in Today: %s",
            datetime.datetime.now())
