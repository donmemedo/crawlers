import logging
from datetime import date, timedelta, datetime
import schedule
import requests
from pymongo import MongoClient, errors



def get_database():
    CONNECTION_STRING = os.environ.get("DATABASE_URL")
    client = MongoClient(CONNECTION_STRING)
    db = client["brokerage"]
    return db


def get_trades_list(page_size=50, page_index=0, date="2022-12-31"):
    req = requests.get(
        f"https://tadbirwrapper.tavana.net/tadbir/GetDailyTradeList?request.date={date}&request.pageIndex={page_index}&request.pageSize={page_size}"
    )

    if req.status_code != 200:
        raise RuntimeError(f"Http response code {req.status_code}")

    else:
        response = req.json()

        return response.get("Result"), response.get("TotalRecords")


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def getter():
    print(datetime.now())
    page_index=0
    while True:
        response, total = get_trades_list(page_index=page_index, date=date.today())
        if not response:
            logger.info("list is empty")
            break
        else:
            print(f'Page {page_index+1} of {1+total//50} Pages')
            for record in response:
                collection.insert_one(record)
                logger.info(f'Added: {record.get("TradeNumber")}, {record.get("TradeDate")}, {record.get("MarketInstrumentISIN")} \n')
                logger.info(f"TradeNumber {record.get('TradeNumber')} added to mongodb")
            print("\t \t All were gotten!!!")
            logger.info(
                f"Time of getting List of Customers of {date.today()} is: {datetime.now()}"
            )
        
        page_index+=1


if __name__ == "__main__":
    logging.basicConfig(
        filename="Trades.log",
        filemode="a",
        encoding="utf-8",
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.debug("it has been started to log...")

    #ToDo: Change Start day to 2023/02/01
    start_date = date(2023, 1, 15)
    end_date = datetime.now()
    

    db = get_database()
    collection = db["trades"]

    for single_date in daterange(start_date, end_date):
        selected_date = single_date.strftime("%Y-%m-%d")
        print(selected_date)
        page_index = 0

        logger.info(f"Getting trades of {single_date}")

        while True:
        # while page_index < 1:
            response, total = get_trades_list(page_index=page_index, date=selected_date)

            if not response:
                logger.info("list is empty")
                break
            else:
                print(f'Page {page_index+1} of {1+total//50} Pages')
                for record in response:
                    collection.insert_one(record)
                    logger.info(f'Added: {record.get("TradeNumber")}, {record.get("TradeDate")}, {record.get("MarketInstrumentISIN")} \n')
                    logger.info(
                        f"TradeNumber {record.get('TradeNumber')} added to mongodb"
                    )
                print("\t \t All were gotten!!!")
                logger.info(
                    f"Time of getting List of Customers of {selected_date} is: {datetime.now()}"
                )
            
            page_index += 1
    getter()
    logger.info(f"Ending Time of getting List of Trades in Today: {datetime.now()}")
    print(f"Ending Time of getting List of Trades in Today: {datetime.now()}")
