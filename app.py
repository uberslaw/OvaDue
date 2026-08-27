from __future__ import annotations

from pathlib import Path
import json
import re

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_js_eval import streamlit_js_eval

from ovadue.analysis_ui import render_analysis

st.set_page_config(page_title="OvaDue", layout="wide")

DATA_DIR = Path(__file__).parent
UPLOADS_DIR = DATA_DIR / "uploads"
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
REGION_STORAGE_KEY = "ovadue_regions"
OFFICE_STORAGE_KEY = "ovadue_offices"
OFFICE_SETUP_STORAGE_KEY = "ovadue_office_setup_complete"
OFFICE_MANUALLY_SET_KEY = "ovadue_offices_manual"
REGION_SELECTION_STORAGE_KEY = "ovadue_region_selection"
FILTER_PREFS_INITIALIZED_KEY = "ovadue_filters_initialized"
DELIVERED_ORDERS_PATH = DATA_DIR / "data" / "delivered_orders.json"
VERSION_PATH = DATA_DIR / "deploy" / "version.json"
DEPLOYED_VERSION_PATH = DATA_DIR / "data" / "deployed-version.json"
PROCUREMENT_DEFAULT_COLUMNS = ["Status", "Order date", "Planned delivery", "Office", "Items", "QTY", "PO / Order"]
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
    "Ho Chi Minh City": ("HO CHI MINH", "UNG VAN KHIEM"),
    "Bangkok": ("BANGKOK", "KHLONG TOEI", "RATCHADAPISEK", "THE PARQ"),
    "Manila": ("PASIG", "PASIG CITY"),
    "Jakarta": ("JAKARTA", "EPICENTRUM", "SUNTER AGUNG"),
    "Seoul": ("SEOUL",),
    "Dubai": ("DUBAI",),
    "Belgrade": ("BEOGRAD", "BELGRADE"),
    "Toronto": ("TORONTO", "BLOOR ST"),
    "Calgary": ("CALGARY",),
    "San Diego": ("SAN DIEGO",),
    "Los Angeles": ("LOS ANGELES", "WILSHIRE"),
    "San Francisco": ("SAN FRANCISCO", "MISSION ST"),
    "Oakland": ("OAKLAND",),
    "Houston": ("HOUSTON",),
    "Newark": ("NEWARK", "RAYMOND BOUL"),
    "Manchester": ("MANCHESTER", "M1 3BN", "PICCADILLY PLACE"),
    "York": ("YORK", "YO1 "),
    "Sunderland": ("SUNDERLAND", "SR6 "),
    "Andover": ("ANDOVER", "SP11 8"),
    "Bangalore": ("BANGALORE", "560025"),
    "Gurgaon": ("GURGAON", "122002", "CYBERCITY"),
    "Zaragoza": ("ZARAGOZA",),
    "Getafe": ("GETAFE",),
    "Cape Town": ("CAPE TOWN", "V&A WATERFRONT", "WATERFRONT"),
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
    "Ho Chi Minh City": "Asia/Ho_Chi_Minh", "Bangkok": "Asia/Bangkok", "Manila": "Asia/Manila",
    "Jakarta": "Asia/Jakarta", "Seoul": "Asia/Seoul", "Dubai": "Asia/Dubai", "Belgrade": "Europe/Belgrade",
    "Toronto": "America/Toronto", "Calgary": "America/Edmonton", "San Diego": "America/Los_Angeles",
    "Los Angeles": "America/Los_Angeles", "San Francisco": "America/Los_Angeles", "Oakland": "America/Los_Angeles",
    "Houston": "America/Chicago", "Newark": "America/New_York", "Manchester": "Europe/London",
    "York": "Europe/London", "Sunderland": "Europe/London", "Andover": "Europe/London",
    "Bangalore": "Asia/Kolkata", "Gurgaon": "Asia/Kolkata", "Zaragoza": "Europe/Madrid",
    "Getafe": "Europe/Madrid", "Cape Town": "Africa/Johannesburg",
}


COUNTRY_OFFICE_FALLBACKS = {
    "South Korea": "Seoul",
}


def extract_office_location(address: object, country: object = None) -> str:
    if pd.isna(address):
        text = ""
    else:
        text = re.sub(r"\s+", " ", str(address)).strip().upper()

    if text:
        for city, patterns in CITY_PATTERNS.items():
            if any(pattern.upper() in text for pattern in patterns):
                return city

    if country:
        fallback = COUNTRY_OFFICE_FALLBACKS.get(str(country).strip())
        if fallback:
            return fallback

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


def region_for_office(df: pd.DataFrame, office: str) -> str | None:
    matches = df.loc[df["Office"].astype(str) == office, "Region"].dropna().astype(str)
    if matches.empty:
        return None
    return str(matches.mode().iat[0])


def save_region_to_storage() -> None:
    streamlit_js_eval(
        js_expressions=(
            f"localStorage.setItem('{REGION_SELECTION_STORAGE_KEY}', {json.dumps(st.session_state.get('selected_region', 'Global'))});"
            f"localStorage.setItem('{FILTER_PREFS_INITIALIZED_KEY}', 'true');"
            "JSON.stringify({value: 'ok'})"
        ),
        key="save_region_selection",
    )


def initialize_filter_preferences(
    df: pd.DataFrame,
    regions: list[str],
    offices: list[str],
    browser_timezone: str | None,
) -> bool:
    """Load saved filters or apply timezone defaults on first visit. Returns False if browser JS is not ready."""
    prefs_raw = streamlit_js_eval(
        js_expressions=f"""JSON.stringify({{
            initialized: localStorage.getItem({json.dumps(FILTER_PREFS_INITIALIZED_KEY)}),
            offices: localStorage.getItem({json.dumps(OFFICE_STORAGE_KEY)}),
            region: localStorage.getItem({json.dumps(REGION_SELECTION_STORAGE_KEY)}),
            officeManuallySet: localStorage.getItem({json.dumps(OFFICE_MANUALLY_SET_KEY)})
        }})""",
        key="load_filter_preferences",
    )
    if prefs_raw is None:
        return False

    try:
        prefs = json.loads(json.loads(prefs_raw))
    except (TypeError, json.JSONDecodeError):
        prefs = {}

    has_saved_offices = bool(prefs.get("offices"))
    office_manually_set = prefs.get("officeManuallySet") == "true"
    first_visit = not prefs.get("initialized") and not has_saved_offices and not office_manually_set

    if first_visit and not st.session_state.get("_initial_filters_applied"):
        default_office = preferred_office_for_timezone(df, browser_timezone)
        default_region = region_for_office(df, default_office) if default_office else None
        if (
            default_office
            and default_region
            and default_region in regions
            and default_office in offices
        ):
            st.session_state["selected_region"] = default_region
            st.session_state["selected_offices"] = [default_office]
        else:
            st.session_state["selected_region"] = "Global"
            st.session_state["selected_offices"] = ["All"]

        st.session_state["_initial_filters_applied"] = True

        offices_json = json.dumps(st.session_state["selected_offices"])
        region_json = json.dumps(st.session_state["selected_region"])
        streamlit_js_eval(
            js_expressions=(
                f"localStorage.setItem({json.dumps(OFFICE_STORAGE_KEY)}, {json.dumps(offices_json)});"
                f"localStorage.setItem({json.dumps(REGION_SELECTION_STORAGE_KEY)}, {region_json});"
                f"localStorage.setItem({json.dumps(FILTER_PREFS_INITIALIZED_KEY)}, 'true');"
                "JSON.stringify({value: 'ok'})"
            ),
            key="save_initial_filter_preferences",
        )
        return True

    if "selected_region" not in st.session_state:
        saved_region = prefs.get("region")
        if saved_region and saved_region in ["Global", *regions]:
            st.session_state["selected_region"] = saved_region
        else:
            st.session_state["selected_region"] = "Global"

    if "selected_offices" not in st.session_state and not st.session_state.get("_office_manually_set"):
        try:
            saved_offices = json.loads(prefs.get("offices") or "[]")
        except json.JSONDecodeError:
            saved_offices = []
        restored_offices = [office for office in saved_offices if office in ["All", *offices]]
        if office_manually_set or restored_offices:
            st.session_state["selected_offices"] = restored_offices
        else:
            st.session_state["selected_offices"] = ["All"]

    return True


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


def parse_standard_lt_bounds(value: object) -> tuple[int | None, int | None]:
    """Return lower/upper Standard LT bounds in days from values like '6 - 8 WK' or '23'."""
    if pd.isna(value):
        return None, None

    value_str = str(value).strip().upper()

    if "WK" in value_str:
        weeks = [int(match) for match in re.findall(r"\d+", value_str)]
        if weeks:
            lower_weeks, upper_weeks = min(weeks), max(weeks)
            return lower_weeks * 7, upper_weeks * 7

    try:
        days = int(float(value_str.split()[0]))
        return days, days
    except (ValueError, IndexError):
        return None, None


def parse_standard_lt_to_days(value: object) -> int | None:
    """Return the upper-bound Standard LT in days."""
    _, upper = parse_standard_lt_bounds(value)
    return upper


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

    # Do not coerce Standard LT — values are week-range text like "10 - 14 WK".
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
        df["Office"] = df.apply(
            lambda row: extract_office_location(row.get("ShipToAddr"), row.get("ShipToCountry")),
            axis=1,
        )
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

    df = df.sort_values(["OrderLineKey", "SnapshotDate"])
    df["PreviousPlannedDeliveryDate"] = df.groupby("OrderLineKey")["PlannedDeliveryDate"].shift(1)
    df["PreviousSnapshotDate"] = df.groupby("OrderLineKey")["SnapshotDate"].shift(1)
    df["RecentPlanChangeDays"] = (df["PlannedDeliveryDate"] - df["PreviousPlannedDeliveryDate"]).dt.days
    df["HasRecentPlanChange"] = (
        df["PreviousPlannedDeliveryDate"].notna()
        & df["PlannedDeliveryDate"].notna()
        & (df["PlannedDeliveryDate"] != df["PreviousPlannedDeliveryDate"])
    )

    observed_shipped = df[df["Status"].eq("Shipped")].groupby("OrderLineKey")["SnapshotDate"].min()
    df["FirstObservedShippedSnapshot"] = df["OrderLineKey"].map(observed_shipped)
    df["ObservedShipVsInitialPlanDays"] = (df["FirstObservedShippedSnapshot"] - df["InitialPlannedDeliveryDate"]).dt.days

    df["IsMissingPlannedDelivery"] = df["IsOutstanding"] & df["PlannedDeliveryDate"].isna()

    df["OverdueDays"] = (df["SnapshotDate"] - df["InitialPlannedDeliveryDate"]).dt.days
    df["OverdueDays"] = df["OverdueDays"].fillna(0).clip(lower=0).astype(int)
    df["IsOverdue"] = (
        df["IsOutstanding"]
        & df["InitialPlannedDeliveryDate"].notna()
        & (df["OverdueDays"] > 0)
        & ~df["IsMissingPlannedDelivery"]
    )
    df["OverdueWeeks"] = (df["OverdueDays"] / 7.0).round(1)

    # Flag when planned delivery exceeds the upper bound of Standard LT
    if "Standard LT" in df.columns:
        lt_bounds = df["Standard LT"].apply(parse_standard_lt_bounds)
        df["StandardLTLowerDays"] = lt_bounds.apply(lambda bounds: bounds[0])
        df["StandardLTUpperDays"] = lt_bounds.apply(lambda bounds: bounds[1])

        df["StandardLTLowerDate"] = df.apply(
            lambda row: (pd.to_datetime(row["HPReceiveDate"]) + pd.to_timedelta(row["StandardLTLowerDays"], unit="D"))
            if pd.notna(row["HPReceiveDate"]) and pd.notna(row["StandardLTLowerDays"]) else pd.NaT,
            axis=1,
        )
        df["StandardLTUpperDate"] = df.apply(
            lambda row: (pd.to_datetime(row["HPReceiveDate"]) + pd.to_timedelta(row["StandardLTUpperDays"], unit="D"))
            if pd.notna(row["HPReceiveDate"]) and pd.notna(row["StandardLTUpperDays"]) else pd.NaT,
            axis=1,
        )
        df["BaselineExpectedDeliveryDate"] = df["StandardLTUpperDate"]

        df["OutsideLTDays"] = (df["PlannedDeliveryDate"] - df["StandardLTUpperDate"]).dt.days
        df["OutsideLTDays"] = df["OutsideLTDays"].fillna(0).clip(lower=0).astype(int)
        df["IsOutsideLT"] = df["IsOutstanding"] & (df["OutsideLTDays"] > 0) & ~df["IsMissingPlannedDelivery"]
        df["OutsideLTWeeks"] = (df["OutsideLTDays"] / 7.0).round(1)
    else:
        df["StandardLTLowerDate"] = pd.NaT
        df["StandardLTUpperDate"] = pd.NaT
        df["BaselineExpectedDeliveryDate"] = pd.NaT
        df["OutsideLTDays"] = 0
        df["IsOutsideLT"] = False
        df["OutsideLTWeeks"] = 0.0

    df["IsDelayed"] = df["IsOverdue"] | df["IsOutsideLT"] | df["IsMissingPlannedDelivery"]
    # Backward-compatible aliases used elsewhere
    df["DelayDays"] = df["OutsideLTDays"]
    df["DelayWeeks"] = df["OutsideLTWeeks"]

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
        js_expressions=(
            f"localStorage.setItem('{storage_key}', {json.dumps(value)});"
            f"localStorage.setItem('{FILTER_PREFS_INITIALIZED_KEY}', 'true');"
            "JSON.stringify({value: 'ok'})"
        ),
        key=f"save_{storage_key}",
    )


def save_office_selection() -> None:
    st.session_state["_office_manually_set"] = True
    save_filter_to_storage(OFFICE_STORAGE_KEY, "selected_offices")
    streamlit_js_eval(
        js_expressions=(
            f"localStorage.setItem('{OFFICE_MANUALLY_SET_KEY}', 'true');"
            f"localStorage.setItem('{FILTER_PREFS_INITIALIZED_KEY}', 'true');"
            "JSON.stringify({value: 'ok'})"
        ),
        key="save_office_manual_flag",
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
        save_office_selection()
        save_region_to_storage()
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{FILTER_PREFS_INITIALIZED_KEY}', 'true')",
            key="save_office_setup_complete",
        )
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{OFFICE_SETUP_STORAGE_KEY}', 'true')",
            key="save_office_setup_complete_legacy",
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


MY_ORDERS_SEARCH_COLUMNS = [
    "PurchaseOrderNo", "HPOrderNo", "LaptopModel", "ProductNumber", "Status",
    "ShipToAddr", "Office", "Region", "TransportModePlanned",
]
MY_ORDERS_SEARCH_DATE_COLUMNS = ["HPReceiveDate", "PlannedDeliveryDate", "PlannedShipDate", "CustomerRequestedDate"]
LATE_OTD_THRESHOLD = 7
LATE_DELIVERY_GRACE_DAYS = 0
STATUS_COLORS = {
    "Shipped": "green",
    "ShipmentCanceled": "gray",
    "Cancelled": "gray",
    "Canceled": "gray",
    "Presumed Delivered": "blue",
    "Delivered": "blue",
}


def load_delivered_orders() -> set[str]:
    if not DELIVERED_ORDERS_PATH.exists():
        return set()
    try:
        payload = json.loads(DELIVERED_ORDERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(payload, list):
        return {str(key) for key in payload}
    return set()


def save_delivered_orders(delivered_keys: set[str]) -> None:
    DELIVERED_ORDERS_PATH.parent.mkdir(exist_ok=True)
    DELIVERED_ORDERS_PATH.write_text(
        json.dumps(sorted(delivered_keys), indent=2),
        encoding="utf-8",
    )


def ensure_delivered_orders_loaded() -> set[str]:
    if "delivered_orders" not in st.session_state:
        st.session_state.delivered_orders = load_delivered_orders()
    return st.session_state.delivered_orders


def build_order_tracking_key(row: pd.Series | dict) -> str:
    po = str(row.get("PurchaseOrderNo") or "").strip()
    hp_order = str(row.get("HPOrderNo") or "").strip()
    return f"{po}|{hp_order}"


def delivered_checkbox_key(tracking_key: str) -> str:
    return "delivered_" + re.sub(r"[^a-zA-Z0-9_]", "_", tracking_key)


def toggle_delivered(tracking_key: str) -> None:
    delivered = set(ensure_delivered_orders_loaded())
    widget_key = delivered_checkbox_key(tracking_key)
    if st.session_state.get(widget_key):
        delivered.add(tracking_key)
    else:
        delivered.discard(tracking_key)
    st.session_state.delivered_orders = delivered
    save_delivered_orders(delivered)


def effective_status_for_row(row: pd.Series, delivered_keys: set[str]) -> str:
    if build_order_tracking_key(row) in delivered_keys:
        return "Delivered"
    return str(row.get("Status") or "Unknown")


def apply_effective_status(df: pd.DataFrame, delivered_keys: set[str]) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    result["EffectiveStatus"] = result.apply(lambda row: effective_status_for_row(row, delivered_keys), axis=1)
    return result


def format_short_date(value: object) -> str:
    if pd.isna(value):
        return "—"
    return pd.Timestamp(value).strftime("%d %b %Y")


def format_standard_lt_due(lower_date: object, upper_date: object) -> str:
    if pd.isna(lower_date) and pd.isna(upper_date):
        return "—"
    if pd.isna(lower_date) or pd.isna(upper_date) or pd.Timestamp(lower_date) == pd.Timestamp(upper_date):
        return format_short_date(upper_date if pd.notna(upper_date) else lower_date)
    return f"{format_short_date(lower_date)} – {format_short_date(upper_date)}"


def format_overdue_message(overdue_weeks: float) -> str:
    if overdue_weeks <= 0:
        return ""
    return f"Overdue {overdue_weeks:.1f} Weeks"


def format_outside_lt_message(outside_lt_weeks: float) -> str:
    if outside_lt_weeks <= 0:
        return ""
    return f"Delayed {outside_lt_weeks:.1f} Weeks"


def format_planned_delivery_date(row: pd.Series) -> str:
    date_str = format_short_date(row.get("PlannedDeliveryDate"))
    if not row.get("HasRecentPlanChange"):
        return date_str

    change_days = row.get("RecentPlanChangeDays", 0)
    if pd.isna(change_days) or change_days == 0:
        return date_str

    color = "#1a7f37" if change_days < 0 else "#cc0000"
    return f'<span style="color: {color}; font-weight: 600;">{date_str}</span>'

def is_order_flagged(row: pd.Series) -> bool:
    return pd.notna(row.get("IsDelayed")) and row.get("IsDelayed")


def is_order_overdue(row: pd.Series) -> bool:
    return pd.notna(row.get("IsOverdue")) and row.get("IsOverdue")


def is_order_outside_lt(row: pd.Series) -> bool:
    return pd.notna(row.get("IsOutsideLT")) and row.get("IsOutsideLT")


def is_order_missing_delivery_date(row: pd.Series) -> bool:
    return pd.notna(row.get("IsMissingPlannedDelivery")) and row.get("IsMissingPlannedDelivery")


def is_service_row(mm_type: object) -> bool:
    return "service" in str(mm_type or "").lower()


def is_logistics_row(mm_series: object) -> bool:
    return "logistic" in str(mm_series or "").lower()


NON_DISPLAY_ITEM_PATTERNS = (
    "logistic",
    "priority management",
    "priority access",
    "onsite support",
    "onsite",
    "care pack",
    "warranty",
    "support w/travel",
)


def is_non_display_item_row(row: pd.Series) -> bool:
    if is_service_row(row.get("MM_MH_Type")):
        return True

    series = str(row.get("MM_MH_Series") or "").lower()
    description = str(row.get("ProductDescription") or "").lower()
    return any(pattern in series or pattern in description for pattern in NON_DISPLAY_ITEM_PATTERNS)


def displayable_item_rows(group: pd.DataFrame) -> pd.DataFrame:
    if group.empty:
        return group
    return group[~group.apply(is_non_display_item_row, axis=1)]


def format_transport_mode(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\{([^}]+)\}", r"(\1)", text)


def format_ordered_delivery_method(header_row: pd.Series, delivery_service_names: list[str]) -> str | None:
    parts: list[str] = []
    transport_mode = format_transport_mode(header_row.get("TransportModePlanned"))
    if transport_mode:
        parts.append(transport_mode)
    parts.extend(delivery_service_names)
    return " · ".join(parts) if parts else None


def render_order_group_card(group: pd.DataFrame, show_snapshot_date: bool = False) -> None:
    item_rows = displayable_item_rows(group)
    if item_rows.empty:
        return

    has_type = "MM_MH_Type" in group.columns
    has_series = "MM_MH_Series" in group.columns

    service_mask = group["MM_MH_Type"].apply(is_service_row) if has_type else pd.Series(False, index=group.index)
    logistics_mask = service_mask & (group["MM_MH_Series"].apply(is_logistics_row) if has_series else False)
    delivery_service_names = sorted(set(group.loc[logistics_mask, "ProductDescription"].dropna().astype(str))) if "ProductDescription" in group.columns else []
    delivery_method = format_ordered_delivery_method(item_rows.iloc[0], delivery_service_names)

    header_row = item_rows.iloc[0]
    tracking_key = build_order_tracking_key(header_row)
    delivered_keys = ensure_delivered_orders_loaded()
    is_delivered = tracking_key in delivered_keys

    if is_delivered:
        status = "Delivered"
        status_color = STATUS_COLORS.get("Delivered", "blue")
    else:
        status = header_row.get("DisplayStatus", header_row.get("Status", "—")) or "—"
        status_color = STATUS_COLORS.get(status, "orange")

    is_overdue = is_order_overdue(header_row) and not is_delivered
    is_outside_lt = is_order_outside_lt(header_row) and not is_overdue and not is_delivered
    is_missing_delivery_date = is_order_missing_delivery_date(header_row) and not is_delivered
    is_flagged = is_overdue or is_outside_lt or is_missing_delivery_date

    if is_missing_delivery_date:
        banner_message = "No Date Given"
        banner_bg = "#f3f0ff"
        banner_border = "#6f42c1"
        banner_text = "#5a32a3"
        divider_color = "#6f42c1"
    elif is_overdue:
        banner_message = format_overdue_message(header_row.get("OverdueWeeks", 0))
        banner_bg = "#ffe6e6"
        banner_border = "red"
        banner_text = "#cc0000"
        divider_color = "red"
    elif is_outside_lt:
        banner_message = format_outside_lt_message(header_row.get("OutsideLTWeeks", 0))
        banner_bg = "#fff4e6"
        banner_border = "#e67700"
        banner_text = "#b35900"
        divider_color = "#e67700"
    else:
        banner_message = ""

    if is_flagged and banner_message:
        st.markdown(
            f"<div style='background-color: {banner_bg}; border-left: 4px solid {banner_border}; padding: 12px; margin-bottom: 10px; border-radius: 4px;'>"
            f"<p style='color: {banner_text}; font-weight: bold; margin: 0;'>{banner_message}</p></div>",
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        if is_flagged:
            st.markdown(f"<hr style='border: 1px solid {divider_color}; margin: 0 0 12px 0;'>", unsafe_allow_html=True)

        if show_snapshot_date:
            st.caption(f"Snapshot: {format_short_date(header_row.get('SnapshotDate'))}")

        top_columns = st.columns([1, 1, 1, 1])
        top_columns[0].markdown(
            f"**PO / HP Order**  \n{header_row.get('PurchaseOrderNo', '—') or '—'} / {header_row.get('HPOrderNo', '—') or '—'}"
        )
        delivery_text = f"**Planned Delivery**  \n{format_planned_delivery_date(header_row)}"
        top_columns[1].markdown(delivery_text, unsafe_allow_html=True)
        lt_range_value = format_standard_lt_due(header_row.get("StandardLTLowerDate"), header_row.get("StandardLTUpperDate"))
        top_columns[2].markdown(
            f'<p title="HP&#39;s Standard Lead Time at time of order"><strong>LT Range</strong><br>{lt_range_value}</p>',
            unsafe_allow_html=True,
        )
        top_columns[3].markdown(f"**Status**  \n:{status_color}[{status}]")

        item_names = item_rows["LaptopModel"].fillna("Unknown item").astype(str).tolist()
        item_qtys = item_rows["OrderedQuantity"].fillna(0).tolist()
        has_plan_change = bool(header_row.get("HasRecentPlanChange")) and pd.notna(header_row.get("PreviousPlannedDeliveryDate"))

        bottom_columns = st.columns([1, 1, 1, 1])
        bottom_columns[0].markdown(
            '<div style="overflow-wrap: anywhere; word-break: break-word; max-width: 100%;">'
            f"<strong>Item</strong><br>{'<br>'.join(item_names)}"
            "</div>",
            unsafe_allow_html=True,
        )
        bottom_columns[1].markdown("**QTY**  \n" + "  \n".join(f"{qty:,.0f}" for qty in item_qtys))
        bottom_columns[2].markdown(f"**Order Placed**  \n{format_short_date(header_row.get('HPReceiveDate'))}")
        if has_plan_change:
            bottom_columns[3].markdown(
                f"**Previous Delivery Date**  \n{format_short_date(header_row.get('PreviousPlannedDeliveryDate'))}"
            )

        if delivery_method:
            st.markdown(
                f"<div style='margin-top: 10px; font-size: 0.875rem; color: rgba(49, 51, 63, 0.75);'>"
                f"<strong>Delivery method</strong>  \n{delivery_method}</div>",
                unsafe_allow_html=True,
            )

        st.checkbox(
            "Mark as delivered",
            value=is_delivered,
            key=delivered_checkbox_key(tracking_key),
            on_change=toggle_delivered,
            args=(tracking_key,),
        )


def build_procurement_dataframe(snapshot: pd.DataFrame, delivered_keys: set[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_columns = ["PurchaseOrderNo", "HPOrderNo"]
    if not all(column in snapshot.columns for column in group_columns):
        return pd.DataFrame(columns=PROCUREMENT_DEFAULT_COLUMNS)

    for (purchase_order, hp_order), group in snapshot.groupby(group_columns, dropna=False):
        item_rows = displayable_item_rows(group)
        if item_rows.empty:
            continue

        header = item_rows.iloc[0]
        tracking_key = f"{purchase_order}|{hp_order}"
        display_status = header.get("DisplayStatus", header.get("Status", "—"))
        status = "Delivered" if tracking_key in delivered_keys else str(display_status or "—")
        item_names = item_rows["LaptopModel"].fillna("Unknown item").astype(str).tolist()
        quantity = item_rows["OrderedQuantity"].fillna(0).sum()

        rows.append(
            {
                "Status": status,
                "Order date": header.get("HPReceiveDate"),
                "Planned delivery": header.get("PlannedDeliveryDate"),
                "Office": header.get("Office", "—"),
                "Items": "; ".join(item_names),
                "QTY": int(quantity) if float(quantity).is_integer() else quantity,
                "PO / Order": f"{purchase_order} / {hp_order}",
            }
        )

    if not rows:
        return pd.DataFrame(columns=PROCUREMENT_DEFAULT_COLUMNS)

    procurement_df = pd.DataFrame(rows)
    return procurement_df.sort_values("Order date", ascending=True, na_position="last")


def render_procurement_column_controls() -> list[str]:
    order = list(st.session_state.get("procurement_column_order", PROCUREMENT_DEFAULT_COLUMNS))
    order = [column for column in order if column in PROCUREMENT_DEFAULT_COLUMNS]
    for column in PROCUREMENT_DEFAULT_COLUMNS:
        if column not in order:
            default_index = PROCUREMENT_DEFAULT_COLUMNS.index(column)
            insert_at = len(order)
            for index in range(default_index - 1, -1, -1):
                previous_column = PROCUREMENT_DEFAULT_COLUMNS[index]
                if previous_column in order:
                    insert_at = order.index(previous_column) + 1
                    break
            order.insert(insert_at, column)
    st.session_state.procurement_column_order = order

    column_order = list(st.session_state.procurement_column_order)
    with st.expander("Customize columns", expanded=False):
        picker_col, left_col, right_col = st.columns([3, 1, 1])
        selected_column = picker_col.selectbox("Column", column_order, key="procurement_column_picker")
        selected_index = column_order.index(selected_column)
        if left_col.button("← Left", disabled=selected_index == 0, key="procurement_col_left"):
            column_order[selected_index], column_order[selected_index - 1] = (
                column_order[selected_index - 1],
                column_order[selected_index],
            )
            st.session_state.procurement_column_order = column_order
            st.rerun()
        if right_col.button("Right →", disabled=selected_index == len(column_order) - 1, key="procurement_col_right"):
            column_order[selected_index], column_order[selected_index + 1] = (
                column_order[selected_index + 1],
                column_order[selected_index],
            )
            st.session_state.procurement_column_order = column_order
            st.rerun()

    return column_order


def render_procurement_column_filters(column_order: list[str]) -> dict[str, str]:
    label_col, clear_col = st.columns([6, 1])
    label_col.caption("Filter by column")
    if clear_col.button("Clear", key="procurement_clear_col_filters"):
        for column in column_order:
            st.session_state.pop(f"procurement_col_filter_{column}", None)
        st.rerun()

    filter_columns = st.columns(len(column_order))
    filters: dict[str, str] = {}
    for index, column in enumerate(column_order):
        with filter_columns[index]:
            filters[column] = st.text_input(
                column,
                key=f"procurement_col_filter_{column}",
                label_visibility="collapsed",
                placeholder=column,
            )
    return filters


def filter_procurement_dataframe(df: pd.DataFrame, filters: dict[str, str]) -> pd.DataFrame:
    filtered = df.copy()
    for column, value in filters.items():
        if not value.strip() or column not in filtered.columns:
            continue

        needle = value.strip()
        if column in {"Order date", "Planned delivery"}:
            series = pd.to_datetime(filtered[column], errors="coerce").dt.strftime("%d %b %Y").fillna("")
        else:
            series = filtered[column].fillna("").astype(str)
        filtered = filtered[series.str.contains(needle, case=False, na=False)]

    return filtered


def render_procurement_page(current_snapshot: pd.DataFrame, delivered_keys: set[str]) -> None:
    st.subheader("Procurement")

    search_term = st.text_input(
        "Search procurement orders",
        value="",
        placeholder="Filter by status, office, item, PO, HP order #...",
        key="procurement_search",
    )

    procurement_df = build_procurement_dataframe(current_snapshot, delivered_keys)
    if procurement_df.empty:
        st.info("No orders match the current filters.")
        return

    if search_term.strip():
        mask = procurement_df.astype(str).apply(
            lambda column: column.str.contains(search_term.strip(), case=False, na=False)
        ).any(axis=1)
        procurement_df = procurement_df[mask]
        if procurement_df.empty:
            st.warning(f'No procurement rows found matching "{search_term.strip()}".')
            return

    column_order = render_procurement_column_controls()
    column_filters = render_procurement_column_filters(column_order)
    filtered_procurement_df = filter_procurement_dataframe(procurement_df, column_filters)
    if filtered_procurement_df.empty:
        st.warning("No procurement rows match the current column filters.")
        return

    st.dataframe(
        filtered_procurement_df,
        column_order=column_order,
        column_config={
            "Order date": st.column_config.DateColumn("Order date", format="DD MMM YYYY"),
            "Planned delivery": st.column_config.DateColumn("Planned delivery", format="DD MMM YYYY"),
            "QTY": st.column_config.NumberColumn("QTY", format="%d"),
        },
        hide_index=True,
        width="stretch",
    )
    st.caption(
        f"Showing {len(filtered_procurement_df):,} of {len(procurement_df):,} order(s). "
        "Use the row above to filter by column, or click a column header to sort."
    )


def set_app_page(page: str) -> None:
    st.session_state.app_page = page


def render_page_nav() -> None:
    page = st.session_state.get("app_page", "orders")
    st.sidebar.markdown("---")
    if page != "orders":
        st.sidebar.button(
            "← Orders",
            key="nav_orders",
            type="secondary",
            width="stretch",
            on_click=set_app_page,
            args=("orders",),
        )
    if page != "procurement":
        st.sidebar.button(
            "Procurement",
            key="nav_procurement",
            type="secondary",
            width="stretch",
            on_click=set_app_page,
            args=("procurement",),
        )
    if page != "analytics":
        st.sidebar.button(
            "Analytics",
            key="nav_analytics",
            type="secondary",
            width="stretch",
            on_click=set_app_page,
            args=("analytics",),
        )


def render_my_orders_page(history: pd.DataFrame, current_snapshot: pd.DataFrame, latest_order_line_keys: set) -> None:
    title_col, scope_col = st.columns([4, 1], vertical_alignment="bottom")
    title_col.subheader("Current Orders")
    include_past = scope_col.checkbox(
        "Include Past Orders",
        value=False,
        help="Search all historical snapshots, not just the latest one, and include orders that have already shipped or been cancelled.",
    )

    search_term = st.text_input(
        "Search",
        value="",
        placeholder="Search (PO, HP order #, item, office, status, transport mode, date...)",
        label_visibility="collapsed",
    )

    base = history if include_past else current_snapshot
    if not include_past:
        base = base[base["IsOutstanding"]]
    display = base.copy()

    delivered_keys = ensure_delivered_orders_loaded()
    display["DisplayStatus"] = display["Status"]
    manually_delivered = display.apply(lambda row: build_order_tracking_key(row) in delivered_keys, axis=1)
    display.loc[manually_delivered, "DisplayStatus"] = "Delivered"

    if not include_past:
        display = display[~manually_delivered]
    if include_past and "OrderLineKey" in display.columns:
        presumed_delivered = (
            ~display["OrderLineKey"].isin(latest_order_line_keys)
            & (display["Status"] != "Shipped")
            & ~manually_delivered
        )
        display.loc[presumed_delivered, "DisplayStatus"] = "Presumed Delivered"

    if search_term.strip():
        text_columns = [column for column in MY_ORDERS_SEARCH_COLUMNS if column in display.columns] + ["DisplayStatus"]
        mask = pd.Series(False, index=display.index)
        for column in text_columns:
            mask |= display[column].astype(str).str.contains(search_term, case=False, na=False)
        for column in MY_ORDERS_SEARCH_DATE_COLUMNS:
            if column in display.columns:
                mask |= display[column].dt.strftime("%Y-%m-%d %d %b %Y").str.contains(search_term, case=False, na=False)
        display = display[mask]
        if display.empty:
            st.warning(f'No orders found matching "{search_term.strip()}".')
            st.caption(f"Showing 0 of {len(base):,} order lines in total.")
            return

    display = display.sort_values(["PlannedDeliveryDate", "PlannedShipDate"], na_position="last")
    display["OrderGroupKey"] = list(zip(
        display["PurchaseOrderNo"].astype(str),
        display["HPOrderNo"].astype(str),
        display["PlannedDeliveryDate"].astype(str),
        display["SnapshotDate"].astype(str),
    ))

    for office in sorted(display.get("Office", pd.Series(dtype=str)).dropna().astype(str).unique()):
        office_orders = display[display["Office"] == office]
        if office_orders.empty:
            continue
        addresses = office_orders.get("ShipToAddr", pd.Series(dtype=str)).dropna().astype(str)
        address = addresses.mode().iat[0] if not addresses.empty else "Address unknown"

        order_summary = f"{len(office_orders):,} order line(s) across {office_orders['OrderGroupKey'].nunique():,} order(s)"
        st.markdown(
            f"### {office}<span style='font-size: 0.875rem; font-weight: normal; color: rgba(49, 51, 63, 0.6); margin-left: 0.75rem;'>{order_summary}</span>",
            unsafe_allow_html=True,
        )
        st.caption(address)

        order_groups = office_orders.groupby("OrderGroupKey", sort=False)
        for _, group in order_groups:
            render_order_group_card(group, show_snapshot_date=include_past)

    st.caption(f"Showing {len(display):,} of {len(base):,} order lines in total.")


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


def load_api_version() -> str:
    for path in (DEPLOYED_VERSION_PATH, VERSION_PATH):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        api_version = payload.get("apiVersion")
        if api_version is not None:
            return str(api_version)
    return "dev"


def render_page_header() -> None:
    api_version = load_api_version()
    st.markdown(
        f"""
        <style>
        .ovadue-top-bar {{
            position: fixed;
            top: 3.75rem;
            left: var(--sidebar-width, 21rem);
            right: 0;
            z-index: 999;
            background: var(--background-color, #ffffff);
            border-bottom: 1px solid rgba(49, 51, 63, 0.12);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            padding: 0.65rem 1.5rem 0.8rem;
            box-sizing: border-box;
        }}

        /* Streamlit sets --sidebar-width on .stApp; keep the bar aligned when the sidebar collapses */
        .stApp[data-testid="stAppViewContainer"] .ovadue-top-bar {{
            left: var(--sidebar-width, 21rem);
        }}

        .ovadue-top-bar h1 {{
            font-size: 2.25rem;
            font-weight: 600;
            margin: 0;
            line-height: 1.2;
        }}

        .ovadue-top-bar p {{
            color: rgba(49, 51, 63, 0.6);
            margin: 0.25rem 0 0;
            font-size: 0.95rem;
        }}

        .ovadue-top-bar-spacer {{
            height: 5.25rem;
        }}
        </style>
        <div class="ovadue-top-bar">
            <h1>OvaDue</h1>
            <p>Outstanding orders and delivery-time analysis. API v{api_version}</p>
        </div>
        <div class="ovadue-top-bar-spacer"></div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render_page_header()

    if "app_page" not in st.session_state:
        st.session_state.app_page = "orders"

    ensure_delivered_orders_loaded()

    # Each active dashboard session rescans the data directory every hour.
    st_autorefresh(interval=60 * 60 * 1000, key="hourly_data_check")
    files = discover_data_files(DATA_DIR)
    file_signature = data_file_signature(files)

    df_all = load_all_data(file_signature)
    if df_all.empty:
        st.error("No readable .xls or .xlsx files were found in this folder or uploads directory.")
        return

    latest_snapshot_date = latest_snapshot(df_all)
    latest_order_line_keys = (
        set(df_all.loc[df_all["SnapshotDate"] == latest_snapshot_date, "OrderLineKey"])
        if pd.notna(latest_snapshot_date) else set()
    )

    st.sidebar.header("Filters")
    if st.sidebar.button("Refresh data now", width="stretch"):
        st.rerun()

    regions = sorted(df_all.get("Region", pd.Series(dtype=str)).dropna().astype(str).unique())
    offices = sorted(df_all.get("Office", pd.Series(dtype=str)).dropna().astype(str).unique())
    statuses = sorted(df_all.get("Status", pd.Series(dtype=str)).dropna().astype(str).unique())
    status_options = sorted(set(statuses) | {"Delivered"})

    browser_timezone = streamlit_js_eval(
        js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
        key="browser_timezone",
    )
    if browser_timezone is None:
        st.stop()
    if not initialize_filter_preferences(df_all, regions, offices, browser_timezone):
        st.stop()

    st.session_state["office_setup_complete"] = True
    nearest_office = preferred_office_for_timezone(df_all, browser_timezone)

    # Region selector (dropdown with "Global" option)
    region_options = ["Global"] + regions
    selected_region = st.sidebar.selectbox(
        "Region",
        options=region_options,
        index=region_options.index(st.session_state.get("selected_region", "Global")),
        key="selected_region",
        on_change=save_region_to_storage,
    )

    # Determine which offices to show based on selected region
    if selected_region == "Global":
        available_offices = offices
        selected_regions_for_filter = regions  # Use all regions for filtering later
    else:
        # Get offices that belong to the selected region
        available_offices = sorted(df_all[df_all["Region"] == selected_region].get("Office", pd.Series(dtype=str)).dropna().astype(str).unique())
        selected_regions_for_filter = [selected_region]

    # Office selector with "All" option at the top
    office_options = ["All"] + available_offices
    current_office_selection = st.session_state.get("selected_offices", [])
    valid_office_selection = [office for office in current_office_selection if office in office_options]
    if valid_office_selection != current_office_selection:
        st.session_state["selected_offices"] = valid_office_selection

    selected_offices = st.sidebar.multiselect(
        "Office",
        options=office_options,
        key="selected_offices",
        on_change=save_office_selection,
    )

    # If "All" is selected or no offices selected, use all available offices for filtering
    offices_for_filter = available_offices if "All" in selected_offices or not selected_offices else [o for o in selected_offices if o != "All"]

    use_timezone_office = st.sidebar.checkbox(
        "Filter to same-timezone office",
        value=False,
        disabled=nearest_office is None,
    )
    selected_statuses = st.sidebar.multiselect("Status", options=status_options, default=status_options)

    st.sidebar.subheader("Problem filters")
    show_outside_lt_filter = st.sidebar.toggle("Show delayed (outside LT)", key="show_outside_lt_filter")
    show_overdue_filter = st.sidebar.toggle("Show overdue", key="show_overdue_filter")
    show_no_date_filter = st.sidebar.toggle("Show no date given", key="show_no_date_filter")

    render_page_nav()

    df = df_all.copy()
    if selected_regions_for_filter:
        df = df[df["Region"].astype(str).isin(selected_regions_for_filter)]
    if offices_for_filter:
        df = df[df["Office"].astype(str).isin(offices_for_filter)]
    if use_timezone_office and nearest_office:
        df = df[df["Office"] == nearest_office]
    delivered_keys = ensure_delivered_orders_loaded()
    df = apply_effective_status(df, delivered_keys)
    if selected_statuses:
        df = df[df["EffectiveStatus"].astype(str).isin(selected_statuses)]

    problem_masks = []
    if show_outside_lt_filter and "IsOutsideLT" in df.columns:
        problem_masks.append(df["IsOutsideLT"] == True)
    if show_overdue_filter and "IsOverdue" in df.columns:
        problem_masks.append(df["IsOverdue"] == True)
    if show_no_date_filter and "IsMissingPlannedDelivery" in df.columns:
        problem_masks.append(df["IsMissingPlannedDelivery"] == True)
    if problem_masks:
        combined_mask = problem_masks[0]
        for mask in problem_masks[1:]:
            combined_mask = combined_mask | mask
        df = df[combined_mask]

    active_problem_filters = [
        label for enabled, label in (
            (show_outside_lt_filter, "delayed (outside LT)"),
            (show_overdue_filter, "overdue"),
            (show_no_date_filter, "no date given"),
        ) if enabled
    ]
    if active_problem_filters:
        st.info("Showing orders flagged as: " + ", ".join(active_problem_filters))

    if df.empty:
        st.warning("No rows match the selected filters.")
        return

    current_date = latest_snapshot(df)
    current_snapshot = df[df["SnapshotDate"] == current_date].copy() if pd.notna(current_date) else df.copy()

    page = st.session_state.get("app_page", "orders")
    if page == "procurement":
        render_procurement_page(current_snapshot, delivered_keys)
    elif page == "analytics":
        outstanding_tab, delivery_tab, analysis_tab = st.tabs(
            ["Outstanding Orders", "Delivery Performance", "Analysis"]
        )
        with outstanding_tab:
            render_outstanding_page(current_snapshot, LATE_OTD_THRESHOLD, LATE_DELIVERY_GRACE_DAYS)
        with delivery_tab:
            render_delivery_page(df, current_snapshot)
        with analysis_tab:
            # Handover 2.0 drop-in: Regional flux, Hardware, Offices by region, Performance (Top 3)
            render_analysis(DATA_DIR)
    else:
        render_my_orders_page(df, current_snapshot, latest_order_line_keys)

    csv = df.drop(columns=["EffectiveStatus"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name="ovadue_orders_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
