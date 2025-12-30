import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Operational Insights",
    page_icon="🛫",
    layout="wide"
)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOAD DATA (FROM VIEW)
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
df["dep_time_utc"] = pd.to_datetime(df["dep_time_utc"])
df["arr_time_utc"] = pd.to_datetime(df["arr_time_utc"])

df["dep_delay"] = df["dep_delayed"].fillna(0)
df["arr_delay"] = df["arr_delayed"].fillna(0)

# Determine if arrival or departure at CYVR
df["is_departure"] = df["dep_icao"] == "CYVR"
df["is_arrival"] = df["arr_icao"] == "CYVR"

# Unified delay metric
df["delay"] = df.apply(
    lambda r: r["dep_delay"] if r["is_departure"] else r["arr_delay"],
    axis=1
)

# ============================
# PAGE TITLE
# ============================
st.title("✈️ Operational Insights")
st.caption("Operational performance analysis based on real flight data")

# ============================
# KPI SECTION
# ============================
col1, col2, col3 = st.columns(3)

avg_delay = round(df["delay"].mean(), 1)
on_time_pct = round((df["delay"] <= 15).mean() * 100, 1)
flights_per_hour = round(
    len(df) / df["dep_time_utc"].dt.date.nunique() / 24, 2
)

col1.metric("Average Delay", f"{avg_delay} min")
col2.metric("On-Time Flights", f"{on_time_pct} %")
col3.metric("Avg Flights / Hour", flights_per_hour)

# ============================
# DELAY BY AIRLINE
# ============================
st.subheader("Average Delay by Airline")

airline_delay = (
    df.dropna(subset=["airline_name"])
      .groupby("airline_name")["delay"]
      .mean()
      .sort_values(ascending=False)
      .head(10)
)

fig_airline = px.bar(
    airline_delay.sort_values(),
    orientation="h",
    title="Average Delay per Airline (min)",
)

fig_airline.update_layout(
    xaxis_title="Delay (minutes)",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_airline, use_container_width=True)

# ============================
# HOURLY TRAFFIC
# ============================
st.subheader("Hourly Traffic Load")

df["hour"] = df["dep_time_utc"].dt.hour

hourly = (
    df.groupby("hour")
      .size()
      .reset_index(name="flights")
)

fig_hour = px.line(
    hourly,
    x="hour",
    y="flights",
    markers=True,
    title="Flights per Hour (Arrivals + Departures)"
)

fig_hour.update_layout(
    xaxis_title="Hour of Day",
    yaxis_title="Number of Flights"
)

st.plotly_chart(fig_hour, use_container_width=True)

# ============================
# DELAY DISTRIBUTION
# ============================
st.subheader("Delay Distribution")

fig_dist = px.histogram(
    df,
    x="delay",
    nbins=40,
    title="Distribution of Flight Delays (minutes)"
)

fig_dist.update_layout(
    xaxis_title="Delay (minutes)",
    yaxis_title="Number of Flights"
)

st.plotly_chart(fig_dist, use_container_width=True)

# ============================
# FOOTER
# ============================
st.caption("Data source: AirLabs + Open-Meteo | Processed via Supabase")
