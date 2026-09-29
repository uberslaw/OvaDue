# OvaDue architecture (PoC)

OvaDue is a single-tenant, single-host Streamlit dashboard for Arup HP backlog reports. This document is the operator map of the running system. It is not a certified target architecture.

## Process model

```
Office browsers  --HTTP LAN :8501-->  Streamlit (one process)
                                          ^
                                          | start / stop / health / backup
                                    Launch Control (WinForms)
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
             data/ovadue.db      uploads/ + imported data/   data/delivered_orders.json
             (SQLite, WAL)       (.xls / .xlsx snapshots)    (shared "mark delivered")
```

- **UI:** [`app.py`](../app.py) plus [`pages/1_Analysis.py`](../pages/1_Analysis.py).
- **Library:** [`ovadue/`](../ovadue/) (import, scoring, charts).
- **Supervisor:** [`scripts/OvaDue-LaunchControl.ps1`](../scripts/OvaDue-LaunchControl.ps1). Not a Windows service.
- **Bind:** [`/.streamlit/config.toml`](../.streamlit/config.toml) `0.0.0.0:8501`, HTTP. Anyone who can reach that port can use the app.

## Trust boundary

| Inside the host | Outside the host |
|---|---|
| SQLite, Excel archives, delivered-order flags, Launch Control | Browsers on the LAN; GitHub (source); PyPI (install) |

There is **no application login**. Access control is whatever the Windows host and LAN already provide. Corporate TLS / Entra SSO wait until the app is an approved Arup system.

## Data path

1. Operator drops `osreport_ArupBacklog_YYYY-MM-DD_HHMM.xls(x)` into `uploads\`.
2. Open sessions rescan hourly; **Refresh data now** imports immediately.
3. [`ovadue/store.py`](../ovadue/store.py) stores each row as JSON in SQLite, moves the file to `imported data\`, and prunes archives older than 365 days.
4. The dashboard scores and displays history in process memory (`@st.cache_data`).

## What is stateful

- SQLite (`data/ovadue.db`) — WAL + busy timeout so a refresh and a reader do not deadlock as easily.
- `data/delivered_orders.json` — any browser session can toggle it.
- Streamlit `session_state` and browser `localStorage` for filters / appearance only.

One Streamlit process, one database file. Do not run a second instance against the same DB.

## Deploy / rollback

Upgrade packages (`OvaDue_*.zip`) include `app.py`, `ovadue/`, `pages/`, scripts, deploy config, `.streamlit`, and Product Info. Live data paths are preserved (`deploy/package-include.json` → `preserveOnUpgrade`).

Rollback = apply an older `OvaDue_*.zip` via **Upgrade from Push**, or restore data with **Import Migration Pack**.

## If this outgrows one machine

Documented only: Postgres/SQL Server + a reverse proxy + Entra in front of this same app. Do not rewrite scoring/UI for that step.
