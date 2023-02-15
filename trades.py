"""_summary_

Raises:
    RuntimeError: _description_

Returns:
    _type_: _description_
"""
import logging
import os
from datetime import date, datetime, timedelta
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
    db = client["brokerage"]
    return db


def get_trades_list(page_size=50, page_index=0, date="2022-12-31"):
    """_summary_

    Args:
        page_size (int, optional): _description_. Defaults to 50.
        page_index (int, optional): _description_. Defaults to 0.
        date (str, optional): _description_. Defaults to "2022-12-31".

    Raises:
        RuntimeError: _description_

    Returns:
        _type_: _description_
    """
    req = requests.get(
        f"https://tadbirwrapper.tavana.net/tadbir/GetDailyTradeList?request.date={date}&request.pageIndex={page_index}&request.pageSize={page_size}"
    )

    if req.status_code != 200:
        raise RuntimeError(f"Http response code {req.status_code}")

    else:
        response = req.json()

        return response.get("Result"), response.get("TotalRecords")


def getter():
    """_summary_
    """
    logger.info(datetime.now())
    page_index = 0
    logger.info(f"Getting trades of {date.today()}")
    while True:
        response, total = get_trades_list(page_index=page_index, date=date.today())
        if not response:
            logger.info("\t \t \t List is Empty!!!")
            break
        else:
            logger.info(f"Page {page_index+1} of {1+total//50} Pages")
            for record in response:
                try:
                    collection.insert_one(record)
                    logger.info(
                        f'Added: {record.get("TradeNumber")}, {record.get("TradeDate")}, {record.get("MarketInstrumentISIN")} \n'
                    )
                    logger.info(
                        f"TradeNumber {record.get('TradeNumber')} added to mongodb"
                    )
                except errors.DuplicateKeyError as e:
                    logging.error("%s" % e)
            logger.info("\t \t All were gotten!!!")
            logger.info(
                f"Time of getting List of Customers of {date.today()} is: {datetime.now()}"
            )
        page_index += 1


if __name__ == "__main__":
    logging.basicConfig(
        encoding="utf-8",
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.debug("it has been started to log...")

    start_date = date(2023, 1, 23)
    end_date = datetime.now().date()

    db = get_database()
    collection = db["trades"]
    getter()
    logger.info(f"Ending Time of getting List of Trades in Today: {datetime.now()}")
