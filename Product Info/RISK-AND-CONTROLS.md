# OvaDue PoC risk register and control map

ISO 27001 is a **management system**, not a Streamlit feature. This file lists the assets, the risks we accept as a PoC, and the technical/process controls we actually operate. It is **not** a Statement of Applicability and does not claim certification.

## Assets

| Asset | Owner (PoC) | Location |
|---|---|---|
| Application code | Operator / this GitHub repo | Host + `github.com/uberslaw/OvaDue` |
| SQLite history | Operator | `data/ovadue.db` |
| HP Excel snapshots | Operator | `uploads/`, `imported data/` |
| Delivered-order flags | Shared LAN users | `data/delivered_orders.json` |
| Launch Control / deploy scripts | Operator | `scripts/` |
| Windows host | Operator / whoever owns the PC | Typically `C:\OvaDue` |

## Risks we accept (until Arup approval)

| ID | Risk | Why accepted |
|---|---|---|
| R1 | No SSO / MFA / RBAC — anyone on the LAN who can open `:8501` sees all orders | No Entra app registration or corporate cert is available |
| R2 | HTTP on the LAN (MITM if the LAN is hostile) | Corporate TLS needs an Arup certificate; self-signed TLS would break browsers |
| R3 | Single host, single SQLite file, single operator | PoC scale; HA would be a different system |
| R4 | Shared “mark delivered” with no user identity | No login to attribute |
| R5 | Excel parsers (`xlrd` / `openpyxl`) if an untrusted file is dropped in `uploads\` | Inbox is operator-trusted |

## Risks we mitigate now

| ID | Risk | Control |
|---|---|---|
| R6 | Package-and-Push ships a broken app (missing `ovadue/` / `pages/`) | `deploy/package-include.json` include list + layout health check |
| R7 | Search `*` / regex crash | Literal `series_contains` (`regex=False`) |
| R8 | HTML injection from report fields | `html_text()` on `unsafe_allow_html` interpolations |
| R9 | CSV dump of addresses and prices | Allow-list export in `ovadue/safe.py` |
| R10 | SQLite lock on refresh | WAL + `busy_timeout` |
| R11 | No recoverable copy of the DB | Local `data\backups`, Test restore, optional daily Task Scheduler job |
| R12 | Unpinned / unscanned dependencies | Pinned `requirements.txt`, CI `pip-audit`, Dependabot |
| R13 | Charts fail offline (Plotly CDN) | Load Plotly JS from the installed Python package |
| R14 | Oversized / unexpected ingest | 50 MB Excel cap; `.xls`/`.xlsx` only |
| R15 | No operator trail | `data/ovadue-app.log` for import, prune, mark-delivered, plus deploy log |
| R16 | Stale backups unnoticed | Check & Repair warns if no backup or last zip > 48 hours |

## Annex A themes (mapping, not a SoA)

| Theme | What we do on this PoC |
|---|---|
| Access control | Network trust to the host; no app accounts. Documented in [DATA.md](DATA.md). |
| Cryptography | Host BitLocker if the Windows image has it. No app-level field encryption. HTTP on LAN. |
| Operations / backups | Local zip backups, tested restore, 14-zip retention. Migration pack for machine move. |
| Logging | App + Streamlit + deploy logs on disk. No SIEM. |
| Vulnerability / suppliers | Pinned deps, `pip-audit`, Dependabot. Inventory below. |
| Incident management | [RUNBOOK.md](RUNBOOK.md). No pager. |
| Supplier / license | Permissive OSS (BSD/MIT/Apache). `xlrd` is legacy, required for `.xls`. |
| Continual improvement | GitHub CI on each push; update this register when a control changes. |

## Dependency inventory

| Package | Role | License (typical) |
|---|---|---|
| streamlit | Web UI | Apache-2.0 |
| pandas | Tables | BSD-3 |
| plotly | Charts | MIT |
| openpyxl | `.xlsx` | MIT |
| xlrd | Legacy `.xls` | BSD |
| streamlit-js-eval | Browser timezone / JS helpers | MIT |
| streamlit-autorefresh | Hourly import scan | Apache-2.0 |

Outbound services: **GitHub** (source install), **PyPI** (pip). No payment gateway, no email API, no HP API — reports are files.

## When approval exists

Next enterprise step is **reverse proxy + Entra** in front of this same app (TLS + identity + offboarding). Then revisit R1, R2, and R4. Do not rewrite scoring to get there.
