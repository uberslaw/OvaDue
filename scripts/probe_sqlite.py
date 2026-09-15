"""Stdlib-only SQLite probe for Launch Control Test restore. No pandas required."""

from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: probe_sqlite.py <ovadue.db>", file=sys.stderr)
        return 2
    conn = sqlite3.connect(sys.argv[1])
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        try:
            rows = conn.execute("SELECT COUNT(*) FROM snapshot_rows").fetchone()[0]
        except sqlite3.Error:
            rows = 0
    finally:
        conn.close()
    print(integrity)
    print(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
