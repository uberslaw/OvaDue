# OvaDue — Handover Notes

Streamlit app for local office leads (and later, regional leads) to track HP laptop/hardware order backlog from OS report exports. Single file: [app.py](app.py).

## Run it

```powershell
cd "c:\Users\christopher.owen\OneDrive - Arup\Arup\AI\OvaDue"
"C:/Program Files/Python314/python.exe" -m pip install -r requirements.txt
"C:/Program Files/Python314/python.exe" -m streamlit run app.py
```

Or activate the existing venv: `.venv\Scripts\Activate.ps1` then `streamlit run app.py`.

Data files: `.xls`/`.xlsx` OS reports are read from the repo root **and** `uploads/`. Filename should contain a date like `osreport_ArupBacklog_2026-08-25_0807.xls` — the app parses that as the snapshot date; if no date is found it falls back to file mtime.

## Current state — "My Orders" page

This is the primary/default view (sidebar → View → "My Orders"), built for local office leads. Function: `render_my_orders_page` in [app.py](app.py).

- Orders are grouped into **cards**, one per office, one card per `(PurchaseOrderNo, HPOrderNo, PlannedDeliveryDate, SnapshotDate)` group — so multi-line orders with a shared delivery date collapse into a single card, but split into separate cards if line items on the same order have different planned delivery dates.
- Card layout (3-column grid, stacks vertically on narrow screens — no horizontal scroll):
  - Row 1: **PO / HP Order** | **Planned Delivery** (with the logistics/delivery-service description shown directly underneath the date, if present) | **Status**
  - Row 2: **Item** (list, one per line, hardware only) | **QTY** (matching list) | **Order Placed**
- **Search box** + **Include past orders** checkbox (searches full history instead of just the latest snapshot; shows shipped/cancelled too).
- **More filters** expander: date-range filter on any of the four key date fields.
- Per-office quick filter text box appears next to the office header, but only when that office has more than `OFFICE_FILTER_ROW_THRESHOLD` (currently 6) order lines — avoids clutter for small offices.
- **Presumed Delivered**: when browsing "Include past orders", any historical order line whose `OrderLineKey` no longer appears in the *true latest* snapshot (computed from unfiltered `df_all`, not the office/region-filtered set) is shown with status `Presumed Delivered` (blue badge) instead of its stale historical status, unless it was already `Shipped`.

### Item vs. service/logistics filtering (just implemented, needs visual verification)

The source data mixes hardware lines with service/logistics lines (support contracts, priority management, delivery/logistics SKUs). These are distinguished via `MM_MH_Type` / `MM_MH_Series`, **not** by column letter (see schema note below):

- `MM_MH_Type` containing "service" (case-insensitive) → excluded from the **Item/QTY** list entirely (this removes onsite support, priority management/warranty lines).
- Of those service rows, the ones where `MM_MH_Series` contains "logistic" (case-insensitive) are treated as the delivery/shipping method — their `ProductDescription` is shown as a second line directly under **Planned Delivery**.
- Logic lives in `is_service_row`, `is_logistics_row`, and `render_order_group_card`.

**⚠️ Not yet visually verified against a live run** — the last request that added this was implemented based on column inspection via temp scripts, not by running the Streamlit app itself. Next session should launch the app, pick an office/snapshot known to have service lines (see below), and confirm:
1. Service/warranty lines (onsite support, priority management) no longer appear in the Item list.
2. Delivery/logistics description appears correctly under Planned Delivery.
3. No card ends up empty if an order was *all* service lines (current fallback: if filtering would remove every row, all rows are shown instead of an empty card — double check this still reads sensibly).

### ⚠️ Schema inconsistency across historical files (important gotcha)

Column **letter positions differ between file vintages** — always reference columns by header **name**, never by letter, when reading with pandas (this is already how `app.py` works, but worth remembering if extending):

- **Newer files** (June 2026 onward, e.g. everything in `uploads/`) have an extra `CustomerRequestedDate` column, shifting everything after it by one letter. In these files: `Q=ProductDescription`, `R=MM_MH_Model`, `S=MM_MH_Category`, `T=MM_MH_Series`, `U=MM_MH_Type`.
- **Older files** (root folder, e.g. `osreport_ArupBacklog_2026-02-19_0931.xls`) lack `CustomerRequestedDate`: `P=ProductDescription`, `Q=MM_MH_Model`, `R=MM_MH_Category`, `S=MM_MH_Series`, `T=MM_MH_Type`.
- The current `uploads/` files (Aug 20/25 2026) contain **zero** service/logistics line items — only hardware. To test the service-filtering logic, use one of the many historical files in the repo root (e.g. `osreport_ArupBacklog_2026-02-19_0931.xls` has ~143 service/logistics rows) via the "Include past orders" checkbox.
- If new OS report exports arrive with yet another schema, re-verify column names haven't changed before trusting `MM_MH_Type`/`MM_MH_Series`-based filtering.

## Other pages (largely untouched this session)

- **Outstanding Orders**: laptop-only (`laptop_only()` filters `MM_MH_Type` for Notebook/Mobile Workstation) KPIs, model breakdowns, late-order detail. Separate from "My Orders" — intentionally still laptop-scoped.
- **Delivery Performance**: lead-time and plan-movement analytics across snapshots.

## Known-good design decisions from user feedback (don't re-litigate)

- No horizontal scrollbars — cards use `st.columns()` which stacks on narrow viewports, not `st.dataframe()`.
- Region/Country/full address are deliberately **not** shown per-card since office selection in the sidebar already implies them; office name + one representative address shown once per office group.
- Removed the earlier "All order details" expander per card (user didn't want it) — nothing currently surfaces the *other* raw spreadsheet columns (CustomerName, AccountName, NetLineDollarPrice, OTD stats, etc.) in this view. If asked to bring some of that back, prefer adding it selectively rather than restoring the old catch-all expander.

## Not yet started (from original ask)

- Regional views/rollups (beyond the existing sidebar Region filter).
- Full "search all fields" (current search covers a curated column list, not literally every column).
- Pricing and delivery-trend tracking over time (there's `NetLineDollarPrice` in the data, untouched so far; `Delivery Performance` page has some trend analysis but nothing pricing-specific).

## Useful constants/functions to know (in app.py)

- `MY_ORDERS_SEARCH_COLUMNS` / `MY_ORDERS_SEARCH_DATE_COLUMNS` — what the search box matches against.
- `OFFICE_FILTER_ROW_THRESHOLD` — per-office filter box visibility threshold.
- `STATUS_COLORS` — status → badge color mapping.
- `render_order_group_card` — single card renderer, takes a grouped sub-dataframe (all rows for one PO/HP-order/date/snapshot).
- `render_my_orders_page` — top-level page: filters, grouping, per-office iteration.
- `latest_order_line_keys` (computed in `main()`) — used for the Presumed Delivered logic; passed into `render_my_orders_page`.
