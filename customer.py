import click
import logging
from pymongo import MongoClient
import requests
from config import setting


with open("/etc/hosts", "a", encoding='utf-8') as file:
   file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    connection_sting = setting.MONGO_CONNECTION_STRING
    client = MongoClient(connection_sting)
    database = client[setting.MONGO_DATABASE]

    return database


logging.basicConfig(
    encoding="utf-8",
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

brokerage = get_database()


@click.command()
@click.option(
    "--date", default="2023-03-23", help="Enter register or modified date of the users"
)
def get_customers_by_date(date):
    CUSTOMER_URL = "https://tadbirwrapper.tavana.net/tadbir/GetCustomerList"
    PAGE_SIZE = 10

    total_request = requests.get(
        CUSTOMER_URL,
        params={
            "request.date": date,
            "request.pageSize": PAGE_SIZE,
            "request.pageIndex": 0,
        },
    )

    total_records = int(total_request.json()["TotalRecords"])
    logger.info(
        f"{total_records} have been registered or modified in Tadbir system on {date}"
    )

    for page_index in range(0, total_records // PAGE_SIZE + 1):
        customer_request = requests.get(
            CUSTOMER_URL,
            params={
                "request.date": date,
                "request.pageSize": PAGE_SIZE,
                "request.pageIndex": page_index,
            },
        )
        customers_list = customer_request.json()["Result"]

        for customer in customers_list:
            if customer is None:
                logger.info(f"Empty record retrived from Tadbir Systems.")
            else:
                user_trade_code = {"PAMCode": customer.get("PAMCode")}
                logger.info(
                    f"New customer {user_trade_code} retrived from Tadbier Systems."
                )

                result = next(brokerage.customers.find(user_trade_code), None)
                
                if result:
                    logger.info(f"User {user_trade_code} has been already stored in the database")
                    brokerage.customers.delete_one(user_trade_code)
                    logger.info(f"User {user_trade_code} deleted")

                brokerage.customers.insert_one(customer)
                logger.info(f"User {user_trade_code} has been updated and stored into database")


if __name__ == "__main__":
    get_customers_by_date()
