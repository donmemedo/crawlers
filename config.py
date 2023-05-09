"""Configurations

"""
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Class of Basic Settings

    """
    VERSION = "0.0.1"
    DATABASE_URL = "mongodb://root:1qaz1qaz@localhost:27017/"
    MONGO_DATABASE = "brokerage"
    CUSTOMER_COLLECTION = "customers"
    FIRMS_COLLECTION = "firms"
    TRADES_COLLECTION = "trades"


setting = Settings()
