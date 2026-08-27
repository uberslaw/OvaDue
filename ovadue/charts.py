"""Plotly figures for the Analysis page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

REGION_COLORS = {
    "EMEA": "#2563eb",
    "APJ": "#059669",
    "US": "#d97706",
    "CA": "#7c3aed",
    "Unknown": "#64748b",
}

# Soft / dark text pair for Top 3 office cards (charts keep REGION_COLORS).
PASTEL_REGION_COLORS = {
    "EMEA": "#7aa8d4",
    "APJ": "#7ab894",
    "US": "#d4a85c",
    "CA": "#b494d4",
    "Unknown": "#94a3b8",
}
DARK_REGION_COLORS = {
    "EMEA": "#3d6f9c",
    "APJ": "#3a7a52",
    "US": "#9a7428",
    "CA": "#6e4d96",
    "Unknown": "#4b5a6e",
}


def _region_color(region: str) -> str:
    return REGION_COLORS.get(str(region), "#64748b")


def category_colors(names: list[object]) -> dict[str, str]:
    palette = list(px.colors.qualitative.Dark24) + list(px.colors.qualitative.Set3)
    unique = []
    for name in names:
        text = "Unknown" if name is None or (isinstance(name, float) and pd.isna(name)) else str(name)
        if text not in unique:
            unique.append(text)
    return {name: palette[i % len(palette)] for i, name in enumerate(unique)}


def regional_flux_lines(flux: pd.DataFrame, y: str, y_title: str, title: str) -> go.Figure:
    fig = px.line(
        flux,
        x="snapshot_at",
        y=y,
        color="region",
        markers=True,
        color_discrete_map=REGION_COLORS,
        title=title,
    )
    fig.update_traces(line={"width": 2.4}, marker={"size": 8})
    fig.update_layout(
        xaxis_title="Report date",
        yaxis_title=y_title,
        legend_title="Region",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=60, b=40),
        dragmode="zoom",
    )
    return fig


def hardware_lateness_scatter(
    outcomes: pd.DataFrame, grain: str, colors: dict[str, str] | None = None
) -> go.Figure:
    fig = px.scatter(
        outcomes,
        x="on_time_rate",
        y="avg_days_late",
        size="n_closed",
        color=grain,
        hover_name=grain,
        color_discrete_map=colors or {},
        hover_data={
            "n_closed": True,
            "n_late": True,
            "n_on_time": True,
            "on_time_rate": ":.0%",
            "avg_days_late": ":.1f",
        },
        title="Hardware: on-time rate vs typical delay",
    )
    fig.update_layout(
        xaxis_title="On-time share (closed lines)",
        yaxis_title="Average days late (0 if on time)",
        xaxis_tickformat=".0%",
        margin=dict(l=40, r=20, t=60, b=40),
        dragmode="zoom",
        legend_title_text="Click a name to jiggle its pair",
    )
    fig.update_traces(marker=dict(sizemode="area", sizeref=2.0, line=dict(width=0.5, color="white")))
    for trace in fig.data:
        trace.meta = trace.name
        trace.legendgroup = trace.name
    return fig


def date_change_scatter(
    changes: pd.DataFrame, grain: str, colors: dict[str, str] | None = None
) -> go.Figure:
    fig = px.scatter(
        changes,
        x="n_lines",
        y="avg_changes",
        size="n_lines",
        color=grain,
        hover_name=grain,
        color_discrete_map=colors or {},
        hover_data={
            "share_changed": ":.0%",
            "max_changes": True,
            "avg_changes": ":.2f",
        },
        title="How often planned delivery dates change",
    )
    fig.update_layout(
        xaxis_title="Line items seen",
        yaxis_title="Average planned-date revisions per line",
        margin=dict(l=40, r=20, t=60, b=40),
        dragmode="zoom",
        legend_title_text="Click a name to jiggle its pair",
    )
    for trace in fig.data:
        trace.meta = trace.name
        trace.legendgroup = trace.name
    return fig


def office_lines(ts: pd.DataFrame, y: str, y_title: str, title: str) -> go.Figure:
    fig = px.line(
        ts,
        x="snapshot_at",
        y=y,
        color="office",
        markers=True,
        title=title,
    )
    fig.update_traces(line={"width": 2}, marker={"size": 6})
    fig.update_layout(
        xaxis_title="Report date",
        yaxis_title=y_title,
        legend_title="Office",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(font=dict(size=11)),
        dragmode="zoom",
    )
    return fig
