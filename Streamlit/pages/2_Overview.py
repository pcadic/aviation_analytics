import streamlit as st
import pandas as pd
from supabase import create_client
import os

st.set_page_config(
    page_title="Aviation Overview",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Aviation Traffic Overview")
st.caption("Vancouver International Airport – Data Analytics Dashboard")

# -----------------------------------
# SUPABASE
# -----------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------
# LOAD DATA
# -----------------------------------
@st.cache_data(ttl=3600)
def load_data():
    res = supabase.table("flights_airlabs").select("*").execute()
    return pd.DataFrame(res.data)

df = load_data()

# -----------------------------------
# SAFETY CHECK
# -----------------------------------
st.write("Columns:", df.columns.tolist())
st.write("Rows:", len(df))
st.dataframe(df.head())

if df.empty:
    st.warning("No data available yet.")
    st.stop()

# Normalize column names (safety)
df.columns = df.columns.str.lower()

# -----------------------------------
# SAFE FEATURE ENGINEERING
# -----------------------------------
if "dep_icao" in df.columns:
    df["is_departure"] = df["dep_icao"] == "CYVR"
else:
    df["is_departure"] = False

if "arr_icao" in df.columns:
    df["is_arrival"] = df["arr_icao"] == "CYVR"
else:
    df["is_arrival"] = False

if "arr_delayed" in df.columns:
    df["delay"] = df["arr_delayed"].fillna(0)
else:
    df["delay"] = 0

# -----------------------------------
# KPI SECTION
# -----------------------------------
st.subheader("📊 Key Metrics")

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

# -----------------------------------
# TRAFFIC OVERVIEW
# -----------------------------------
st.subheader("Traffic Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✈️ Top Airlines")
    if "airline_name" in df.columns:
        airline_share = (
            df["airline_name"]
            .value_counts(normalize=True)
            .head(10) * 100
        )
        st.bar_chart(airline_share)
    else:
        st.info("Airline data not available yet.")

with col2:
    st.markdown("### 🛩 Aircraft Types")
    if "aircraft_icao" in df.columns:
        aircraft_share = (
            df["aircraft_icao"]
            .value_counts(normalize=True)
            .head(10) * 100
        )
        st.bar_chart(aircraft_share)
    else:
        st.info("Aircraft data not available yet.")

# -----------------------------------
# DELAYS
# -----------------------------------
st.subheader("Operational Performance")

if "airline_name" in df.columns:
    delay_by_airline = (
        df.groupby("airline_name")["delay"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
    )
    st.bar_chart(delay_by_airline)
else:
    st.info("Delay analysis not available.")

# -----------------------------------
# ROUTES
# -----------------------------------
st.subheader("Top Destinations")

if "arr_icao" in df.columns:
    top_routes = (
        df["arr_icao"]
        .value_counts(normalize=True)
        .head(10) * 100
    )
    st.bar_chart(top_routes)
else:
    st.info("Destination data not available.")

st.caption("""
Data source: AirLabs + Open-Meteo  
Automated pipeline – GitHub Actions  
Portfolio project – Aviation Analytics
""")
