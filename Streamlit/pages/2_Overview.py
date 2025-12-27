import streamlit as st
import pandas as pd
from supabase import create_client
import os

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(
    page_title="Aviation Overview",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Aviation Traffic Overview")
st.caption("Vancouver International Airport – Data Analytics Dashboard")

# -------------------------------
# SUPABASE
# -------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# LOAD DATA
# -------------------------------
@st.cache_data(ttl=3600)
def load_data():
    data = supabase.table("flights_airlabs") \
        .select("*") \
        .execute()
    return pd.DataFrame(data.data)

df = load_data()

# -------------------------------
# BASIC CLEANING
# -------------------------------
df["is_departure"] = df["dep_icao"] == "CYVR"
df["is_arrival"] = df["arr_icao"] == "CYVR"

df["delay"] = df["arr_delayed"].fillna(0)

# -------------------------------
# KPI SECTION
# -------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("✈️ Total Flights", len(df))

with col2:
    st.metric("🛫 Departures %",
              f"{round(df['is_departure'].mean()*100,1)}%")

with col3:
    st.metric("🛬 Arrivals %",
              f"{round(df['is_arrival'].mean()*100,1)}%")

with col4:
    st.metric("⏱ Avg Delay (min)",
              round(df["delay"].mean(), 1))

st.divider()

# -------------------------------
# TRAFFIC DISTRIBUTION
# -------------------------------
st.subheader("Traffic Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✈️ Top Airlines")
    airline_share = (
        df["airline_name"]
        .value_counts(normalize=True)
        .head(10)
        * 100
    )
    st.bar_chart(airline_share)

with col2:
    st.markdown("### 🛩 Aircraft Types")
    aircraft_share = (
        df["aircraft_icao"]
        .value_counts(normalize=True)
        .head(10)
        * 100
    )
    st.bar_chart(aircraft_share)

# -------------------------------
# DELAYS
# -------------------------------
st.subheader("Operational Performance")

delay_by_airline = (
    df.groupby("airline_name")["delay"]
    .mean()
    .sort_values(ascending=False)
    .head(10)
)

st.markdown("### ⏱ Average Delay by Airline")
st.bar_chart(delay_by_airline)

# -------------------------------
# ROUTES
# -------------------------------
st.subheader("Top Destinations")

top_routes = (
    df["arr_icao"]
    .value_counts(normalize=True)
    .head(10) * 100
)

st.bar_chart(top_routes)

# -------------------------------
# FOOTER
# -------------------------------
st.caption("""
Data source: AirLabs + Open-Meteo  
Updated automatically via GitHub Actions  
Built for data analytics portfolio
""")
