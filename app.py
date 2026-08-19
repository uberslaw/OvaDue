from __future__ import annotations

from pathlib import Path
import json
import re

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="OvaDue", layout="wide")

DATA_DIR = Path(__file__).parent
UPLOADS_DIR = DATA_DIR / "uploads"
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
REGION_STORAGE_KEY = "ovadue_regions"
OFFICE_STORAGE_KEY = "ovadue_offices"
OFFICE_SETUP_STORAGE_KEY = "ovadue_office_setup_complete"
COUNTRY_REGIONS = {
    "Australia": "APAC",
    "Canada": "AMR",
    "Denmark": "EUR",
    "Germany": "EUR",
    "Hong Kong": "APAC",
    "India": "APAC",
    "Ireland": "UKEMEA",
    "Italy": "EUR",
    "Japan": "APAC",
    "Malaysia": "APAC",
    "Netherlands": "EUR",
    "New Zealand": "APAC",
    "Poland": "EUR",
    "Singapore": "APAC",
    "South Africa": "UKEMEA",
    "Spain": "EUR",
    "Taiwan": "APAC",
    "Turkey": "UKEMEA",
    "United Kingdom": "UKEMEA",
    "United States": "AMR",
    "Vietnam": "APAC",
}
CITY_PATTERNS = {
    "Adelaide": ("ADELAIDE",),
    "Amsterdam": ("AMSTERDAM",),
    "Auckland": ("AUCKLAND",),
    "Belfast": ("BELFAST", "BT2 7F"),
    "Berlin": ("BERLIN",),
    "Birmingham": ("BIRMINGHAM", "B3 3A"),
    "Boston": ("BOSTON",),
    "Brisbane": ("BRISBANE",),
    "Bristol": ("BRISTOL", "BS1 6A"),
    "Cardiff": ("CARDIFF", "CF10 4"),
    "Chicago": ("CHICAGO",),
    "Copenhagen": ("COPENHAGEN",),
    "Cork": ("CORK",),
    "Dublin": ("DUBLIN",),
    "Edinburgh": ("EDINBURGH", "EH2 2"),
    "Frankfurt": ("FRANKFURT",),
    "Glasgow": ("GLASGOW", "G2 1R"),
    "Hong Kong": ("HONG KONG", "KOWLOON"),
    "Hyderabad": ("HYDERABAD",),
    "Istanbul": ("ISTANBUL", "LEVENT"),
    "Johannesburg": ("JOHANNESBURG", "2196"),
    "Krakow": ("KRAKOW",),
    "Leeds": ("LEEDS", "LS1 4"),
    "London": ("LONDON", "W1T 4"),
    "Madrid": ("MADRID",),
    "Melbourne": ("MELBOURNE",),
    "Milan": ("MILAN", "MILANO"),
    "Montreal": ("MONTREAL", "VILLE-MARIE"),
    "Mumbai": ("MUMBAI", "ANDHERI-KURLA"),
    "Newcastle": ("NEWCASTLE", "NE1 3"),
    "New York": ("NEW YORK", "140 BROADWAY"),
    "Nottingham": ("NOTTINGHAM", "NG1 5"),
    "Penang": ("PENANG", "GURNEY"),
    "Perth": ("PERTH", "Westralia"),
    "Petaling Jaya": ("PETALING JAYA", "BANDAR UTAMA"),
    "Shanghai": ("SHANGHAI", "上海"),
    "Sheffield": ("SHEFFIELD", "S1 2"),
    "Singapore": ("SINGAPORE", "FRASERS TOWER"),
    "Sydney": ("SYDNEY", "CLARENCE ST"),
    "Taipei": ("台北", "TAIPEI"),
    "Tokyo": ("千代田", "飯田橋", "TOKYO"),
    "Warsaw": ("WARSZAWA",),
    "Winchester": ("WINCHESTER", "SO23 9"),
}
CITY_TIMEZONES = {
    "Adelaide": "Australia/Adelaide", "Amsterdam": "Europe/Amsterdam", "Auckland": "Pacific/Auckland",
    "Belfast": "Europe/London", "Berlin": "Europe/Berlin", "Birmingham": "Europe/London",
    "Boston": "America/New_York", "Brisbane": "Australia/Brisbane", "Bristol": "Europe/London",
    "Cardiff": "Europe/London", "Chicago": "America/Chicago", "Copenhagen": "Europe/Copenhagen",
    "Cork": "Europe/Dublin", "Dublin": "Europe/Dublin", "Edinburgh": "Europe/London",
    "Frankfurt": "Europe/Berlin", "Glasgow": "Europe/London", "Hong Kong": "Asia/Hong_Kong",
    "Hyderabad": "Asia/Kolkata", "Istanbul": "Europe/Istanbul", "Johannesburg": "Africa/Johannesburg",
    "Krakow": "Europe/Warsaw", "Leeds": "Europe/London", "London": "Europe/London",
    "Madrid": "Europe/Madrid", "Melbourne": "Australia/Melbourne", "Milan": "Europe/Rome",
    "Montreal": "America/Toronto", "Mumbai": "Asia/Kolkata", "Newcastle": "Europe/London",
    "New York": "America/New_York", "Nottingham": "Europe/London", "Penang": "Asia/Kuala_Lumpur",
    "Perth": "Australia/Perth", "Petaling Jaya": "Asia/Kuala_Lumpur", "Shanghai": "Asia/Shanghai",
    "Sheffield": "Europe/London", "Singapore": "Asia/Singapore", "Sydney": "Australia/Sydney",
    "Taipei": "Asia/Taipei", "Tokyo": "Asia/Tokyo", "Warsaw": "Europe/Warsaw",
    "Winchester": "Europe/London",
}


def extract_office_location(address: object) -> str:
    if pd.isna(address):
        return "Unknown"

    text = re.sub(r"\s+", " ", str(address)).strip().upper()
    if not text:
        return "Unknown"

    for city, patterns in CITY_PATTERNS.items():
        if any(pattern.upper() in text for pattern in patterns):
            return city

    return "Unknown"


def normalize_region(country: object, source_region: object) -> str:
    region = COUNTRY_REGIONS.get(str(country).strip())
    if region:
        return region

    source = str(source_region).strip().upper()
    return {"APJ": "APAC", "CA": "AMR", "US": "AMR", "EMEA": "UKEMEA"}.get(source, "UKEMEA")


def preferred_office_for_timezone(df: pd.DataFrame, timezone: str | None) -> str | None:
    if not timezone:
        return None

    matching_cities = [city for city, city_timezone in CITY_TIMEZONES.items() if city_timezone == timezone]
    available_cities = set(df["Office"].dropna().astype(str))
    for city in matching_cities:
        if city in available_cities:
            return city
    return None


def extract_snapshot_date(filename: str) -> pd.Timestamp | pd.NaT:
    match = DATE_PATTERN.search(filename)
    if not match:
        return pd.NaT
    return pd.to_datetime(match.group(1), errors="coerce")


def discover_data_files(folder: Path) -> list[Path]:
    UPLOADS_DIR.mkdir(exist_ok=True)
    root_files = [file for pattern in ("*.xls", "*.xlsx") for file in folder.glob(pattern)]
    upload_files = [file for pattern in ("*.xls", "*.xlsx") for file in UPLOADS_DIR.rglob(pattern)]
    return sorted({file.resolve() for file in root_files + upload_files})


def data_file_signature(files: list[Path]) -> tuple[tuple[str, int, int], ...]:
    return tuple((str(file), file.stat().st_mtime_ns, file.stat().st_size) for file in files)


@st.cache_data(show_spinner=False)
def load_all_data(files_signature: tuple[tuple[str, int, int], ...]) -> pd.DataFrame:
    files = [Path(file_path) for file_path, _, _ in files_signature]
    if not files:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for file in files:
        try:
            engine = "xlrd" if file.suffix.lower() == ".xls" else None
            frame = pd.read_excel(file, sheet_name=0, engine=engine)
        except Exception as exc:
            st.warning(f"Skipping {file.name}: {exc}")
            continue

        frame["SnapshotFile"] = file.name
        frame["SnapshotDate"] = extract_snapshot_date(file.name)
        if frame["SnapshotDate"].isna().all():
            frame["SnapshotDate"] = pd.Timestamp(file.stat().st_mtime, unit="s").normalize()
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    for col in ["OrderedQuantity", "NetLineDollarPrice", "OTD Days", "OTD weeks"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        "HPReceiveDate",
        "CustomerRequestedDate",
        "PlannedShipDate",
        "PlannedDeliveryDate",
        "SnapshotDate",
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "ShipToAddr" in df.columns:
        df["Office"] = df["ShipToAddr"].apply(extract_office_location)
    else:
        df["Office"] = "Unknown"

    model_series = df.get("MM_MH_Model", pd.Series(index=df.index, dtype=object)).fillna("").astype(str).str.strip()
    product_series = df.get("ProductNumber", pd.Series(index=df.index, dtype=object)).fillna("Unknown").astype(str).str.strip()
    df["LaptopModel"] = model_series.mask(model_series.eq(""), product_series)

    df["Region"] = df.apply(lambda row: normalize_region(row.get("ShipToCountry"), row.get("ShipToHPRegion")), axis=1)
    df["Status"] = df.get("Status", pd.Series(index=df.index, dtype=object)).fillna("Unknown").astype(str).str.strip()
    df["IsOutstanding"] = ~df["Status"].isin(["Shipped", "ShipmentCanceled"])
    df["PlannedLeadDays"] = (df["PlannedDeliveryDate"] - df["HPReceiveDate"]).dt.days
    df["RequestedDateVarianceDays"] = (df["PlannedDeliveryDate"] - df["CustomerRequestedDate"]).dt.days
    df["OrderLineKey"] = (
        df.get("HPOrderNo", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
        + "|" + df.get("ItemNumber", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
        + "|" + df.get("ProductNumber", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    )

    dated = df.dropna(subset=["PlannedDeliveryDate"]).sort_values("SnapshotDate")
    initial_plan = dated.groupby("OrderLineKey")["PlannedDeliveryDate"].first()
    df["InitialPlannedDeliveryDate"] = df["OrderLineKey"].map(initial_plan)
    df["PlanChangeDays"] = (df["PlannedDeliveryDate"] - df["InitialPlannedDeliveryDate"]).dt.days
    observed_shipped = df[df["Status"].eq("Shipped")].groupby("OrderLineKey")["SnapshotDate"].min()
    df["FirstObservedShippedSnapshot"] = df["OrderLineKey"].map(observed_shipped)
    df["ObservedShipVsInitialPlanDays"] = (df["FirstObservedShippedSnapshot"] - df["InitialPlannedDeliveryDate"]).dt.days

    return df


def latest_snapshot(df: pd.DataFrame) -> pd.Timestamp:
    if "SnapshotDate" not in df.columns or df["SnapshotDate"].dropna().empty:
        return pd.NaT
    return df["SnapshotDate"].max()


def format_money(value: float) -> str:
    if pd.isna(value):
        return "$0"
    return f"${value:,.0f}"


def restore_filter_from_storage(storage_key: str, state_key: str, options: list[str]) -> bool:
    if state_key in st.session_state:
        return True

    raw_value = streamlit_js_eval(
        js_expressions=f"JSON.stringify({{value: localStorage.getItem('{storage_key}')}})",
        key=f"load_{storage_key}",
    )
    if raw_value is None:
        return False

    try:
        saved_values = json.loads(json.loads(raw_value).get("value") or "[]")
    except (TypeError, json.JSONDecodeError):
        saved_values = []

    restored_values = [value for value in saved_values if value in options]
    st.session_state[state_key] = restored_values or options
    return True


def save_filter_to_storage(storage_key: str, state_key: str) -> None:
    value = json.dumps(st.session_state[state_key])
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('{storage_key}', {json.dumps(value)})",
        key=f"save_{storage_key}",
    )


@st.dialog("Choose Your Offices")
def choose_initial_offices(offices: list[str]) -> None:
    st.write("Choose the office cities you want to see by default. You can change this at any time from the sidebar.")
    selected_offices = st.multiselect("Office cities", options=offices, key="initial_office_selection")
    if st.button("Show dashboard", type="primary", width="stretch"):
        if not selected_offices:
            st.warning("Choose at least one office city to continue.")
            return

        st.session_state["selected_offices"] = selected_offices
        save_filter_to_storage(OFFICE_STORAGE_KEY, "selected_offices")
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{OFFICE_SETUP_STORAGE_KEY}', 'true')",
            key="save_office_setup_complete",
        )
        st.session_state["office_setup_complete"] = True
        st.rerun()


def build_late_orders_frame(snapshot: pd.DataFrame, reference_date: pd.Timestamp, otd_threshold: int, grace_days: int) -> pd.DataFrame:
    late = snapshot.copy()

    if "OTD Days" in late.columns:
        late_from_otd = late["OTD Days"] >= otd_threshold
    else:
        late_from_otd = pd.Series(False, index=late.index)

    if pd.notna(reference_date) and "PlannedDeliveryDate" in late.columns:
        late["DaysPastPlannedDelivery"] = (reference_date - late["PlannedDeliveryDate"]).dt.days
        late_from_delivery = late["DaysPastPlannedDelivery"] > grace_days
    else:
        late["DaysPastPlannedDelivery"] = pd.NA
        late_from_delivery = pd.Series(False, index=late.index)

    late["IsLate"] = late_from_otd.fillna(False) | late_from_delivery.fillna(False)
    late["LateReason"] = ""
    late.loc[late_from_otd.fillna(False), "LateReason"] = late.loc[late_from_otd.fillna(False), "LateReason"] + f"OTD Days >= {otd_threshold}; "
    late.loc[late_from_delivery.fillna(False), "LateReason"] = late.loc[late_from_delivery.fillna(False), "LateReason"] + f"Past planned delivery by > {grace_days} days; "
    late["LateReason"] = late["LateReason"].str.rstrip("; ")

    return late[late["IsLate"]].copy()


def laptop_only(df: pd.DataFrame) -> pd.DataFrame:
    laptop_type = df.get("MM_MH_Type", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    laptops = df[laptop_type.str.contains("Notebook|Mobile Workstation", case=False, na=False)].copy()
    return laptops if not laptops.empty else df.copy()


def render_outstanding_page(current_snapshot: pd.DataFrame, late_otd_threshold: int, late_delivery_grace_days: int) -> None:
    outstanding = current_snapshot[current_snapshot["IsOutstanding"]].copy()
    laptops = laptop_only(outstanding)
    reference_date = latest_snapshot(current_snapshot)
    late_orders = build_late_orders_frame(outstanding, reference_date, late_otd_threshold, late_delivery_grace_days)

    st.subheader("Outstanding at a Glance")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Outstanding Order Lines", f"{len(outstanding):,}")
    kpi2.metric("Laptops Waiting", f"{laptops.get('OrderedQuantity', pd.Series(dtype=float)).sum():,.0f}")
    kpi3.metric("Late Order Lines", f"{len(late_orders):,}")
    known_delivery = outstanding["PlannedDeliveryDate"].notna().mean() * 100 if len(outstanding) else 0
    kpi4.metric("Delivery Date Available", f"{known_delivery:,.0f}%")

    st.subheader("Laptop Models Awaiting Delivery")
    model_summary = (
        laptops.groupby("LaptopModel", dropna=False)["OrderedQuantity"]
        .sum().reset_index(name="QuantityWaiting")
        .sort_values("QuantityWaiting", ascending=False)
    )
    summary_left, summary_right = st.columns((1, 2))
    with summary_left:
        st.dataframe(model_summary, hide_index=True, width="stretch")
    with summary_right:
        fig_models = px.bar(model_summary, x="QuantityWaiting", y="LaptopModel", orientation="h", text_auto=True)
        fig_models.update_layout(title="Quantity Waiting by Laptop Model", yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_models, width="stretch")

    st.subheader("Laptop Models by Current Status")
    model_status = pd.pivot_table(laptops, index="LaptopModel", columns="Status", values="OrderedQuantity", aggfunc="sum", fill_value=0).reset_index()
    status_columns = [column for column in model_status.columns if column != "LaptopModel"]
    model_status["Total"] = model_status[status_columns].sum(axis=1)
    st.dataframe(model_status.sort_values("Total", ascending=False), hide_index=True, width="stretch")

    st.subheader("Outstanding Laptop Orders")
    order_columns = ["PurchaseOrderNo", "HPOrderNo", "LaptopModel", "OrderedQuantity", "Status", "PlannedShipDate", "PlannedDeliveryDate", "Office", "Region"]
    existing_columns = [column for column in order_columns if column in laptops.columns]
    st.dataframe(laptops[existing_columns].sort_values(["PlannedDeliveryDate", "PlannedShipDate"], na_position="last"), hide_index=True, width="stretch")

    with st.expander("Late Order Detail"):
        late_columns = ["PurchaseOrderNo", "HPOrderNo", "LaptopModel", "Office", "Region", "Status", "PlannedDeliveryDate", "OTD Days", "LateReason", "Actions / Guidance"]
        st.dataframe(late_orders[[column for column in late_columns if column in late_orders.columns]], hide_index=True, width="stretch")


def render_delivery_page(history: pd.DataFrame, current_snapshot: pd.DataFrame) -> None:
    outstanding = current_snapshot[current_snapshot["IsOutstanding"]].copy()
    valid_lead = outstanding.dropna(subset=["PlannedLeadDays"])
    valid_requested = outstanding.dropna(subset=["RequestedDateVarianceDays"])
    valid_change = outstanding.dropna(subset=["PlanChangeDays"])

    st.subheader("Delivery Timeframes")
    st.caption("Actual delivery timestamps are not supplied in these reports. OvaDue shows promised delivery, current planned delivery, plan movement, and first observed shipped status separately.")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Avg Planned Lead Time", f"{valid_lead['PlannedLeadDays'].mean():,.1f} days" if not valid_lead.empty else "n/a")
    kpi2.metric("Median Planned Lead Time", f"{valid_lead['PlannedLeadDays'].median():,.1f} days" if not valid_lead.empty else "n/a")
    on_request = (valid_requested["RequestedDateVarianceDays"] <= 0).mean() * 100 if not valid_requested.empty else 0
    kpi3.metric("On or Before Requested Date", f"{on_request:,.0f}%" if not valid_requested.empty else "n/a")
    kpi4.metric("Avg Plan Movement", f"{valid_change['PlanChangeDays'].mean():+,.1f} days" if not valid_change.empty else "n/a")

    comparison_dimension = st.selectbox("Comparison perspective", ["Region", "Country", "Office"], key="delivery_comparison_dimension")
    comparison_summary = (
        valid_lead.groupby(comparison_dimension, dropna=False)
        .agg(AveragePlannedLeadDays=("PlannedLeadDays", "mean"), MedianPlannedLeadDays=("PlannedLeadDays", "median"), OrderLines=("OrderLineKey", "size"))
        .reset_index().sort_values("AveragePlannedLeadDays", ascending=False)
    )
    global_average = valid_lead["PlannedLeadDays"].mean() if not valid_lead.empty else 0
    fig_compare = px.bar(comparison_summary, x=comparison_dimension, y="AveragePlannedLeadDays", text_auto=".1f")
    fig_compare.add_hline(y=global_average, line_dash="dash", annotation_text=f"Selected view average: {global_average:.1f} days")
    fig_compare.update_layout(title=f"Planned Lead Time by {comparison_dimension}", yaxis_title="Days from HP receipt to planned delivery")
    st.plotly_chart(fig_compare, width="stretch")
    st.dataframe(comparison_summary, hide_index=True, width="stretch")

    history_outstanding = history[history["IsOutstanding"]].dropna(subset=["PlannedLeadDays"])
    trend = (
        history_outstanding.groupby(["SnapshotDate", "Region"], dropna=False)
        .agg(AveragePlannedLeadDays=("PlannedLeadDays", "mean"), MedianPlannedLeadDays=("PlannedLeadDays", "median"))
        .reset_index().sort_values("SnapshotDate")
    )
    st.subheader("Planned Lead Time Trend")
    fig_trend = px.line(trend, x="SnapshotDate", y="AveragePlannedLeadDays", color="Region", markers=True)
    fig_trend.update_layout(yaxis_title="Average planned lead time (days)")
    st.plotly_chart(fig_trend, width="stretch")

    st.subheader("Promised Date Versus Current Plan")
    promised_summary = (
        valid_requested.groupby("Region", dropna=False)
        .agg(AverageVarianceDays=("RequestedDateVarianceDays", "mean"), OnOrBeforeRequestedPct=("RequestedDateVarianceDays", lambda values: (values <= 0).mean() * 100), OrderLines=("OrderLineKey", "size"))
        .reset_index().sort_values("AverageVarianceDays", ascending=False)
    )
    st.dataframe(promised_summary, hide_index=True, width="stretch")

    st.subheader("Delivery Plan Movement")
    movement = (
        valid_change.groupby("Region", dropna=False)
        .agg(AverageChangeDays=("PlanChangeDays", "mean"), MedianChangeDays=("PlanChangeDays", "median"), MovedLaterPct=("PlanChangeDays", lambda values: (values > 0).mean() * 100), OrderLines=("OrderLineKey", "size"))
        .reset_index().sort_values("AverageChangeDays", ascending=False)
    )
    st.dataframe(movement, hide_index=True, width="stretch")

    with st.expander("Observed Shipment Timing"):
        observed = current_snapshot.dropna(subset=["FirstObservedShippedSnapshot", "ObservedShipVsInitialPlanDays"])
        st.caption("First observed shipped date is the first backlog snapshot in which the order was marked Shipped. It is not an actual delivery confirmation.")
        observed_summary = observed.groupby("Region", dropna=False).agg(AverageObservedShipVsInitialPlanDays=("ObservedShipVsInitialPlanDays", "mean"), ShippedOrderLines=("OrderLineKey", "size")).reset_index()
        st.dataframe(observed_summary, hide_index=True, width="stretch")


def main() -> None:
    st.title("OvaDue")
    st.caption("Outstanding orders and delivery-time analysis for local office, regional, and leadership perspectives.")

    # Each active dashboard session rescans the data directory every hour.
    st_autorefresh(interval=60 * 60 * 1000, key="hourly_data_check")
    files = discover_data_files(DATA_DIR)
    file_signature = data_file_signature(files)

    df_all = load_all_data(file_signature)
    if df_all.empty:
        st.error("No readable .xls or .xlsx files were found in this folder or uploads directory.")
        return

    st.sidebar.header("Filters")
    if st.sidebar.button("Refresh data now", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.caption(f"Monitoring {len(files)} source file(s). Hourly check enabled.")
    st.sidebar.caption(f"Uploads folder: {UPLOADS_DIR}")

    regions = sorted(df_all.get("Region", pd.Series(dtype=str)).dropna().astype(str).unique())
    offices = sorted(df_all.get("Office", pd.Series(dtype=str)).dropna().astype(str).unique())
    statuses = sorted(df_all.get("Status", pd.Series(dtype=str)).dropna().astype(str).unique())
    regions_restored = restore_filter_from_storage(REGION_STORAGE_KEY, "selected_regions", regions)
    offices_restored = restore_filter_from_storage(OFFICE_STORAGE_KEY, "selected_offices", offices)
    if not regions_restored or not offices_restored:
        st.stop()

    if "office_setup_complete" not in st.session_state:
        saved_setup_state = streamlit_js_eval(
            js_expressions=f"JSON.stringify({{value: localStorage.getItem('{OFFICE_SETUP_STORAGE_KEY}')}})",
            key="load_office_setup_complete",
        )
        if saved_setup_state is None:
            st.stop()
        try:
            st.session_state["office_setup_complete"] = json.loads(saved_setup_state).get("value") == "true"
        except (TypeError, json.JSONDecodeError):
            st.session_state["office_setup_complete"] = False
    if not st.session_state["office_setup_complete"]:
        choose_initial_offices(offices)
        return

    browser_timezone = streamlit_js_eval(
        js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
        key="browser_timezone",
    )
    nearest_office = preferred_office_for_timezone(df_all, browser_timezone)
    if nearest_office:
        st.sidebar.caption(f"Browser timezone: {browser_timezone}. Same-timezone office: {nearest_office}.")
    elif browser_timezone:
        st.sidebar.caption(f"Browser timezone: {browser_timezone}. No matching office in the current data.")

    selected_regions = st.sidebar.multiselect(
        "Region",
        options=regions,
        key="selected_regions",
        on_change=save_filter_to_storage,
        args=(REGION_STORAGE_KEY, "selected_regions"),
    )
    selected_offices = st.sidebar.multiselect(
        "Office",
        options=offices,
        key="selected_offices",
        on_change=save_filter_to_storage,
        args=(OFFICE_STORAGE_KEY, "selected_offices"),
    )
    use_timezone_office = st.sidebar.checkbox(
        "Filter to same-timezone office",
        value=False,
        disabled=nearest_office is None,
    )
    selected_statuses = st.sidebar.multiselect("Status", options=statuses, default=statuses)

    page = st.sidebar.radio("View", ["Outstanding Orders", "Delivery Performance"])

    st.sidebar.subheader("Late Order Rules")
    late_otd_threshold = st.sidebar.number_input("Late if OTD Days >=", min_value=0, max_value=365, value=7, step=1)
    late_delivery_grace_days = st.sidebar.number_input("Late if planned delivery is overdue by more than (days)", min_value=0, max_value=365, value=0, step=1)

    min_date = df_all["SnapshotDate"].min()
    max_date = df_all["SnapshotDate"].max()
    selected_date_range = st.sidebar.date_input(
        "Snapshot date range",
        value=(min_date.date(), max_date.date()) if pd.notna(min_date) and pd.notna(max_date) else None,
    )

    df = df_all.copy()
    if selected_regions:
        df = df[df["Region"].astype(str).isin(selected_regions)]
    if selected_offices:
        df = df[df["Office"].astype(str).isin(selected_offices)]
    if use_timezone_office and nearest_office:
        df = df[df["Office"] == nearest_office]
    if selected_statuses:
        df = df[df["Status"].astype(str).isin(selected_statuses)]

    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
        start_date = pd.to_datetime(selected_date_range[0])
        end_date = pd.to_datetime(selected_date_range[1])
        df = df[(df["SnapshotDate"] >= start_date) & (df["SnapshotDate"] <= end_date)]

    if df.empty:
        st.warning("No rows match the selected filters.")
        return

    current_date = latest_snapshot(df)
    current_snapshot = df[df["SnapshotDate"] == current_date].copy() if pd.notna(current_date) else df.copy()
    if page == "Outstanding Orders":
        render_outstanding_page(current_snapshot, int(late_otd_threshold), int(late_delivery_grace_days))
    else:
        render_delivery_page(df, current_snapshot)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name="ovadue_orders_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
