import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# ============================
# CONFIG
# ============================
st.set_page_config(page_title="Operational Insights", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    res = supabase.table("v_flights_enriched").select("*").execute()
    return pd.DataFrame(res.data)

df = load_data()

# ============================
# CLEANING
# ============================
df["dep_time_utc"] = pd.to_datetime(df["dep_time_utc"])
df["arr_time_utc"] = pd.to_datetime(df["arr_time_utc"])

df["dep_delay"] = df["dep_delayed"].fillna(0)
df["arr_delay"] = df["arr_delayed"].fillna(0)

df["is_departure"] = df["dep_icao"] == "CYVR"
df["is_arrival"] = df["arr_icao"] == "CYVR"

df["delay"] = df.apply(
    lambda r: r["dep_delay"] if r["is_departure"] else r["arr_delay"],
    axis=1
)

# Passenger estimate
df["avg_pax"] = (df["ac_min_pax"] + df["ac_max_pax"]) / 2

# ============================
# KPI SECTION
# ============================
st.title("✈️ Operational Insights")

avg_delay = round(df["delay"].mean(), 1)
#on_time_pct = round((df["delay"] <= 15).mean() * 100, 1)

traffic = pd.concat([
    df[df["is_departure"]][["dep_time_utc"]].rename(columns={"dep_time_utc": "time"}),
    df[df["is_arrival"]][["arr_time_utc"]].rename(columns={"arr_time_utc": "time"})
])

traffic["hour"] = traffic["time"].dt.hour
avg_flights_per_hour = round(traffic.groupby("hour").size().mean(), 2)

avg_pax = int(df["avg_pax"].mean())
#total_pax = int(df["avg_pax"].sum())

# ============================
# WEATHER IMPACT KPI
# ============================

weather_df = df.copy()

weather_df["is_rain"] = (
    weather_df["dep_is_rain"].fillna(False) |
    weather_df["arr_is_rain"].fillna(False)
)

weather_df["is_strong_wind"] = (
    weather_df["dep_is_strong_wind"].fillna(False) |
    weather_df["arr_is_strong_wind"].fillna(False)
)

weather_df["is_severe_weather"] = (
    (weather_df["dep_weather_severity"].fillna(0) >= 2) |
    (weather_df["arr_weather_severity"].fillna(0) >= 2)
)


rain_pct = round(weather_df["is_rain"].mean() * 100, 1)
wind_pct = round(weather_df["is_strong_wind"].mean() * 100, 1)
severe_pct = round(weather_df["is_severe_weather"].mean() * 100, 1)


c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Avg Delay", f"{avg_delay} min")
#c2.metric("On-time Flights", f"{on_time_pct}%")
c2.metric("Flights / Hour", avg_flights_per_hour)
c3.metric("Avg Pax / Flight", avg_pax)
#c5.metric("Total Estimated Pax", f"{total_pax:,}")
c4.metric("Flights affected by rain", f"{rain_pct} %")
c5.metric("Flights affected by strong wind", f"{wind_pct} %")
c6.metric("Flights with severe weather", f"{severe_pct} %")

st.divider()

# ============================
# DELAY BY AIRLINE
# ============================
st.subheader("Average Delay by Airline")

airline_delay = (
    df.dropna(subset=["airline_name"])
      .groupby("airline_name")["delay"]
      .mean()
      .sort_values()
      .tail(10)
)

fig_airline = px.bar(
    airline_delay,
    orientation="h",
    title="Average Delay per Airline (minutes)"
)

fig_airline.update_traces(
    text=airline_delay.round(1),
    texttemplate="%{text} min",
    hoverinfo="skip"
)

fig_airline.update_layout(
    xaxis_title="Delay (minutes)",
    yaxis_title="",
    showlegend=False
)

fig_airline.add_vline(
    x=15,
    line_dash="dot",
    line_color="red",
    annotation_text="15 min threshold"
)

st.plotly_chart(fig_airline, width="stretch")

# ============================
# HOURLY TRAFFIC
# ============================
st.subheader("Hourly Traffic Load")

hourly = traffic.groupby("hour").size().reset_index(name="flights")

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

st.plotly_chart(fig_hour, width="stretch")

# ============================
# DELAY DISTRIBUTION
# ============================
st.subheader("Delay Distribution")

fig_dist = px.histogram(
    df,
    x="delay",
    nbins=40,
    title="Distribution of Flight Delays"
)

fig_dist.update_layout(
    xaxis_title="Delay (minutes)",
    yaxis_title="Flights"
)

st.plotly_chart(fig_dist, width="stretch")

# ============================
# PASSENGER LOAD BY HOUR
# ============================
st.subheader("Estimated Passenger Load per Hour")

pax_hour = (
    df.assign(hour=df["dep_time_utc"].dt.hour)
      .groupby("hour")["avg_pax"]
      .sum()
      .reset_index()
)

fig_pax = px.bar(
    pax_hour,
    x="hour",
    y="avg_pax",
    title="Estimated Passenger Volume per Hour"
)

fig_pax.update_layout(
    xaxis_title="Hour",
    yaxis_title="Estimated Passengers"
)

st.plotly_chart(fig_pax, width="stretch")

# ============================
# AVERAGE DELAY BY AIRCRAFT TYPE
# ============================
st.subheader("Average Delay by Aircraft Type")

aircraft_delay = (
    df.dropna(subset=["aircraft_icao", "delay"])
      .groupby("aircraft_icao")["delay"]
      .mean()
      .sort_values(ascending=False)
      .head(10)
)

fig_aircraft = px.bar(
    aircraft_delay.sort_values(),
    orientation="h",
    title="Average Delay per Aircraft Type (minutes)"
)

fig_aircraft.update_traces(
    texttemplate="%{x:.0f} min",
    textposition="outside",
    hoverinfo="skip",
    hovertemplate=None
)

fig_aircraft.update_layout(
    xaxis_title="Delay (minutes)",
    yaxis_title="",
    showlegend=False,
    uniformtext_minsize=10,
    uniformtext_mode="hide"
)

st.plotly_chart(fig_aircraft, width="stretch")


# ============================
# FOOTER
# ============================
st.caption("Data source: AirLabs + Open-Meteo | Processed via Supabase")
