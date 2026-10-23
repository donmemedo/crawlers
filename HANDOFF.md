# HANDOFF

Branch `fix/crawler-hardening` (8 code/CI commits plus one documentation commit, on top of `ea30521`). Full evidence: `docs/LAST_Report.md`.

## What changed (each commit is independently revertible)
| Commit | Change | Risk to production |
| --- | --- | --- |
| Make crawlers import-safe and fix the assets import path | `hosts.py` helper replaces the import-time `/etc/hosts` write; `ENV PYTHONPATH=/usr/src/app`; remove duplicate `assets/config.py`; add `.dockerignore` | Low. Same behavior as root. **Image change, not build-tested** (no Docker daemon here). |
| Fix assets crawler failures hidden behind the import crash | no more `ZeroDivisionError` at the end of a shard; bare `except:` replaced by a logged `requests.RequestException` | Low, dev only |
| Make duplicate handling atomic and honor the page size | `replace_one(upsert=True)` instead of delete+insert; operator-shaped/missing `PAMCode` is skipped; page count uses `size` | Low. Default size 10 unchanged. |
| **Fail the job on HTTP errors and bound the trades paging loop** | non-200 raises `RuntimeError` (exit non-zero, k8s retries); trades stops paging after `total // 50 + 2` pages | **Behavior change.** See D4. |
| Add regression tests and a minimal ruff config | 26 tests, `ruff.toml` | None |
| ci: refuse deploy-pro without a tag | guard before the `sed` that rewrites `latest` | Low. Pipeline not run. Manual pro deploys from a plain `main` pipeline are now always refused (they produced an invalid image anyway); `retry: 2` will retry that failure pointlessly. |
| Make the hosts pin match real entries and tolerate odd bytes | a commented-out or look-alike line no longer counts as pinned; non-UTF-8 bytes do not raise | None |
| Keep gaps visible: null Result in range and understated trade totals | customers/firms raise on a null `Result` inside the promised page range; trades raises instead of silently truncating when `TotalRecords` is understated | Same direction as D4 |

Behavior changes beyond the HTTP-error one (called out by the independent verifier):
- A null `Result` on the spare last page is now an empty page (it used to raise `TypeError`); inside the promised range it still fails the job.
- Duplicates use `replace_one`, so the stored `_id` stays stable (delete+insert re-stamped it on every update). Whether any consumer relies on `_id` changing is unverified.
- The trades loop is bounded by `total // 50 + 2` pages and fails loudly past that; the old loop ran until an empty page.

## Decisions needed from the owner
- **D1 Credentials (urgent).** The repository is public and tracked configuration and deployment manifests contain
  database credentials. Treat them as compromised: rotate them, move them to Kubernetes Secrets (`secretKeyRef`),
  give each job a least-privilege user, then remove the default from `config.py`. Editing files does not remove
  them from git history or from anything already pulled, so rotation is the real fix. This PR deliberately does
  not touch them (removing a default without rotating gives false assurance). Values are intentionally not listed here.
- **D2 Trades window.** `trades.py` fetches *yesterday* on every run (the prod schedule runs it during the day, three
  times); README/logs used to say "today". Choose: (a) yesterday once after market close, (b) today intraday,
  (c) rolling today + yesterday like customers/firms (a missed run self-heals). Only the wording was corrected.
- **D3 Unique indexes.** Nothing in the repo creates indexes, yet duplicate handling and re-runs depend on them.
  Run `getIndexes()` on `customers`, `firms`, `trades`, `momentaryassets`, `remain`. Create indexes as a one-off
  migration (de-duplicate first); do not create them at script start-up.
- **D4 Fail-loud on HTTP errors.** Matches the docstrings but changes exit codes. With `backoffLimit: 3` one outage
  can mean four crawls. Consider `backoffLimit: 1`, `concurrencyPolicy: Forbid` and `activeDeadlineSeconds` in the manifests.
  To undo: revert that single commit.
- **D5 `firm.py`** calls `getter(date='')` before today/yesterday. Intent is unknown (kept as is).
- **D6 `assets` `get_national()`** is never called but is the only code that writes `pamcodes.NationalCode`
  (kept as is; make it a documented one-shot rather than deleting it silently).
- **D7 Merge order.** The first dev image built from this branch makes the 16 `assets` CronJobs run for the first time
  since they started crashing on import (commit `dd8522a`). Confirm the dev MongoDB target first.

## Follow-ups, in priority order (not done here)
1. **Secrets** (D1) and CI variables: mark them protected/masked; move SMS credentials out of URLs; `docker login --password-stdin`; drop the inert `--build-arg`.
2. **Manifests** (all 25 CronJobs): `batch/v1beta1` is removed in Kubernetes 1.25, so check the cluster and move to `batch/v1`; add `hostAliases` (then the container can stop being root: `USER`, `runAsNonRoot`, drop the `/etc/hosts` pin), `resources`, `securityContext`, `concurrencyPolicy: Forbid`, `activeDeadlineSeconds`; avoid `:latest`.
3. **Dependencies**: `pip-audit` reports advisories for every pinned runtime package (`requests`, `urllib3`, `certifi`, `idna`, `pymongo`, `pydantic`, `dnspython`) and for `black`. Bump in a separate PR with a dev canary (requests 2.28 pins urllib3 1.x, so they move together; Python 3.9 is end-of-life). Remove unused pins (`splunk-handler`, `DateTime`/`datetime`, `black`, `click` and their dependencies) and the duplicated `pydantic` line.
4. **CI**: add a test stage (`pytest -q`, `ruff check .`); the sonar job runs a .NET image against a Python repo and is allowed to fail.
5. **Consolidate** the 16 `assets*.py` into one script taking the group as an argument (about 1,900 duplicated lines) and share one `get_database()` (19 copies). Needs `dev.yaml` command changes, so it was left out.
6. **Observability**: one summary line per run (job, window, outcome, expected/fetched/inserted/updated, duration); stop logging expected duplicates at ERROR; `logger.py` has dead uvicorn config, a non-existent `modulename` field and colors in `kubectl logs`; `SPLUNK_INDEX` is unused.
7. Validate the API response at the boundary (type and size of `TotalRecords`, allow-listed fields) and cap `.json()` sizes.

## Not verified / not run
`docker build` and anything that needs the private registry or a cluster; a real MongoDB or the real API (no request was sent to any external or internal system); the GitLab pipeline; hadolint/trivy/gitleaks (not installed); a penetration test (static review only). Python 3.9 (the image) was not available locally: tests ran on 3.12.

## Verify locally
```bash
pip install -r requirements.txt pytest mongomock ruff
pytest -q && ruff check .
```
