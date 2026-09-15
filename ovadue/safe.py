"""Input and export helpers that do not depend on Streamlit."""

from __future__ import annotations

from html import escape

import pandas as pd

SENSITIVE_CSV_COLUMNS = frozenset(
    {
        "ShipToAddr",
        "CustomerName",
        "AccountName",
        "NetLineDollarPrice",
        "NetLinePrice",
        "Email",
        "ShipToEmail",
    }
)

CSV_EXPORT_COLUMNS = [
    "PurchaseOrderNo",
    "HPOrderNo",
    "Status",
    "EffectiveStatus",
    "DisplayStatus",
    "Office",
    "Region",
    "ShipToCountry",
    "LaptopModel",
    "ProductNumber",
    "ProductDescription",
    "OrderedQuantity",
    "MM_MH_Type",
    "MM_MH_Category",
    "MM_MH_Series",
    "HPReceiveDate",
    "PlannedDeliveryDate",
    "PlannedShipDate",
    "CustomerRequestedDate",
    "SnapshotDate",
    "OTD Days",
    "IsOutstanding",
    "TransportModePlanned",
]


def html_text(value: object) -> str:
    """Escape a value for interpolation into ``unsafe_allow_html`` markup."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return escape(str(value), quote=True)


def series_contains(series: pd.Series, needle: str) -> pd.Series:
    """Case-insensitive substring match that does not treat the needle as regex."""
    return series.astype(str).str.contains(needle, case=False, na=False, regex=False)


def csv_export_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Keep operational columns; drop address, names, and price fields by default."""
    keep = [column for column in CSV_EXPORT_COLUMNS if column in df.columns]
    if keep:
        return df.loc[:, keep].copy()
    drop = [column for column in df.columns if column in SENSITIVE_CSV_COLUMNS]
    return df.drop(columns=drop, errors="ignore")
