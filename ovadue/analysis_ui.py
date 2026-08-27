"""Analysis views from handover 2.0 — call render_analysis(data_dir) from the live app."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from ovadue.charts import (
    DARK_REGION_COLORS,
    PASTEL_REGION_COLORS,
    category_colors,
    date_change_scatter,
    hardware_lateness_scatter,
    office_lines,
    regional_flux_lines,
)
from ovadue.load import load_history
from ovadue.metrics import (
    build_lifecycle,
    date_change_by_type,
    hardware_outcomes,
    office_scorecard,
    office_timeseries,
    regional_flux,
    scorecard_years,
)
from ovadue.ui import apply_appearance, inject_chart_css, is_showing, scatter_pair, show_plotly


@st.cache_data(show_spinner="Loading backlog snapshots…")
def _load(path: str) -> pd.DataFrame:
    return load_history(path)


def render_analysis(data_dir: str | Path) -> None:
    """Render the handover 2.0 Analysis UI (four tabs including Performance / Top 3)."""
    inject_chart_css()
    st.subheader("Analysis")
    st.caption(
        "Late means a line was still on the backlog after its **first promised** "
        "delivery date. Actual POD dates are not in these reports, so a line that "
        "vanishes after that point is treated as landed late."
    )

    try:
        history = _load(str(data_dir))
    except Exception as exc:
        st.error(f"Could not load reports from `{data_dir}`: {exc}")
        return

    if history.empty:
        st.warning("No backlog snapshots found. Place `osreport_ArupBacklog_*` files next to the app.")
        return

    lifecycle = build_lifecycle(history)
    min_closed = st.sidebar.number_input("Min closed lines for Top 3", min_value=1, value=3, step=1)
    year_choices = ["All years"] + [str(y) for y in scorecard_years(lifecycle, history)]
    st.session_state.setdefault("t3_period", "All years")
    st.session_state.setdefault("t3_detailed", False)
    if st.session_state["t3_period"] not in year_choices:
        st.session_state["t3_period"] = "All years"
    max_offices = st.sidebar.slider("Max offices per region chart", min_value=4, max_value=40, value=12)
    promise = st.sidebar.radio(
        "Lateness vs",
        options=["original", "current"],
        format_func=lambda v: "Original promise" if v == "original" else "Latest ETA",
        index=0,
    )
    regions = ["All"] + sorted(history["region"].dropna().unique().tolist())
    region_filter = st.sidebar.multiselect("Regions", options=regions[1:], default=regions[1:])
    apply_appearance()
    if region_filter:
        history_f = history[history["region"].isin(region_filter)]
        life_f = lifecycle[lifecycle["region"].isin(region_filter)]
    else:
        history_f = history
        life_f = lifecycle

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Snapshots", int(history["snapshot_at"].nunique()))
    c2.metric(
        "Line items (latest)",
        int(history.loc[history["snapshot_at"].eq(history["snapshot_at"].max()), "line_key"].nunique()),
    )
    c3.metric("Offices", int(history["office"].nunique()))
    c4.metric("Closed lines", int(life_f["closed_at"].notna().sum()))

    tab_flux, tab_hw, tab_offices, tab_top = st.tabs(
        ["Regional flux", "Hardware & date changes", "Offices by region", "Performance"]
    )

    with tab_flux:
        st.subheader("When deliveries ran late, by region")
        metric = st.radio(
            "What to plot",
            options=["n_late", "late_share", "n_date_pushes"],
            format_func=lambda v: {
                "n_late": "Count of late lines",
                "late_share": "Share of open lines that are late",
                "n_date_pushes": "Planned dates pushed later",
            }[v],
            horizontal=True,
        )
        flux = regional_flux(history_f, promise=promise)
        titles = {
            "n_late": "Lines still on the backlog after their promised delivery date",
            "late_share": "Share of open lines past their promised delivery date",
            "n_date_pushes": "Order lines whose planned delivery date moved later",
        }
        y_titles = {
            "n_late": "Late line items",
            "late_share": "Late share",
            "n_date_pushes": "Date slips",
        }
        fig = regional_flux_lines(flux, metric, y_titles[metric], titles[metric])
        if metric == "late_share":
            fig.update_layout(yaxis_tickformat=".0%")
        show_plotly(fig, key="flux", group=("flux",))
        bits = []
        for region, group in flux.groupby("region", dropna=False):
            if group[metric].notna().any() and group[metric].fillna(0).gt(0).any():
                row = group.loc[group[metric].idxmax()]
                bits.append(f"**{region}** peaked {row['snapshot_at'].strftime('%d %b %Y')}")
        if bits:
            st.markdown("Peak flux: " + " · ".join(bits))

    with tab_hw:
        st.subheader("Which hardware is late or on time")
        grain = st.radio(
            "Group hardware by",
            options=["hardware_type", "hardware_category", "model"],
            format_func=lambda v: {"hardware_type": "Type", "hardware_category": "Category", "model": "Model"}[v],
            horizontal=True,
        )
        outcomes = hardware_outcomes(life_f, grain=grain)
        changes = date_change_by_type(life_f, grain=grain)
        names = []
        if not outcomes.empty:
            names.extend(outcomes[grain].tolist())
        names.extend(changes[grain].tolist())
        colors = category_colors(names)
        if outcomes.empty:
            st.info("No closed lines yet to score on-time vs late.")
            show_plotly(
                date_change_scatter(changes, grain, colors),
                key="hw_chg",
                group=("hw_chg",),
            )
        else:
            scatter_pair(
                hardware_lateness_scatter(outcomes, grain, colors),
                date_change_scatter(changes, grain, colors),
                group=("hw_late", "hw_chg"),
            )
        st.caption(
            "Click a bubble or a legend name to jiggle the same item on the other chart. "
            "Bubble size is volume. On-time uses closed lines only (dropped off a later report). "
            "Date-change scatter includes open lines too. Drag to zoom, scroll to zoom, double-click to reset."
        )

    with tab_offices:
        st.subheader("Offices inside each region")
        chart_kind = st.radio(
            "Office chart",
            options=["churn", "reliability", "lead"],
            format_func=lambda v: {
                "churn": "Models / dates that change the most",
                "reliability": "Least reliable vs the promised date",
                "lead": "Longest lead time",
            }[v],
            horizontal=True,
        )
        ts_all = office_timeseries(history_f)
        region_order = [r for r in ["EMEA", "APJ", "US", "CA"] if r in set(ts_all["region"])]
        region_order += [r for r in sorted(ts_all["region"].unique()) if r not in region_order]
        office_keys = tuple(f"office_{region}" for region in region_order)
        for region in region_order:
            key = f"office_{region}"
            if not is_showing(key, office_keys):
                continue
            ts = ts_all[ts_all["region"] == region]
            if ts.empty:
                continue
            busiest = ts.groupby("office")["n_lines"].sum().nlargest(int(max_offices)).index
            ts = ts[ts["office"].isin(busiest)]
            if chart_kind == "churn":
                fig = office_lines(
                    ts,
                    "n_date_pushes",
                    "Planned dates pushed later",
                    f"{region}: delivery dates revised",
                )
                show_plotly(fig, key=key, group=office_keys)
                top_models = (
                    history_f[history_f["region"].eq(region)]
                    .groupby("model", dropna=False)["date_pushed"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(3)
                )
                if not top_models.empty:
                    labels = ", ".join(f"{name} ({int(n)})" for name, n in top_models.items())
                    st.caption(f"Models with the most date slips in {region}: {labels}")
            elif chart_kind == "reliability":
                fig = office_lines(
                    ts,
                    "late_share",
                    "Share past original promise",
                    f"{region}: least reliable vs promised date",
                )
                fig.update_layout(yaxis_tickformat=".0%")
                show_plotly(fig, key=key, group=office_keys)
            else:
                fig = office_lines(
                    ts,
                    "median_lead",
                    "Median promised lead time (days)",
                    f"{region}: longest lead time",
                )
                show_plotly(fig, key=key, group=office_keys)

    with tab_top:
        ctrl_period, ctrl_detail = st.columns([1.35, 1], vertical_alignment="center")
        with ctrl_period:
            t3_period = st.segmented_control(
                "Period",
                options=year_choices,
                key="t3_period",
            )
        with ctrl_detail:
            t3_detailed = st.toggle("Detailed view", key="t3_detailed")
        if t3_period not in year_choices:
            t3_period = "All years"
        close_year = None if t3_period == "All years" else int(t3_period)
        card_all = office_scorecard(life_f, history_f, min_closed=int(min_closed))
        card = (
            card_all
            if close_year is None
            else office_scorecard(life_f, history_f, min_closed=int(min_closed), close_year=close_year)
        )
        if card_all.empty:
            st.info("Need closed lines before office standings can be ranked.")
        else:
            def _pool(frame: pd.DataFrame) -> pd.DataFrame:
                if frame.empty:
                    return frame
                ranked = frame[frame["qualified"]].copy()
                return ranked if not ranked.empty else frame

            period_pool = _pool(card)
            all_pool = _pool(card_all)
            if not card.empty and card["qualified"].sum() == 0:
                st.warning("No office met the minimum closed-line count for this period; showing everyone.")

            def _top3(frame: pd.DataFrame, col: str, ascending: bool = False) -> pd.DataFrame:
                if frame.empty or col not in frame.columns:
                    return frame
                return frame.sort_values(col, ascending=ascending, na_position="last").head(3)

            def _bottom3(frame: pd.DataFrame, col: str, ascending: bool = False) -> pd.DataFrame:
                return _top3(frame, col, ascending=not ascending)

            def _render_office_cards(subset: pd.DataFrame, col: str, fmt: str, tip: str) -> None:
                if subset.empty:
                    st.caption("No offices met the minimum closed-line count for this period.")
                    return
                cols = st.columns(3)
                for i, (_, row) in enumerate(subset.iterrows()):
                    with cols[i]:
                        value = row[col]
                        if pd.isna(value):
                            shown = "—"
                        else:
                            shown = fmt.format(value)
                        region_key = str(row["region"])
                        office_color = DARK_REGION_COLORS.get(region_key, "#4b5a6e")
                        region_color = PASTEL_REGION_COLORS.get(region_key, "#94a3b8")
                        meta = ""
                        if t3_detailed:
                            meta = (
                                f'<div style="font-size:0.8rem;opacity:0.65;margin-top:0.12rem;text-align:left;">'
                                f"{int(row['n_closed'])} closed · {int(row['n_on_time'])} on time · {int(row['n_late'])} late"
                                f"</div>"
                            )
                        st.markdown(
                            f"""
                            <div class="ovadue-t3-card" title="{tip}" style="padding:0.15rem 0 0.95rem 0;text-align:left;width:100%;">
                              <div style="line-height:1.2;margin-bottom:0.28rem;text-align:left;">
                                <span style="font-size:1.45rem;font-weight:700;color:{office_color};">{escape(str(row["office"]))}</span><span style="font-size:1.31rem;font-weight:500;color:#94a3b8;"> - </span><span style="font-size:1.31rem;font-weight:600;color:{region_color};">{escape(str(row["region"]))}</span>
                              </div>
                              <div title="{tip}" style="font-size:1.72rem;font-weight:600;line-height:1.2;text-align:left;">{escape(shown)}</div>
                              {meta}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            board_tips = {
                "Volume": (
                    "Unique HP order numbers among closed lines in the selected period. "
                    "One HP order with several lines counts as 1. Year filter applies."
                ),
                "On-Time": (
                    "Share of closed lines that dropped off the backlog before the first "
                    "promised PlannedDeliveryDate. Shown as a percent. Year filter applies."
                ),
                "Late": (
                    "Share of closed lines still on the backlog after the first promised "
                    "date, then dropped off. Shown as a percent. Year filter applies."
                ),
                "Consistency": (
                    "Composite score: (on-time rate × 100) − (average date changes × 8). "
                    "Not a percent. Year filter applies."
                ),
                "Clean Streak": (
                    "Longest run of consecutive reports with zero overdue lines, in reports. "
                    "Year filter limits the streak to that year’s reports."
                ),
                "Longest Delay": (
                    "Single worst delay in days: the max days from the original promise to close. "
                    "All-time — ignores the period switch."
                ),
                "Fastest Delivery": (
                    "Shortest median calendar days from HPReceiveDate (or first-seen) to close. "
                    "Year filter applies."
                ),
            }
            boards = [
                ("Volume", period_pool, "n_orders", "{:.0f} orders", False),
                ("On-Time", period_pool, "on_time_rate", "{:.0%}", False),
                ("Late", period_pool, "late_rate", "{:.0%}", False),
                ("Consistency", period_pool, "consistency", "{:.0f} score", False),
                ("Clean Streak", period_pool, "longest_streak", "{:.0f} reports", False),
                ("Longest Delay", all_pool, "longest_delay", "{:.0f} days", False),
                ("Fastest Delivery", period_pool, "median_lead", "{:.0f} days", True),
            ]
            group_label_inner = (
                "font-size:3.44rem;font-weight:600;text-align:center;display:inline-block;"
                "white-space:nowrap;overflow:visible;min-width:12ch;margin:0 -2rem;"
                "padding-bottom:0.2em;border-bottom:2px solid currentColor;"
                "color:rgba(49, 51, 63, 0.4);"
            )

            def _t3_spine(min_height: str) -> None:
                st.markdown(
                    f'<div style="border-left:1px solid rgba(49,51,63,0.18);'
                    f'height:100%;min-height:{min_height};margin:0 auto;"></div>',
                    unsafe_allow_html=True,
                )

            def _t3_group_label(label: str) -> None:
                st.markdown(
                    f'<div class="ovadue-t3-group" style="margin:0.55em 0 0.15em;line-height:1.2;'
                    f'text-align:center;width:100%;overflow:visible;">'
                    f'<div style="{group_label_inner}">{escape(label)}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            top_hdr, gap_hdr, bot_hdr = st.columns([1, 0.08, 1])
            with top_hdr:
                _h0, top_mid, _h2 = st.columns(3)
                with top_mid:
                    _t3_group_label("Top 3")
            with gap_hdr:
                _t3_spine("4.5rem")
            with bot_hdr:
                _h4, bot_mid, _h6 = st.columns(3)
                with bot_mid:
                    _t3_group_label("Bottom 3")
            for title, pool, col, fmt, ascending in boards:
                tip = escape(board_tips[title], quote=True)
                top = _top3(pool, col, ascending)
                bottom = _bottom3(pool, col, ascending)
                st.markdown(
                    f'<div class="ovadue-t3-heading" title="{tip}" style="margin:1.85em 0 1.15em;line-height:1.2;text-align:left;width:100%;">'
                    f'<div style="font-size:1.92rem;font-weight:700;text-align:left;display:inline-block;padding-bottom:0.2em;border-bottom:2px solid currentColor;">{escape(title)}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if top.empty and bottom.empty:
                    st.caption("No offices met the minimum closed-line count for this period.")
                    continue
                top_block, gap, bot_block = st.columns([1, 0.08, 1])
                with top_block:
                    _render_office_cards(top, col, fmt, tip)
                with gap:
                    _t3_spine("6.5rem")
                with bot_block:
                    _render_office_cards(bottom, col, fmt, tip)
            if t3_detailed:
                with st.expander("Full office table"):
                    if card.empty:
                        st.caption(f"No closed lines in {t3_period}.")
                    else:
                        show = card.copy()
                        show["on_time_rate"] = show["on_time_rate"].map(lambda v: None if pd.isna(v) else f"{v:.0%}")
                        show["late_rate"] = show["late_rate"].map(lambda v: None if pd.isna(v) else f"{v:.0%}")
                        st.caption(f"Closed-line figures for {t3_period}. Longest Delay on the boards uses all-time history.")
                        st.dataframe(
                            show[
                                [
                                    "region",
                                    "office",
                                    "n_orders",
                                    "n_closed",
                                    "n_on_time",
                                    "n_late",
                                    "on_time_rate",
                                    "late_rate",
                                    "consistency",
                                    "longest_streak",
                                    "longest_delay",
                                    "median_lead",
                                    "qualified",
                                ]
                            ],
                            width="stretch",
                            hide_index=True,
                        )
