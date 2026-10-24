
# Project: Crawler
Small Python cron jobs that pull ***Customers***, ***Firms***, ***Trades*** and per-customer ***Assets*** from the
TadbirWrapper API and write them into the MongoDB database **"brokerage"**. They run as Kubernetes CronJobs
(`deployment/<env>/<env>.yaml`); there is no web server or UI.

| Script | What it fetches | Collection(s) |
| --- | --- | --- |
| `customer.py` | customers registered today, then yesterday | `customers` |
| `firm.py` | firms for an empty date, today, then yesterday | `firms` |
| `trades.py` | trades of **yesterday** (`today - 1 day`) | `trades` |
| `assets/assets0.py` ... `assetsf.py` | assets of one shard (last hex digit of the `pamcodes` `_id`) of the PAM codes | `momentaryassets`, `remain` |

The `assets*.py` files are copies of one script that differ only in `group_sep`. They are only deployed in `dev`.

## Behavior worth knowing
- A non-200 answer from the API raises `RuntimeError`, so the job exits non-zero and Kubernetes retries it
  (`backoffLimit`). It used to log `critical` and exit 0.
- Re-running is safe only if the collections have a unique index (`PAMCode` for customers/firms, `TradeNumber`
  for trades). No code creates those indexes: check them in MongoDB. On a duplicate key customers/firms are
  replaced in place (`replace_one`), trades are skipped.
- `hosts.pin_tadbir_host()` pins `tadbirwrapper.tavana.net` in `/etc/hosts` when the process can write it
  (the container runs as root) and is a no-op otherwise.

## Configuration
`config.py` reads environment variables (pydantic `BaseSettings`); the CronJobs set `MONGO_CONNECTION_STRING`.

| Variable | Meaning |
| --- | --- |
| `MONGO_CONNECTION_STRING` | MongoDB URI. Always set it explicitly; do not rely on the default. |
| `MONGO_DATABASE`, `CUSTOMER_COLLECTION`, `FIRMS_COLLECTION`, `TRADES_COLLECTION` | names (defaults: `brokerage`, `customers`, `firms`, `trades`) |
| `SPLUNK_HOST`, `SPLUNK_PORT` | UDP syslog target of `logger.py` (JSON logs) |

## Run
```bash
pip install -r requirements.txt
MONGO_CONNECTION_STRING=... python3 customer.py   # or firm.py / trades.py
```
In the image the app lives in `/usr/src/app` and `PYTHONPATH` points there, so `assets/assetsN.py` can import
`logger`, `config` and `hosts` from the app root.

## Tests and lint
```bash
pip install -r requirements.txt pytest mongomock ruff
pytest -q          # no network, no MongoDB server, never writes /etc/hosts
ruff check .
```
`.gitlab-ci.yml` has no test stage yet.

## Notes for maintainers
See `HANDOFF.md` for open decisions and the prioritized follow-ups (secrets, manifests, dependencies).
