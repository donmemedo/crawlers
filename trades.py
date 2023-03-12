"""Get the Trades List from the TadbirWrapper

Raises:
    RuntimeError: Server error when getting the trades list (500)
    OR the trades have Duplicity in Trades

Returns:
    Collection : Unique Trades.
"""
import logging
from datetime import date, datetime, timedelta
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


def get_trades_list(page_size=50, page_index=0, selected_date="2022-12-31"):
    """Getting List of Trades in Selected Date

    Args:
        page_size (int, optional): Page Size in Pagination of Results. Defaults to 50.
        page_index (int, optional): Page Index in Pagination of Results. Defaults to 0.
        selected_date (str, optional): Selected Date. Defaults to "2022-12-31".

    Raises:
        RuntimeError: Server Error.

    Returns:
        Records: List of Trades in JSON.
    """
    req = requests.get(
        "https://tadbirwrapper.tavana.net/tadbir/GetDailyTradeList",
        params={'request.date': selected_date, 'request.pageIndex': page_index,
                'request.pageSize': page_size},
        timeout=100)
    if req.status_code != 200:
        logging.critical("Http response code: %s", req.status_code)
        return "", 0
    response = req.json()
    return response.get("Result"), response.get("TotalRecords")


def getter():
    """Getting List of Trades in Today.
    """
    logger.info(datetime.now())
    page_index = 0
    logger.info("Getting trades of %s", date.today())
    while True:
        response, total = get_trades_list(page_index=page_index,
                                          selected_date=date.today() - timedelta(1))
        if not response:
            logger.info("\t \t \t List is Empty!!!")
            break
        logger.info("Page %d of %d Pages", page_index + 1, 1 + total // 50)
        for record in response:
            try:
                collection.insert_one(record)
                logger.info(
                    "Added: %s, %s, %s \n", record.get("TradeNumber"),
                    record.get("TradeDate"), record.get("MarketInstrumentISIN"))
                logger.info("TradeNumber %s added to mongodb", record.get('TradeNumber'))
            except errors.DuplicateKeyError as dupp_error:
                logging.error("%s", dupp_error)
        logger.info("\t \t All were gotten!!!")
        logger.info("Time of getting List of Trades of %s is: %s",
                    date.today(), datetime.now())
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
    collection = db[setting.TRADES_COLLECTION]
    getter()
    logger.info("Ending Time of getting List of Trades in Yesterday: %s", datetime.now())
