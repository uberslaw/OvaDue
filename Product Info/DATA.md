# OvaDue data classification, retention, residency

## Where data lives

All live data stays on the install machine (typical paths: `C:\OvaDue` or the operator OneDrive copy). Nothing is sent to a public cloud as part of the app.

| Path | Contents |
|---|---|
| `data/ovadue.db` | Imported snapshot rows (full Excel row as JSON) |
| `uploads/` | Inbox for new HP OS reports |
| `imported data/` | Archived reports after import |
| `data/delivered_orders.json` | Operator “mark as delivered” keys (`PO\|HP`) |
| `data/backups/` | Local `OvaDue_Backup_*.zip` (operator-controlled) |

Backup zips live wherever the operator saves them (`data\backups` or a Migration Pack path such as `C:\temp`). If you copy a zip off the machine, **you** chose that residency.

## Classification

Treat the HP OS report as **internal / commercially sensitive**. Some fields can identify a person or a site.

| Sensitivity | Fields (source names) | Notes |
|---|---|---|
| Sensitive location / possible PII | `ShipToAddr` | Office ship-to; may include street address |
| Identity | `CustomerName`, `AccountName` | Present in source rows even when the UI hides them |
| Commercial | `NetLineDollarPrice` (and similar price columns) | Omitted from the default CSV export |
| Operational identifiers | `PurchaseOrderNo`, `HPOrderNo`, `ProductNumber` | Needed to run the dashboard |
| Operational | status, model, qty, planned/ship dates, office, region | Shown in the UI |

Disk encryption (BitLocker on the Windows host) is the at-rest control. The app does **not** field-encrypt SQLite — keys would sit next to the database.

## Retention

- Imported Excel archives and matching DB file records: **365 days** (`RETENTION_DAYS` in [`ovadue/store.py`](../ovadue/store.py)).
- Local backup zips: last **14** in `data\backups`.
- The live database is **not** auto-deleted.
- Streamlit / deploy logs rotate or grow on disk; they are not a compliance archive.

## CSV export

**Download filtered data as CSV** writes an operational allow-list (PO, HP order, status, office, model, dates, qty, …). Address, customer name, and price columns are omitted by default. The SQLite file still holds the full source row.

## Right to access / delete (Privacy Act / GDPR)

The PoC has no login, so it cannot prove a requester’s identity. Do **not** add a public “delete my data” button.

To prepare for an operator-handled request:

1. Search SQLite / the UI for the PO, HP order, or office.
2. Stop Streamlit.
3. Either restore a backup from before the data existed, or re-import a filtered history (remove matching Excel rows / files and rebuild).
4. Record what you did in `data\ovadue-app.log` / deploy log.

A dedicated purge command can be added later if legal asks for repeatable deletion.

## Onboarding / offboarding (no IdP)

- **Access:** reach the host on `:8501` (LAN) or RDP/share to Launch Control.
- **Offboarding:** remove network/RDP access to that host. There are no app accounts to revoke.
- **Privileged:** anyone with the box can read the DB and run Launch Control. That is the admin surface.
