import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Airport Overview",
    page_icon="✈️",
    layout="wide"
)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data():
    data = supabase.table("flights_airlabs").select("*").execute()
    df = pd.DataFrame(data.data)
    return df

df = load_data()

st.title("✈️ Airport Overview — Vancouver (CYVR)")
st.caption("Operational overview based on live flight & weather data")

# -----------------------------
# CLEANING
# -----------------------------
df["dep_country"] = df["dep_country"].astype(str).str.strip()
df["arr_country"] = df["arr_country"].astype(str).str.strip()

df["dep_icao"] = df["dep_icao"].astype(str)
df["arr_icao"] = df["arr_icao"].astype(str)

df["delay"] = df["arr_delayed"].fillna(0)

# -----------------------------
# DOMESTIC VS INTERNATIONAL
# -----------------------------
df["is_domestic"] = (
    ((df["dep_icao"] == "CYVR") & (df["arr_country"] == "Canada")) |
    ((df["arr_icao"] == "CYVR") & (df["dep_country"] == "Canada"))
)

domestic_pct = round(df["is_domestic"].mean() * 100, 2)
international_pct = round(100 - domestic_pct, 2)

# -----------------------------
# FLIGHTS PER HOUR
# -----------------------------
df["hour"] = pd.to_datetime(df["dep_time"], errors="coerce").dt.floor("H")
avg_flights_per_hour = round(len(df) / df["hour"].nunique(), 2)

# -----------------------------
# ON-TIME
# -----------------------------
on_time_pct = round((df["delay"] <= 15).mean() * 100, 2)

# -----------------------------
# KPI DISPLAY
# -----------------------------
st.subheader("📊 Key Operational Indicators")

k1, k2, k3 = st.columns(3)

k1.metric("✈️ Avg Flights / Hour", avg_flights_per_hour)
k2.metric("🌍 Domestic Flights", f"{domestic_pct:.2f}%")
k3.metric("⏱ On-Time Flights", f"{on_time_pct:.2f}%")

st.divider()

# ============================================================
# GRAPHS
# ============================================================

st.subheader("📈 Traffic & Fleet Overview")

# -----------------------------
# AIRLINES
# -----------------------------
airlines = (
    df["airline_name"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values(ascending=False)
    .head(10)
)

fig_airlines = px.bar(
    airlines.sort_values(),
    orientation="h",
    labels={"value": "Percentage (%)", "index": "Airline"},
    title="Top Airlines (Share of Flights)",
    text=airlines.sort_values().round(2)
)
fig_airlines.update_traces(texttemplate="%{text} %", textposition="outside")
fig_airlines.update_layout(xaxis_title="Percentage (%)")

st.plotly_chart(fig_airlines, use_container_width=True)

# -----------------------------
# AIRCRAFT TYPES
# -----------------------------
aircrafts = (
    df["aircraft_icao"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values(ascending=False)
    .head(10)
)

fig_aircraft = px.bar(
    aircrafts.sort_values(),
    orientation="h",
    labels={"value": "Percentage (%)", "index": "Aircraft Type"},
    title="Most Frequent Aircraft Types",
    text=aircrafts.sort_values().round(2)
)
fig_aircraft.update_traces(texttemplate="%{text} %", textposition="outside")
fig_aircraft.update_layout(xaxis_title="Percentage (%)")

st.plotly_chart(fig_aircraft, use_container_width=True)

# -----------------------------
# DESTINATIONS FROM CYVR
# -----------------------------
destinations = (
    df[df["dep_icao"] == "CYVR"]["arr_country"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values(ascending=False)
    .head(10)
)

fig_dest = px.bar(
    destinations.sort_values(),   # keep visual order
    orientation="h"
)

fig_dest.update_traces(
    text=destinations.sort_values().round(2).astype(str) + " %",
    textposition="outside"
)

fig_dest.update_layout(
    title="Top Destination Countries (Departures from CYVR)",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False,
    hovermode=False   # ✅ disables tooltip completely
)

st.plotly_chart(fig_dest, use_container_width=True)



# -----------------------------
# ORIGINS TO CYVR
# -----------------------------
origins = (
    df[df["arr_icao"] == "CYVR"]["dep_country"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values(ascending=False)
    .head(10)
)

fig_orig = px.bar(
    origins.sort_values(),
    orientation="h"
)

fig_orig.update_traces(
    text=origins.sort_values().round(2).astype(str) + " %",
    textposition="outside"
)

fig_orig.update_layout(
    title="Top Origin Countries (Arrivals to CYVR)",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False,
    hovermode=False   # ✅ suppression définitive de l’infobulle
)

st.plotly_chart(fig_orig, use_container_width=True)

