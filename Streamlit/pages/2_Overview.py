import streamlit as st
import pandas as pd
from supabase import create_client
import os

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Aviation Overview",
    page_icon="✈️",
    layout="wide"
)

st.markdown("""
<style>
    h1 { font-size: 2.2rem; }
    h2 { margin-top: 2rem; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Aviation Traffic Overview")
st.caption("Vancouver International Airport — Data Analytics Dashboard")

# --------------------------------------------------
# SUPABASE CONNECTION
# --------------------------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data(ttl=3600)
def load_data():
    res = supabase.table("flights_airlabs").select("*").execute()
    return pd.DataFrame(res.data)

df = load_data()

if df.empty:
    st.warning("No data available yet.")
    st.stop()

df.columns = df.columns.str.lower()

# --------------------------------------------------
# FEATURE ENGINEERING
# --------------------------------------------------
df["dep_time"] = pd.to_datetime(df.get("dep_time"), errors="coerce")
df["hour"] = df["dep_time"].dt.floor("H")

df["is_departure"] = df.get("dep_icao", "") == "CYVR"
df["is_arrival"] = df.get("arr_icao", "") == "CYVR"

df["delay"] = df.get("arr_delayed", 0).fillna(0)

df["is_domestic"] = (
    (df.get("dep_country") == "Canada") |
    (df.get("arr_country") == "Canada")
)

# --------------------------------------------------
# KPI CALCULATION
# --------------------------------------------------
hours_covered = df["hour"].nunique()
avg_flights_per_hour = round(len(df) / hours_covered, 2) if hours_covered else 0

domestic_pct = round(df["is_domestic"].mean() * 100, 1)
on_time_pct = round((df["delay"] <= 15).mean() * 100, 1)

# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------
st.subheader("📊 Key Performance Indicators")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("✈️ Avg Flights / Hour", avg_flights_per_hour)

with col2:
    st.metric("🌍 Domestic Flights", f"{domestic_pct}%")

with col3:
    st.metric("⏱ On-Time Flights", f"{on_time_pct}%")

st.divider()

# --------------------------------------------------
# TRAFFIC OVERVIEW
# --------------------------------------------------
st.subheader("✈️ Traffic Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Top Airlines")
    if "airline_name" in df.columns:
        airlines = (
            df["airline_name"]
            .value_counts(normalize=True)
            .head(10)
            .sort_values(ascending=True) * 100
        )
        st.bar_chart(airlines)
    else:
        st.info("Airline data not available.")

with col2:
    st.markdown("### Aircraft Types")
    if "aircraft_icao" in df.columns:
        aircrafts = (
            df["aircraft_icao"]
            .value_counts(normalize=True)
            .head(10)
            .sort_values(ascending=True) * 100
        )
        st.bar_chart(aircrafts)
    else:
        st.info("Aircraft data not available.")

# --------------------------------------------------
# ROUTES ANALYSIS
# --------------------------------------------------
st.subheader("🌍 Route Distribution")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Destination Countries (Departures)")
    if "arr_country" in df.columns:
        dest = (
            df[df["dep_icao"] == "CYVR"]["arr_country"]
            .value_counts(normalize=True)
            .head(10)
            .sort_values(ascending=True) * 100
        )
        st.bar_chart(dest)
    else:
        st.info("No destination data.")

with col2:
    st.markdown("### Origin Countries (Arrivals)")
    if "dep_country" in df.columns:
        origin = (
            df[df["arr_icao"] == "CYVR"]["dep_country"]
            .value_counts(normalize=True)
            .head(10)
            .sort_values(ascending=True) * 100
        )
        st.bar_chart(origin)
    else:
        st.info("No origin data.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.caption("""
Data source: AirLabs & Open-Meteo  
Automated ETL via GitHub Actions  
Portfolio Project – Aviation Analytics
""")
