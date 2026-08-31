"""
Handra Job Application Dashboard
Read-only dashboard for Google Sheets "List Lamaran Kerjaan".

Supports two modes:
1. LOCAL DEV: Reuses OAuth token from google-workspace skill
2. STREAMLIT CLOUD: Uses st.secrets for OAuth client config + token.json in repo

SPREADSHEET_ID is read from env var / secrets, never hardcoded.
"""

import json
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from googleapiclient.discovery import build


# ============================================================================
# CONFIG
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
# OAUTH
# ============================================================================
def get_credentials():
    """Get Google OAuth credentials for Streamlit Cloud or local dev."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_info = None
    try:
        if "google_token" in st.secrets:
            token_info = json.loads(st.secrets["google_token"])
    except Exception as e:
        if not os.path.exists(r"C:\Users"):
            st.error(
                f"Failed to load Google credentials from secrets.\n\n"
                f"Error: `{e}`\n\n"
                f"Please configure `google_token` in Streamlit Cloud Secrets. "
                f"See DEPLOY.md for the format."
            )
            st.stop()

    if token_info is None:
        token_path = r"C:\Users\Handra\AppData\Local\hermes\google_token.json"
        try:
            with open(token_path, encoding="utf-8") as f:
                token_info = json.load(f)
        except Exception as e:
            st.error(
                f"Failed to load Google credentials.\n\n"
                f"Local token error: `{e}`\n\n"
                f"Make sure `google_token` is set in Streamlit Cloud Secrets, "
                f"or the local Hermes token exists at `{token_path}`."
            )
            st.stop()

    scopes = token_info.get("scopes") or [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_authorized_user_info(token_info, scopes)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


SHEET_NAME = "Sheet1"
DATA_START_ROW = 6
STATUS_ORDER = ["Applied", "Interview", "Interview-R", "No Response", "Rejected"]
STATUS_COLORS = {
    "Applied": "#2563eb",
    "Interview": "#059669",
    "Interview-R": "#d97706",
    "Rejected": "#dc2626",
    "No Response": "#6b7280",
}

st.set_page_config(
    page_title="Job Application Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data(ttl=300)
def load_data():
    """Read all data from Google Sheets."""
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        st.error("SPREADSHEET_ID not configured. Set it in Streamlit secrets or an environment variable.")
        st.stop()

    service = build("sheets", "v4", credentials=get_credentials())
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A{DATA_START_ROW}:I200",
    ).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()

    columns = ["No", "Date Applied", "Job Title", "Company", "Source", "CV Used", "Status", "Type", "Link"]
    df = pd.DataFrame(values, columns=columns)
    df["Date Applied"] = pd.to_datetime(df["Date Applied"], format="%d/%m/%Y", errors="coerce")
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
    df = df.dropna(subset=["Date Applied", "No"]).copy()
    df["No"] = df["No"].astype(int)
    df["Days Since Applied"] = (datetime.now() - df["Date Applied"]).dt.days
    df["Week"] = df["Date Applied"].dt.to_period("W").dt.start_time
    df["Month"] = df["Date Applied"].dt.to_period("M").astype(str)
    return df


def pct(part, total):
    return (part / total * 100) if total else 0


def count_status(data, status):
    return int((data["Status"] == status).sum()) if not data.empty else 0


def response_rows(data):
    return data[data["Status"].isin(["Interview", "Rejected", "Interview-R"])]


def explain(label, value):
    st.caption(f"{label}: {value}")


def tune(fig, height=390):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=40),
        legend_title_text="",
        hovermode="closest",
    )
    return fig


# ============================================================================
# UI
# ============================================================================
st.title("Handra Job Application Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%d %B %Y, %H:%M')} | Auto-refresh every 5 minutes")

with st.spinner("Loading data from Google Sheets..."):
    df = load_data()

if df.empty:
    st.error("No data found. Check your spreadsheet.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    all_sources = sorted(df["Source"].dropna().unique().tolist())
    all_statuses = sorted(df["Status"].dropna().unique().tolist())
    all_statuses = [s for s in STATUS_ORDER if s in all_statuses] + [s for s in all_statuses if s not in STATUS_ORDER]
    all_cvs = sorted(df["CV Used"].dropna().unique().tolist())
    all_types = sorted(df["Type"].dropna().unique().tolist())

    selected_sources = st.multiselect("Source", all_sources, default=all_sources)
    selected_statuses = st.multiselect("Status", all_statuses, default=all_statuses)
    selected_cvs = st.multiselect("CV Used", all_cvs, default=all_cvs)
    selected_types = st.multiselect("Type", all_types, default=all_types)

    min_date = df["Date Applied"].min().date()
    max_date = df["Date Applied"].max().date()
    date_range = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    start_date, end_date = date_range if len(date_range) == 2 else (min_date, max_date)

    st.divider()
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

filtered = df[
    df["Source"].isin(selected_sources)
    & df["Status"].isin(selected_statuses)
    & df["CV Used"].isin(selected_cvs)
    & df["Type"].isin(selected_types)
    & (df["Date Applied"].dt.date >= start_date)
    & (df["Date Applied"].dt.date <= end_date)
].copy()

# ============================================================================
# TOP METRICS
# ============================================================================
st.divider()
total = len(filtered)
applied = count_status(filtered, "Applied")
interview = count_status(filtered, "Interview")
interview_r = count_status(filtered, "Interview-R")
rejected = count_status(filtered, "Rejected")
no_response = count_status(filtered, "No Response")
responded = len(response_rows(filtered))
active_days = max((end_date - start_date).days + 1, 1)
per_week = total / active_days * 7
avg_age = filtered["Days Since Applied"].mean() if total else 0

cols = st.columns(6)
cols[0].metric("Total", total)
cols[1].metric("Applied", applied, help="Lamaran yang masih menunggu progres berikutnya.")
cols[2].metric("Interview", interview, delta=f"{pct(interview, total):.1f}%" if total else "0%")
cols[3].metric("Rejected", rejected)
cols[4].metric("No Response", no_response, help="Lamaran tanpa respons pada data yang sedang difilter.")
cols[5].metric("Response Rate", f"{pct(responded, total):.1f}%", help="Interview + Interview-R + Rejected / Total")

with st.expander("Ringkasan data terfilter", expanded=True):
    best_source = "-"
    if total:
        source_total = filtered["Source"].value_counts()
        best_source = f"{source_total.index[0]} ({source_total.iloc[0]} lamaran)"
    st.write(
        f"Periode ini berisi **{total}** lamaran dari **{start_date.strftime('%d/%m/%Y')}** "
        f"sampai **{end_date.strftime('%d/%m/%Y')}**. Rata-rata pengiriman adalah "
        f"**{per_week:.1f} lamaran per minggu**. Sumber paling banyak dipakai: **{best_source}**. "
        f"Umur rata-rata lamaran: **{avg_age:.1f} hari**."
    )

# ============================================================================
# CHARTS
# ============================================================================
st.divider()
st.subheader("Overview")
tab_overview, tab_channels, tab_timing, tab_aging = st.tabs([
    "Status and Funnel",
    "Sources, CV, and Type",
    "Time Pattern",
    "Aging and Follow-up",
])

with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        status_counts = filtered["Status"].value_counts().reindex(STATUS_ORDER).dropna().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig = px.pie(
            status_counts,
            values="Count",
            names="Status",
            title="Status Distribution",
            hole=0.45,
            color="Status",
            color_discrete_map=STATUS_COLORS,
        )
        fig.update_traces(textinfo="label+percent", hovertemplate="%{label}<br>%{value} lamaran<br>%{percent}<extra></extra>")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Menunjukkan komposisi status. Porsi Applied dan No Response yang tinggi berarti banyak lamaran masih menunggu tindak lanjut.")
    with c2:
        funnel = pd.DataFrame({
            "Stage": ["Submitted", "Responded", "Interview", "Closed"],
            "Count": [total, responded, interview, rejected + interview_r],
        })
        fig = go.Figure(go.Funnel(y=funnel["Stage"], x=funnel["Count"], textinfo="value+percent initial"))
        fig.update_layout(title="Application Funnel")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Funnel memperlihatkan penyusutan dari lamaran terkirim ke respons, interview, dan status tertutup.")

with tab_channels:
    c1, c2 = st.columns(2)
    with c1:
        source_status = filtered.groupby(["Source", "Status"]).size().reset_index(name="Count")
        fig = px.bar(
            source_status,
            x="Source",
            y="Count",
            color="Status",
            title="Applications by Source and Status",
            color_discrete_map=STATUS_COLORS,
            text="Count",
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Bandingkan volume dan hasil tiap sumber. Sumber dengan banyak lamaran tetapi sedikit respons perlu dievaluasi.")
    with c2:
        source_stats = filtered.groupby("Source").agg(
            Total=("No", "count"),
            Interview=("Status", lambda x: (x == "Interview").sum()),
            Responded=("Status", lambda x: x.isin(["Interview", "Interview-R", "Rejected"]).sum()),
        ).reset_index()
        source_stats["Response Rate %"] = source_stats.apply(lambda r: pct(r["Responded"], r["Total"]), axis=1).round(1)
        source_stats["Interview Rate %"] = source_stats.apply(lambda r: pct(r["Interview"], r["Total"]), axis=1).round(1)
        source_stats = source_stats.sort_values(["Response Rate %", "Total"], ascending=False)
        fig = px.scatter(
            source_stats,
            x="Total",
            y="Response Rate %",
            size="Interview" if source_stats["Interview"].sum() else "Total",
            color="Interview Rate %",
            hover_name="Source",
            title="Source Quality: Volume vs Response Rate",
            color_continuous_scale="YlGnBu",
        )
        fig.update_layout(xaxis_title="Total Applications", yaxis_title="Response Rate (%)")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Titik kanan berarti volume tinggi. Titik atas berarti respons lebih baik. Prioritaskan sumber yang berada kanan-atas.")

    c3, c4 = st.columns(2)
    with c3:
        cv_stats = filtered.groupby("CV Used").agg(
            Total=("No", "count"),
            Interview=("Status", lambda x: (x == "Interview").sum()),
            Responded=("Status", lambda x: x.isin(["Interview", "Interview-R", "Rejected"]).sum()),
        ).reset_index()
        cv_stats["Response Rate %"] = cv_stats.apply(lambda r: pct(r["Responded"], r["Total"]), axis=1).round(1)
        fig = px.bar(
            cv_stats,
            x="CV Used",
            y="Total",
            color="Response Rate %",
            text="Total",
            title="CV Usage and Response Rate",
            hover_data=["Interview", "Responded", "Response Rate %"],
            color_continuous_scale="Viridis",
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Warna menunjukkan response rate, sedangkan tinggi bar menunjukkan jumlah pemakaian CV.")
    with c4:
        type_source = filtered.groupby(["Type", "Source"]).size().reset_index(name="Count")
        fig = px.treemap(type_source, path=["Type", "Source"], values="Count", title="Role Type by Source")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Treemap memperlihatkan kombinasi jenis role dan sumber yang paling dominan.")

with tab_timing:
    c1, c2 = st.columns(2)
    with c1:
        daily = filtered.groupby("Date Applied").size().reset_index(name="Count").sort_values("Date Applied")
        daily["7-Day Average"] = daily["Count"].rolling(7, min_periods=1).mean()
        fig = go.Figure()
        fig.add_bar(x=daily["Date Applied"], y=daily["Count"], name="Daily applications", marker_color="#93c5fd")
        fig.add_trace(go.Scatter(x=daily["Date Applied"], y=daily["7-Day Average"], name="7-day average", line=dict(color="#1d4ed8", width=3)))
        fig.update_layout(title="Applications Over Time", xaxis_title="Date", yaxis_title="Applications")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Bar menunjukkan jumlah harian. Garis rata-rata 7 hari membantu melihat tren tanpa terlalu terpengaruh lonjakan satu hari.")
    with c2:
        weekly_status = filtered.groupby(["Week", "Status"]).size().reset_index(name="Count")
        fig = px.area(
            weekly_status,
            x="Week",
            y="Count",
            color="Status",
            title="Weekly Status Mix",
            color_discrete_map=STATUS_COLORS,
        )
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Area mingguan menunjukkan perubahan campuran status dari waktu ke waktu.")

    c3, c4 = st.columns(2)
    with c3:
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow = filtered.assign(**{"Day of Week": filtered["Date Applied"].dt.day_name()})
        dow_counts = dow.groupby("Day of Week").size().reindex(dow_order, fill_value=0).reset_index(name="Count")
        fig = px.bar(dow_counts, x="Day of Week", y="Count", text="Count", title="Applications by Day of Week", color="Count", color_continuous_scale="Blues")
        fig.update_traces(textposition="outside")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Memperlihatkan hari paling aktif untuk mengirim lamaran.")
    with c4:
        heat = filtered.assign(Weekday=filtered["Date Applied"].dt.day_name(), Month=filtered["Month"])
        heat = heat.groupby(["Month", "Weekday"]).size().reset_index(name="Count")
        fig = px.density_heatmap(heat, x="Weekday", y="Month", z="Count", category_orders={"Weekday": dow_order}, title="Monthly Activity Heatmap", color_continuous_scale="Blues")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Heatmap membantu melihat bulan dan hari yang paling padat aktivitas lamaran.")

with tab_aging:
    c1, c2 = st.columns(2)
    with c1:
        bins = [-1, 7, 14, 30, 60, 9999]
        labels = ["0-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
        aging = filtered.copy()
        aging["Age Bucket"] = pd.cut(aging["Days Since Applied"], bins=bins, labels=labels)
        age_status = aging.groupby(["Age Bucket", "Status"], observed=False).size().reset_index(name="Count")
        fig = px.bar(age_status, x="Age Bucket", y="Count", color="Status", title="Application Aging by Status", color_discrete_map=STATUS_COLORS, text="Count")
        fig.update_traces(textposition="inside")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Bucket umur membantu menentukan lamaran mana yang sudah cukup lama untuk dipantau atau ditindaklanjuti.")
    with c2:
        follow_up = filtered[filtered["Status"].isin(["Applied", "No Response"])].sort_values("Days Since Applied", ascending=False).head(15)
        fig = px.bar(
            follow_up,
            x="Days Since Applied",
            y="Company",
            color="Status",
            orientation="h",
            title="Oldest Open Applications",
            hover_data=["Job Title", "Source", "Date Applied"],
            color_discrete_map=STATUS_COLORS,
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Days Since Applied")
        st.plotly_chart(tune(fig), use_container_width=True)
        explain("Keterangan", "Daftar ini mengurutkan lamaran terbuka paling lama, berguna untuk prioritas follow-up.")

    st.subheader("Detailed Follow-up Candidates")
    detail_cols = ["Date Applied", "Company", "Job Title", "Source", "CV Used", "Status", "Days Since Applied", "Link"]
    follow_display = follow_up[detail_cols].copy()
    follow_display["Date Applied"] = follow_display["Date Applied"].dt.strftime("%d/%m/%Y")
    st.dataframe(follow_display, use_container_width=True, hide_index=True)

# ============================================================================
# DATA TABLE
# ============================================================================
st.divider()
st.subheader(f"Applications ({len(filtered)} of {len(df)})")

display_df = filtered.copy()
display_df["Date Applied"] = display_df["Date Applied"].dt.strftime("%d/%m/%Y")


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
        "Link": st.column_config.LinkColumn("Link", width="small", display_text="View"),
    },
    hide_index=True,
)

st.divider()
col_dl1, col_dl2 = st.columns([1, 5])
with col_dl1:
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Export CSV",
        data=csv,
        file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_dl2:
    st.caption(
        f"Showing **{len(filtered)}** of **{len(df)}** total applications. "
        f"Range: **{start_date.strftime('%d/%m/%Y')}** to **{end_date.strftime('%d/%m/%Y')}**"
    )

st.divider()
st.caption("Built with Streamlit | Data source: Google Sheets | Read-only dashboard")
