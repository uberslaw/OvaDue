# OvaDue runbook (PoC)

Uptime target: **the dashboard works when the Windows host is on and Launch Control has started Streamlit.** There is no SLA and no on-call rota.

## The app is down

1. Open Launch Control (`launch control.cmd`).
2. Click **Refresh Status**. Note PID, port, Health.
3. If Health is not ok, click **Start Dashboard** (or **Restart Dashboard**).
4. Open `http://127.0.0.1:8501/_stcore/health` and `http://127.0.0.1:8501`.
5. If Start fails, click **Check & Repair** and read `data\self-heal-report.txt`.

### Port 8501 already in use

Only one Streamlit should listen.

```powershell
netstat -ano | findstr :8501
# or
Get-NetTCPConnection -LocalPort 8501 -State Listen
```

Stop the owning process, or use Launch Control **Stop Dashboard** / delete `data\streamlit.pid` then `taskkill /PID <id> /T /F`.

### Broken venv after a folder copy

Copied `.venv` folders usually break. **Check & Repair** → confirm **Install Server** (needs Python 3.11+ on PATH and network for pip).

### Corrupt or empty database

- Symptom: UI says no imported history, or Streamlit errors mentioning `ovadue.db`.
- If you have `data\backups\OvaDue_Backup_*.zip`, use **Test restore** first (does not overwrite live data).
- Full recovery of data/config: **Import Migration Pack** (overwrites matching paths). App code is not replaced.
- Last resort: keep the broken `data\ovadue.db` aside, put reports back in `uploads\`, **Refresh data now**.

### Search box crash / `*` in search

Search is a literal substring (not regex). If an old build still crashes on `*`, upgrade so `ovadue/safe.py` is on the host.

## Backups

| Action | What it does |
|---|---|
| **Backup now** | Zip `ovadue.db`, `delivered_orders.json`, and local config into `data\backups\`. Keeps 14 zips. |
| **Test restore** | Extract newest zip to a temp folder; `PRAGMA integrity_check`. Live data unchanged. |
| **Register daily backup** | Optional Task Scheduler job at 02:00 for the current Windows user (`OvaDue-DailyBackup`). |
| **Backup Migration Pack** | Larger zip for moving machines (uploads + imported data + config). |

Suggested PoC numbers:

- **RPO:** last successful local backup (or last import if you have never backed up).
- **RTO:** new folder + Install Server + Import Migration Pack / restore backup contents.

RAID or OneDrive sync is **not** a tested backup.

## Logs

| File | Content |
|---|---|
| `data\ovadue-app.log` | App events: imports, prune, mark-delivered (no user id). |
| `data\streamlit.log` / `streamlit-error.log` | Streamlit stdout/stderr |
| `data\deploy.log` | Package, upgrade, backup, migration |
| `data\self-heal-report.txt` | Last Check & Repair |
| `data\launchcontrol-startup.log` / `launchcontrol-crash.log` | Launch Control |

## Rollback a bad code deploy

1. Keep older `OvaDue_*.zip` files (push target / `C:\temp`).
2. **Upgrade from Push** using the previous zip, or extract it over the app folder (data paths stay).
3. **Start Dashboard** and confirm health.

## When you cannot fix it

This is a PoC. If the host is off, the disk is gone, and there is no backup zip, the recoverable state is whatever Excel files you still have in email/`uploads`. Re-import those.
