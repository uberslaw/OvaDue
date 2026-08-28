# OvaDue manual install (Launch Control fallback)

Use this when **Launch Control** (`launch control.cmd`) does not start or its buttons fail. Prefer Launch Control when it works; this doc is the operator fallback.

**Example machine path (this workspace):**  
`C:\Users\christopher.owen\OneDrive - Arup\Arup\AI\OvaDue`  

**Typical server path (from `deploy\deploy-config.json` → `gitInstallPath`):**  
`C:\OvaDue`  

Below, `$Root` means the folder that contains `app.py`. All other paths are relative to `$Root` unless noted.

---

## A. Fresh install (no Launch Control)

### 1. Prerequisites

| Requirement | Notes |
|---|---|
| Windows + PowerShell 5.1+ | Scripts use `#Requires -Version 5.1` |
| Python **3.11+** on PATH | Prefer the **py** launcher (`deploy-config.json`: `pythonLauncher` = `py`, args `["-3"]`) |
| Network | Needed for `pip install -r requirements.txt` and for `git clone` |
| Permissions | Write access under `$Root`; create `data\`, `uploads\`, `.venv\` |
| Git for Windows | Only if installing via git |

Check Python:

```powershell
py -3 --version
# or: python --version
```

### 2. Get the app onto the machine

Pick **one** path. The folder must include at least: `app.py`, `requirements.txt`, `launch control.cmd`, `scripts\`, `deploy\` (see `Test-OvaDueDeployLayout` in `scripts\OvaDue-Deploy.ps1`).

#### Option A — Git clone (recommended)

Values come from `deploy\deploy-config.json` (`gitRepositoryUrl`, `gitBranch`, `gitInstallPath`):

```powershell
git clone --branch main --single-branch https://github.com/uberslaw/OvaDue.git "C:\OvaDue"
cd "C:\OvaDue"
```

#### Option B — Copy full folder

Copy the entire project tree from a working machine (USB/share). Do **not** rely on copying only `app.py`. You may omit `.venv` (recreate below). Keep or omit local `uploads\` / `data\` depending on whether you want existing data.

See also **section C** (whole-folder copy checklist and when to prefer a Migration Pack).

#### Option C — Unzip deploy package (`OvaDue_*.zip`)

Upgrade packages are named `OvaDue_yyyyMMdd_HHmmss.zip` (prefix from `packageNamePrefix`). Contents follow `deploy\package-include.json` → `includePaths` (app code + `scripts\`, `deploy\`, `.streamlit\`; **not** `.venv` or live `uploads\` data).

1. Copy the newest `OvaDue_*.zip` to the machine (often `C:\temp`, matching `upgradeSource`).
2. Extract to a permanent folder (e.g. `C:\OvaDue`).
3. Confirm `app.py`, `scripts\`, and `deploy\` are present.

For an **existing** install that already has a venv, operators normally use Launch Control **Upgrade from Push** (`Invoke-OvaDueUpgradeFromPush`). For a brand-new machine, extract + install deps as below is enough.

### 3. Create venv + install requirements

```powershell
cd $Root   # e.g. cd "C:\OvaDue"

py -3 -m venv .venv
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

# Verify (same imports Install Server checks)
.\.venv\Scripts\python.exe -c "import streamlit, pandas, plotly; print(streamlit.__version__)"
```

Equivalent via Deploy script (same as Launch Control **Install Server**):

```powershell
cd $Root
. .\scripts\OvaDue-Deploy.ps1
Initialize-OvaDueDeploy -Root (Get-Location).Path
Invoke-OvaDueInstallServer
```

`requirements.txt` packages: `pandas`, `xlrd`, `streamlit`, `plotly`, `streamlit-js-eval`, `streamlit-autorefresh`, `openpyxl`.

### 4. Ensure `data\` and `uploads\` exist

```powershell
New-Item -ItemType Directory -Force -Path .\data, .\uploads | Out-Null
```

(`package-include.json` → `ensureDirectories`: `data`, `uploads`.)

Put outstanding-order reports (`.xls` / `.xlsx`) in `uploads\`.

### 5. Start Streamlit manually

Matches Launch Control `Start-Dashboard` and `.streamlit\config.toml` (`address` `0.0.0.0`, `port` `8501`, `headless` `true`):

```powershell
cd $Root
.\.venv\Scripts\python.exe -m streamlit run ".\app.py" `
  --server.headless true `
  --server.address 0.0.0.0 `
  --server.port 8501
```

To run detached and capture logs (similar to Launch Control):

```powershell
cd $Root
$proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
  -ArgumentList '-m streamlit run ".\app.py" --server.headless true --server.address 0.0.0.0 --server.port 8501' `
  -WorkingDirectory (Get-Location).Path `
  -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput ".\data\streamlit.log" `
  -RedirectStandardError ".\data\streamlit-error.log"
Set-Content -LiteralPath ".\data\streamlit.pid" -Value $proc.Id -NoNewline
```

Stop later:

```powershell
$pidText = Get-Content ".\data\streamlit.pid" -TotalCount 1
taskkill.exe /PID $pidText /T /F
Remove-Item ".\data\streamlit.pid" -Force -ErrorAction SilentlyContinue
```

### 6. Verify

| Check | URL / command |
|---|---|
| Health | `http://127.0.0.1:8501/_stcore/health` |
| Browser (local) | `http://127.0.0.1:8501` |
| Browser (LAN) | `http://<hostname-or-ip>:8501` |

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8501/_stcore/health" -UseBasicParsing
Start-Process "http://127.0.0.1:8501"
```

### 7. Optional: register / start Launch Control later

Once the install works:

```powershell
cd $Root
# Double-click: launch control.cmd
# or:
.\scripts\OvaDue-LaunchControl.cmd
```

For Master Launch Control, register `scripts\OvaDue-LaunchControl.cmd` as a Generic app (see [README](../README.md)). Config: `launch control\launch-control.json` (same inode as `scripts\launch-control.json` hard link for MLC).

---

## B. Migration onto a new machine (no Launch Control UI)

Migration packs are **data + config only**. They do **not** replace app code and do **not** include `.venv` or runtime logs.

**Pack name:** `OvaDue_Migration_<COMPUTERNAME>_yyyyMMdd_HHmmss.zip`  
**Default search/export folder:** `C:\temp` (`upgradeSource`; optional keys `migrationExportDirectory` / `migrationImportDirectory` if added to `deploy-config.json`).

### What is in a migration pack

From `deploy\package-include.json` → `migrationPaths`:

| Path | Kind |
|---|---|
| `uploads\` | **Data** — inbox for new report files (imported on refresh) |
| `imported data\` | **Data** — archived reports after import (1-year retention) |
| `data\ovadue.db` | **Data** — SQLite snapshot history |
| `data\delivered_orders.json` | **Data** |
| `data\deployed-version.json` | Deploy metadata |
| `deploy\deploy-config.json` | **Config** — push/git/python paths |
| `.streamlit\` | **Config** — Streamlit server settings |
| `launch control\launch-control.json` | **Config** — MLC / Launch Control metadata |

**Not migrated** (`migrationNeverPackage`): `.venv`, `data\streamlit*.log`, `streamlit.pid`, `deploy.log`, install/git verify logs, crash/startup logs.

### What is app code (install separately)

`app.py`, `requirements.txt`, `scripts\`, `launch control\` (except optional `launch-control.json` restore), `deploy\` (except restored `deploy-config.json`), `launch control.cmd`, packaged `.streamlit\` defaults until migration overwrites.

### Order of operations

1. **Target:** install app code (git / copy / unzip app package).
2. **Target:** install server deps (`Invoke-OvaDueInstallServer` or manual venv + pip).
3. **Source:** export migration pack.
4. **Target:** import migration pack (overwrites matching paths).
5. **Target:** start Streamlit (section A.5).

### Export (source machine) — PowerShell

```powershell
cd $Root   # source app root
. .\scripts\OvaDue-Deploy.ps1
Initialize-OvaDueDeploy -Root (Get-Location).Path

# Writes under C:\temp by default (or -OutputDirectory / -OutputZipPath)
Invoke-OvaDueExportMigrationPack
# Example explicit path:
# Invoke-OvaDueExportMigrationPack -OutputZipPath "C:\temp\OvaDue_Migration_export.zip"
```

Copy the zip to the target (USB, share, or `C:\temp`).

### Import (target machine) — PowerShell

```powershell
cd $Root   # target app root (full layout already present)
. .\scripts\OvaDue-Deploy.ps1
Initialize-OvaDueDeploy -Root (Get-Location).Path

Invoke-OvaDueImportMigrationPack `
  -ZipPath "C:\temp\OvaDue_Migration_YOURPC_yyyyMMdd_HHmmss.zip" `
  -PidFile ".\data\streamlit.pid"
```

If `-ZipPath` is omitted, import picks the newest `OvaDue_Migration_*.zip` under configured import dirs / `C:\temp`.

Import record: `data\last-migration-import.json`.

### Manual copy (if you cannot run export/import)

Copy the same paths listed under **What is in a migration pack** from source → target, preserving relative layout under `$Root`. Do not copy `.venv` or log/pid files. Then recreate the venv on the target (section A.3).

---

## C. Whole-folder copy to a new machine

**Automated copy to O: drive:** run [`scripts\Copy-OvaDue-To-O.cmd`](../scripts/Copy-OvaDue-To-O.cmd) from the source machine.

**Yes — a whole folder copy can work** for app code, `uploads\`, `data\` (business data), `deploy\`, `.streamlit\`, and scripts. It is the fastest way to move an already-working tree when you want code **and** live data together.

### What usually breaks

| Item | Why |
|---|---|
| `.venv` | Machine-specific (Python home path, arch, absolute paths in `pyvenv.cfg`). Almost always broken after copy. |
| Absolute paths in `deploy\deploy-config.json` | `pushTarget`, `upgradeSource`, `gitInstallPath`, migration dirs may not exist on the new PC/network. |
| Network push targets | `\\server\c$\temp` needs reachability + permissions (often admin). |
| Python not installed | Target needs Python **3.11+** / `py -3` on PATH before Install Server. |

Safe to copy: `app.py`, `ovadue\`, `pages\`, `scripts\`, `deploy\`, `.streamlit\`, `uploads\`, `data\delivered_orders.json`, etc.  
Prefer **deleting `.venv` on the target** (or let **Check & Repair** / **Install Server** replace a broken one) rather than trusting a copied venv.

### Checklist after copy

1. Confirm the folder contains `app.py`, `launch control.cmd`, `scripts\`, `deploy\`.
2. Install Python 3.11+ on the new machine (`py -3 --version`).
3. Double-click `launch control.cmd`.
4. Click **Check & Repair** (left rail). Confirm **Install Server** if prompted (recreates `.venv` + packages).
5. Or click **Install Server** directly if you already know the venv is missing/broken.
6. Click **Start Dashboard**, then **Open Dashboard**.
7. **Import Migration Pack** only if you did **not** copy `uploads\` / delivered-orders data (or need to overlay config from another machine).

Report file: `data\self-heal-report.txt`. Logs: `data\deploy.log`, `data\launchcontrol-startup.log`.

### When to use Migration Pack vs whole-folder copy

| Approach | Use when |
|---|---|
| **Whole-folder copy** | Moving the full working tree (code + data) via USB/share; same major app version; you will re-run Install Server / Check & Repair on the target. |
| **Migration Pack** | Target already has (or will get) app code via git/zip; you only need to move **data + config** (`uploads`, delivered orders, deploy-config, `.streamlit`, launch-control.json). Smaller, safer, no accidental `.venv` copy. |
| **OvaDue_*.zip upgrade package** | Updating app code on an existing install (`Upgrade from Push`); does not replace live uploads/data (see `preserveOnUpgrade`). |

---

## D. Troubleshooting

### Port 8501 in use

```powershell
Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue |
  Select-Object OwningProcess, LocalAddress, LocalPort
# Or: netstat -ano | findstr :8501
```

Stop the owning process, or stop via `data\streamlit.pid` + `taskkill` (section A.5). Only one Streamlit instance should listen on 8501.

### Launch Control black window / instant quit

`scripts\OvaDue-LaunchControl.cmd` runs PowerShell **hidden**. Failures write under `data\`:

| File | Purpose |
|---|---|
| `data\launchcontrol-startup.log` | Startup progress |
| `data\launchcontrol-crash.log` | Fatal/UI crash text |
| `data\deploy.log` | Deploy / Install Server / migration |

Run visibly to see errors:

```powershell
cd $Root
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File ".\scripts\OvaDue-LaunchControl.ps1"
```

### Missing Python / venv

Symptoms: Install Server fails; Start Dashboard reports missing `.venv` Python; Check & Repair reports broken venv after a folder copy.

```powershell
py -3 --version
Test-Path ".\.venv\Scripts\python.exe"
```

Prefer Launch Control **Check & Repair** (confirms Install Server) or **Install Server**. Or:

```powershell
. .\scripts\OvaDue-Deploy.ps1
Initialize-OvaDueDeploy -Root (Get-Location).Path
Invoke-OvaDueHealthCheck -RepairSafe -WriteReport
Invoke-OvaDueInstallServer
```

Verify logs: `data\install-verify.out.log`, `data\install-verify.err.log`, `data\self-heal-report.txt`.

### Where logs live

| File | Content |
|---|---|
| `data\streamlit.log` | Streamlit stdout |
| `data\streamlit-error.log` | Streamlit stderr |
| `data\streamlit.pid` | Supervised process id |
| `data\deploy.log` | Package / upgrade / install / migration |
| `data\self-heal-report.txt` | Last Check & Repair / health check report |
| `data\git-last.out.log` / `git-last.err.log` | Last git install commands |
| `data\launchcontrol-startup.log` | Launch Control start |
| `data\launchcontrol-crash.log` | Launch Control failures |

---

## Quick reference — Deploy.ps1 functions

Dot-source once per session, then call:

```powershell
. .\scripts\OvaDue-Deploy.ps1
Initialize-OvaDueDeploy -Root (Get-Location).Path
```

| Function | Purpose |
|---|---|
| `Invoke-OvaDueInstallServer` | Create/reuse `.venv`, pip install `requirements.txt` (recreates broken venv) |
| `Invoke-OvaDueHealthCheck` | Detect/repair safe issues; write `data\self-heal-report.txt` (`-RepairSafe`, `-WriteReport`) |
| `Invoke-OvaDueInstallFromGit` | Clone/pull to `gitInstallPath`, then Install Server (`-LaunchControl` optional) |
| `Invoke-OvaDuePackageAndPush` | Build `OvaDue_*.zip` → `pushTarget` |
| `Invoke-OvaDueUpgradeFromPush` | Apply newest `OvaDue_*.zip` from `upgradeSource` |
| `Invoke-OvaDueExportMigrationPack` | Build `OvaDue_Migration_*.zip` |
| `Invoke-OvaDueImportMigrationPack` | Restore migration paths only |
| `Get-OvaDueSetupHelp` | Printed setup help (`-Topic overview\|installServer\|installFromGit\|missingFiles\|migration\|healthCheck`) |

Config keys: `deploy\deploy-config.json`. Package/migration path lists: `deploy\package-include.json`.
