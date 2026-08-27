# OvaDue handover 2.0

**This is a drop-in UI package.** Add these Analysis views to the website you already run. Do not start a new Streamlit server from this zip.

The other session already has the live host and the HP data. Copy these pages/modules into that site, keep their layout and scoring, and bind to the site’s existing data/loader.

Every widget label, tab name, default, and session_state key below is quoted from the code. **Read the code before changing scoring.**

Canonical files:

- Document: `C:\OvaDue\HANDOVER-2.0.md` (this file; not `HANDOVER.md`)
- Zip: `C:\OvaDue\handover-2.0.zip`

---

### Drop-in map

| Zip member | Drop into existing site |
| --- | --- |
| `HANDOVER-2.0.md` | Read first |
| `pages/1_Analysis.py` | The Analysis page (four tabs). Adapt imports/router to the live app’s page system if it is not Streamlit. |
| `ovadue/` | Scoring, office parse, chart helpers, appearance. Import as a library. |
| `app.py` | Home **page content only** (title, caption, snapshot-count metric) — not an app server. Merge into the live Home if needed. |

**Do not ship / do not do:** `data/` reports, `pip install` / `streamlit run`, localhost, iframe-a-second-server.

**Bind data:** replace `load_history(data_dir)` with the live app’s history frame, **same columns** `ovadue/load.py` already produces (`read_snapshot` keep-list, then `load_history` adds the promise/late flags):

| Source | Columns |
| --- | --- |
| `read_snapshot` | `snapshot_at`, `source_file`, `line_key`, `PurchaseOrderNo`, `HPOrderNo`, `region`, `ShipToCountry`, `office`, `status`, `HPReceiveDate`, `CustomerRequestedDate`, `planned_delivery`, `ProductNumber`, `qty`, `hardware_type`, `hardware_category`, `model`, `promised_lead_days`, `standard_lt_weeks`, `otd_days` |
| `load_history` adds | `original_planned`, `planned_delta_days`, `date_pushed`, `date_pulled`, `late_vs_original`, `late_vs_current`, `days_past_original` |

Derived in `read_snapshot`: `hardware_type` = `MM_MH_Type` else `MM_MH_Category` else `"Unknown"`; `hardware_category` = `MM_MH_Category` else `"Unknown"`; `model` = `MM_MH_Series` else `MM_MH_Model` via `_short_model`; `region` from `ShipToHPRegion` (`"nan"` → `"Unknown"`); `promised_lead_days` = `OTD Days` if present else `PlannedDeliveryDate − HPReceiveDate` days.

Do not assume a POD column.

---

### Purpose

Display surface for Arup HP backlog snapshots (`osreport_ArupBacklog_*`, first sheet `HP OrderStatus`). Regions from `ShipToHPRegion`: **EMEA, APJ, US, CA** (else `"Unknown"`).

**Site map**

- **Home** — short landing (`app.py`): title, one caption, one metric (snapshot count).
- **Analysis** — all analysis (`pages/1_Analysis.py`): header metrics, sidebar filters, four tabs (Regional flux, Hardware & date changes, Offices by region, Performance).

Reproduce this information architecture and scoring in the live site. Use `ovadue/` as a library (especially `metrics.py`, `offices.py`, `load.py` as the frame shape). Chart chrome in `charts.py` / `ui.py` is the reference for Plotly behaviour (zoom, expand, scatter jiggle), not a requirement to keep Streamlit widgets.

---

### Where things live (absolute paths)

| What | Absolute path / storage | Notes |
| --- | --- | --- |
| Workspace root | `C:\OvaDue` | Project root |
| Home snippet | `C:\OvaDue\app.py` | Title, caption, snapshot-count metric — merge into the live Home |
| Analysis page | `C:\OvaDue\pages\1_Analysis.py` | Entire analysis UI (four tabs) |
| Package | `C:\OvaDue\ovadue\` | `load.py`, `offices.py`, `metrics.py`, `charts.py`, `ui.py`, `__init__.py` |
| This handover | `C:\OvaDue\HANDOVER-2.0.md` | Canonical doc (zip root) |
| Older handover | `C:\OvaDue\HANDOVER.md` | Superseded; do not treat as source of truth |
| Zip output | `C:\OvaDue\handover-2.0.zip` | This drop-in package |
| Older zip | `C:\OvaDue\OvaDue-handover.zip` | Superseded |
| HP reports | **Not in this zip** | Live app already has them; on this machine they sit in `C:\OvaDue\data\` |

**Report filename shape** (only if the live ingest still parses those names). `ovadue/load.py` `select_report_files(data_dir)` does `Path(data_dir).glob("osreport_ArupBacklog_*")`, keeps suffixes `.xls` / `.xlsx` only, and requires regex `osreport_ArupBacklog_(\d{4}-\d{2}-\d{2})_(\d{3,5})` (`SNAPSHOT_RE`, case-insensitive). Same date+time stamp: **prefer `.xlsx`**. HHMM = first 4 digits of the time group. Example names: `osreport_ArupBacklog_2026-02-19_0931.xls`, `…_2026-07-09_06461.xls` (5-digit time group), `…_2026-07-16_0608 1.xls` (space + suffix still matches).

The Analysis sidebar **Data folder** widget is a leftover local-path bind. Drop it and feed the live history frame instead.

**Appearance image — session_state only, not a file on disk.** `apply_appearance()` in `ovadue/ui.py` never writes a background file. Uploaded bytes live in session_state:

| Constant in `ui.py` | Session key | Default | What it holds |
| --- | --- | --- | --- |
| `SS_BG_COLOR` | `appearance_bg_color` | `"#ffffff"` | Colour picker |
| `SS_COLOR_FADE` | `appearance_color_fade` | `100` | Colour wash 0–100 |
| `SS_IMAGE_BYTES` | `appearance_image_bytes` | unset / `None` | Raw uploaded photo bytes |
| `SS_IMAGE_MIME` | `appearance_image_mime` | unset / `None` | `image/png` \| `image/jpeg` \| `image/webp` (`image/jpg` coerced to `image/jpeg`) |
| `SS_IMAGE_FADE` | `appearance_image_fade` | `80` | Photo visibility 0–100 |
| `SS_UPLOAD_NONCE` | `appearance_upload_nonce` | `0` | Suffix so **Clear image** remounts the uploader |
| (widget key, not a constant) | `appearance_upload_{nonce}` | — | `st.file_uploader` key |

**Period / Detailed view (Analysis page, Performance tab):**

| Session key | Default | Widget |
| --- | --- | --- |
| `t3_period` | `"All years"` | `st.segmented_control("Period", …, key="t3_period")` |
| `t3_detailed` | `False` | `st.toggle("Detailed view", key="t3_detailed")` |

**Chart expand (all Analysis tabs):**

| Constant | Session key | Default | Meaning |
| --- | --- | --- | --- |
| `EXPAND_STATE` | `chart_expanded` | unset / `None` | Chart key currently filling the page (`"flux"`, `"hw_late"`, `"hw_chg"`, `"office_EMEA"`, …) |

**What is NOT stored**

- No database. All scoring is computed in memory from the snapshot history.
- No proof-of-delivery (POD) dates in the reports or the code.
- Appearance photo does **not** persist across process restart (session_state only; no save-to-disk path in `ui.py`).
- Period, Detailed view, and expand state also die with the session.

**Not in this package**

- `data/` HP reports (live site already has them).
- `.streamlit/`, `__pycache__/`, `*.pyc`, `.venv/`, `.git/`.
- `requirements.txt` (live stack exists).
- Old zips (`OvaDue-handover.zip`, and this zip itself).

Analysis in the reference UI caches history with `@st.cache_data(show_spinner="Loading backlog snapshots…")` on `_load(path)` in `1_Analysis.py`. That is process memory, not a project file. After the data bind, cache (or equivalent) the live history the same way if the host needs it.

---

### Data model and scoring (closed/late/on-time/line key/office parse)

Reports have **no actual proof-of-delivery dates**. Outcomes are inferred from snapshot presence.

#### Line identity

`ovadue/load.py` `_line_key`:

```
HPOrderNo|PurchaseOrderNo|ProductNumber|ShipToAddr.casefold()|OrderedQuantity
```

Older files lack `ItemNumber`, so identity is built without it. If the same key appears twice in one snapshot, extras get a `|cumcount` suffix (`groupby("line_key").cumcount()`; suffix only when count `> 0`).

#### Closed / late / on time

Implemented in `ovadue/metrics.py` `build_lifecycle`:

| Term | Meaning in code |
| --- | --- |
| **Open** (`is_open`) | `last_seen` equals the latest snapshot in the history |
| **Canceled** | last `Status` is exactly `ShipmentCanceled` |
| **Closed** | not open and not canceled. `closed_at` = the **next snapshot after last seen** (`next_snap` map). Not the last-seen date itself. |
| **Late** (`landed_late`) | closed **and** `last_seen` calendar day is after `original_planned` (first `PlannedDeliveryDate` for that line) |
| **On time** (`landed_on_time`) | closed, not overdue, and `original_planned` is present |
| Still on latest report, or canceled | `closed_at` is null — **not scored as closed** |

A line that vanishes after it was still on the backlog past the first promised date is treated as **landed late**. A line that vanishes before that date is **on time**. There is no POD column to contradict this.

- `days_late` = `closed_at − original_planned` (days), only when `landed_late`; otherwise `0`.
- `actual_lead_days` = `closed_at −` (`HPReceiveDate` on last row, else first-seen `HPReceiveDate`, else `first_seen`).

Also on the lifecycle row: `n_snapshots`, `n_date_pushes`, `n_date_pulls`, `n_date_changes` (count of non-zero planned-date deltas).

#### Original promise vs latest ETA

Set in `load_history`:

- `original_planned` = first `planned_delivery` per `line_key`
- `late_vs_original` = snapshot **calendar day** after `original_planned`
- `late_vs_current` = snapshot calendar day after current `planned_delivery`
- `date_pushed` / `date_pulled` from consecutive `PlannedDeliveryDate` day deltas (`planned_delta_days`)
- `days_past_original` = snapshot day − original planned day

Analysis sidebar radio (widget label **Lateness vs**):

| `st.sidebar.radio` value | Display label (`format_func`) | Used by |
| --- | --- | --- |
| `"original"` (default, `index=0`) | **Original promise** | `regional_flux(..., promise=)` → column `late_vs_original` |
| `"current"` | **Latest ETA** | column `late_vs_current` |

**Office reliability charts always use original-promise lateness** (`late_vs_original` / `late_share` from `office_timeseries`). The **Lateness vs** toggle does **not** change Tab 3 or Performance.

#### Offices

`ovadue/offices.py` `extract_office(addr, country)`: longest-first needles in `ShipToAddr`, then country fallback. Full alias list is under **Office aliases** below.

#### Scorecard fields (`office_scorecard`)

| Field | Formula |
| --- | --- |
| `n_closed` | count of closed `line_key`s |
| `n_orders` | nunique `_order_id` (prefer `HPOrderNo`, else `PurchaseOrderNo`, else `line_key`). If those ids are blank, fall back to `n_closed`. |
| `n_on_time` / `n_late` | sums of `landed_on_time` / `landed_late` |
| `on_time_rate` | `n_on_time / n_closed` |
| `late_rate` | `n_late / n_closed` |
| `consistency` | `(on_time_rate × 100) − (avg_date_changes × 8)`. Not a percent. |
| `longest_streak` | longest run of consecutive snapshots with **zero** `late_vs_original` lines (`_office_on_time_streaks`). Canceled rows excluded. |
| `longest_delay` | max `days_late` |
| `median_lead` | median `actual_lead_days` |
| `qualified` | `n_closed >= min_closed` |

If `close_year` is set: closed rows filtered to `closed_at.dt.year == close_year`; history for streaks filtered to `snapshot_at.dt.year == close_year`.

---

### File map (path → role, every module function that matters)

| Path | Role |
| --- | --- |
| `C:\OvaDue\app.py` | Home display snippet. Title, caption, snapshot-count metric. Calls `apply_appearance()`. |
| `C:\OvaDue\pages\1_Analysis.py` | Analysis: sidebar, four chrome metrics, four tabs, Performance boards. |
| `C:\OvaDue\ovadue\__init__.py` | Package marker: docstring `OvaDue — HP backlog analysis helpers.` |
| `C:\OvaDue\ovadue\load.py` | History-frame shape: parse snapshots, original promise, late flags. |
| `C:\OvaDue\ovadue\offices.py` | Address → canonical office name. |
| `C:\OvaDue\ovadue\metrics.py` | Lifecycle, flux, hardware outcomes, office scorecard, streaks. **Scoring source of truth.** |
| `C:\OvaDue\ovadue\charts.py` | Plotly figures + region color maps. |
| `C:\OvaDue\ovadue\ui.py` | CSS injection, Appearance, expand/restore, linked scatter HTML. |
| `C:\OvaDue\HANDOVER-2.0.md` | This document. |

**`ovadue.load`**

- `SNAPSHOT_RE` — `osreport_ArupBacklog_(\d{4}-\d{2}-\d{2})_(\d{3,5})`
- `DATE_COLS` — `HPReceiveDate`, `CustomerRequestedDate`, `PlannedShipDate`, `PlannedDeliveryDate`
- `select_report_files(data_dir)` — glob + xlsx-over-xls for the same stamp
- `snapshot_at_from_name(name)` — timestamp from filename; HHMM = first 4 digits of the time group
- `_line_key(frame)` — identity string (see above)
- `_short_model(value)` — strips ` IDS Base Model`, ` inch ` → `" `, `Mobile Workstation PC` → `ZBook`
- `_parse_lt_weeks(value)` — mid of `N - M` or first integer from `Standard LT`
- `read_snapshot(path)` — one file → frame with `line_key`, `office`, `region`, dates, hardware fields
- `load_history(data_dir)` — concat, original promise, deltas, late flags — **replace this call with the live history frame**

**`ovadue.offices`**

- `extract_office(addr, country=None) -> str`
- `_OFFICE_NEEDLES` / `_SORTED_NEEDLES` / `_COUNTRY_FALLBACK`

**`ovadue.metrics`**

- `build_lifecycle(history)`
- `regional_flux(history, promise="original")` — `promise` is `"original"` or `"current"`; excludes `ShipmentCanceled`
- `hardware_outcomes(lifecycle, grain="hardware_type")` — closed lines only
- `date_change_by_type(lifecycle, grain="hardware_type")` — non-canceled lines (open included)
- `office_timeseries(history, region=None)` — excludes canceled; `late_share` always from `late_vs_original`
- `scorecard_years(lifecycle, history) -> list[int]` — union of snapshot years and close years
- `office_scorecard(lifecycle, history, min_closed=3, *, close_year=None)`
- `_order_id(frame)` / `_office_on_time_streaks(history)` — private helpers

**`ovadue.charts`**

- Color maps: `REGION_COLORS`, `PASTEL_REGION_COLORS`, `DARK_REGION_COLORS`
- `_region_color(region)`
- `category_colors(names)` — Plotly `Dark24` then `Set3`
- `regional_flux_lines(flux, y, y_title, title)`
- `hardware_lateness_scatter(outcomes, grain, colors=None)`
- `date_change_scatter(changes, grain, colors=None)`
- `office_lines(ts, y, y_title, title)`

**`ovadue.ui`**

- Constants: `EXPAND_STATE`, `PLOTLY_CONFIG`, `CHART_CSS`, `SS_*`, `DEFAULT_BG_COLOR`, `DEFAULT_COLOR_FADE`, `DEFAULT_IMAGE_FADE`
- `inject_css(css, *, slot="default")`, `inject_chart_css()`, `apply_appearance()`
- `_appearance_widgets()`, `_appearance_css()`, `_hex_ok()`, `_image_data_uri()`
- `is_showing(key, group)`, `expand_bar(key)`, `show_plotly(fig, *, key, group, default_height=440)`, `scatter_pair(fig_a, fig_b, *, group, key_a="hw_late", key_b="hw_chg")`
- `_toggle`, `_fig_json`, `_expanded_height()` → `780`

---

### Home page (`app.py`) — every widget, caption, metric

Merge this chrome into the live Home if you want it. `app.py` is page content only.

| Kind | Exact text / behaviour |
| --- | --- |
| Title | `st.title("OvaDue")` |
| Caption | `HP backlog reports, sliced by office and region.` |
| Metric | Label **Backlog snapshots loaded**. Bind the value to the live history (`history["snapshot_at"].nunique()`), same count as Analysis **Snapshots**. |
| Sidebar | Only **Appearance** (from `apply_appearance()`). No Data folder, no filters. |

---

### Analysis page chrome — title, blurb, four metrics, sidebar (promise vs ETA, min closed lines, Appearance: colour/fade/image/clear), tabs list

Reference chrome: `st.set_page_config(page_title="Analysis · OvaDue", layout="wide")`. Immediately `inject_chart_css()` (hides Plotly/Streamlit fullscreen so Expand stays in-page). If the live app is not Streamlit, keep the title/blurb/metrics/tabs and adapt the router.

| Kind | Exact text |
| --- | --- |
| Title | `st.title("Analysis")` |
| Caption (blurb) | `Late means a line was still on the backlog after its **first promised** delivery date. Actual POD dates are not in these reports, so a line that vanishes after that point is treated as landed late.` |

Load in the reference UI is `@st.cache_data(show_spinner="Loading backlog snapshots…")`. Failure copy: `st.error(f"Could not load reports from `{data_dir}`: {exc}")` then `st.stop()`. After the data bind, surface the live loader’s error the same way.

#### Sidebar widgets (order on the page)

| Widget | Label | Defaults / options | Session key |
| --- | --- | --- | --- |
| `st.sidebar.text_input` | **Data folder** | leftover local-path bind — **drop this**; use the live history frame | none (Streamlit auto) |
| `st.sidebar.number_input` | **Min closed lines for Top 3** | `min_value=1`, `value=3`, `step=1` | none |
| `st.sidebar.slider` | **Max offices per region chart** | `min_value=4`, `max_value=40`, `value=12` | none |
| `st.sidebar.radio` | **Lateness vs** | options `["original", "current"]`, `index=0`. Labels: **Original promise** / **Latest ETA** | none |
| `st.sidebar.multiselect` | **Regions** | options = sorted unique `history["region"]`; `default` = all of those (not `"All"`). Internal list is `["All"] + sorted(...)` but `"All"` is **not** offered as an option. | none |
| Appearance expander | **Appearance** | see below | keys in `ui.py` |

If the Regions multiselect is **empty**, filters are skipped (`history_f = history`, `life_f = lifecycle`). If any regions are selected, both frames are `region.isin(region_filter)`.

`apply_appearance()` is called **after** the Regions widget (so Appearance sits at the bottom of the Analysis sidebar).

#### Appearance expander (sidebar, both Home and Analysis)

`st.sidebar.expander("Appearance")` from `_appearance_widgets()`:

| Widget | Label | Defaults / help |
| --- | --- | --- |
| `st.color_picker` | **Background colour** | key `appearance_bg_color`, default `#ffffff`. Help: `Solid wash colour. Strength is Colour fade.` |
| `st.slider` | **Colour fade** | `min_value=0`, `max_value=100`, `format="%d%%"`, key `appearance_color_fade`, default **100**. Help: `How strong the colour wash is. Over a photo this is the overlay.` |
| `st.file_uploader` | **Background image** | `type=["png", "jpg", "jpeg", "webp"]`, key `appearance_upload_{appearance_upload_nonce}`. Help: `Optional photo. Image fade sets how visible it is.` Bytes → `appearance_image_bytes`; MIME → `appearance_image_mime`. |
| `st.slider` | **Image fade** | `min_value=0`, `max_value=100`, `format="%d%%"`, key `appearance_image_fade`, default **80**. Help: `How visible the uploaded photo is.` |
| `st.button` | **Clear image** | Shown only if `appearance_image_bytes` is set. Sets bytes and MIME to `None`, increments `appearance_upload_nonce`, `st.rerun()`. |

CSS: photo on `.stApp::before` (`background-size: cover`, opacity = image fade / 100); colour wash on `.stApp::after`; sidebar uses `color-mix` 94% of the theme/default background.

#### Four page metrics (not in the sidebar)

`st.columns(4)`:

| Column | Label | Value |
| --- | --- | --- |
| c1 | **Snapshots** | unique `history["snapshot_at"]` (unfiltered history) |
| c2 | **Line items (latest)** | unique `line_key` on the max `snapshot_at` (unfiltered) |
| c3 | **Offices** | unique `history["office"]` (unfiltered) |
| c4 | **Closed lines** | count of `life_f["closed_at"].notna()` (**region-filtered** lifecycle) |

#### Tabs list (exact names)

```
st.tabs(["Regional flux", "Hardware & date changes", "Offices by region", "Performance"])
```

Variables: `tab_flux`, `tab_hw`, `tab_offices`, `tab_top`.

`t3_period` / `t3_detailed` are `setdefault`’d here (before the tabs) so the Performance widgets have defaults even before that tab is opened. If `t3_period` is not in `year_choices`, it is reset to `"All years"`.

---

### Tab 1: Regional flux — controls, metrics plotted, chart behaviour (zoom, expand)

- Subheader: **When deliveries ran late, by region**
- Radio **What to plot** (`horizontal=True`):

| Value | Display label | Chart title | Y-axis title | Extra |
| --- | --- | --- | --- | --- |
| `n_late` | **Count of late lines** | `Lines still on the backlog after their promised delivery date` | `Late line items` | — |
| `late_share` | **Share of open lines that are late** | `Share of open lines past their promised delivery date` | `Late share` | `yaxis_tickformat=".0%"` |
| `n_date_pushes` | **Planned dates pushed later** | `Order lines whose planned delivery date moved later` | `Date slips` | — |

Data: `regional_flux(history_f, promise=promise)` — respects **Regions** and **Lateness vs**. Canceled rows excluded in the metric. Plot: `regional_flux_lines` — Plotly line + markers, `color="region"`, `REGION_COLORS`, x = `snapshot_at`, `hovermode="x unified"`, legend title **Region**, x-axis title **Report date**, `dragmode="zoom"`.

Display: `show_plotly(fig, key="flux", group=("flux",))`.

**Zoom / mode bar** (`PLOTLY_CONFIG` in `ui.py`): `scrollZoom=True`, `doubleClick="reset"`, `displayModeBar=True`, `displaylogo=False`. Removed buttons: `lasso2d`, `select2d`, `toggleFullscreen`, `togglefullscreen`. Caption on Tab 2 also states drag/scroll/double-click; Tab 1 uses the same config.

**Expand:** `expand_bar("flux")` — right-aligned button in columns `[6, 1]`. Label **Expand** or **Restore**. Help: `Fill the page area under the sidebar and tabs. Does not hide navigation.` Icons `:material/open_in_full:` / `:material/close_fullscreen:`. Button key `expandbtn_flux`. Expanded height `780` (`_expanded_height`). Default chart height `440`.

**Peak line** under the chart: for each region with any positive/non-null metric, `**{region}** peaked {DD Mon YYYY}` joined with ` · `, prefixed `Peak flux: `.

---

### Tab 2: Hardware & date changes — both scatters, linking/jiggle, expand

- Subheader: **Which hardware is late or on time**
- Radio **Group hardware by** (`horizontal=True`):

| Value | Display label |
| --- | --- |
| `hardware_type` | **Type** |
| `hardware_category` | **Category** |
| `model` | **Model** |

Two datasets:

1. `hardware_outcomes(life_f, grain=grain)` — **closed lines only**. Feeds the on-time scatter.
2. `date_change_by_type(life_f, grain=grain)` — **non-canceled lines, including open**. Feeds the date-change scatter.

Colors: `category_colors` over the union of names from both frames.

#### Scatter A — on-time vs delay (`hardware_lateness_scatter`)

- Title: **Hardware: on-time rate vs typical delay**
- X: `on_time_rate` — axis **On-time share (closed lines)**, tick format `.0%`
- Y: `avg_days_late` — axis **Average days late (0 if on time)**
- Size: `n_closed` (area, `sizeref=2.0`)
- Hover: `n_closed`, `n_late`, `n_on_time`, on-time rate, avg days late
- Legend title: **Click a name to jiggle its pair**
- Plotly key / expand key: `hw_late`

If `outcomes` is empty: `st.info("No closed lines yet to score on-time vs late.")` and only the date-change scatter is shown via `show_plotly(..., key="hw_chg", group=("hw_chg",))` (normal Expand/Restore bar, not the pair toggles).

#### Scatter B — date-change volume (`date_change_scatter`)

- Title: **How often planned delivery dates change**
- X: `n_lines` — axis **Line items seen**
- Y: `avg_changes` — axis **Average planned-date revisions per line**
- Size: `n_lines`
- Hover: `share_changed` (`.0%`), `max_changes`, `avg_changes`
- Legend title: **Click a name to jiggle its pair**
- Plotly / expand key: `hw_chg`

#### Linking / jiggle (`scatter_pair`)

When outcomes exist, both figures render in **one HTML view** (`components.html` in the reference UI) so a click on one jiggles the matching category on the other:

- Click a bubble (`plotly_click`) or a legend name (`plotly_legendclick`, plus DOM `.legend .traces` click). Legend click does **not** toggle visibility (`return false`). Double-click legend disabled.
- Jiggle: marker outline to width `3` color `#111827`; position steps `[0.95, -1.15, 0.8, -0.55, 0.28, 0]` × 2.8% of x-range and 4.5% of y-range; 70 ms per step; then restore.
- Reference Plotly load: `https://cdn.plot.ly/plotly-2.35.2.min.js`. Offline hosts need a local bundle. If the bundle fails: `Plotly failed to load. Check network access to cdn.plot.ly.`

#### Expand (pair-specific labels)

Not the generic **Expand** / **Restore** bar. Two buttons in columns `[1, 1, 4]`:

| Button (collapsed) | Button (expanded) | Key | Help |
| --- | --- | --- | --- |
| **Expand on-time** | **Restore** | `expandbtn_hw_late` | `Fill the page area. Sidebar and tabs stay visible.` |
| **Expand date-changes** | **Restore** | `expandbtn_hw_chg` | same |

Focus `"a"` hides pane B; `"b"` hides pane A; `"both"` stacks both. Pane height 450 when both shown, 780 when one is expanded. Container height 940 vs 780 (+16). If another tab’s chart is expanded (`chart_expanded` not in `("hw_late", "hw_chg")`), this tab still shows both (expand state treated as none for this pair).

Caption under the charts (exact):

> Click a bubble or a legend name to jiggle the same item on the other chart. Bubble size is volume. On-time uses closed lines only (dropped off a later report). Date-change scatter includes open lines too. Drag to zoom, scroll to zoom, double-click to reset.

---

### Tab 3: Offices by region — per-region charts, series, controls

- Subheader: **Offices inside each region**
- Radio **Office chart** (`horizontal=True`):

| Value | Display label | Series (`y`) | Y-axis title | Chart title pattern |
| --- | --- | --- | --- | --- |
| `churn` | **Models / dates that change the most** | `n_date_pushes` | `Planned dates pushed later` | `{region}: delivery dates revised` |
| `reliability` | **Least reliable vs the promised date** | `late_share` | `Share past original promise` | `{region}: least reliable vs promised date` (y tick `.0%`) |
| `lead` | **Longest lead time** | `median_lead` | `Median promised lead time (days)` | `{region}: longest lead time` |

Data: `office_timeseries(history_f)` — **Lateness vs** does **not** apply; reliability is always `late_vs_original`. Canceled excluded. `median_lead` here is **promised** lead (`promised_lead_days`), not scorecard `actual_lead_days`.

**Region order:** `EMEA`, `APJ`, `US`, `CA` first (if present), then any other regions alphabetically (e.g. `Unknown`).

**Offices plotted:** per region, `groupby("office")["n_lines"].sum().nlargest(int(max_offices))` — slider **Max offices per region chart** (4–40, default **12**).

**Expand group:** keys `office_EMEA`, `office_APJ`, `office_US`, `office_CA`, plus `office_{region}` for extras. `is_showing` + `show_plotly` so **one region expands at a time**; others in the group hide. Buttons are generic **Expand** / **Restore** (`expandbtn_office_EMEA`, …).

**Churn-only caption:** top 3 models in that region by `date_pushed` sum: `Models with the most date slips in {region}: {name} ({n}), …`

Each figure: Plotly line + markers, color = office, legend **Office**, x **Report date**, `hovermode="x unified"`, `dragmode="zoom"`, same `PLOTLY_CONFIG`.

---

### Tab 4: Performance — complete

No tab-level subheader. Controls sit at the top of the tab.

#### Period control

| | |
| --- | --- |
| Widget | `st.segmented_control` |
| Label | **Period** |
| Key | `t3_period` |
| Options | `year_choices` = `["All years"]` + `str(y)` for each year from `scorecard_years(lifecycle, history)` (union of `snapshot_at` years and `closed_at` years, sorted) |
| Default | `"All years"` (`setdefault` before the tabs) |
| Layout | Left of two columns `[1.35, 1]`, `vertical_alignment="center"` |
| What it filters | If not All years, `close_year = int(t3_period)`. `office_scorecard(..., close_year=close_year)` keeps closed lines with `closed_at` in that calendar year, and clips streak history to snapshots in that year. **Longest Delay boards ignore this** and use `card_all` / `all_pool`. |

#### Detailed view

| | |
| --- | --- |
| Widget | `st.toggle` |
| Label | **Detailed view** |
| Key | `t3_detailed` |
| Default | `False` (off) |
| When on | (1) Under every card, a meta line: `{n} closed · {n} on time · {n} late` at `font-size:0.8rem;opacity:0.65`. (2) Expander **Full office table** at the bottom. |

Empty scorecard (`card_all.empty`): `st.info("Need closed lines before office standings can be ranked.")` — no boards.

#### Full office table (detailed view only)

`st.expander("Full office table")`. If `card` is empty: caption `No closed lines in {t3_period}.` Else caption:

> Closed-line figures for {t3_period}. Longest Delay on the boards uses all-time history.

`st.dataframe` columns, `width="stretch"`, `hide_index=True`:

`region`, `office`, `n_orders`, `n_closed`, `n_on_time`, `n_late`, `on_time_rate`, `late_rate`, `consistency`, `longest_streak`, `longest_delay`, `median_lead`, `qualified`

Rates formatted as `{:.0%}` strings in the table only.

#### Top 3 / Bottom 3 layout

```
top_hdr | gap_hdr (0.08) | bot_hdr     columns [1, 0.08, 1]
  each header is itself 3 columns; label sits in the **middle** column
  gap: 1px vertical spine, min-height 4.5rem

then for each of 7 boards:
  heading (full width, left)
  top_block | gap (0.08) | bot_block
  each block: st.columns(3) — up to 3 cards
  gap: 1px spine, min-height 6.5rem
```

- Labels **Top 3** and **Bottom 3** sit **over the middle cards** (the center of the three-card row), not over the left/right edges.
- Vertical divider: `border-left:1px solid rgba(49,51,63,0.18)`.
- Group-label class `ovadue-t3-group`; heading class `ovadue-t3-heading`; card class `ovadue-t3-card`.

If both top and bottom subsets are empty: caption `No offices met the minimum closed-line count for this period.` Same caption inside a side if that subset is empty.

Warning if the period card has rows but `qualified.sum() == 0`:

> No office met the minimum closed-line count for this period; showing everyone.

`_pool`: prefer `qualified` rows; if none qualify, use the full frame.

`_top3(frame, col, ascending)`: `sort_values(col, ascending=ascending, na_position="last").head(3)`.

`_bottom3`: same with `ascending` flipped.

#### All 7 boards

Display name, metric field, Top sort, Bottom sort, unit format, year-filter, tooltip (`board_tips` — also used as HTML `title` on heading and value).

| Display name | Field | Top 3 sort | Bottom 3 sort | Unit (`fmt`) | Year filter | Tooltip meaning (exact string) |
| --- | --- | --- | --- | --- | --- | --- |
| **Volume** | `n_orders` | descending (most orders) | ascending | `{:.0f} orders` | yes (`period_pool`) | `Unique HP order numbers among closed lines in the selected period. One HP order with several lines counts as 1. Year filter applies.` |
| **On-Time** | `on_time_rate` | descending (highest %) | ascending | `{:.0%}` | yes | `Share of closed lines that dropped off the backlog before the first promised PlannedDeliveryDate. Shown as a percent. Year filter applies.` |
| **Late** | `late_rate` | descending (highest late % = “top”) | ascending (lowest late %) | `{:.0%}` | yes | `Share of closed lines still on the backlog after the first promised date, then dropped off. Shown as a percent. Year filter applies.` |
| **Consistency** | `consistency` | descending (highest score) | ascending | `{:.0f} score` | yes | `Composite score: (on-time rate × 100) − (average date changes × 8). Not a percent. Year filter applies.` |
| **Clean Streak** | `longest_streak` | descending (longest run) | ascending | `{:.0f} reports` | yes (history clipped to that year’s snapshots) | `Longest run of consecutive reports with zero overdue lines, in reports. Year filter limits the streak to that year’s reports.` |
| **Longest Delay** | `longest_delay` | descending (worst delay = “top”) | ascending | `{:.0f} days` | **no** — `all_pool` / `card_all` | `Single worst delay in days: the max days from the original promise to close. All-time — ignores the period switch.` |
| **Fastest Delivery** | `median_lead` | **ascending** (shortest days = top) | descending (longest days) | `{:.0f} days` | yes | `Shortest median calendar days from HPReceiveDate (or first-seen) to close. Year filter applies.` |

NaN values render as `—`.

#### Card anatomy

Format: **`{office} - {region}`** (literal ` - ` between, not an en-dash). Left-aligned (`text-align:left`; centering was reverted).

| Part | Style in code |
| --- | --- |
| Office (city) | `font-size:1.45rem; font-weight:700;` color `DARK_REGION_COLORS[region]` else `#4b5a6e` |
| Separator | ` - ` at `font-size:1.31rem; font-weight:500; color:#94a3b8` |
| Region | `font-size:1.31rem; font-weight:600;` color `PASTEL_REGION_COLORS[region]` else `#94a3b8` |
| Value | `font-size:1.72rem; font-weight:600; line-height:1.2;` `title={tip}` |
| Detailed meta | `font-size:0.8rem; opacity:0.65; margin-top:0.12rem` — `{n_closed} closed · {n_on_time} on time · {n_late} late` |
| Card wrapper | class `ovadue-t3-card`, `title={tip}`, `padding:0.15rem 0 0.95rem 0` |
| Office/region row | `line-height:1.2; margin-bottom:0.28rem` |

Region colors on cards (`charts.py`):

| Region | Dark (city) | Pastel (region) | Chart line (`REGION_COLORS`) |
| --- | --- | --- | --- |
| EMEA | `#3d6f9c` | `#7aa8d4` | `#2563eb` |
| APJ | `#3a7a52` | `#7ab894` | `#059669` |
| US | `#9a7428` | `#d4a85c` | `#d97706` |
| CA | `#6e4d96` | `#b494d4` | `#7c3aed` |
| Unknown | `#4b5a6e` | `#94a3b8` | `#64748b` |

#### Underlines

- Board name (**Volume**, **On-Time**, …): `font-size:1.92rem; font-weight:700;` `padding-bottom:0.2em; border-bottom:2px solid currentColor;` left-aligned; `title={tip}` on the heading wrapper.
- **Top 3** / **Bottom 3**: `font-size:3.44rem; font-weight:600;` `color:rgba(49, 51, 63, 0.4);` same 2px underline; `min-width:12ch; margin:0 -2rem;` centered.

#### Hover title

`title` attributes on the heading (`ovadue-t3-heading`) and on the value `div` (and the card wrapper). Text is `escape(board_tips[title], quote=True)`. Browser-native tooltip, not a Streamlit popover.

#### Min closed lines behaviour

Sidebar **Min closed lines for Top 3** (`min_value=1`, **default 3**) is passed as `min_closed` into both `office_scorecard` calls. `qualified = n_closed >= min_closed`. Rankings use `_pool` (qualified only). If nobody qualifies, everyone is shown and the warning above appears. Does not change flux/hardware/office-line charts.

#### Font sizes currently in code (complete)

| Element | Size |
| --- | --- |
| Board category heading | **1.92rem** (weight 700) |
| Top 3 / Bottom 3 labels | **3.44rem** (weight 600, `rgba(49, 51, 63, 0.4)`) |
| Card value | **1.72rem** (weight 600) |
| Office name | **1.45rem** (weight 700) |
| Separator and region | **1.31rem** (weights 500 / 600) |
| Detailed closed meta | **0.8rem** (opacity 0.65) |

---

### Charts/UI helpers (`ovadue/ui.py`, `charts.py`) — expand/restore, scatter_pair jiggle, inject_css pitfalls

#### Expand / restore

- Session: `chart_expanded` (`EXPAND_STATE`).
- `is_showing(key, group)`: if `chart_expanded` is `None` or not in `group`, show all members; else show only the expanded key.
- `expand_bar(key)`: **Expand** / **Restore**, key `expandbtn_{key}`, help *Fill the page area under the sidebar and tabs. Does not hide navigation.*
- `show_plotly`: skip if not showing; then expand bar; height 440 or 780; `uirevision=key`; `theme="streamlit"`; `width="stretch"`. When expanded, also injects a `<style>` targeting `.st-key-{key}` (`min-height: calc(100vh - 13.5rem)`) via `st.markdown` — this is a **known weak path** (Streamlit may strip `<style>`).
- `inject_chart_css()` hides Plotly/Streamlit fullscreen buttons so users use in-page Expand.

#### scatter_pair jiggle

See Tab 2. Defaults `key_a="hw_late"`, `key_b="hw_chg"`. Reference Plotly 2.35.2 inside the linked-scatter view. Offline hosts need a local bundle.

#### inject_css pitfalls

Streamlit **strips `<style>` from `st.markdown`**. Performance cards therefore use **inline `style=`** only. Do **not** put raw `<h2>` in markdown HTML (Streamlit sanitizes headings).

`inject_css(css, slot=...)` writes into **`parent.document`** via a **zero-height** `components.html` script: creates/updates `<style id="ovadue-css-{slot}">` in `parent.document.head`. Then hides its own iframe (`height:0; visibility:hidden`). Backup: `st.html(fragment)` if present, else `st.markdown` of a `<style>` block (unreliable for tab-bar rules). Slots used: `"charts"`, `"appearance"`.

`st.html` style-only fragments go to the event container and **do not restyle the tab bar** — that is why the parent-document inject exists.

---

### Office aliases (Getafe→Madrid, others, Pasig left as-is)

Needles are tried **longest first**. Match is `needle in lowered` or `needle in text` (CJK needles match the raw address).

| Needle (in address) | Canonical office |
| --- | --- |
| `getafe` | **Madrid** |
| `madrid` | Madrid |
| `pasig` | **Pasig** (left as its own city; not Manila) |
| `bangalore` / `bengaluru` | Bengaluru |
| `warszawa` / `warsaw` | Warsaw |
| `marina bay` / `singapore` | Singapore |
| `jakarta selatan` / `dki jakarta` / `jakarta` | Jakarta |
| `selangor` | Petaling Jaya |
| `petaling jaya` | Petaling Jaya |
| `gurgaon` / `gurugram` | Gurugram |
| `milano` / `milan` | Milan |
| `miami beach` / `miami` | Miami |
| `hong kong` / `hongkong` | Hong Kong |
| `newcastle upon tyne` | Newcastle |
| `frankfurt am main` / `frankfurt` | Frankfurt |
| `ho chi minh city` | Ho Chi Minh City |
| `levent istanbul` / `istanbul` | Istanbul |
| `beograd` / `belgrade` | Belgrade |
| `千代田` / `富士見` | Tokyo |
| `上海市` / `shanghai` | Shanghai |
| `北京市` / `beijing` | Beijing |
| `深圳市` / `shenzhen` | Shenzhen |
| `广州` / `guangzhou/广州` / `guangzhou` | Guangzhou |
| `台北` / `taipei` | Taipei |
| `서울` | Seoul |

Other city needles (canonical = title-cased city unless noted): San Francisco, Johannesburg, Cape Town, New York, San Diego, Los Angeles, Southampton, Birmingham, Manchester, Edinburgh, Nottingham, Copenhagen, Amsterdam, Hyderabad, Melbourne, Auckland, Winchester, Sunderland, Sheffield, Glasgow, Bristol, Belfast, Cardiff, Andover, Dublin, London, Leeds, York, Cork, Krakow, Zaragoza, Berlin, Penang, Mumbai, Perth, Sydney, Adelaide, Brisbane, Toronto, Montreal, Calgary, Ottawa, Austin, Houston, Oakland, Seattle, Boston, Chicago, Newark, Dubai, Ankara, Bangkok.

**Country fallback** (`_COUNTRY_FALLBACK`) if no needle hits:

| `ShipToCountry` (casefold) | Office |
| --- | --- |
| `japan` | Tokyo |
| `china` | `China (unmapped)` |
| `south korea` | Seoul |
| `taiwan` | Taipei |
| `hong kong` | Hong Kong |

Else the country string itself; if country is empty → `"Unknown"`.

---

### Wiring into the existing live app

Copy these modules into the site you already host. Keep layout and scoring. Bind the live history frame. Do **not** start a second Streamlit process, and do **not** iframe another server.

1. Drop `pages/1_Analysis.py` into the live page/router (adapt imports if the host is not Streamlit).
2. Import `ovadue/` as a library — `metrics.py` / `offices.py` for scoring, `charts.py` / `ui.py` for Plotly chrome.
3. Merge `app.py` into the live Home only if you want the title, caption, and snapshot-count metric.
4. **Data bind:** replace `load_history(data_dir)` (and the **Data folder** sidebar) with the live app’s history frame, **same columns** listed in the drop-in map.
5. Rebuild charts in the live UI if needed; keep Plotly behaviour from `charts.py` / `ui.py` if you keep Plotly.

#### Session state keys (complete, from `ui.py` and Analysis)

| Key | Default | Where |
| --- | --- | --- |
| `t3_period` | `"All years"` | Performance **Period** segmented control |
| `t3_detailed` | `False` | **Detailed view** toggle |
| `appearance_bg_color` | `"#ffffff"` | Appearance **Background colour** |
| `appearance_color_fade` | `100` | Appearance **Colour fade** |
| `appearance_image_fade` | `80` | Appearance **Image fade** |
| `appearance_image_bytes` | unset / `None` | uploaded photo (not on disk) |
| `appearance_image_mime` | unset / `None` | `image/png` \| `image/jpeg` \| `image/webp` |
| `appearance_upload_nonce` | `0` | uploader widget key suffix |
| `appearance_upload_{nonce}` | — | file_uploader widget key |
| `chart_expanded` | unset / `None` | which chart is expanded |

Widget keys also include `expandbtn_{chart_key}` and Plotly keys `flux`, `hw_late`, `hw_chg`, `office_EMEA`, `office_APJ`, `office_US`, `office_CA` (plus `office_{region}` for any extra region).

---

### Do not change without reading metrics.py (scoring list)

Do not invent or “improve” these without reading `C:\OvaDue\ovadue\metrics.py` and agreeing with the product owner:

1. **Close date** = next snapshot after last seen — not last-seen, not a POD.
2. **Late** = last_seen calendar day after **original** `PlannedDeliveryDate`, then vanished.
3. **On time** = closed, not that overdue, original promise present.
4. **Canceled** (`ShipmentCanceled`) never get `closed_at`.
5. **Volume** = unique HP order ids (then PO, then line_key), not line count (except blank-id fallback).
6. **Consistency** = `(on_time_rate × 100) − (avg_date_changes × 8)` — weight `8` is intentional; not a percent.
7. **Clean streak** = consecutive snapshots with zero `late_vs_original` (canceled excluded). Year filter clips **snapshots**, not close dates.
8. **Longest Delay** UI always ranks from the **unfiltered** scorecard (`card_all`).
9. **Fastest Delivery** = median `actual_lead_days` (receive/first-seen → close); Top 3 is **shortest**.
10. **Office reliability / late_share** in Tab 3 ignores the **Lateness vs** radio (always original promise).
11. `regional_flux` late column **does** follow **Lateness vs**.
12. Hardware on-time scatter = closed only; date-change scatter = open + closed, not canceled.

---

### Known pitfalls

- **Streamlit style stripping** — `<style>` inside `st.markdown` is unreliable. Cards use inline `style=`. Global CSS goes through `inject_css()` → `parent.document`. The expanded-chart `.st-key-{key}` block in `show_plotly` is the one place that still uses markdown `<style>`.
- **Duplicate `.xls` / `.xlsx`** — same stamp keeps **xlsx**.
- **Min closed lines** — default 3. Boards hide small-sample offices unless none qualify.
- **Year filter does not apply to Longest Delay** — that board uses `all_pool` / `card_all`. The detailed table caption says this explicitly.
- **Linked scatters need a Plotly bundle** (reference uses `cdn.plot.ly` 2.35.2). Offline live apps need a local bundle.
- **Filename time group** is 3–5 digits; parse uses the first 4 as HHMM. Names like `06461` or `0608 1.xls` still match the regex.
- **Empty Regions multiselect** = no filter (all regions), not “no data”.
- **Home metric vs Analysis Snapshots** — both should be unique `snapshot_at` on the same live history frame.
- **Appearance does not persist** — image bytes are session_state only; restart loses the photo.
- **No database / no POD** — do not add a POD-based close without a real column.
- **Do not change scoring semantics** without reading `metrics.py`.

---

## Inventory at zip time (`handover-2.0.zip`)

Included: `HANDOVER-2.0.md`, `pages/1_Analysis.py`, `ovadue/` (`load.py`, `offices.py`, `metrics.py`, `charts.py`, `ui.py`, `__init__.py`), `app.py` (Home **display** only — not an app server).

Excluded: `data/` (reports), `.git`, `.venv`, `__pycache__`, `*.pyc`, `.streamlit/`, `requirements.txt` (live stack exists), old zips.
