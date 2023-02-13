import logging
import datetime
import requests
import os
from pymongo import MongoClient, errors


with open("/etc/hosts", "a") as file:
    file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    CONNECTION_STRING = os.environ.get("DATABASE_URL")
    client = MongoClient(CONNECTION_STRING)
    db = client["brokerage"]
    return db


def get_firm_list(page_size=10, page_index=0, from_date="2023-01-31"):
    req = requests.get(f"https://tadbirwrapper.tavana.net/tadbir/GetFirmList?request.date={from_date}&request.pageIndex={page_index}&request.pageSize={page_size}")
    if req.status_code != 200:
        raise RuntimeError(f"Http response code {req.status_code}")
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


db = get_database()
collection = db["firms"]


def getter(size=10, date="2023-01-31"):
    total_records = requests.get(f"https://tadbirwrapper.tavana.net/tadbir/GetFirmList?request.date={date}&request.pageIndex={0}&request.pageSize={1}").json()["TotalRecords"]
    logger.info(f"\t  \t  \t  {date} \t  \t  \t  {total_records}")
    for i in range(0, total_records // 10 + 1):
        logger.info(f"Getting Page{i+1} from {total_records // 10 + 1} pages")
        records = get_firm_list(size, i, date)

        for record in records:
            if record is None:
                logger.info(f"Record is empty.")
                continue
            else:
                try:
                    collection.insert_one(record)
                    logger.info(f"Record {record.get('PAMCode')} added to Mongodb")
                except errors.DuplicateKeyError as e:
                    logging.error("%s" % e)

    logger.info("\n \n \n \t \t All were gotten!!!")
    logger.info(
        f"Time of getting List of Firms of {date} is: {datetime.datetime.now()}"
    )


#f = open("./dates.txt", "r")
#cc = f.read().splitlines()
#for i in range(len(cc)):
#    getter(date=cc[i])
#print(f"DB was Gotten from {cc[0]} to {cc[len(cc)-1]}")
today = datetime.date.today()
logger.info(datetime.datetime.now())

getter(date=today)
logger.info(
    f"Ending Time of getting List of Registered Firms in Today: {datetime.datetime.now()}"
)
