"""SQLite persistence for HP backlog snapshot imports."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
RETENTION_DAYS = 365
IMPORTED_DATA_DIRNAME = "imported data"


def extract_snapshot_date(filename: str) -> pd.Timestamp | pd.NaT:
    match = DATE_PATTERN.search(filename)
    if not match:
        return pd.NaT
    return pd.to_datetime(match.group(1), errors="coerce")


def imported_data_dir(root: Path) -> Path:
    return root / IMPORTED_DATA_DIRNAME


def db_path_for(root: Path) -> Path:
    return root / "data" / "ovadue.db"


def ensure_directories(root: Path) -> tuple[Path, Path, Path]:
    uploads = root / "uploads"
    imported = imported_data_dir(root)
    data_dir = root / "data"
    uploads.mkdir(exist_ok=True)
    imported.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    return uploads, imported, data_dir


def connect(root: Path) -> sqlite3.Connection:
    ensure_directories(root)
    conn = sqlite3.connect(db_path_for(root))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS imported_files (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            mtime_ns INTEGER NOT NULL,
            snapshot_date TEXT,
            row_count INTEGER NOT NULL DEFAULT 0,
            imported_at TEXT NOT NULL,
            UNIQUE(filename, file_hash)
        );
        CREATE TABLE IF NOT EXISTS snapshot_rows (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL REFERENCES imported_files(id) ON DELETE CASCADE,
            row_index INTEGER NOT NULL,
            row_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_snapshot_rows_file_id ON snapshot_rows(file_id);
        """
    )
    conn.commit()


def file_content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_pending_files(root: Path) -> list[Path]:
    uploads, imported, _ = ensure_directories(root)
    imported_resolved = imported.resolve()
    unique: dict[str, Path] = {}
    for pattern in ("*.xls", "*.xlsx"):
        for path in root.glob(pattern):
            if imported_resolved not in path.resolve().parents:
                unique[str(path.resolve())] = path
        for path in uploads.rglob(pattern):
            if imported_resolved not in path.resolve().parents:
                unique[str(path.resolve())] = path
    return sorted(unique.values(), key=lambda item: item.name)


def read_excel_file(path: Path) -> pd.DataFrame:
    engine = "xlrd" if path.suffix.lower() == ".xls" else None
    return pd.read_excel(path, sheet_name=0, engine=engine)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_json(row: pd.Series) -> str:
    payload: dict[str, object | None] = {}
    for key, value in row.items():
        if pd.isna(value):
            payload[str(key)] = None
        elif isinstance(value, (pd.Timestamp, datetime)):
            payload[str(key)] = value.isoformat()
        else:
            payload[str(key)] = value
    return json.dumps(payload, default=str)


def _delete_file_records(conn: sqlite3.Connection, filename: str) -> None:
    conn.execute("DELETE FROM imported_files WHERE filename = ?", (filename,))


def _archive_duplicate(path: Path, imported_dir: Path) -> None:
    if not path.exists():
        return
    dest = imported_dir / path.name
    if dest.exists():
        path.unlink()
        return
    shutil.move(str(path), str(dest))


def _import_one_file(conn: sqlite3.Connection, path: Path, imported_dir: Path) -> bool:
    path = path.resolve()
    if not path.exists():
        return False

    file_hash = file_content_hash(path)
    stat = path.stat()
    filename = path.name

    existing = conn.execute(
        "SELECT id, stored_path FROM imported_files WHERE filename = ? AND file_hash = ?",
        (filename, file_hash),
    ).fetchone()
    if existing:
        _archive_duplicate(path, imported_dir)
        return False

    frame = read_excel_file(path)
    snapshot_date = extract_snapshot_date(filename)
    if isinstance(snapshot_date, pd.Timestamp) and pd.notna(snapshot_date):
        snapshot_iso = snapshot_date.normalize().strftime("%Y-%m-%d")
    else:
        snapshot_iso = pd.Timestamp(stat.st_mtime, unit="s").normalize().strftime("%Y-%m-%d")

    _delete_file_records(conn, filename)

    imported_at = _utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO imported_files
            (filename, original_path, stored_path, file_hash, mtime_ns, snapshot_date, row_count, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            str(path),
            str(path),
            file_hash,
            stat.st_mtime_ns,
            snapshot_iso,
            len(frame),
            imported_at,
        ),
    )
    file_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO snapshot_rows (file_id, row_index, row_json) VALUES (?, ?, ?)",
        ((file_id, int(idx), _row_to_json(row)) for idx, row in frame.iterrows()),
    )
    conn.commit()

    dest = imported_dir / filename
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        dest = imported_dir / f"{stem}_{stat.st_mtime_ns}{suffix}"

    shutil.move(str(path), str(dest))
    conn.execute(
        "UPDATE imported_files SET stored_path = ? WHERE id = ?",
        (str(dest.resolve()), file_id),
    )
    conn.commit()
    return True


def _file_reference_date(path: Path, snapshot_date_str: str | None) -> datetime:
    if snapshot_date_str:
        try:
            return datetime.strptime(snapshot_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    match = DATE_PATTERN.search(path.name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def prune_imported_data(
    conn: sqlite3.Connection,
    imported_dir: Path,
    retention_days: int = RETENTION_DAYS,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0

    for record in conn.execute(
        "SELECT id, stored_path, snapshot_date FROM imported_files"
    ).fetchall():
        stored = Path(record["stored_path"])
        if not stored.exists():
            conn.execute("DELETE FROM imported_files WHERE id = ?", (record["id"],))
            removed += 1
            continue
        if _file_reference_date(stored, record["snapshot_date"]) >= cutoff:
            continue
        stored.unlink(missing_ok=True)
        conn.execute("DELETE FROM imported_files WHERE id = ?", (record["id"],))
        removed += 1

    for path in sorted(imported_dir.glob("*.xls")) + sorted(imported_dir.glob("*.xlsx")):
        if not path.exists():
            continue
        if _file_reference_date(path, None) >= cutoff:
            continue
        path.unlink(missing_ok=True)
        removed += 1

    conn.commit()
    return removed


def db_signature(conn: sqlite3.Connection) -> tuple[str, int, int]:
    row = conn.execute(
        """
        SELECT COUNT(*) AS file_count,
               COALESCE(SUM(row_count), 0) AS total_rows,
               COALESCE(MAX(imported_at), '') AS latest_import
        FROM imported_files
        """
    ).fetchone()
    return (row["latest_import"], int(row["file_count"]), int(row["total_rows"]))


def load_raw_dataframe(conn: sqlite3.Connection) -> pd.DataFrame:
    records = conn.execute(
        """
        SELECT f.filename, f.snapshot_date, r.row_json
        FROM snapshot_rows r
        JOIN imported_files f ON f.id = r.file_id
        ORDER BY f.snapshot_date, f.filename, r.row_index
        """
    ).fetchall()
    if not records:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for record in records:
        data = json.loads(record["row_json"])
        data["SnapshotFile"] = record["filename"]
        snapshot = pd.to_datetime(record["snapshot_date"], errors="coerce")
        if pd.isna(snapshot):
            snapshot = extract_snapshot_date(record["filename"])
        data["SnapshotDate"] = snapshot
        rows.append(data)
    return pd.DataFrame(rows)


def sync_imports(root: Path) -> tuple[tuple[str, int, int], list[str]]:
    """Import pending spreadsheets, archive them, and prune old history."""
    _, imported_dir, _ = ensure_directories(root)
    warnings: list[str] = []
    conn = connect(root)

    for path in discover_pending_files(root):
        try:
            _import_one_file(conn, path, imported_dir)
        except Exception as exc:
            warnings.append(f"Skipping {path.name}: {exc}")

    prune_imported_data(conn, imported_dir)
    signature = db_signature(conn)
    conn.close()
    return signature, warnings
