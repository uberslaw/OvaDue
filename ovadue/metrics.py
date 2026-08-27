"""Lifecycle and chart-ready aggregations from snapshot history."""

from __future__ import annotations

import pandas as pd


def build_lifecycle(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return history.copy()
    latest = history["snapshot_at"].max()
    snap_list = pd.Series(sorted(history["snapshot_at"].unique()))
    next_snap = {snap_list.iloc[i]: snap_list.iloc[i + 1] for i in range(len(snap_list) - 1)}

    grouped = history.groupby("line_key", sort=False)
    last = grouped.tail(1).set_index("line_key")
    first = grouped.head(1).set_index("line_key")
    n_snaps = grouped.size().rename("n_snapshots")
    n_pushed = grouped["date_pushed"].sum().rename("n_date_pushes")
    n_pulled = grouped["date_pulled"].sum().rename("n_date_pulls")
    n_changes = grouped["planned_delta_days"].apply(lambda s: int(s.fillna(0).ne(0).sum())).rename(
        "n_date_changes"
    )

    last_cols = [
        "region",
        "office",
        "ShipToCountry",
        "hardware_type",
        "hardware_category",
        "model",
        "status",
        "qty",
        "promised_lead_days",
        "standard_lt_weeks",
        "HPReceiveDate",
        "planned_delivery",
        "original_planned",
        "snapshot_at",
    ]
    for extra in ("HPOrderNo", "PurchaseOrderNo"):
        if extra in last.columns:
            last_cols.append(extra)
    life = last[last_cols].rename(
        columns={"snapshot_at": "last_seen", "planned_delivery": "last_planned", "status": "last_status"}
    )
    life["first_seen"] = first["snapshot_at"]
    life["first_status"] = first["status"]
    life = life.join([n_snaps, n_pushed, n_pulled, n_changes])
    life["is_open"] = life["last_seen"].eq(latest)
    life["canceled"] = life["last_status"].eq("ShipmentCanceled")
    closed_at = life["last_seen"].map(next_snap)
    life["closed_at"] = closed_at.where(~life["is_open"] & ~life["canceled"])
    landed = life["closed_at"].notna()
    # Still on a report after the original promise, then later vanished → landed late.
    was_overdue = life["last_seen"].dt.normalize() > life["original_planned"].dt.normalize()
    life["landed_late"] = landed & was_overdue
    life["landed_on_time"] = landed & ~was_overdue & life["original_planned"].notna()
    late_days = (life["closed_at"].dt.normalize() - life["original_planned"].dt.normalize()).dt.days
    life["days_late"] = late_days.where(life["landed_late"], 0)
    receive = life["HPReceiveDate"]
    if "HPReceiveDate" in first.columns:
        receive = receive.fillna(first["HPReceiveDate"])
    order_start = receive.fillna(life["first_seen"])
    life["actual_lead_days"] = (life["closed_at"].dt.normalize() - order_start.dt.normalize()).dt.days
    return life.reset_index()


def regional_flux(history: pd.DataFrame, promise: str = "original") -> pd.DataFrame:
    late_col = "late_vs_original" if promise == "original" else "late_vs_current"
    active = history[history["status"] != "ShipmentCanceled"].copy()
    flux = (
        active.groupby(["snapshot_at", "region"], dropna=False)
        .agg(
            n_lines=("line_key", "nunique"),
            n_late=(late_col, "sum"),
            n_date_pushes=("date_pushed", "sum"),
            n_date_changes=("planned_delta_days", lambda s: int(s.fillna(0).ne(0).sum())),
        )
        .reset_index()
    )
    flux["late_share"] = (flux["n_late"] / flux["n_lines"]).where(flux["n_lines"] > 0)
    return flux


def hardware_outcomes(lifecycle: pd.DataFrame, grain: str = "hardware_type") -> pd.DataFrame:
    closed = lifecycle[lifecycle["closed_at"].notna()].copy()
    if closed.empty:
        return pd.DataFrame(columns=[grain, "n_closed", "n_on_time", "n_late", "on_time_rate", "avg_days_late", "avg_date_changes"])
    out = (
        closed.groupby(grain, dropna=False)
        .agg(
            n_closed=("line_key", "count"),
            n_on_time=("landed_on_time", "sum"),
            n_late=("landed_late", "sum"),
            avg_days_late=("days_late", "mean"),
            avg_date_changes=("n_date_changes", "mean"),
            median_lead=("actual_lead_days", "median"),
        )
        .reset_index()
    )
    out["on_time_rate"] = (out["n_on_time"] / out["n_closed"]).where(out["n_closed"] > 0)
    out["late_rate"] = (out["n_late"] / out["n_closed"]).where(out["n_closed"] > 0)
    return out


def date_change_by_type(lifecycle: pd.DataFrame, grain: str = "hardware_type") -> pd.DataFrame:
    frame = lifecycle[~lifecycle["canceled"]].copy()
    out = (
        frame.groupby(grain, dropna=False)
        .agg(
            n_lines=("line_key", "count"),
            avg_changes=("n_date_changes", "mean"),
            share_changed=("n_date_changes", lambda s: float((s > 0).mean())),
            max_changes=("n_date_changes", "max"),
        )
        .reset_index()
    )
    return out


def office_timeseries(history: pd.DataFrame, region: str | None = None) -> pd.DataFrame:
    frame = history[history["status"] != "ShipmentCanceled"].copy()
    if region:
        frame = frame[frame["region"] == region]
    ts = (
        frame.groupby(["snapshot_at", "region", "office"], dropna=False)
        .agg(
            n_lines=("line_key", "nunique"),
            n_late_original=("late_vs_original", "sum"),
            n_date_pushes=("date_pushed", "sum"),
            n_date_changes=("planned_delta_days", lambda s: int(s.fillna(0).ne(0).sum())),
            median_lead=("promised_lead_days", "median"),
        )
        .reset_index()
    )
    ts["late_share"] = (ts["n_late_original"] / ts["n_lines"]).where(ts["n_lines"] > 0)
    return ts


def _order_id(frame: pd.DataFrame) -> pd.Series:
    """Prefer HP order numbers; fall back to PO, then the line key."""
    blank = {"", "nan", "none", "<na>", "nat"}

    def _clean(col: str) -> pd.Series | None:
        if col not in frame.columns:
            return None
        text = frame[col].astype(str).str.strip()
        return text.where(~text.str.casefold().isin(blank))

    order = _clean("HPOrderNo")
    po = _clean("PurchaseOrderNo")
    if order is None and po is None:
        return frame["line_key"]
    if order is None:
        return po.fillna(frame["line_key"])
    if po is None:
        return order.fillna(frame["line_key"])
    return order.fillna(po).fillna(frame["line_key"])


def scorecard_years(lifecycle: pd.DataFrame, history: pd.DataFrame) -> list[int]:
    """Calendar years that appear on snapshot or close dates."""
    years: set[int] = set()
    if not history.empty and "snapshot_at" in history.columns:
        years.update(history["snapshot_at"].dt.year.dropna().astype(int).tolist())
    if not lifecycle.empty and "closed_at" in lifecycle.columns:
        years.update(lifecycle["closed_at"].dt.year.dropna().astype(int).tolist())
    return sorted(years)


def office_scorecard(
    lifecycle: pd.DataFrame,
    history: pd.DataFrame,
    min_closed: int = 3,
    *,
    close_year: int | None = None,
) -> pd.DataFrame:
    closed = lifecycle[lifecycle["closed_at"].notna()].copy()
    hist = history
    if close_year is not None:
        closed = closed[closed["closed_at"].dt.year == close_year]
        if not hist.empty and "snapshot_at" in hist.columns:
            hist = hist[hist["snapshot_at"].dt.year == close_year]
    if closed.empty:
        return pd.DataFrame()
    closed = closed.copy()
    closed["_order_id"] = _order_id(closed)
    card = (
        closed.groupby(["region", "office"], dropna=False)
        .agg(
            n_closed=("line_key", "count"),
            n_orders=("_order_id", "nunique"),
            n_on_time=("landed_on_time", "sum"),
            n_late=("landed_late", "sum"),
            longest_delay=("days_late", "max"),
            avg_days_late=("days_late", "mean"),
            avg_date_changes=("n_date_changes", "mean"),
            median_lead=("actual_lead_days", "median"),
        )
        .reset_index()
    )
    card["n_orders"] = card["n_orders"].fillna(0).astype(int)
    # If HP/PO ids were blank, fall back to closed-line volume so ranking still works.
    missing_orders = card["n_orders"].eq(0) & card["n_closed"].gt(0)
    card.loc[missing_orders, "n_orders"] = card.loc[missing_orders, "n_closed"]
    card["on_time_rate"] = (card["n_on_time"] / card["n_closed"]).where(card["n_closed"] > 0)
    card["late_rate"] = (card["n_late"] / card["n_closed"]).where(card["n_closed"] > 0)
    # Consistency: mix of high on-time rate and few date revisions.
    card["consistency"] = (card["on_time_rate"].fillna(0) * 100) - (card["avg_date_changes"].fillna(0) * 8)
    streaks = _office_on_time_streaks(hist)
    card = card.merge(streaks, on=["region", "office"], how="left")
    card["longest_streak"] = card["longest_streak"].fillna(0).astype(int)
    card["qualified"] = card["n_closed"] >= min_closed
    return card.sort_values(["region", "office"])


def _office_on_time_streaks(history: pd.DataFrame) -> pd.DataFrame:
    """Longest run of consecutive snapshots with zero original-promise overdue lines."""
    empty = pd.DataFrame(columns=["region", "office", "longest_streak"])
    if history.empty:
        return empty
    active = history[history["status"] != "ShipmentCanceled"]
    weekly = (
        active.groupby(["region", "office", "snapshot_at"], dropna=False)["late_vs_original"]
        .sum()
        .reset_index()
    )
    rows = []
    for (region, office), group in weekly.groupby(["region", "office"], dropna=False):
        group = group.sort_values("snapshot_at")
        best = current = 0
        for late in group["late_vs_original"]:
            if late == 0:
                current += 1
                best = max(best, current)
            else:
                current = 0
        rows.append({"region": region, "office": office, "longest_streak": best})
    return pd.DataFrame(rows) if rows else empty
