"""
🦌 Handra Job Application Dashboard
Read-only dashboard for Google Sheets "List Lamaran Kerjaan"

Supports two modes:
1. LOCAL DEV: Reuses OAuth token from google-workspace skill
2. STREAMLIT CLOUD: Uses st.secrets for OAuth client config + token.json in repo

SPREADSHEET_ID is read from env var / secrets — never hardcoded.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser
import plotly.express as px
import plotly.graph_objects as go
from googleapiclient.discovery import build
import sys
import os
import json
import tempfile

# ============================================================================
# CONFIG — Read SPREADSHEET_ID from env / secrets (never hardcoded)
# ============================================================================
def get_spreadsheet_id():
    """Read SPREADSHEET_ID from env var or Streamlit secrets."""
    try:
        if "SPREADSHEET_ID" in st.secrets:
            return st.secrets["SPREADSHEET_ID"]
    except Exception:
        pass
    return os.getenv("SPREADSHEET_ID", "")

# ============================================================================
# OAUTH — works in both local and Streamlit Cloud
# ============================================================================
def get_credentials():
    """Get Google OAuth credentials.

    - LOCAL: Reuses token from google-workspace skill
    - STREAMLIT CLOUD: Reconstructs from st.secrets
    """
    # Try Streamlit secrets first (for cloud deployment)
    try:
        if "google_token" in st.secrets and "google_client_secret" in st.secrets:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            token_info = json.loads(st.secrets["google_token"])
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/documents.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)

            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
    except Exception:
        pass

    # Fallback: import from local google-workspace skill
    SKILL_PATH = r"C:\Users\Handra\AppData\Local\hermes\skills\productivity\google-workspace\scripts"
    if SKILL_PATH not in sys.path:
        sys.path.insert(0, SKILL_PATH)
    from google_api import get_credentials as local_get_credentials
    return local_get_credentials()

SHEET_NAME = "Sheet1"
DATA_START_ROW = 6  # data starts at row 6
HEADER_ROW = 5

st.set_page_config(
    page_title="🦌 Job Application Dashboard",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=300)  # cache 5 minutes
def load_data():
    """Read all data from Google Sheets."""
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        st.error(
            "⚠️ SPREADSHEET_ID not configured. "
            "Set it in Streamlit secrets or as an environment variable."
        )
        st.stop()

    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    # Get all data up to row 200
    range_ = f"{SHEET_NAME}!A{DATA_START_ROW}:I200"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_
    ).execute()
    values = result.get("values", [])

    if not values:
        return pd.DataFrame()

    # Convert to DataFrame
    columns = [
        "No", "Date Applied", "Job Title", "Company", "Source",
        "CV Used", "Status", "Type", "Link"
    ]
    df = pd.DataFrame(values, columns=columns)

    # Parse dates (format: dd/mm/yyyy)
    df["Date Applied"] = pd.to_datetime(
        df["Date Applied"], format="%d/%m/%Y", errors="coerce"
    )
    df = df.dropna(subset=["Date Applied"])

    # Convert No to int
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
    df = df.dropna(subset=["No"])
    df["No"] = df["No"].astype(int)

    # Days since applied
    df["Days Since Applied"] = (datetime.now() - df["Date Applied"]).dt.days

    return df


def get_link_url(row):
    """Extract URL from a row's Link cell (it might be =HYPERLINK formula or text)."""
    link_value = row["Link"]
    if not link_value or pd.isna(link_value):
        return None
    if link_value.startswith("http"):
        return link_value
    return None


# ============================================================================
# UI
# ============================================================================

st.title("🦌 Handra Job Application Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%d %B %Y, %H:%M')} | Auto-refresh every 5 minutes")

# Load data
with st.spinner("Loading data from Google Sheets..."):
    df = load_data()

if df.empty:
    st.error("No data found. Check your spreadsheet.")
    st.stop()

# ============================================================================
# SIDEBAR - FILTERS
# ============================================================================
with st.sidebar:
    st.header("🔍 Filters")

    # Source filter
    all_sources = sorted(df["Source"].unique().tolist())
    selected_sources = st.multiselect(
        "Source", all_sources, default=all_sources
    )

    # Status filter
    all_statuses = sorted(df["Status"].unique().tolist())
    status_order = [
        "Applied", "Interview", "Interview-R",
        "No Response", "Rejected"
    ]
    # Sort by logical order
    all_statuses_sorted = [s for s in status_order if s in all_statuses] + \
                          [s for s in all_statuses if s not in status_order]
    selected_statuses = st.multiselect(
        "Status", all_statuses_sorted, default=all_statuses_sorted
    )

    # CV filter
    all_cvs = sorted(df["CV Used"].unique().tolist())
    selected_cvs = st.multiselect(
        "CV Used", all_cvs, default=all_cvs
    )

    # Date range
    min_date = df["Date Applied"].min().date()
    max_date = df["Date Applied"].max().date()
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Apply filters
filtered = df[
    (df["Source"].isin(selected_sources))
    & (df["Status"].isin(selected_statuses))
    & (df["CV Used"].isin(selected_cvs))
    & (df["Date Applied"].dt.date >= start_date)
    & (df["Date Applied"].dt.date <= end_date)
].copy()

# ============================================================================
# TOP METRICS
# ============================================================================
st.divider()
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Total", len(filtered))
with col2:
    applied = len(filtered[filtered["Status"] == "Applied"])
    st.metric("Applied", applied)
with col3:
    interview = len(filtered[filtered["Status"] == "Interview"])
    st.metric("Interview", interview, delta=f"{(interview/len(filtered)*100):.1f}%" if len(filtered) else "0%")
with col4:
    rejected = len(filtered[filtered["Status"] == "Rejected"])
    st.metric("Rejected", rejected)
with col5:
    no_resp = len(filtered[filtered["Status"] == "No Response"])
    st.metric("No Response", no_resp)
with col6:
    # Response rate: (Interview + Rejected) / Total
    responded = interview + rejected
    rate = (responded / len(filtered) * 100) if len(filtered) else 0
    st.metric("Response Rate", f"{rate:.1f}%", help="Interview + Rejected / Total")

# ============================================================================
# CHARTS - Row 1
# ============================================================================
st.divider()
st.subheader("📊 Overview")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Status distribution (donut)
    status_counts = filtered["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]

    color_map = {
        "Applied": "#3b82f6",
        "Interview": "#10b981",
        "Interview-R": "#f59e0b",
        "Rejected": "#ef4444",
        "No Response": "#6b7280",
    }
    fig = px.pie(
        status_counts,
        values="Count",
        names="Status",
        title="Status Distribution",
        hole=0.4,
        color="Status",
        color_discrete_map=color_map,
    )
    fig.update_layout(height=380, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    # Applications over time
    daily = filtered.groupby("Date Applied").size().reset_index(name="Count")
    daily = daily.sort_values("Date Applied")
    fig = px.line(
        daily,
        x="Date Applied",
        y="Count",
        title="Applications Over Time",
        markers=True,
    )
    fig.update_traces(line_color="#3b82f6", line_width=3, marker_size=8)
    fig.update_layout(height=380, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# CHARTS - Row 2
# ============================================================================
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    # Source breakdown (stacked bar by status)
    source_status = (
        filtered.groupby(["Source", "Status"])
        .size()
        .reset_index(name="Count")
    )
    fig = px.bar(
        source_status,
        x="Source",
        y="Count",
        color="Status",
        title="Applications by Source",
        color_discrete_map=color_map,
        text="Count",
    )
    fig.update_traces(textposition="inside")
    fig.update_layout(height=380, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with chart_col4:
    # Success rate by source (Interview / Total per source)
    source_stats = (
        filtered.groupby("Source")
        .agg(Total=("No", "count"),
             Interview=("Status", lambda x: (x == "Interview").sum()),
             Rejected=("Status", lambda x: (x == "Rejected").sum()))
        .reset_index()
    )
    source_stats["Response Rate %"] = (
        (source_stats["Interview"] + source_stats["Rejected"])
        / source_stats["Total"] * 100
    ).round(1)
    source_stats = source_stats.sort_values("Response Rate %", ascending=False)

    fig = px.bar(
        source_stats,
        x="Source",
        y="Response Rate %",
        title="Response Rate by Source",
        text="Response Rate %",
        color="Response Rate %",
        color_continuous_scale="RdYlGn",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(height=380, xaxis_tickangle=-30, yaxis_title="Response Rate (%)")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# CHARTS - Row 3
# ============================================================================
chart_col5, chart_col6 = st.columns(2)

with chart_col5:
    # Day of week pattern
    df_dow = filtered.copy()
    df_dow["Day of Week"] = df_dow["Date Applied"].dt.day_name()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    dow_counts = (
        df_dow.groupby("Day of Week")
        .size()
        .reindex(dow_order, fill_value=0)
        .reset_index(name="Count")
    )
    fig = px.bar(
        dow_counts,
        x="Day of Week",
        y="Count",
        title="Applications by Day of Week",
        text="Count",
        color="Count",
        color_continuous_scale="Blues",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with chart_col6:
    # CV effectiveness
    cv_stats = (
        filtered.groupby("CV Used")
        .agg(Total=("No", "count"),
             Interview=("Status", lambda x: (x == "Interview").sum()),
             Rejected=("Status", lambda x: (x == "Rejected").sum()))
        .reset_index()
    )
    cv_stats["Response Rate %"] = (
        (cv_stats["Interview"] + cv_stats["Rejected"])
        / cv_stats["Total"] * 100
    ).round(1)

    fig = px.bar(
        cv_stats,
        x="CV Used",
        y="Total",
        title="Applications by CV Used",
        text="Total",
        color="Response Rate %",
        color_continuous_scale="Viridis",
        hover_data=["Interview", "Rejected", "Response Rate %"],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# DATA TABLE
# ============================================================================
st.divider()
st.subheader(f"📋 Applications ({len(filtered)} of {len(df)})")

# Format date for display
display_df = filtered.copy()
display_df["Date Applied"] = display_df["Date Applied"].dt.strftime("%d/%m/%Y")

# Status color formatting
def color_status(val):
    color_map = {
        "Applied": "background-color: #dbeafe; color: #1e40af",
        "Interview": "background-color: #d1fae5; color: #065f46",
        "Interview-R": "background-color: #fed7aa; color: #9a3412",
        "Rejected": "background-color: #fee2e2; color: #991b1b",
        "No Response": "background-color: #f3f4f6; color: #374151",
    }
    return color_map.get(val, "")

styled = display_df.style.map(color_status, subset=["Status"])

# Show table
st.dataframe(
    styled,
    use_container_width=True,
    height=500,
    column_config={
        "No": st.column_config.NumberColumn("No", width="small"),
        "Date Applied": st.column_config.TextColumn("Date", width="small"),
        "Job Title": st.column_config.TextColumn("Job Title", width="medium"),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Source": st.column_config.TextColumn("Source", width="small"),
        "CV Used": st.column_config.TextColumn("CV", width="small"),
        "Status": st.column_config.TextColumn("Status", width="small"),
        "Type": st.column_config.TextColumn("Type", width="small"),
        "Days Since Applied": st.column_config.NumberColumn("Days", width="small"),
        "Link": st.column_config.LinkColumn("Link", width="small",
                                            display_text="View"),
    },
    hide_index=True,
)

# ============================================================================
# EXPORT
# ============================================================================
st.divider()
col_dl1, col_dl2 = st.columns([1, 5])
with col_dl1:
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export CSV",
        data=csv,
        file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_dl2:
    st.caption(
        f"Showing **{len(filtered)}** of **{len(df)}** total applications. "
        f"Range: **{start_date.strftime('%d/%m/%Y')}** → **{end_date.strftime('%d/%m/%Y')}**"
    )

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption("🦌 Built with Streamlit • Data source: Google Sheets • Read-only dashboard")
