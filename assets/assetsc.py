import logging
from datetime import datetime
import requests
from pymongo import MongoClient, errors
from khayyam import JalaliDatetime as jd
import time
from config import setting


with open("/etc/hosts", "a", encoding='utf-8') as file:
    file.write("172.20.20.120 tadbirwrapper.tavana.net\n")


def get_database():
    """Getting Database

    Returns:
        Database: Mongo Database
    """
    # connection_string = "mongodb://root:root@172.24.65.106:30001/"
    # client = MongoClient(connection_string)
    # database = client["brokerage"]
    connection_string = setting.MONGO_CONNECTION_STRING
    client = MongoClient(connection_string)
    database = client[setting.MONGO_DATABASE]
    return database


logging.basicConfig(
    encoding="utf-8",
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.debug("it has been started to log...")
db = get_database()


def get_national():
    db = get_database()

    pam_coll = db["pamcodes"]
    cus_coll = db["customers"]
    fir_coll = db["firms"]
    query_result = pam_coll.find({})
    users = dict(enumerate(query_result))
    j = 0
    for i in range(len(users)):
        nat = "000"
        pam = users[i]["PAMCode"]
        if cus_coll.find_one({"PAMCode": pam}, {"_id": False}):
            nat = cus_coll.find_one({"PAMCode": pam}, {"_id": False}).get(
                "NationalCode"
            )
        elif fir_coll.find_one({"PAMCode": pam}, {"_id": False}):
            nat = fir_coll.find_one({"PAMCode": pam}, {"_id": False}).get(
                "NationalIdentification"
            )
        if not nat:
            nat = "000"
            j += 1
        pam_coll.update_one({"PAMCode": pam}, {"$set": {"NationalCode": nat}})


def get_assets(pam="18692280625164", nat="2280625164"):
    db = get_database()
    pam_coll = db["pamcodes"]
    mom_coll = db["momentaryassets"]
    rem_coll = db["remain"]
    try:
        start = time.time()
        temp_req = requests.get(
            "https://tadbirwrapper.tavana.net/tadbir/CustomerAssets",
            params={"nationalCode": nat, "tradeCode": pam},
            timeout=100,
        )
        end = time.time()
    except:
        return
    if temp_req.status_code == 200:
        total_records = temp_req.json()
        momentary_assets = total_records["MomentaryAssets"]
        remain = total_records["Remain"]
        if not momentary_assets:
            return
        remain["CustomerTitle"] = momentary_assets[0]["CustomerTitle"]
        remain["TradeCode"] = momentary_assets[0]["TradeCode"]
        remain["Date"] = datetime.now().date().isoformat()
        remain["JDate"] = jd.now().date().isoformat()

        for record in momentary_assets:
            record["Date"] = datetime.now().date().isoformat()
            record["JDate"] = jd.now().date().isoformat()
            try:
                mom_coll.insert_one(record)
            except errors.DuplicateKeyError as dupp_error:
                logger.error("%s", dupp_error)
                pass
        try:
            rem_coll.insert_one(remain)
        except errors.DuplicateKeyError as dupp_error:
            logger.error("%s", dupp_error)
            pass

    logger.info(end - start)
    return end - start


if __name__ == "__main__":
    # get_national()
    sto = time.time()
    db = get_database()
    pam_coll = db["pamcodes"]
    trades_coll = db["trades"]
    cus_coll = db["customers"]
    fir_coll = db["firms"]

    data0 = []
    query_result = pam_coll.find({})
    data = dict(enumerate(query_result))
    group_sep = "c"
    for i in range(len(data)):
        if str(data[i]["_id"])[23] == group_sep:
            data0.append(data[i])
    timer = 0
    j = 0
    for i in range(len(data0)):
        nat = data0[i]["NationalCode"]
        pam = data0[i]["PAMCode"]
        d = get_assets(pam=pam, nat=nat)
        if d and d > 1:
            timer = timer + d
            j = j + 1
            logger.info(timer / j)
    endo = time.time()
    logger.info(f"Running Average Time for {group_sep} is {timer/j}")
    logger.info(f"Number of {group_sep}s is {j}")
    logger.info(f"Total Running Time for {group_sep} is {endo-sto}")
