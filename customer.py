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

with open("/etc/hosts", "a") as file:
    file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    """_summary_

    Returns:
        _type_: _description_
    """
    CONNECTION_STRING = os.environ.get("DATABASE_URL")
    client = MongoClient(CONNECTION_STRING)
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
        f"https://tadbirwrapper.tavana.net/tadbir/GetCustomerList?request.date={from_date}&request.pageIndex={page_index}&request.pageSize={page_size}"
    )
    if req.status_code != 200:
        logging.critical(f"Http response code {req.status_code}")
        return ""
    else:
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
    total_records = requests.get(
        f"https://tadbirwrapper.tavana.net/tadbir/GetCustomerList?request.date={date}&request.pageIndex={0}&request.pageSize={1}"
    ).json()["TotalRecords"]
    logger.info(f"\t  \t  \t  {date} \t  \t  \t  {total_records}")
    for i in range(0, total_records // 10 + 1):
        logger.info(f"Getting Page{i+1} from {total_records // 10 + 1} pages")
        records = get_customer_list(size, i, date)

        for record in records:
            if record is None:
                logger.info(f"Record is empty.")
                continue
            else:
                try:
                    collection.insert_one(record)
                    logger.info(
                        f"Record {record.get('PAMCode')} added to Mongodb")
                except errors.DuplicateKeyError as e:
                    logging.error("%s" % e)

    logger.info("\n \n \n \t \t All were gotten!!!")
    logger.info(
        f"Time of getting List of Customers of {date} is: {datetime.datetime.now()}"
    )


today = datetime.date.today()
logger.info(datetime.datetime.now())

getter(date=today)
logger.info(
    f"Ending Time of getting List of Registered Customers in Today: {datetime.datetime.now()}"
)
