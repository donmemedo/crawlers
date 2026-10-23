"""Regression tests for the crawlers: no network, no MongoDB server, no writes to /etc/hosts.

Run: pip install -r requirements.txt pytest mongomock && pytest -q
"""
import builtins
import importlib
import os
import runpy
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from bson import ObjectId
from pymongo import errors

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Forced, not setdefault: a developer's real environment must never reach these tests.
# logger.py ships DEBUG records over UDP to SPLUNK_HOST:SPLUNK_PORT, so point it at a local sink.
_sink = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_sink.bind(("127.0.0.1", 0))
os.environ["SPLUNK_HOST"] = "127.0.0.1"
os.environ["SPLUNK_PORT"] = str(_sink.getsockname()[1])
os.environ["MONGO_CONNECTION_STRING"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100"

import hosts  # noqa: E402  (must come after the env above)


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = {} if body is None else body

    def json(self):
        return self._body


class FakeCollection:
    """Like pymongo: insert_one stamps _id on the caller's dict before the server can reject it."""

    def __init__(self, duplicate_keys=()):
        self.duplicate_keys = list(duplicate_keys)
        self.inserted, self.replaced, self.deleted = [], [], []

    def insert_one(self, record):
        record.setdefault("_id", ObjectId())
        if record.get("PAMCode") in self.duplicate_keys:
            raise errors.DuplicateKeyError("duplicate")
        self.inserted.append(record)

    def replace_one(self, flt, record, upsert=False):
        assert "_id" not in record, "mongo rejects a replacement carrying a different _id"
        self.replaced.append((flt, record))

    def delete_one(self, flt):
        self.deleted.append(flt)


def paged_api(total, calls=None):
    """Fake tadbirwrapper list endpoint: pageSize=1 is the count probe, other sizes return real pages."""

    def fake_get(url, params=None, timeout=None):
        index, size = params["request.pageIndex"], params["request.pageSize"]
        if calls is not None:
            calls.append((index, size))
        if size == 1:
            return Resp(200, {"TotalRecords": total, "Result": []})
        start = index * size
        rows = [{"PAMCode": str(i)} for i in range(start, min(start + size, total))]
        return Resp(200, {"TotalRecords": total, "Result": rows})

    return fake_get


@pytest.fixture(params=["customer", "firm"])
def paged(request, monkeypatch):
    module = importlib.import_module(request.param)
    monkeypatch.setattr(module, "collection", FakeCollection())
    return module


@pytest.mark.parametrize("size,total", [(10, 0), (10, 25), (5, 11), (50, 100)])
def test_pagination_fetches_every_record_for_any_page_size(paged, monkeypatch, size, total):
    monkeypatch.setattr(paged.requests, "get", paged_api(total))
    paged.getter(size=size, date="2024-01-01")
    assert len(paged.collection.inserted) == total


@pytest.mark.parametrize("fail_on", ["probe", "page"])
def test_http_error_fails_the_job(paged, monkeypatch, fail_on):
    def fake_get(url, params=None, timeout=None):
        if params["request.pageSize"] == 1 and fail_on == "page":
            return Resp(200, {"TotalRecords": 3})
        return Resp(500)

    monkeypatch.setattr(paged.requests, "get", fake_get)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        paged.getter(date="2024-01-01")
    assert paged.collection.inserted == []


def test_null_result_is_an_empty_page(paged, monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return Resp(200, {"TotalRecords": 3, "Result": None})

    monkeypatch.setattr(paged.requests, "get", fake_get)
    paged.getter(date="2024-01-01")
    assert paged.collection.inserted == []


def test_duplicate_is_replaced_not_deleted_and_reinserted(paged, monkeypatch):
    paged.collection.duplicate_keys = ["7"]
    monkeypatch.setattr(paged.requests, "get", paged_api(10))
    paged.getter(date="2024-01-01")
    assert [flt for flt, _ in paged.collection.replaced] == [{"PAMCode": "7"}]
    assert paged.collection.deleted == []


def test_duplicate_without_a_plain_key_never_reaches_a_mongo_filter(paged, monkeypatch):
    hostile = [{"name": "no key"}, {"PAMCode": {"$ne": None}}, {"PAMCode": ["a"]}]
    paged.collection.duplicate_keys = [None, {"$ne": None}, ["a"]]

    def fake_get(url, params=None, timeout=None):
        return Resp(200, {"TotalRecords": 3, "Result": hostile})

    monkeypatch.setattr(paged.requests, "get", fake_get)
    paged.getter(size=10, date="2024-01-01")
    assert paged.collection.replaced == [] and paged.collection.deleted == []


def test_replace_after_failed_insert_leaves_exactly_one_document(monkeypatch):
    mongomock = pytest.importorskip("mongomock")
    customer = importlib.import_module("customer")
    coll = mongomock.MongoClient()["brokerage"]["customers"]
    coll.create_index("PAMCode", unique=True)
    coll.insert_one({"PAMCode": "1", "version": 1})
    monkeypatch.setattr(customer, "collection", coll)

    def fake_get(url, params=None, timeout=None):
        return Resp(200, {"TotalRecords": 1, "Result": [{"PAMCode": "1", "version": 2}]})

    monkeypatch.setattr(customer.requests, "get", fake_get)
    customer.getter(size=10, date="2024-01-01")
    assert coll.count_documents({}) == 1
    assert coll.find_one({"PAMCode": "1"})["version"] == 2


def test_trades_http_error_fails_the_job(monkeypatch):
    trades = importlib.import_module("trades")
    monkeypatch.setattr(trades.requests, "get", lambda *a, **k: Resp(500))
    with pytest.raises(RuntimeError, match="HTTP 500"):
        trades.get_trades_list(page_index=0, selected_date="2024-01-01")


def test_trades_stops_when_the_api_repeats_its_last_page(monkeypatch):
    trades = importlib.import_module("trades")
    monkeypatch.setattr(trades, "collection", FakeCollection(), raising=False)
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params["request.pageIndex"])
        assert len(calls) < 20, "getter keeps paging an API that never returns an empty page"
        return Resp(200, {"TotalRecords": 120, "Result": [{"TradeNumber": i} for i in range(50)]})

    monkeypatch.setattr(trades.requests, "get", fake_get)
    trades.getter()
    assert len(calls) <= 4


def test_pin_host_is_idempotent_and_keeps_existing_lines(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost")  # no trailing newline
    hosts.pin_tadbir_host(str(hosts_file))
    hosts.pin_tadbir_host(str(hosts_file))
    assert hosts_file.read_text().splitlines() == ["127.0.0.1 localhost", hosts.HOSTS_LINE]


def test_pin_host_never_fails_the_job(tmp_path):
    hosts.pin_tadbir_host(str(tmp_path))  # a directory: open() raises OSError, like a non-root /etc/hosts


def test_importing_the_crawlers_does_not_touch_etc_hosts(monkeypatch):
    real_open = builtins.open

    def guarded(file, *args, **kwargs):
        assert str(file) != "/etc/hosts", "import-time /etc/hosts write"
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
    for name in ("customer", "firm", "trades"):
        sys.modules.pop(name, None)
        importlib.import_module(name)


class _EmptyDb:
    def __getitem__(self, _):
        return self

    def find(self, *_args, **_kwargs):
        return []


def test_assets_shard_with_nothing_to_do_finishes_cleanly(monkeypatch):
    # used to end with ZeroDivisionError (timer / j with j == 0) after all the work was done
    monkeypatch.setattr("pymongo.MongoClient", lambda *a, **k: _EmptyDb())
    monkeypatch.setattr("hosts.pin_tadbir_host", lambda *a, **k: None)
    runpy.run_path(str(ROOT / "assets" / "assets0.py"), run_name="__main__")


def test_assets_scripts_import_the_way_the_cronjobs_launch_them():
    # CronJobs run `python3 /usr/src/app/assets/assetsN.py`: sys.path[0] is assets/, so logger/config/hosts
    # (repo root) only resolve through PYTHONPATH, which the Dockerfile must set.
    assert "ENV PYTHONPATH=/usr/src/app" in (ROOT / "Dockerfile").read_text()
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    done = subprocess.run(
        [sys.executable, "-c", "import assets0"], cwd=ROOT / "assets", env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0, done.stderr
