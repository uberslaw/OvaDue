from html import escape

import pandas as pd

from ovadue.safe import csv_export_frame, html_text, series_contains


def test_html_text_escapes_markup() -> None:
    assert html_text("<script>alert(1)</script>") == escape("<script>alert(1)</script>", quote=True)
    assert "&" not in html_text(None)
    assert html_text("London") == "London"


def test_series_contains_is_literal_not_regex() -> None:
    frame = pd.Series(["PO-100", "star * value", "ok"])
    assert series_contains(frame, "*").tolist() == [False, True, False]
    assert series_contains(frame, "PO-100").tolist() == [True, False, False]


def test_csv_export_drops_sensitive_columns() -> None:
    frame = pd.DataFrame(
        {
            "PurchaseOrderNo": ["PO1"],
            "HPOrderNo": ["HP1"],
            "Office": ["London"],
            "ShipToAddr": ["1 Secret Street"],
            "CustomerName": ["Acme"],
            "NetLineDollarPrice": [99.0],
            "Status": ["Open"],
        }
    )
    exported = csv_export_frame(frame)
    assert "ShipToAddr" not in exported.columns
    assert "CustomerName" not in exported.columns
    assert "NetLineDollarPrice" not in exported.columns
    assert list(exported.columns) == ["PurchaseOrderNo", "HPOrderNo", "Status", "Office"]


def test_csv_export_fallback_when_no_allowlist_match() -> None:
    frame = pd.DataFrame({"ShipToAddr": ["hidden"], "Notes": ["keep"]})
    exported = csv_export_frame(frame)
    assert "ShipToAddr" not in exported.columns
    assert exported.columns.tolist() == ["Notes"]
