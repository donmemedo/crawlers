from pydantic import BaseSettings


class Settings(BaseSettings):
    VERSION = ""
    MONGO_CONNECTION_STRING = "mongodb://root:root@mongo-marketer.stg-marketer-db.svc.cluster.local:27017/"
    MONGO_DATABASE = "brokerage"
    CUSTOMER_COLLECTION = "customers"
    FIRMS_COLLECTION = "firms"
    TRADES_COLLECTION = "trades"


setting = Settings()

