import streamlit as st

st.set_page_config(
    page_title="Data Pipeline Overview",
    layout="wide"
)

st.title("📊 Data Pipeline Overview")
st.markdown(
    """
This page explains **how data is collected, processed, enriched, and stored**
before being used for analysis and visualization.
"""
)

# =====================================================
# SECTION 1 — ARCHITECTURE
# =====================================================
st.header("🧱 Data Architecture")

st.markdown("""
```text
AirLabs API  ──────┐
                   │
                   ▼
            Python ETL Scripts
                   │
Open-Meteo API ────┘
                   ▼
              Supabase
                   ▼
           Streamlit Dashboard
This project follows a modern data pipeline architecture:

External APIs provide raw data

Python handles extraction and transformation

Supabase stores cleaned and structured data

Streamlit displays analytics and insights
""")

=====================================================
SECTION 2 — DATA SOURCES
=====================================================

st.header("📡 Data Sources")

st.markdown("""

✈️ AirLabs API

Used to retrieve:

Flight number

Airline

Departure & arrival airports

Scheduled and actual times

Aircraft information

🌦️ Open-Meteo API

Used to enrich each flight with:

Temperature

Wind speed

Visibility

Precipitation

Weather conditions (rain, fog, icing)

🗺️ Airports Reference Table

Static dataset containing:

ICAO code

Airport name

Country

Latitude / Longitude
""")

=====================================================
SECTION 3 — DATA PROCESSING
=====================================================

st.header("⚙️ Data Processing")

st.markdown("""
The ETL pipeline performs the following steps:

Extract

Fetch flights from AirLabs API

Fetch weather data from Open-Meteo

Transform

Normalize timestamps (UTC)

Match flights with nearest weather data

Create derived features:

is_rain

is_fog

is_icing

weather_severity

Load

Store data in Supabase (PostgreSQL)

Avoid duplicate inserts

Skip already enriched rows
""")

=====================================================
SECTION 4 — DATA MODEL
=====================================================

st.header("🗄️ Data Model")

st.markdown("""

Main Table: flights_airlabs

Key fields:

flight_icao

airline_name

dep_icao, arr_icao

dep_time, arr_time

dep_delay, arr_delay

temperature

wind_speed

visibility

weather_severity

Reference Table:

airports_reference

airport name

latitude / longitude

country
""")

=====================================================
SECTION 5 — DATA QUALITY & SAFETY
=====================================================

st.header("🔐 Data Quality & Safety")

st.markdown("""
✔ Duplicate prevention using unique constraints
✔ Weather data fetched only if missing
✔ API rate limits respected
✔ Read-only access from Streamlit
✔ Supabase Row Level Security (RLS) enabled

This ensures:

No accidental overwrite

No unnecessary API calls

Secure public dashboard access
""")

=====================================================
SECTION 6 — PROJECT GOALS
=====================================================

st.header("🎯 Project Objectives")

st.markdown("""
This project demonstrates:

✅ End-to-end data engineering
✅ API integration
✅ Data enrichment
✅ SQL + Python workflow
✅ Analytics-ready dataset
✅ Dashboard-oriented thinking

It is designed as a portfolio-grade project showcasing real-world data handling.
""")

st.success("✅ Data Pipeline successfully documented.")
