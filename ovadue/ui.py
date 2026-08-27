"""Shared Plotly display: zoom, in-page expand, linked scatter jiggle."""

from __future__ import annotations

import base64
import json

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

EXPAND_STATE = "chart_expanded"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "scrollZoom": True,
    "responsive": True,
    "doubleClick": "reset",
    "displayModeBar": True,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "toggleFullscreen",
        "togglefullscreen",
    ],
}


CHART_CSS = """
.modebar-btn[data-title="Fullscreen"],
.modebar-btn[data-title="Full screen"],
button[aria-label="Fullscreen"],
[data-testid="StyledFullScreenButton"] {
  display: none !important;
}
"""

SS_BG_COLOR = "appearance_bg_color"
SS_COLOR_FADE = "appearance_color_fade"
SS_IMAGE_BYTES = "appearance_image_bytes"
SS_IMAGE_MIME = "appearance_image_mime"
SS_IMAGE_FADE = "appearance_image_fade"
SS_UPLOAD_NONCE = "appearance_upload_nonce"

DEFAULT_BG_COLOR = "#ffffff"
DEFAULT_COLOR_FADE = 100
DEFAULT_IMAGE_FADE = 80


def inject_css(css: str, *, slot: str = "default") -> None:
    """Write CSS into the parent Streamlit document head.

    ``st.html`` style-only fragments go to the event container and do not
    restyle the tab bar. A zero-height component reaches ``parent.document``.
    """
    style_id = f"ovadue-css-{slot}"
    components.html(
        f"""<script>
        (function() {{
          const id = {json.dumps(style_id)};
          const css = {json.dumps(css)};
          const doc = window.parent.document;
          let s = doc.getElementById(id);
          if (!s) {{
            s = doc.createElement("style");
            s.id = id;
            doc.head.appendChild(s);
          }}
          s.textContent = css;
          try {{
            const frames = doc.querySelectorAll("iframe");
            for (const frame of frames) {{
              if (frame.contentWindow === window) {{
                const wrap = frame.closest('[data-testid="stCustomComponentV1"]')
                  || frame.parentElement;
                if (wrap) {{
                  wrap.style.cssText =
                    "height:0;min-height:0;overflow:hidden;position:absolute;visibility:hidden;";
                }}
              }}
            }}
          }} catch (err) {{}}
        }})();
        </script>""",
        height=0,
        scrolling=False,
    )
    # Backup for non-tab rules if the component iframe cannot reach parent.
    fragment = f"<style>\n{css}\n</style>"
    if hasattr(st, "html"):
        st.html(fragment)
    else:
        st.markdown(fragment, unsafe_allow_html=True)


def inject_chart_css() -> None:
    """Hide Plotly's viewport fullscreen so Expand stays inside the page chrome."""
    inject_css(CHART_CSS, slot="charts")


def apply_appearance() -> None:
    """Sidebar Appearance controls plus page background. Call on every page."""
    _appearance_widgets()
    _appearance_css()


def _appearance_widgets() -> None:
    if SS_UPLOAD_NONCE not in st.session_state:
        st.session_state[SS_UPLOAD_NONCE] = 0
    st.session_state.setdefault(SS_BG_COLOR, DEFAULT_BG_COLOR)
    st.session_state.setdefault(SS_COLOR_FADE, DEFAULT_COLOR_FADE)
    st.session_state.setdefault(SS_IMAGE_FADE, DEFAULT_IMAGE_FADE)
    with st.sidebar.expander("Appearance"):
        st.color_picker(
            "Background colour",
            key=SS_BG_COLOR,
            help="Solid wash colour. Strength is Colour fade.",
        )
        st.slider(
            "Colour fade",
            min_value=0,
            max_value=100,
            format="%d%%",
            key=SS_COLOR_FADE,
            help="How strong the colour wash is. Over a photo this is the overlay.",
        )
        uploaded = st.file_uploader(
            "Background image",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"appearance_upload_{st.session_state[SS_UPLOAD_NONCE]}",
            help="Optional photo. Image fade sets how visible it is.",
        )
        if uploaded is not None:
            st.session_state[SS_IMAGE_BYTES] = uploaded.getvalue()
            mime = (uploaded.type or "image/png").lower()
            if mime == "image/jpg":
                mime = "image/jpeg"
            st.session_state[SS_IMAGE_MIME] = mime
        st.slider(
            "Image fade",
            min_value=0,
            max_value=100,
            format="%d%%",
            key=SS_IMAGE_FADE,
            help="How visible the uploaded photo is.",
        )
        if st.session_state.get(SS_IMAGE_BYTES):
            if st.button("Clear image"):
                st.session_state[SS_IMAGE_BYTES] = None
                st.session_state[SS_IMAGE_MIME] = None
                st.session_state[SS_UPLOAD_NONCE] += 1
                st.rerun()


def _hex_ok(color: str) -> str:
    raw = (color or DEFAULT_BG_COLOR).strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return DEFAULT_BG_COLOR
    try:
        int(raw, 16)
    except ValueError:
        return DEFAULT_BG_COLOR
    return f"#{raw}"


def _image_data_uri() -> str | None:
    blob = st.session_state.get(SS_IMAGE_BYTES)
    if not blob:
        return None
    mime = st.session_state.get(SS_IMAGE_MIME) or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        mime = "image/png"
    encoded = base64.standard_b64encode(blob).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _appearance_css() -> None:
    color = _hex_ok(str(st.session_state.get(SS_BG_COLOR, DEFAULT_BG_COLOR)))
    color_fade = max(0, min(100, int(st.session_state.get(SS_COLOR_FADE, DEFAULT_COLOR_FADE))))
    image_fade = max(0, min(100, int(st.session_state.get(SS_IMAGE_FADE, DEFAULT_IMAGE_FADE))))
    color_a = color_fade / 100.0
    image_a = image_fade / 100.0
    uri = _image_data_uri()
    image_rule = ""
    if uri:
        image_rule = f"""
.stApp::before {{
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: url("{uri}");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: {image_a:.3f};
}}
"""
    inject_css(
        f"""
.stApp {{
  background-color: var(--background-color, {DEFAULT_BG_COLOR}) !important;
}}
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.stMainBlockContainer,
.main {{
  background: transparent !important;
}}
{image_rule}
.stApp::after {{
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-color: {color};
  opacity: {color_a:.3f};
}}
.stApp > * {{
  position: relative;
  z-index: 1;
}}
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
section[data-testid="stSidebar"] {{
  background-color: color-mix(in srgb, var(--background-color, {DEFAULT_BG_COLOR}) 94%, transparent) !important;
}}
""",
        slot="appearance",
    )


def is_showing(key: str, group: tuple[str, ...]) -> bool:
    current = st.session_state.get(EXPAND_STATE)
    if current is None or current not in group:
        return True
    return current == key


def expand_bar(key: str) -> bool:
    """Right-aligned Expand/Restore. Returns True if this chart is expanded."""
    expanded = st.session_state.get(EXPAND_STATE) == key
    _left, right = st.columns([6, 1])
    with right:
        label = "Restore" if expanded else "Expand"
        help_txt = (
            "Fill the page area under the sidebar and tabs. "
            "Does not hide navigation."
        )
        if st.button(
            label,
            key=f"expandbtn_{key}",
            help=help_txt,
            width="stretch",
            icon=":material/close_fullscreen:" if expanded else ":material/open_in_full:",
        ):
            st.session_state[EXPAND_STATE] = None if expanded else key
            st.rerun()
    return expanded


def show_plotly(
    fig: go.Figure,
    *,
    key: str,
    group: tuple[str, ...],
    default_height: int = 440,
) -> None:
    if not is_showing(key, group):
        return
    expanded = expand_bar(key)
    height = _expanded_height() if expanded else default_height
    styled = go.Figure(fig)
    styled.update_layout(height=height, dragmode="zoom", uirevision=key, autosize=True)
    if expanded:
        st.markdown(
            f"""
            <style>
            .st-key-{key} {{
                min-height: calc(100vh - 13.5rem) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        height = _expanded_height()
        styled.update_layout(height=height)
    st.plotly_chart(
        styled,
        width="stretch",
        height=height,
        config=PLOTLY_CONFIG,
        key=key,
        theme="streamlit",
    )


def _expanded_height() -> int:
    return 780


def scatter_pair(
    fig_a: go.Figure,
    fig_b: go.Figure,
    *,
    group: tuple[str, ...],
    key_a: str = "hw_late",
    key_b: str = "hw_chg",
) -> None:
    """Two scatters in one view so a click on one jiggles the match on the other."""
    current = st.session_state.get(EXPAND_STATE)
    if current is not None and current not in group:
        # Another tab is expanded; still show this tab's charts.
        current = None
    if current in group and current not in {key_a, key_b}:
        return

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        _toggle(key_a, "Expand on-time")
    with c2:
        _toggle(key_b, "Expand date-changes")

    focus = "both"
    if current == key_a:
        focus = "a"
    elif current == key_b:
        focus = "b"

    pane_h = _expanded_height() if focus != "both" else 450
    iframe_h = _expanded_height() if focus != "both" else 940
    html = _SCATTER_HTML.replace("__FIG_A__", _fig_json(fig_a, key_a, pane_h))
    html = html.replace("__FIG_B__", _fig_json(fig_b, key_b, pane_h))
    html = html.replace("__FOCUS__", focus)
    html = html.replace("__CONFIG__", json.dumps(PLOTLY_CONFIG))
    components.html(html, height=iframe_h + 16, scrolling=False)


def _toggle(key: str, label: str) -> None:
    expanded = st.session_state.get(EXPAND_STATE) == key
    text = "Restore" if expanded else label
    if st.button(
        text,
        key=f"expandbtn_{key}",
        help="Fill the page area. Sidebar and tabs stay visible.",
        icon=":material/close_fullscreen:" if expanded else ":material/open_in_full:",
    ):
        st.session_state[EXPAND_STATE] = None if expanded else key
        st.rerun()


def _fig_json(fig: go.Figure, rev: str, height: int) -> str:
    styled = go.Figure(fig)
    styled.update_layout(height=height, dragmode="zoom", autosize=True, uirevision=rev, meta=rev)
    for trace in styled.data:
        name = trace.name or ""
        trace.meta = name
        if getattr(trace, "legendgroup", None) in (None, ""):
            trace.legendgroup = name
        if trace.x is not None:
            trace.x = [float(v) if v is not None else None for v in list(trace.x)]
        if trace.y is not None:
            trace.y = [float(v) if v is not None else None for v in list(trace.y)]
    return json.dumps(json.loads(styled.to_json())).replace("<", "\\u003c")


_SCATTER_HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: transparent;
      font-family: "Source Sans Pro", sans-serif;
    }
    .wrap {
      display: flex;
      flex-direction: column;
      gap: 10px;
      height: 100vh;
      box-sizing: border-box;
    }
    .wrap[data-focus="a"] #pane-b { display: none; }
    .wrap[data-focus="b"] #pane-a { display: none; }
    .pane {
      flex: 1;
      min-height: 0;
      position: relative;
    }
    .plot { width: 100%; height: 100%; }
  </style>
</head>
<body>
  <div class="wrap" id="wrap" data-focus="__FOCUS__">
    <div class="pane" id="pane-a"><div id="plot-a" class="plot"></div></div>
    <div class="pane" id="pane-b"><div id="plot-b" class="plot"></div></div>
  </div>
  <script>
    if (typeof Plotly === "undefined") {
      document.body.innerHTML = "<p style='padding:1rem;font-family:sans-serif'>Plotly failed to load. Check network access to cdn.plot.ly.</p>";
    } else {
    const figA = __FIG_A__;
    const figB = __FIG_B__;
    const config = __CONFIG__;
    const jiggling = new WeakMap();

    function nameOf(trace) {
      if (!trace) return "";
      const meta = trace.meta;
      if (typeof meta === "string" && meta) return meta;
      if (Array.isArray(meta) && meta.length) return String(meta[0]);
      return String(trace.name || trace.legendgroup || "");
    }

    function findTrace(gd, name) {
      const want = String(name);
      return gd.data.findIndex(t => nameOf(t) === want);
    }

    function asNums(v) {
      if (v == null) return [];
      if (typeof v === "number") return [v];
      if (Array.isArray(v)) return v.slice();
      if (ArrayBuffer.isView(v)) return Array.from(v);
      if (v._inputArray) return asNums(v._inputArray);
      try { return Array.from(v); } catch (e) { return []; }
    }

    function traceXY(gd, i) {
      const full = (gd._fullData && gd._fullData[i]) || gd.data[i] || {};
      let x = asNums(full.x);
      let y = asNums(full.y);
      if (!x.length && gd.data[i] && gd.data[i].x != null && typeof gd.data[i].x === "object" && "0" in (gd.data[i].x._inputArray || {})) {
        x = [gd.data[i].x._inputArray[0]];
      }
      if (!y.length && gd.data[i] && gd.data[i].y != null && typeof gd.data[i].y === "object" && "0" in (gd.data[i].y._inputArray || {})) {
        y = [gd.data[i].y._inputArray[0]];
      }
      return {x, y};
    }

    function jiggle(gd, name) {
      if (!gd || !name) return;
      const i = findTrace(gd, name);
      if (i < 0) return;
      if (jiggling.get(gd) === i) return;
      jiggling.set(gd, i);

      const orig = traceXY(gd, i);
      const x0 = orig.x;
      const y0 = orig.y;
      if (!x0.length || !y0.length) {
        jiggling.delete(gd);
        return;
      }
      const xaxis = (gd._fullLayout && gd._fullLayout.xaxis) || {};
      const yaxis = (gd._fullLayout && gd._fullLayout.yaxis) || {};
      const xr = xaxis.range || [0, 1];
      const yr = yaxis.range || [0, 1];
      const dx = (xr[1] - xr[0]) * 0.028;
      const dy = (yr[1] - yr[0]) * 0.045;
      const seq = [0.95, -1.15, 0.8, -0.55, 0.28, 0];
      let n = 0;
      const prevWidth = (gd.data[i].marker && gd.data[i].marker.line && gd.data[i].marker.line.width) || 0.5;
      Plotly.restyle(gd, {"marker.line.width": 3, "marker.line.color": "#111827"}, [i]);

      function tick() {
        const k = seq[n];
        const xs = x0.map(v => v + dx * k);
        const ys = y0.map(v => v + dy * k * (n % 2 === 0 ? 1 : -0.7));
        Plotly.restyle(gd, {x: [xs], y: [ys]}, [i]).then(() => {
          n += 1;
          if (n < seq.length) {
            setTimeout(tick, 70);
          } else {
            Plotly.restyle(gd, {x: [x0], y: [y0], "marker.line.width": prevWidth}, [i]);
            jiggling.delete(gd);
          }
        });
      }
      tick();
    }

    function wireLegend(src, dst) {
      src.querySelectorAll(".legend .traces").forEach((el, idx) => {
        el.style.cursor = "pointer";
        el.addEventListener("click", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          const trace = src.data[idx];
          jiggle(dst, nameOf(trace));
        });
      });
    }

    function wire(src, dst) {
      src.on("plotly_click", (ev) => {
        if (!ev.points || !ev.points.length) return;
        jiggle(dst, nameOf(ev.points[0].data));
      });
      src.on("plotly_legendclick", (ev) => {
        const trace = ev.data && ev.data[ev.curveNumber];
        jiggle(dst, nameOf(trace));
        return false;
      });
      src.on("plotly_legenddoubleclick", () => false);
    }

    Promise.all([
      Plotly.newPlot("plot-a", figA.data, figA.layout, config),
      Plotly.newPlot("plot-b", figB.data, figB.layout, config),
    ]).then(([a, b]) => {
      wire(a, b);
      wire(b, a);
      window.ovadueJiggle = jiggle;
      window.ovaduePlots = {a, b};
      window.ovadueReady = true;
      const resize = () => {
        Plotly.Plots.resize(a);
        Plotly.Plots.resize(b);
      };
      window.addEventListener("resize", resize);
      setTimeout(() => {
        resize();
        wireLegend(a, b);
        wireLegend(b, a);
      }, 50);
    }).catch((err) => {
      window.ovadueErr = String(err && err.stack || err);
    });
    }
  </script>
</body>
</html>
"""
