import pandas as pd

from ovadue.metrics import build_lifecycle


def test_build_lifecycle_marks_late_when_line_vanishes_after_promise() -> None:
    history = pd.DataFrame(
        [
            {
                "line_key": "L1",
                "snapshot_at": pd.Timestamp("2026-01-01"),
                "region": "EMEA",
                "office": "London",
                "ShipToCountry": "United Kingdom",
                "hardware_type": "Notebook",
                "hardware_category": "Notebook",
                "model": "ZBook",
                "status": "Production",
                "qty": 1,
                "promised_lead_days": 20,
                "standard_lt_weeks": 3,
                "HPReceiveDate": pd.Timestamp("2025-12-01"),
                "planned_delivery": pd.Timestamp("2026-01-10"),
                "original_planned": pd.Timestamp("2026-01-10"),
                "date_pushed": False,
                "date_pulled": False,
                "planned_delta_days": 0,
                "HPOrderNo": "H1",
                "PurchaseOrderNo": "P1",
            },
            {
                "line_key": "L1",
                "snapshot_at": pd.Timestamp("2026-01-15"),
                "region": "EMEA",
                "office": "London",
                "ShipToCountry": "United Kingdom",
                "hardware_type": "Notebook",
                "hardware_category": "Notebook",
                "model": "ZBook",
                "status": "Production",
                "qty": 1,
                "promised_lead_days": 20,
                "standard_lt_weeks": 3,
                "HPReceiveDate": pd.Timestamp("2025-12-01"),
                "planned_delivery": pd.Timestamp("2026-01-10"),
                "original_planned": pd.Timestamp("2026-01-10"),
                "date_pushed": False,
                "date_pulled": False,
                "planned_delta_days": 0,
                "HPOrderNo": "H1",
                "PurchaseOrderNo": "P1",
            },
            {
                "line_key": "L2",
                "snapshot_at": pd.Timestamp("2026-01-15"),
                "region": "EMEA",
                "office": "London",
                "ShipToCountry": "United Kingdom",
                "hardware_type": "Notebook",
                "hardware_category": "Notebook",
                "model": "Elite",
                "status": "Production",
                "qty": 1,
                "promised_lead_days": 10,
                "standard_lt_weeks": 2,
                "HPReceiveDate": pd.Timestamp("2026-01-01"),
                "planned_delivery": pd.Timestamp("2026-02-01"),
                "original_planned": pd.Timestamp("2026-02-01"),
                "date_pushed": False,
                "date_pulled": False,
                "planned_delta_days": 0,
                "HPOrderNo": "H2",
                "PurchaseOrderNo": "P2",
            },
            {
                "line_key": "L2",
                "snapshot_at": pd.Timestamp("2026-01-20"),
                "region": "EMEA",
                "office": "London",
                "ShipToCountry": "United Kingdom",
                "hardware_type": "Notebook",
                "hardware_category": "Notebook",
                "model": "Elite",
                "status": "Production",
                "qty": 1,
                "promised_lead_days": 10,
                "standard_lt_weeks": 2,
                "HPReceiveDate": pd.Timestamp("2026-01-01"),
                "planned_delivery": pd.Timestamp("2026-02-01"),
                "original_planned": pd.Timestamp("2026-02-01"),
                "date_pushed": False,
                "date_pulled": False,
                "planned_delta_days": 0,
                "HPOrderNo": "H2",
                "PurchaseOrderNo": "P2",
            },
        ]
    )
    life = build_lifecycle(history)
    late = life.set_index("line_key").loc["L1"]
    assert bool(late["landed_late"]) is True
    assert bool(late["is_open"]) is False
    open_row = life.set_index("line_key").loc["L2"]
    assert bool(open_row["is_open"]) is True
