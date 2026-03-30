"""
Streamlit dashboard for enrichment monitoring.
Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

from enrichment import config
from enrichment.pipeline_control import (
    clear_pid,
    is_pid_running,
    read_pid,
    start_pipeline,
    stop_pipeline,
)


st.set_page_config(page_title="Enrichment Monitor", layout="wide")
st.title("Data Enrichment Monitor")


def _read_jsonl(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _read_output() -> pd.DataFrame:
    if not config.OUTPUT_FILE.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(config.OUTPUT_FILE, dtype=str)
    except Exception:
        return pd.DataFrame()


def _read_log_tail(path: Path, max_lines: int = 200) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except Exception:
        return ""


col_a, col_b, col_c = st.columns(3)
with col_a:
    auto_refresh = st.checkbox("Auto refresh", value=True)
with col_b:
    refresh_seconds = st.slider("Refresh (seconds)", min_value=5, max_value=60, value=10, step=5)
with col_c:
    if st.button("Refresh now"):
        st.rerun()

pipeline_pid = read_pid()
pipeline_running = is_pid_running(pipeline_pid)
if pipeline_pid and not pipeline_running:
    clear_pid()

st.subheader("Pipeline Controls")
ctrl_a, ctrl_b, ctrl_c = st.columns([1, 1, 2])
with ctrl_a:
    start_clicked = st.button("Start Enrichment", use_container_width=True)
with ctrl_b:
    stop_clicked = st.button("Stop Enrichment", use_container_width=True)
with ctrl_c:
    if pipeline_running:
        st.success(f"Pipeline running (PID {pipeline_pid})")
    else:
        st.info("Pipeline stopped")

if start_clicked:
    ok, msg = start_pipeline()
    if ok:
        st.success(msg)
    else:
        st.warning(msg)

if stop_clicked:
    ok, msg = stop_pipeline()
    if ok:
        st.success(msg)
    else:
        st.warning(msg)

output_df = _read_output()
events_df = _read_jsonl(config.EVENTS_FILE)
search_df = _read_jsonl(config.SEARCH_HISTORY_FILE)

processed = len(output_df)
errors = 0
if not events_df.empty and "level" in events_df.columns:
    errors = int((events_df["level"].astype(str).str.lower() == "error").sum())

high_conf = 0
if not output_df.empty and "Confidence_%" in output_df.columns:
    high_conf = int(pd.to_numeric(output_df["Confidence_%"], errors="coerce").fillna(0).ge(config.MIN_CONFIDENCE_SCORE).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows processed", processed)
m2.metric("High confidence rows", high_conf)
m3.metric("Search events", len(search_df))
m4.metric("Error events", errors)

st.subheader("Proxy and Search History")
if search_df.empty:
    st.info("No search history yet. Start enrichment to see live events.")
else:
    if "provider" in search_df.columns:
        provider_counts = search_df["provider"].fillna("unknown").value_counts().reset_index()
        provider_counts.columns = ["provider", "count"]
        st.bar_chart(provider_counts.set_index("provider"))

    status_filter = st.selectbox("Filter search status", ["all", "ok", "error", "rate_limited", "timeout"])
    show_search = search_df.copy()
    if status_filter != "all" and "status" in show_search.columns:
        show_search = show_search[show_search["status"] == status_filter]
    st.dataframe(show_search.tail(300), use_container_width=True)

st.subheader("Enriched Output Preview")
if output_df.empty:
    st.info("Output file not found yet.")
else:
    st.dataframe(output_df.tail(200), use_container_width=True)

st.subheader("Runtime Events")
if events_df.empty:
    st.info("No runtime events logged yet.")
else:
    level_filter = st.selectbox("Filter event level", ["all", "info", "warning", "error"])
    show_events = events_df.copy()
    if level_filter != "all" and "level" in show_events.columns:
        show_events = show_events[show_events["level"] == level_filter]
    st.dataframe(show_events.tail(500), use_container_width=True)

st.subheader("Log Tail")
log_tail = _read_log_tail(Path("enrichment.log"), max_lines=200)
if not log_tail:
    st.info("No log file yet.")
else:
    st.text_area("Latest logs", log_tail, height=280)

if auto_refresh:
    st.caption(f"Auto refresh enabled: every {refresh_seconds}s")
    if st_autorefresh:
        st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_autorefresh")
    else:
        st.warning("Auto refresh helper is missing. Install dependencies to enable smooth auto refresh.")
