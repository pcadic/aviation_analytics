import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os

# ============================
# CONFIG
# ============================
st.set_page_config(page_title="Operational Insights", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select("*")
        .execute()
    )
    return response.data

df = pd.DataFrame(load_data())

# ============================
# CLEANING
# ============================
df["dep_delayed"] = df["dep_delayed"].fillna(0)
df["arr_delayed"] = df["arr_delayed"].fillna(0)

df["hour_dep"] = pd.to_datetime(df["scheduled_departure"], errors="coerce").dt.hour
df["hour_arr"] = pd.to_datetime(df["scheduled_arrival"], errors="coerce").dt.hour

df["is_departure"] = df["dep_icao"] == "CYVR"
df["is_arrival"] = df["arr_icao"] == "CYVR"

# ============================
# PAGE TITLE
# ============================
st.title("✈️ Operational Insights – Vancouver International Airport")
st.markdown("Operational performance analysis based on real flight activity data.")

# ============================
# SECTION 1 — TRAFFIC
# ============================
st.subheader("🕒 Traffic Load")

traffic_hourly = (
    pd.concat([
        df[df["is_departure"]]["hour_dep"],
        df[df["is_arrival"]]["hour_arr"]
    ])
    .value_counts()
    .sort_index()
)

fig_traffic = px.bar(
    traffic_hourly,
    labels={"value": "Average Flights", "index": "Hour of Day"},
    title="Average Number of Flights per Hour"
)

st.plotly_chart(fig_traffic, use_container_width=True)

# ============================
# SECTION 2 — ON-TIME PERFORMANCE
# ============================
st.subheader("⏱ On-Time Performance")

df["effective_delay"] = df.apply(
    lambda x: x["arr_delayed"] if x["is_arrival"] else x["dep_delayed"],
    axis=1
)

on_time_pct = round((df["effective_delay"] <= 15).mean() * 100, 2)
avg_delay = round(df["effective_delay"].mean(), 2)

col1, col2 = st.columns(2)
col1.metric("On-Time Flights (%)", f"{on_time_pct}%")
col2.metric("Average Delay (min)", avg_delay)

# ============================
# SECTION 3 — AIRLINE PERFORMANCE
# ============================
st.subheader("✈️ Airline Performance")

airline_perf = (
    df[df["airline_name"].notna()]
    .groupby("airline_name")["effective_delay"]
    .agg(
        avg_delay="mean",
        on_time_rate=lambda x: (x <= 15).mean() * 100
    )
    .sort_values("on_time_rate", ascending=False)
    .head(10)
)

fig_airline = px.bar(
    airline_perf.sort_values("on_time_rate"),
    x="on_time_rate",
    y=airline_perf.sort_values("on_time_rate").index,
    orientation="h",
    title="Top Airlines by On-Time Performance",
    labels={"x": "On-Time Rate (%)", "y": ""}
)

fig_airline.update_layout(showlegend=False)
st.plotly_chart(fig_airline, use_container_width=True)

# ============================
# SECTION 4 — AIRCRAFT TYPES
# ============================
st.subheader("🛩 Aircraft Types")

aircrafts = (
    df["aircraft_icao"]
    .dropna()
    .value_counts(normalize=True)
    .mul(100)
    .head(10)
)

fig_aircraft = px.bar(
    aircrafts.sort_values(),
    orientation="h",
    labels={"value": "Percentage (%)", "index": "Aircraft Type"},
    title="Most Common Aircraft Types"
)

fig_aircraft.update_layout(showlegend=False)
st.plotly_chart(fig_aircraft, use_container_width=True)

# ============================
# SECTION 5 — INSIGHTS
# ============================
st.subheader("📌 Operational Insights")

st.markdown("""
- Traffic peaks occur during morning and late afternoon hours, indicating commuter and long-haul waves.
- On-time performance remains generally high, with delays concentrated during peak periods.
- A small number of airlines represent the majority of flights.
- Aircraft usage is dominated by short and medium-haul models, consistent with regional and North American traffic.
- These indicators suggest optimization opportunities in ground operations during peak hours.
""")
