import streamlit as st
import pandas as pd
import plotly.express as px

import os
from supabase import create_client
import streamlit as st


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select("*")
        .execute()
    )
    return pd.DataFrame(response.data)

df = load_data()

# =========================
# BASIC CLEANING
# =========================
df = df.copy()

# Drop rows without airport references
df = df.dropna(subset=[
    "dep_icao",
    "arr_icao",
    "dep_country_ref",
    "arr_country_ref"
])

# =========================
# KPI — DOMESTIC vs INTERNATIONAL
# =========================
df["is_domestic"] = (
    (df["dep_country_ref"] == "Canada") &
    (df["arr_country_ref"] == "Canada")
)

domestic_pct = round(df["is_domestic"].mean() * 100, 2)
international_pct = round(100 - domestic_pct, 2)

# =========================
# KPI — AVERAGE TRAFFIC PER HOUR
# =========================

# Arrivals
arrivals = df[df["arr_icao"] == "CYVR"][["arr_time_utc"]].rename(
    columns={"arr_time_utc": "time"}
)

# Departures
departures = df[df["dep_icao"] == "CYVR"][["dep_time_utc"]].rename(
    columns={"dep_time_utc": "time"}
)

traffic = pd.concat([arrivals, departures])
traffic["hour"] = pd.to_datetime(traffic["time"]).dt.hour

avg_flights_per_hour = round(
    traffic["hour"].value_counts().mean(),
    2
)

# =========================
# KPI — ON TIME FLIGHTS
# =========================

df["effective_delay"] = df.apply(
    lambda r: r["arr_delayed"] if r["arr_icao"] == "CYVR" else r["dep_delayed"],
    axis=1
)

df["effective_delay"] = df["effective_delay"].fillna(0)

on_time_pct = round(
    (df["effective_delay"] <= 15).mean() * 100,
    2
)

# =========================
# KPI DISPLAY
# =========================

col1, col2, col3 = st.columns(3)

col1.metric("Avg aircraft movements / hour", avg_flights_per_hour)
col2.metric("Domestic flights (%)", f"{domestic_pct}%")
col3.metric("On-time flights (%)", f"{on_time_pct}%")

st.divider()

# =========================
# ORIGINS → CYVR
# =========================
origins = (
    df[df["arr_icao"] == "CYVR"]["dep_country_ref"]
    .dropna()
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

fig_orig = px.bar(
    origins,
    orientation="h",
)

fig_orig.update_traces(
    text=origins.round(2),
    texttemplate="%{text} %",
    hoverinfo="skip"
)

fig_orig.update_layout(
    title="Top Origin Countries (Arrivals to CYVR)",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_orig, width="stretch")

# =========================
# DESTINATIONS FROM CYVR
# =========================
destinations = (
    df[df["dep_icao"] == "CYVR"]["arr_country_ref"]
    .dropna()
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

fig_dest = px.bar(
    destinations,
    orientation="h",
)

fig_dest.update_traces(
    text=destinations.round(2),
    texttemplate="%{text} %",
    hoverinfo="skip"
)

fig_dest.update_layout(
    title="Top Destination Countries (Departures from CYVR)",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_dest, width="stretch")

# =========================
# AIRCRAFT TYPES
# =========================
aircrafts = (
    df["aircraft_icao"]
    .dropna()
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

fig_aircraft = px.bar(
    aircrafts,
    orientation="h"
)

fig_aircraft.update_traces(
    text=aircrafts.round(2),
    texttemplate="%{text} %",
    hoverinfo="skip"
)

fig_aircraft.update_layout(
    title="Most Common Aircraft Types",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_aircraft, width="stretch")

# =========================
# AIRLINES
# =========================
airlines = (
    df["airline_name"]
    .dropna()
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

fig_airlines = px.bar(
    airlines,
    orientation="h"
)

fig_airlines.update_traces(
    text=airlines.round(2),
    texttemplate="%{text} %",
    hoverinfo="skip"
)

fig_airlines.update_layout(
    title="Top Airlines",
    xaxis_title="Percentage (%)",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_airlines, width="stretch")
