import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    res = supabase.table("v_flights_enriched").select("*").execute()
    return pd.DataFrame(res.data)

df = load_data()

st.title("✈️ Overview")

if df.empty:
    st.warning("No data available.")
    st.stop()

# =========================
# BASIC CLEANING
# =========================
df = df.dropna(subset=["dep_icao", "arr_icao", "dep_country_ref", "arr_country_ref"])

# Estimated passengers (robuste aux NULL)
df["ac_min_pax"] = df["ac_min_pax"].fillna(0)
df["ac_max_pax"] = df["ac_max_pax"].fillna(0)
df["avg_pax"] = (df["ac_min_pax"] + df["ac_max_pax"]) / 2
df.loc[df["avg_pax"] == 0, "avg_pax"] = pd.NA

# =========================
# KPI — DOMESTIC VS INTL
# =========================
df["is_domestic"] = (
    (df["dep_country_ref"] == "Canada")
    & (df["arr_country_ref"] == "Canada")
)

domestic_pct = round(df["is_domestic"].mean() * 100, 1) if not df.empty else 0
international_pct = round(100 - domestic_pct, 1)

# =========================
# KPI — TRAFFIC PER HOUR
# =========================
traffic = pd.concat(
    [
        df[df["arr_icao"] == "CYVR"][["arr_time_utc"]].rename(columns={"arr_time_utc": "time"}),
        df[df["dep_icao"] == "CYVR"][["dep_time_utc"]].rename(columns={"dep_time_utc": "time"}),
    ]
)

traffic["time"] = pd.to_datetime(traffic["time"], errors="coerce")
traffic = traffic.dropna(subset=["time"])
traffic["hour"] = traffic["time"].dt.hour

avg_flights_per_hour = (
    round(traffic.groupby("hour").size().mean(), 2)
    if not traffic.empty
    else 0
)

# =========================
# KPI — ON TIME
# =========================
df["effective_delay"] = df.apply(
    lambda r: r["arr_delayed"] if r["arr_icao"] == "CYVR" else r["dep_delayed"],
    axis=1,
)

df["effective_delay"] = df["effective_delay"].fillna(0)
on_time_pct = round((df["effective_delay"] <= 15).mean() * 100, 1)

# =========================
# KPI — PASSENGERS
# =========================
avg_pax_per_flight = round(df["avg_pax"].mean(), 0) if df["avg_pax"].notna().any() else 0

# =========================
# FLIGHT DURATION BUCKETS
# =========================
df_duration = df.dropna(subset=["duration"]).copy()

df_duration["flight_type"] = pd.cut(
    df_duration["duration"],
    bins=[0, 120, 300, 10_000],
    labels=[
        "Short-haul (<2h)",
        "Medium-haul (2–5h)",
        "Long-haul (>5h)",
    ],
)

duration_pct = (
    df_duration["flight_type"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
)

# =========================
# KPI DISPLAY
# =========================
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Avg flights / hour", avg_flights_per_hour)
c2.metric("Domestic flights", f"{domestic_pct}%")
c3.metric("On-time flights", f"{on_time_pct}%")
c4.metric("Short-haul flights", f"{duration_pct.get('Short-haul (<2h)', 0)} %")
c5.metric("Medium-haul flights", f"{duration_pct.get('Medium-haul (2–5h)', 0)} %")
c6.metric("Long-haul flights", f"{duration_pct.get('Long-haul (>5h)', 0)} %")

st.divider()

# =========================
# ORIGINS
# =========================
origins = (
    df[df["arr_icao"] == "CYVR"]["dep_country_ref"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

if not origins.empty:
    fig_orig = px.bar(
        origins,
        orientation="h",
        title="Top Origin Countries (Arrivals)",
    )
    fig_orig.update_traces(
        text=origins.round(2),
        texttemplate="%{text} %",
        hoverinfo="skip",
    )
    fig_orig.update_layout(
        xaxis_title="Percentage (%)",
        yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig_orig, width="stretch")

# =========================
# DESTINATIONS
# =========================
destinations = (
    df[df["dep_icao"] == "CYVR"]["arr_country_ref"]
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
    .tail(10)
)

if not destinations.empty:
    fig_dest = px.bar(
        destinations,
        orientation="h",
        title="Top Destination Countries (Departures)",
    )
    fig_dest.update_traces(
        text=destinations.round(2),
        texttemplate="%{text} %",
        hoverinfo="skip",
    )
    fig_dest.update_layout(
        xaxis_title="Percentage (%)",
        yaxis_title="",
        showlegend=False,
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

if not aircrafts.empty:
    fig_aircraft = px.bar(
        aircrafts,
        orientation="h",
        title="Most Common Aircraft Types",
    )
    fig_aircraft.update_traces(
        text=aircrafts.round(2),
        texttemplate="%{text} %",
        hoverinfo="skip",
    )
    fig_aircraft.update_layout(
        xaxis_title="Percentage (%)",
        yaxis_title="",
        showlegend=False,
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

if not airlines.empty:
    fig_airlines = px.bar(
        airlines,
        orientation="h",
        title="Top Airlines",
    )
    fig_airlines.update_traces(
        text=airlines.round(2),
        texttemplate="%{text} %",
        hoverinfo="skip",
    )
    fig_airlines.update_layout(
        xaxis_title="Percentage (%)",
        yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig_airlines, width="stretch")
