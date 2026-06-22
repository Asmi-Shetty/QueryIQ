# app.py
# Section 4 — Streamlit UI for the NL-to-SQL Agent
# FIXED: render_result() split into separate st.markdown() calls
# so HTML never leaks as raw text

import streamlit as st
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Page config (must be FIRST Streamlit call) 
st.set_page_config(
    page_title="QueryIQ",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from agent          import run_agent
from chat_history   import ChatHistory
from schema_context import get_schema_context


# CUSTOM CSS

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-primary:    #0d0f12;
    --bg-secondary:  #13161b;
    --bg-card:       #1a1e26;
    --bg-hover:      #1f2430;
    --accent-green:  #00e5a0;
    --accent-blue:   #4d9fff;
    --accent-amber:  #ffb347;
    --accent-red:    #ff5f5f;
    --text-primary:  #e8eaf0;
    --text-secondary:#8892a4;
    --text-muted:    #525c6e;
    --border:        #252a35;
    --border-accent: #2e3545;
    --font-mono:     'JetBrains Mono', monospace;
    --font-display:  'Inter', sans-serif;
    --radius:        10px;
}

html, body, .stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.main .block-container {
    padding: 0rem 2.5rem 4rem 2.5rem !important;
    max-width: 1000px !important;
    margin-top: -80px !important;
}

/* Remove Streamlit's built-in top gap */
[data-testid="stAppViewContainer"] > .main {
    padding-top: 0px !important;
}
[data-testid="stHeader"] {
    height: 0px !important;
    display: none !important;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    font-family: var(--font-mono) !important;
    color: var(--text-primary) !important;
}

.agent-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 0 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.agent-header-icon {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, var(--accent-green) 0%, var(--accent-blue) 100%);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; flex-shrink: 0;
}
.agent-title {
    font-family: var(--font-display) !important;
    font-size: 1.5rem; font-weight: 600;
    color: var(--text-primary);
    letter-spacing: 0px; line-height: 1.2; margin: 0;
}
.agent-subtitle {
    font-size: 0.72rem; color: var(--text-secondary);
    letter-spacing: 0.08em; text-transform: uppercase;
    margin: 2px 0 0 0;
}

.msg-user {
    display: flex; justify-content: flex-end;
    margin: 1.2rem 0 0.4rem 0;
}
.msg-user-bubble {
    background: linear-gradient(135deg, #1a3a5c 0%, #0f2a45 100%);
    border: 1px solid #1e4a7a;
    border-radius: 16px 16px 4px 16px;
    padding: 12px 18px; max-width: 75%;
    font-size: 0.88rem; color: #c8dff5; line-height: 1.5;
}

/* ── Card wrapper — purely decorative border/header ── */
.card-header-html {
    background: var(--bg-secondary);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius) var(--radius) 0 0;
    padding: 10px 16px;
    display: flex; align-items: center; gap: 8px;
    font-size: 0.72rem; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.1em;
}
.card-body-wrap {
    background: var(--bg-card);
    border: 1px solid var(--border-accent);
    border-top: none;
    border-radius: 0 0 var(--radius) var(--radius);
    padding: 16px;
}

.meta-row {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;
}
.meta-pill {
    background: var(--bg-secondary);
    border: 1px solid var(--border-accent);
    border-radius: 20px; padding: 4px 12px;
    font-size: 0.70rem; color: var(--text-secondary);
    display: flex; align-items: center; gap: 5px;
}
.meta-pill span.val { color: var(--accent-green); font-weight: 600; }
.meta-pill.retry span.val { color: var(--accent-amber); }

.explanation-box {
    background: #111827;
    border-left: 3px solid var(--accent-green);
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 0.84rem; color: #a8c4b0; line-height: 1.6;
    margin-bottom: 14px;
}

.sql-block {
    background: #080b10;
    border: 1px solid #1c2535;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: var(--font-mono) !important;
    font-size: 0.80rem; color: #7dd3fc;
    white-space: pre-wrap; overflow-x: auto;
    line-height: 1.6; margin-bottom: 14px;
}

.error-box {
    background: #1a0d0d;
    border: 1px solid #3d1515;
    border-left: 3px solid var(--accent-red);
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 0.83rem; color: #f08080; line-height: 1.5;
}

.suggest-label {
    font-size: 0.70rem; text-transform: uppercase;
    letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 10px;
}

.stButton > button {
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-accent) !important;
    color: var(--text-secondary) !important;
    border-radius: 8px !important; padding: 6px 14px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: var(--bg-hover) !important;
    border-color: var(--accent-green) !important;
    color: var(--accent-green) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #004d35 0%, #003826 100%) !important;
    border-color: var(--accent-green) !important;
    color: var(--accent-green) !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #006647 0%, #004d35 100%) !important;
}

.stTextInput > div > div > input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-accent) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent-green) !important;
    box-shadow: 0 0 0 2px rgba(0,229,160,0.08) !important;
}

hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.5rem 0 !important;
}

.schema-table {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;
    font-size: 0.72rem;
}
.schema-table-name { color: var(--accent-blue); font-weight: 600; margin-bottom: 4px; }
.schema-col { color: var(--text-secondary); padding-left: 10px; line-height: 1.8; }
.schema-col .col-type { color: var(--text-muted); font-size: 0.66rem; margin-left: 4px; }

.status-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--accent-green); display: inline-block;
    margin-right: 6px;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.empty-state { text-align: center; padding: 0.2rem 2rem; color: var(--text-muted); }
.empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-title {
    font-family: var(--font-display); font-size: 1.1rem;
    color: var(--text-secondary); margin-bottom: 0.5rem;
}
.empty-sub { font-size: 0.78rem; line-height: 1.6; }

.no-rows-msg {
    color: var(--text-muted); font-size: 0.78rem; padding: 4px 0 12px;
}

/* ── Visualization Section ──────────────────────── */
.viz-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius) var(--radius) 0 0;
    font-size: 0.72rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 14px;
}
.viz-accent { color: var(--accent-green); font-weight: 700; }
.viz-body {
    background: var(--bg-card);
    border: 1px solid var(--border-accent);
    border-top: none;
    border-radius: 0 0 var(--radius) var(--radius);
    padding: 16px;
}

/* ── Custom Loader ───────────────────────────────── */
.custom-loader-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2.5rem 0;
    gap: 1.2rem;
}
.loader-orbit {
    position: relative;
    width: 64px;
    height: 64px;
}
.loader-core {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 18px; height: 18px;
    border-radius: 50%;
    background: var(--accent-green);
    box-shadow: 0 0 14px 4px rgba(0,229,160,0.45);
    animation: core-pulse 1.4s ease-in-out infinite;
}
@keyframes core-pulse {
    0%,100% { transform: translate(-50%,-50%) scale(1);   opacity: 1; }
    50%      { transform: translate(-50%,-50%) scale(1.25); opacity: 0.6; }
}
.loader-ring {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    border-radius: 50%;
    animation: ring-spin 1.6s linear infinite;
}
.loader-ring::before {
    content: '';
    position: absolute;
    top: -3px; left: 50%;
    transform: translateX(-50%);
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--accent-blue);
    box-shadow: 0 0 8px 2px rgba(77,159,255,0.6);
}
.loader-ring2 {
    position: absolute;
    top: 6px; left: 6px;
    width: calc(100% - 12px); height: calc(100% - 12px);
    border-radius: 50%;
    animation: ring-spin 2.2s linear infinite reverse;
}
.loader-ring2::before {
    content: '';
    position: absolute;
    top: -3px; left: 50%;
    transform: translateX(-50%);
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent-amber);
    box-shadow: 0 0 7px 2px rgba(255,179,71,0.55);
}
@keyframes ring-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.loader-label {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--text-secondary);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.loader-dots span {
    animation: blink 1.2s infinite;
    opacity: 0;
}
.loader-dots span:nth-child(1) { animation-delay: 0s; }
.loader-dots span:nth-child(2) { animation-delay: 0.3s; }
.loader-dots span:nth-child(3) { animation-delay: 0.6s; }
@keyframes blink { 0%,80%,100%{opacity:0} 40%{opacity:1} }
.loader-bar-wrap {
    width: 120px;
    height: 2px;
    background: var(--border);
    border-radius: 99px;
    overflow: hidden;
}
.loader-bar {
    height: 100%;
    width: 40%;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--accent-green), var(--accent-blue));
    animation: bar-slide 1.6s ease-in-out infinite;
}
@keyframes bar-slide {
    0%   { transform: translateX(-100%); }
    50%  { transform: translateX(200%);  }
    100% { transform: translateX(-100%); }
}
</style>
""", unsafe_allow_html=True)



# SESSION STATE
if "history"   not in st.session_state:
    st.session_state.history  = ChatHistory()
if "messages"  not in st.session_state:
    st.session_state.messages = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0


# ════════════════════════════════════════════════════════════════════════════
# RENDER RESULT  ←  THE FIXED FUNCTION
# Every piece is its own st.markdown() call — nothing is bundled together.
# st.dataframe() is always called as a standalone Streamlit element.
# ════════════════════════════════════════════════════════════════════════════
def render_result(result: dict):

    # ── ERROR ────────────────────────────────────────────────────────
    if result["error"]:
        st.markdown(
            '<div class="card-header-html"><span class="status-dot"></span>Agent response</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="card-body-wrap"><div class="error-box">{result["error"]}</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── CARD HEADER ──────────────────────────────────────────────────
    st.markdown(
        '<div class="card-header-html"><span class="status-dot"></span>Query result</div>',
        unsafe_allow_html=True,
    )

    # ── CARD BODY OPEN ───────────────────────────────────────────────
    st.markdown('<div class="card-body-wrap">', unsafe_allow_html=True)

    # ── META PILLS ───────────────────────────────────────────────────
    retry_class = "retry" if result["retries"] > 0 else ""
    retry_label = (
        f"🔁 {result['retries']} retr{'y' if result['retries']==1 else 'ies'}"
        if result["retries"] > 0 else "✓ no retries"
    )
    st.markdown(f"""
<div class="meta-row">
    <div class="meta-pill">⏱ time: <span class="val">{result['exec_time']}s</span></div>
    <div class="meta-pill">📋 rows: <span class="val">{result['row_count']}</span></div>
    <div class="meta-pill {retry_class}">{retry_label}</div>
</div>""", unsafe_allow_html=True)

    # ── EXPLANATION ──────────────────────────────────────────────────
    if result.get("explanation"):
        st.markdown(
            f'<div class="explanation-box">💡 {result["explanation"]}</div>',
            unsafe_allow_html=True,
        )

    # ── SQL BLOCK ────────────────────────────────────────────────────
    if result.get("sql"):
        # escape so < > inside SQL don't break HTML rendering
        safe_sql = (
            result["sql"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        st.markdown(
            f'<div class="sql-block">{safe_sql}</div>',
            unsafe_allow_html=True,
        )

    # ── CARD BODY CLOSE ──────────────────────────────────────────────
    st.markdown('</div>', unsafe_allow_html=True)

    # ── DATAFRAME ────────────────────────────────────────────────────
    # Must be OUTSIDE all HTML blocks — called as its own Streamlit element
    df = result.get("dataframe")
    if df is not None:
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            smart_charts(df)
        else:
            st.markdown(
                '<p class="no-rows-msg">No rows returned for this query.</p>',
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════════════════════
# SMART VISUALIZATION
# Auto-detects column types and renders the most actionable chart(s).
# ════════════════════════════════════════════════════════════════════════════
PLOT_THEME = dict(
    paper_bgcolor="#13161b",
    plot_bgcolor="#1a1e26",
    font_color="#8892a4",
    font_family="JetBrains Mono, monospace",
    margin=dict(l=12, r=12, t=36, b=12),
    colorway=["#00e5a0", "#4d9fff", "#ffb347", "#ff5f5f", "#a78bfa", "#34d399"],
)

def _style(fig):
    """Apply dark theme to any Plotly figure."""
    fig.update_layout(
        **PLOT_THEME,
        xaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
        yaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
        legend=dict(bgcolor="#13161b", bordercolor="#252a35"),
    )
    return fig


def smart_charts(df: pd.DataFrame):
    """Render bar and/or line charts intelligently based on column types."""
    if df is None or df.empty or len(df.columns) < 2:
        return

    # ── Classify columns ─────────────────────────────────────────────
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # Detect date-like columns hidden as strings
    date_cols = []
    for col in cat_cols:
        try:
            parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            if parsed.notna().sum() / max(len(df), 1) > 0.5:
                df[col] = parsed
                date_cols.append(col)
        except Exception:
            pass
    cat_cols = [c for c in cat_cols if c not in date_cols]

    charts = []   # list of (label, fig) tuples

    # ── Bar chart: categorical × numeric ─────────────────────────────
    if cat_cols and num_cols:
        x_col = cat_cols[0]
        # Aggregate if rows > unique x values (e.g. GROUP BY already done)
        agg_df = df[[x_col] + num_cols[:3]].copy()
        # If too many categories, keep top 20 by first numeric col
        if agg_df[x_col].nunique() > 20:
            top = agg_df.nlargest(20, num_cols[0])[x_col]
            agg_df = agg_df[agg_df[x_col].isin(top)]
        agg_df = agg_df.sort_values(num_cols[0], ascending=False)

        fig_bar = go.Figure()
        colors = PLOT_THEME["colorway"]
        for i, y_col in enumerate(num_cols[:3]):
            fig_bar.add_trace(go.Bar(
                x=agg_df[x_col].astype(str),
                y=agg_df[y_col],
                name=y_col,
                marker_color=colors[i % len(colors)],
                marker_line_width=0,
                opacity=0.9,
            ))
        fig_bar.update_layout(
            title=dict(text=f"📊  {num_cols[0]} by {x_col}", font_size=13),
            barmode="group",
            bargap=0.2,
            **PLOT_THEME,
            xaxis=dict(gridcolor="#252a35", tickangle=-30),
            yaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
            legend=dict(bgcolor="#13161b", bordercolor="#252a35"),
        )
        charts.append(("Bar Chart", fig_bar))

    # ── Line chart: date × numeric ────────────────────────────────────
    if date_cols and num_cols:
        x_col  = date_cols[0]
        line_df = df[[x_col] + num_cols[:3]].sort_values(x_col)
        fig_line = go.Figure()
        colors = PLOT_THEME["colorway"]
        for i, y_col in enumerate(num_cols[:3]):
            fig_line.add_trace(go.Scatter(
                x=line_df[x_col],
                y=line_df[y_col],
                mode="lines+markers",
                name=y_col,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=5),
                fill="tozeroy" if i == 0 else None,
                fillcolor=f"rgba(0,229,160,0.06)" if i == 0 else None,
            ))
        fig_line.update_layout(
            title=dict(text=f"📈  {num_cols[0]} over time", font_size=13),
            **PLOT_THEME,
            xaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
            yaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
            legend=dict(bgcolor="#13161b", bordercolor="#252a35"),
        )
        charts.append(("Line Chart", fig_line))

    # ── Fallback: two numeric cols → scatter ──────────────────────────
    if not charts and len(num_cols) >= 2:
        fig_sc = px.scatter(
            df, x=num_cols[0], y=num_cols[1],
            trendline="ols" if len(df) > 3 else None,
            title=f"📊  {num_cols[1]} vs {num_cols[0]}",
        )
        fig_sc.update_traces(marker=dict(color="#00e5a0", size=7))
        fig_sc.update_layout(
            **PLOT_THEME,
            xaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
            yaxis=dict(gridcolor="#252a35", zerolinecolor="#252a35"),
        )
        charts.append(("Scatter", fig_sc))

    if not charts:
        return

    # ── Render ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="viz-header">'
        '<span class="viz-accent">▲</span> Insights &nbsp;&mdash;&nbsp; '
        'Auto-generated visualizations'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="viz-body">', unsafe_allow_html=True)

    if len(charts) == 1:
        st.plotly_chart(charts[0][1], use_container_width=True, config={"displayModeBar": False})
    else:
        tabs = st.tabs([label for label, _ in charts])
        for tab, (_, fig) in zip(tabs, charts):
            with tab:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('</div>', unsafe_allow_html=True)



def run_query(question: str):
    if not question.strip():
        return
    loader = st.empty()
    loader.markdown("""
<div class="custom-loader-wrap">
    <div class="loader-orbit">
        <div class="loader-core"></div>
        <div class="loader-ring"></div>
        <div class="loader-ring2"></div>
    </div>
    <div class="loader-label">
        Processing query<span class="loader-dots"><span>.</span><span>.</span><span>.</span></span>
    </div>
    <div class="loader-bar-wrap"><div class="loader-bar"></div></div>
</div>
""", unsafe_allow_html=True)
    result = run_agent(question.strip(), st.session_state.history)
    loader.empty()
    st.session_state.messages.append({"question": question.strip(), "result": result})


def new_conversation():
    st.session_state.history.clear()
    st.session_state.messages  = []
    st.session_state.input_key += 1


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
<div style="padding:0 0 1rem 0;border-bottom:1px solid var(--border);margin-bottom:1.2rem;">
    <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--text-primary);">
        ⚡ QueryIQ
    </div>
    <div style="font-size:0.68rem;color:var(--text-muted);margin-top:2px;text-transform:uppercase;letter-spacing:0.08em;">
        LangChain + Mistral
    </div>
</div>""", unsafe_allow_html=True)

    if st.button("＋  New Conversation", use_container_width=True):
        new_conversation()
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    msg_count  = len(st.session_state.messages)
    hist_count = len(st.session_state.history)
    st.markdown(f"""
<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin-bottom:8px;">
    Session stats
</div>
<div class="meta-row">
    <div class="meta-pill">💬 <span class="val">{msg_count}</span> questions</div>
    <div class="meta-pill">📚 <span class="val">{hist_count}</span> messages</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("""
<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;
            color:var(--text-muted);margin-bottom:10px;">
    Database schema
</div>""", unsafe_allow_html=True)

    try:
        conn = sqlite3.connect("company.db")
        cur  = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols     = cur.fetchall()
            col_html = "".join([
                f'<div class="schema-col">· {c[1]} <span class="col-type">{c[2]}</span></div>'
                for c in cols
            ])
            st.markdown(f"""
<div class="schema-table">
    <div class="schema-table-name">📋 {table}</div>
    {col_html}
</div>""", unsafe_allow_html=True)
        conn.close()
    except Exception as e:
        st.markdown(
            f'<div style="color:var(--accent-red);font-size:0.75rem;">Schema error: {e}</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.messages:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("""
<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;
            color:var(--text-muted);margin-bottom:10px;">
    History
</div>""", unsafe_allow_html=True)
        for i, msg in enumerate(st.session_state.messages, 1):
            q_short = msg["question"][:42] + "…" if len(msg["question"]) > 42 else msg["question"]
            ok      = not msg["result"]["error"]
            status  = "✓" if ok else "✗"
            color   = "#00e5a0" if ok else "#ff5f5f"
            st.markdown(f"""
<div style="font-size:0.70rem;color:var(--text-secondary);padding:4px 0;
            border-bottom:1px solid var(--border);line-height:1.4;">
    <span style="color:{color};margin-right:4px;">{status}</span>
    <span style="color:var(--text-muted);">Q{i}:</span> {q_short}
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

# ── Header ──
st.markdown("""
<div class="agent-header">
    <div class="agent-header-icon">🗄️</div>
    <div>
        <div class="agent-title">QueryIQ</div>
        <div class="agent-subtitle">Ask smarter questions. Get instant answers.</div>
    </div>
</div>""", unsafe_allow_html=True)

# ── Chat messages ──
if not st.session_state.messages:
    st.markdown("""
<div class="empty-state">
    <div class="empty-icon">💬</div>
    <div class="empty-title">Start a conversation</div>
    <div class="empty-sub">
        Type a question below in plain English.<br>
        The agent will generate SQL, run it, and show you the results.
    </div>
</div>""", unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        # User bubble
        st.markdown(f"""
<div class="msg-user">
    <div class="msg-user-bubble">{msg['question']}</div>
</div>""", unsafe_allow_html=True)
        # Result — each piece rendered separately
        render_result(msg["result"])
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Suggested questions ──
SUGGESTIONS = [
    "How many employees are in each department?",
    "List all projects that are overdue.",
    "Which department has the highest average salary?",
    "Show employees hired after January 2023.",
    "What is the total project budget per department?",
    "Which employee has the most projects assigned?",
]

st.markdown('<div class="suggest-label">✦ Try a question</div>', unsafe_allow_html=True)

cols = st.columns(3)
for i, s in enumerate(SUGGESTIONS):
    with cols[i % 3]:
        label = s[:38] + "…" if len(s) > 38 else s
        if st.button(label, key=f"sug_{i}"):
            run_query(s)
            st.rerun()

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ── Input row ──
col_input, col_send = st.columns([5, 1])
with col_input:
    user_input = st.text_input(
        label            = "question",
        placeholder      = "e.g. Which employee earns the most in Sales?",
        label_visibility = "collapsed",
        key              = f"input_{st.session_state.input_key}",
    )
with col_send:
    send_clicked = st.button("Send →", type="primary", use_container_width=True)

if send_clicked and user_input.strip():
    st.session_state.input_key += 1
    run_query(user_input.strip())
    st.rerun()

# ── Footer ──
st.markdown("""
<div style="text-align:center;margin-top:3rem;font-size:0.65rem;
            color:var(--text-muted);text-transform:uppercase;letter-spacing:0.12em;">
    QueryIQ &nbsp;·&nbsp; LangChain + Mistral &nbsp;·&nbsp; SQLite
</div>""", unsafe_allow_html=True)
