import streamlit as st

st.set_page_config(
    page_title="Data Pipeline",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Aviation Data Pipeline")

st.markdown("""
This page explains how flight data is collected, enriched and stored.
""")

st.subheader("1. Data Sources")

st.markdown("""
- **AirLabs API** – Real-time flight data  
- **Open-Meteo API** – Weather at departure and arrival  
- **Supabase** – Central data warehouse  
""")

st.subheader("2. Pipeline Steps")

st.markdown("""
1. Fetch flights from AirLabs  
2. Enrich with aircraft and airport data  
3. Add weather conditions  
4. Store results in Supabase  
5. Visualize using Streamlit  
""")

st.subheader("3. Update Frequency")

st.markdown("""
- Flights: every 12 hours  
- Weather: fetched only when missing  
""")

st.success("Pipeline loaded successfully ✅")
