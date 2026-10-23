# LAST Report: crawler audit-and-fix pass

Date: 2026-10-23. Branch `fix/crawler-hardening` (base `ea30521`). Repository is public, so this report describes
security findings by class only: no credential values, locations or exploit steps.

## 1. Outcome in one paragraph
The project is a small Python 3.9 / MongoDB crawler run as Kubernetes CronJobs, not a web application. The
FastAPI + Next.js, Docker Compose, light/dark, EN/FA + RTL and PWA parts of the generic workflow therefore do **not**
apply and were not built (the workflow itself says not to force a stack onto a project it does not fit). The pass
instead audited the real code, fixed the verified defects that were safe to fix, added a regression suite that fails
on the pre-fix code, and wrote down what needs an owner decision. Nothing was deployed or run against any real system.

## 2. Chronological log
1. Read `CLAUDE.md`, policy docs, README, all Python, `Dockerfile`, `.gitlab-ci.yml`, the three CronJob manifests and git history.
2. Ran the three required reviews (section 4). Built a graphify graph; found 19 copies of `get_database()` and 16 near-identical `assets` scripts.
3. Reproduced the first defect: `python3 assets/assets0.py` fails with `ModuleNotFoundError: No module named 'logger'`.
4. Triage agent routed the task `deep`, risk `high`, specialist `tech-lead`. 18 more agents reviewed read-only against a shared brief; the verifier ran last (section 5).
5. Baseline scans (section 8): ruff, bandit, `pip-audit`.
6. Created the feature branch and made six commits (section 6), verifying each with tests (red to green per commit).
7. Independent `verifier` pass (PASS, section 12). It showed the first draft of the change description was incomplete;
   two follow-up commits closed the silent paths it found (null `Result`, understated trade totals) and hardened the hosts pin.
8. Wrote README, `HANDOFF.md` and this report; refreshed the graph with `graphify update .` (606 nodes, 913 edges).

## 3. Scope decisions
- Fixed in code: defects that were reproduced or verified by reading, with a test, and whose change is local and revertible.
- Reported only: anything that needs credentials rotation, a cluster, a registry, a pipeline or an owner decision.
- Not applicable (no UI exists): Persian UX vocabulary reference, `apple-design`, light/dark, RTL, PWA/APK/IPA, FastAPI skills.
- Credentials: deliberately **not** edited (removing a default without rotating gives false assurance); see `HANDOFF.md` D1.

## 4. Commands and skills (status = what the evidence shows)
| Item | Status | Evidence |
| --- | --- | --- |
| `/graphify .` | RAN, with one deliberate deviation | AST pass over 31 code files: 367 nodes / 797 edges; graph 380 nodes, 665 edges, 55 communities. LLM semantic extraction of the 52 bootstrap `.claude`/docs files was skipped (cost, little value for this code); `graphify-out/` is untracked and not committed. Health check warned (133 dangling, 132 collapsed edges), all from repeated YAML keys in the manifests. `graphify query` was used afterwards. |
| `/ponytail:ponytail` | RAN | Registered under the namespaced alias `ponytail:ponytail`; skill loaded, mode active (full). |
| `/ponytail-review` | RAN (registered as `ponytail:ponytail-review`) | No tracked diff existed at the start, so it reviewed the tracked code. Findings: `assets/assets1..f.py` are copies of `assets0.py` (4 diff lines each): collapse to one script, about -1,900 lines; `assets/config.py` byte-identical to `config.py` (removed in this PR); `customer.py`/`firm.py` near-duplicates; 19 copies of `get_database()`. The consolidation was not applied because it needs manifest changes. |
| Specialist skills | Loaded as guidance inside the agents; **no agent had a Skill tool**, so none was "invoked" as a tool call. Scanners the skills describe (trivy, hadolint, gitleaks) are not installed and did not run. |

## 5. Agents that actually participated (20 of 20 configured)
`triage`, `deep`, `tech-lead`, `product-owner`, `escalate`, `prototyper`, `build`, `builder`, `quick`, `sweeper`,
`maintainer`, `grower`, `qa-qc`, `qa-qc-lead`, `blue-team`, `blue-team-lead`, `red-team`, `red-team-lead`,
`security-auditor`, `verifier`. Each returned a report; all ran read-only except for one lesson line in its own
`MEMORY.md`. One red-team attempt was stopped by a safety classifier and was redone at weakness-class level.

| Role | Main contribution |
| --- | --- |
| triage | route `deep` / risk `high` / checks tests, lint, review; fix vs report split |
| product-owner | acceptance criteria per fix; trades window is an owner question (D2) |
| tech-lead | PYTHONPATH in the Dockerfile over code changes; defer consolidation; do not touch credentials in code yet |
| deep | dependency-ordered plan, rollback notes, top risks of the fixes (retry amplification, `_id` stability) |
| escalate | duplicate-key hazards: null/object `PAMCode` in a filter; unique-index assumption; do not create indexes at start-up |
| prototyper | found the `ZeroDivisionError` at the end of every assets run; unlabeled/misleading logs |
| build, builder | concrete diffs and the regression-suite design (both ran their prototypes offline) |
| quick, sweeper | lint scope (pinned errors-only rules); duplication quantified; regression root cause (`dd8522a`); config shadowing by the copied `assets/config.py` |
| maintainer | dependency/CI hygiene, the `deploy-pro` empty-tag bug, `--build-arg` is inert (correcting an assumption in the brief) |
| grower | no analytics exist; proposed a one-line run summary (not implemented) |
| qa-qc, qa-qc-lead | executed failure-case matrix (500, timeout, bad JSON, null Result, duplicate, Mongo down); infinite trades loop reproduced |
| blue-team, blue-team-lead | image/manifests hardening list with effort/risk; no `.dockerignore`; what can and cannot be verified locally |
| red-team, red-team-lead | upstream-response trust boundary, attack tree, threat-intel lifecycle note (static; no pentest) |
| security-auditor | independent audit with evidence strength per finding |

## 6. Changes made
See `HANDOFF.md` for the table with risk per commit. Files: `hosts.py` (new), `customer.py`, `firm.py`, `trades.py`,
16 x `assets/assets*.py`, `assets/config.py` (deleted), `Dockerfile`, `.dockerignore` (new), `.gitlab-ci.yml`,
`ruff.toml` (new), `tests/test_crawlers.py` (new), README, HANDOFF.

## 7. Findings and disposition
| # | Finding | Severity | Disposition |
| --- | --- | --- | --- |
| 1 | Database credentials in tracked config and manifests of a public repo | critical | Reported (D1). Rotation required. |
| 2 | assets scripts cannot import `logger` when launched as the CronJobs launch them | high (dev) | Fixed (`PYTHONPATH`) + test |
| 3 | `/etc/hosts` appended at import time (duplicate lines, crashes non-root, forces root) | medium | Fixed (helper under `__main__`) + test. Root still needed until `hostAliases` exist. |
| 4 | Duplicate handling deletes then inserts; unguarded filter value from API | high | Fixed (`replace_one`, key guard, `_id` pop) + test incl. mongomock |
| 5 | Page count hard-coded 10 | low | Fixed + test |
| 6 | HTTP errors swallowed, jobs exit 0 | high | Fixed (raise); behavior change, see D4 |
| 7 | trades fetches yesterday, text says today | medium | Wording fixed; window is D2 |
| 8 | 19 copies of `get_database()`, 16 copied scripts | medium | Reported (follow-up 5) |
| 9 | assets run ends in `ZeroDivisionError` | high (dev) | Fixed + test |
| 10 | bare `except:` swallows errors | medium | Fixed (logged `RequestException`) |
| 11 | trades paging loop is unbounded | high | Fixed + test |
| 12 | `deploy-pro` on a non-tag `main` pipeline writes an invalid image | high | Fixed (guard), validated by simulation, pipeline not run |
| 13 | No `.dockerignore`: history, manifests and tooling ship in the image | high | Fixed (not build-tested) |
| 14 | Dependencies pinned to versions with reported advisories; unused pins | high | Reported; needs a canary (follow-up 3) |
| 15 | Manifests: `batch/v1beta1`, no limits/securityContext/concurrencyPolicy, plaintext env | high | Reported (follow-up 2) |
| 16 | CI: plaintext registry, credentials in URLs, no tests, sonar on wrong image | medium | Reported (follow-up 1, 4) |
| 17 | Logs: DEBUG over plaintext UDP, per-record identifiers, dead config | medium | Reported (follow-up 6) |

## 8. Tests, scans, build: what really ran
All on Python 3.12.3 in a scratch venv (pydantic 1.10.26, pymongo 4.19.0, pytest 9.1.1); the image uses 3.9.
| Command | Result |
| --- | --- |
| `pytest -q -p no:cacheprovider` | **33 passed** (26 after the first six commits, 33 after the verifier follow-ups) |
| same 26-test suite per commit (`git archive` exports) | 15 failed -> 14 -> 8 -> **0 failed** across the four main code commits; against the untouched base: 6 failed, 18 errors (the errors are the import-time `/etc/hosts` crash) |
| author's mutation checks on scratch copies | 4 of 4 caught (drop `_id` pop, drop `PAMCode` guard, unbound the trades loop, hard-code page size 10); the verifier then ran 18 more, all caught |
| `ruff check .` (pinned E4,E7,E9,F) | all checks passed. Baseline with default rules: 86 findings (PIE790 x32, I001 x20, E722 x16, F841 x16, PIE808 x2) |
| `bandit -r` | baseline 0 issues over 2,131 lines; product code 0 after the change (Low findings only for `assert`/`subprocess` in the tests) |
| `pip-audit` on the exact versions pip resolves from `requirements.txt` | advisories reported for `requests`, `pymongo`, `pydantic`, `black`, `certifi`, `dnspython`, `idna`, `urllib3`; unpinned `khayyam`, `python-json-logger`, `splunk-handler`, `uvicorn` were not audited |
| added-line secret check on the diff | 0 credential-shaped strings, 0 secret assignments |
| CI guard simulation | empty tag exit 1, manifest unchanged; tag `v1.2.3` exit 0 |
| `docker build` / compose | **not run**: no Docker daemon, private base-image registry unreachable, and there is no compose file (not a web app) |
| hadolint / trivy / gitleaks | **not run** (not installed) |
| penetration test / DAST | **not run**: no HTTP service exists and no external target was authorized; the red-team work was a static review |
| GitLab pipeline, cluster, real MongoDB, real API | **not run** |

## 9. Security summary (class level)
Highest-value cuts, in order: rotate the database credentials and move them to Secrets; protect CI variables and
restrict the build job; treat API responses as untrusted before they reach a Mongo filter (done for the duplicate path);
pin and upgrade dependencies with a canary; run as non-root once `hostAliases` replace the `/etc/hosts` write.
Attack-tree classes considered: credential exposure (repository, CI, image layers), upstream/DNS tampering, build
supply chain, blind monitoring (UDP logs, jobs that exit 0 on failure), availability (unbounded loops, retries).
Threat-intel lifecycle to adopt: secret scanning over full history in CI, weekly `pip-audit` plus advisory feeds,
CI-variable exposure review, owner-only dissemination.

## 10. Performance
Not measured (no API or database available). Design expectations only: one write instead of two on the duplicate
path; at most `total // 50 + 2` requests per trades run instead of unbounded; no extra requests for the default page size.

## 11. Risks of this change set
- The fail-loud commit can multiply crawls through retries until `backoffLimit`/`concurrencyPolicy` are tuned (D4).
- `replace_one` keeps the stored `_id`; the old delete+insert re-stamped it. A consumer relying on `_id` ordering would notice (unverified).
- The first dev image build wakes up 16 dormant assets jobs (D7).
- `.dockerignore` and the Dockerfile line were reasoned about but not built.

## 12. Verifier verdict
**PASS** from the independent read-only `verifier` (no blocking defect), with these caveats:
- It exported the base commit and ran the suite there (6 failed, 18 errors; the errors are mostly the import-time
  `/etc/hosts` crash), then mutation-tested a copy of HEAD with **18 single-fix reversions: all 18 were caught**.
- A differential run of base vs HEAD with an API stub gave byte-identical call sequences and insert counts for the
  default page size (customers/firms at 11 totals, trades at 7), so the only intended difference is error handling.
- Added-line secret scan over all commits: no credential-shaped strings, no secret keywords; the only added IPs are
  loopback and the pre-existing internal address.
- `.dockerignore` excludes none of the 23 runtime files (path-matching script); not build-tested.
- It found that my claim "the only behavior change is raising on HTTP errors" was incomplete and found two
  hardening gaps in `hosts.py`. All were then addressed in the last two commits (null `Result` handling, loud failure when
  `TotalRecords` is understated, exact-entry matching and non-UTF-8 tolerance in the hosts pin) and are listed in
  `HANDOFF.md`. After those fixes the suite is 33 tests, all passing, ruff clean (re-run by the author, not
  re-verified by the verifier).
- Still unverified: Python 3.9 and the pinned dependencies, docker build/runtime, real MongoDB indexes, the real
  API, downstream reliance on `_id` stability; CI does not run the tests and the `mongomock` test is skipped when
  `mongomock` is not installed.

## 13. Remaining work
See `HANDOFF.md`: decisions D1 to D7 and follow-ups 1 to 7.

## 14. Git / PR
Eight code/CI commits plus one documentation commit on `fix/crawler-hardening`. The pull request is opened after this
report is committed; its URL is in the repository's pull request list. Untracked bootstrap files (`.claude/`, `CLAUDE.md`, other `docs/*`, `scripts/`,
`setup-claude-project.sh`) and `graphify-out/` were not staged.
