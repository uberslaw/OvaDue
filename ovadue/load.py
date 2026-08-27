"""Load every HP backlog snapshot under data/ into one history frame."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ovadue.offices import extract_office

SNAPSHOT_RE = re.compile(
    r"osreport_ArupBacklog_(\d{4}-\d{2}-\d{2})_(\d{3,5})",
    re.IGNORECASE,
)

DATE_COLS = (
    "HPReceiveDate",
    "CustomerRequestedDate",
    "PlannedShipDate",
    "PlannedDeliveryDate",
)


def select_report_files(data_dir: str | Path) -> list[Path]:
    chosen: dict[str, Path] = {}
    for path in Path(data_dir).glob("osreport_ArupBacklog_*"):
        if path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        match = SNAPSHOT_RE.search(path.name)
        if not match:
            continue
        stamp = f"{match.group(1)}_{match.group(2)}"
        prev = chosen.get(stamp)
        if prev is None or (path.suffix.lower() == ".xlsx" and prev.suffix.lower() != ".xlsx"):
            chosen[stamp] = path
    return [chosen[k] for k in sorted(chosen)]


def snapshot_at_from_name(name: str) -> pd.Timestamp:
    match = SNAPSHOT_RE.search(name)
    if not match:
        raise ValueError(f"Cannot parse snapshot time from {name!r}")
    day = match.group(1)
    hhmm = match.group(2)[:4]
    hour, minute = int(hhmm[:2]), int(hhmm[2:4])
    return pd.Timestamp(f"{day} {hour:02d}:{minute:02d}:00")


def _line_key(frame: pd.DataFrame) -> pd.Series:
    # Older reports have no ItemNumber, so identity has to work without it.
    hp = frame["HPOrderNo"].astype(str).str.strip()
    product = frame.get("ProductNumber", pd.Series("", index=frame.index)).astype(str).str.strip()
    po = frame.get("PurchaseOrderNo", pd.Series("", index=frame.index)).astype(str).str.strip()
    addr = (
        frame.get("ShipToAddr", pd.Series("", index=frame.index))
        .astype(str)
        .str.strip()
        .str.casefold()
    )
    qty = frame.get("OrderedQuantity", pd.Series("", index=frame.index)).astype(str)
    return hp + "|" + po + "|" + product + "|" + addr + "|" + qty


def _short_model(value: object) -> str:
    text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
    text = (
        text.replace(" IDS Base Model", "")
        .replace(" inch ", '" ')
        .replace("Mobile Workstation PC", "ZBook")
        .strip()
    )
    return text or "Unknown"


def _parse_lt_weeks(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    match = re.search(r"(\d+)\s*-\s*(\d+)", str(value))
    if match:
        return (float(match.group(1)) + float(match.group(2))) / 2
    match = re.search(r"(\d+)", str(value))
    return float(match.group(1)) if match else None


def read_snapshot(path: Path) -> pd.DataFrame:
    engine = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
    frame = pd.read_excel(path, engine=engine)
    frame.columns = [str(c).strip() for c in frame.columns]
    if "HPOrderNo" not in frame.columns:
        raise ValueError(f"{path.name} has no HPOrderNo column")
    snap = snapshot_at_from_name(path.name)
    frame["snapshot_at"] = snap
    frame["source_file"] = path.name
    for col in DATE_COLS:
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
        else:
            frame[col] = pd.NaT
    for col in ("MM_MH_Model", "MM_MH_Category", "MM_MH_Type", "MM_MH_Series", "Status", "Standard LT"):
        if col not in frame.columns:
            frame[col] = pd.NA
    if "OTD Days" not in frame.columns:
        frame["OTD Days"] = pd.NA
    if "OrderedQuantity" not in frame.columns:
        frame["OrderedQuantity"] = pd.NA
    frame["line_key"] = _line_key(frame)
    frame["office"] = [
        extract_office(addr, country)
        for addr, country in zip(frame.get("ShipToAddr", pd.Series(index=frame.index)), frame.get("ShipToCountry", pd.Series(index=frame.index)))
    ]
    frame["region"] = frame["ShipToHPRegion"].astype(str).str.strip().replace({"nan": "Unknown"})
    frame["hardware_type"] = frame["MM_MH_Type"].fillna(frame["MM_MH_Category"]).fillna("Unknown")
    frame["hardware_category"] = frame["MM_MH_Category"].fillna("Unknown")
    frame["model"] = frame["MM_MH_Series"].fillna(frame["MM_MH_Model"]).map(_short_model)
    frame["status"] = frame["Status"].fillna("Unknown").astype(str).str.strip()
    frame["planned_delivery"] = frame["PlannedDeliveryDate"]
    frame["qty"] = pd.to_numeric(frame["OrderedQuantity"], errors="coerce")
    frame["otd_days"] = pd.to_numeric(frame["OTD Days"], errors="coerce")
    frame["standard_lt_weeks"] = frame["Standard LT"].map(_parse_lt_weeks)
    promised = (frame["planned_delivery"] - frame["HPReceiveDate"]).dt.days
    frame["promised_lead_days"] = frame["otd_days"].where(frame["otd_days"].notna(), promised)
    counts = frame.groupby("line_key").cumcount()
    extra = counts.gt(0)
    if extra.any():
        frame.loc[extra, "line_key"] = (
            frame.loc[extra, "line_key"].astype(str) + "|" + counts.loc[extra].astype(str)
        )
    keep = [
        "snapshot_at",
        "source_file",
        "line_key",
        "PurchaseOrderNo",
        "HPOrderNo",
        "region",
        "ShipToCountry",
        "office",
        "status",
        "HPReceiveDate",
        "CustomerRequestedDate",
        "planned_delivery",
        "ProductNumber",
        "qty",
        "hardware_type",
        "hardware_category",
        "model",
        "promised_lead_days",
        "standard_lt_weeks",
        "otd_days",
    ]
    present = [c for c in keep if c in frame.columns]
    return frame[present].copy()


def load_history(data_dir: str | Path) -> pd.DataFrame:
    files = select_report_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No osreport_ArupBacklog_* files in {data_dir}")
    parts = [read_snapshot(path) for path in files]
    history = pd.concat(parts, ignore_index=True)
    history.sort_values(["line_key", "snapshot_at"], inplace=True)
    history.reset_index(drop=True, inplace=True)
    originals = history.groupby("line_key")["planned_delivery"].transform("first")
    history["original_planned"] = originals
    prev_planned = history.groupby("line_key")["planned_delivery"].shift(1)
    delta = (history["planned_delivery"] - prev_planned).dt.days
    history["planned_delta_days"] = delta
    history["date_pushed"] = delta.gt(0)
    history["date_pulled"] = delta.lt(0)
    history["late_vs_original"] = history["original_planned"].notna() & (
        history["snapshot_at"].dt.normalize() > history["original_planned"].dt.normalize()
    )
    history["late_vs_current"] = history["planned_delivery"].notna() & (
        history["snapshot_at"].dt.normalize() > history["planned_delivery"].dt.normalize()
    )
    history["days_past_original"] = (
        history["snapshot_at"].dt.normalize() - history["original_planned"].dt.normalize()
    ).dt.days
    return history
