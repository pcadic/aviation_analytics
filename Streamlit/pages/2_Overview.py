import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Overview",
    layout="wide"
)

st.title("✈️ Flights Overview")

# -------------------------------------------------
# SUPABASE CONNECTION
# -------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

    response = (
        supabase
        .table("v_flights_enriched")
        .select("*")
        .execute()
    )

    if not response.data:
        return pd.DataFrame()

    return pd.DataFrame(response.data)


df = load_data()

# -------------------------------------------------
# EMPTY DATA GUARD
# -------------------------------------------------
if df.empty:
    st.warning("No data available.")
    st.stop()

# -------------------------------------------------
# DATA CLEANING (CRITICAL)
# -------------------------------------------------

# --- Datetime columns (Supabase returns strings)
datetime_cols = ["dep_time", "arr_time"]

for col in datetime_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

# --- Numeric columns
numeric_cols = [
    "ac_min_pax",
    "ac_max_pax",
    "delay_minutes"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove rows with invalid departure time
df = df.dropna(subset=["dep_time"])

# -------------------------------------------------
# KPI CALCULATIONS
# -------------------------------------------------

total_flights = len(df)

date_span_hours = (
    (df["dep_time"].max() - df["dep_time"].min()).total_seconds() / 3600
    if total_flights > 1 else 0
)

avg_flights_per_hour = (
    round(total_flights / date_span_hours, 2)
    if date_span_hours > 0 else 0
)

avg_delay = (
    round(df["delay_minutes"].mean(), 1)
    if "delay_minutes" in df.columns else None
)

avg_pax_per_flight = (
    df[["ac_min_pax", "ac_max_pax"]]
    .mean(axis=1)
    .mean()
)

# -------------------------------------------------
# KPI DISPLAY
# -------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total flights", total_flights)
c2.metric("Avg flights / hour", avg_flights_per_hour)
c3.metric(
    "Avg delay (min)",
    f"{avg_delay:.1f}" if avg_delay is not None else "N/A"
)
c4.metric(
    "Avg pax / flight",
    int(avg_pax_per_flight) if not pd.isna(avg_pax_per_flight) else "N/A"
)

st.divider()

# -------------------------------------------------
# FLIGHTS PER HOUR
# -------------------------------------------------
df["hour"] = df["dep_time"].dt.hour

flights_per_hour = (
    df.groupby("hour")
    .size()
    .reset_index(name="flights")
)

fig_hour = px.bar(
    flights_per_hour,
    x="hour",
    y="flights",
    title="Flights per hour (departure time)",
    labels={"hour": "Hour of day", "flights": "Number of flights"}
)

st.plotly_chart(fig_hour, use_container_width=True)

# -------------------------------------------------
# FLIGHTS PER DAY
# -------------------------------------------------
df["date"] = df["dep_time"].dt.date

flights_per_day = (
    df.groupby("date")
    .size()
    .reset_index(name="flights")
)

fig_day = px.line(
    flights_per_day,
    x="date",
    y="flights",
    markers=True,
    title="Flights per day",
    labels={"date": "Date", "flights": "Number of flights"}
)

st.plotly_chart(fig_day, use_container_width=True)

# -------------------------------------------------
# DELAY DISTRIBUTION
# -------------------------------------------------
if "delay_minutes" in df.columns and df["delay_minutes"].notna().any():
    fig_delay = px.histogram(
        df,
        x="delay_minutes",
        nbins=40,
        title="Delay distribution (minutes)"
    )
    st.plotly_chart(fig_delay, use_container_width=True)

# -------------------------------------------------
# TOP AIRLINES
# -------------------------------------------------
if "airline_iata" in df.columns:
    top_airlines = (
        df["airline_iata"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_airlines.columns = ["airline", "flights"]

    fig_airlines = px.bar(
        top_airlines,
        x="airline",
        y="flights",
        title="Top 10 airlines by number of flights"
    )

    st.plotly_chart(fig_airlines, use_container_width=True)
