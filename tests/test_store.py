import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook

from ovadue.store import (
    MAX_EXCEL_BYTES,
    connect,
    db_signature,
    probe_sqlite,
    prune_imported_data,
    read_excel_file,
    sync_imports,
)


def _write_xlsx(path: Path, rows: list[dict[str, object]]) -> None:
    book = Workbook()
    sheet = book.active
    headers = list(rows[0].keys())
    sheet.append(headers)
    for row in rows:
        sheet.append([row[key] for key in headers])
    book.save(path)


def test_connect_enables_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert str(mode).lower() == "wal"
    assert (tmp_path / "data" / "ovadue.db").exists()


def test_sync_imports_and_probe(tmp_path: Path) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    report = uploads / "osreport_ArupBacklog_2026-09-01_0800.xlsx"
    _write_xlsx(
        report,
        [
            {
                "HPOrderNo": "H1",
                "PurchaseOrderNo": "P1",
                "ProductNumber": "ABC",
                "ShipToAddr": "London",
                "OrderedQuantity": 2,
            }
        ],
    )
    signature, warnings = sync_imports(tmp_path)
    assert warnings == []
    assert signature[1] == 1
    assert signature[2] == 1
    assert not report.exists()
    integrity, rows = probe_sqlite(tmp_path / "data" / "ovadue.db")
    assert integrity == "ok"
    assert rows == 1
    imported, file_count, total_rows = db_signature(connect(tmp_path))
    assert file_count == 1
    assert total_rows == 1
    assert imported


def test_read_excel_rejects_oversize(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "huge.xlsx"
    path.write_bytes(b"not-really-excel")
    monkeypatch.setattr("ovadue.store.MAX_EXCEL_BYTES", 4)
    try:
        read_excel_file(path)
        raise AssertionError("expected oversize reject")
    except ValueError as exc:
        assert "max import size" in str(exc)


def test_prune_removes_old_files(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    imported = tmp_path / "imported data"
    old = imported / "osreport_ArupBacklog_2020-01-01_0800.xlsx"
    _write_xlsx(old, [{"HPOrderNo": "H1"}])
    conn.execute(
        """
        INSERT INTO imported_files
            (filename, original_path, stored_path, file_hash, mtime_ns, snapshot_date, row_count, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("old.xlsx", str(old), str(old), "hash", 1, "2020-01-01", 1, "2020-01-01T00:00:00+00:00"),
    )
    conn.commit()
    removed = prune_imported_data(conn, imported, retention_days=30)
    conn.close()
    assert removed >= 1
    assert not old.exists()


def test_max_excel_constant_is_positive() -> None:
    assert MAX_EXCEL_BYTES >= 1_000_000


def test_probe_sqlite_script(tmp_path: Path) -> None:
    connect(tmp_path).close()
    db = tmp_path / "data" / "ovadue.db"
    script = Path("scripts/probe_sqlite.py")
    result = subprocess.run(
        [sys.executable, str(script), str(db)],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines[0] == "ok"
    assert lines[1] == "0"
