import streamlit as st

st.set_page_config(page_title="Aviation Analytics", layout="wide")

st.title("✈️ Aviation Analytics – Vancouver (YVR)")

st.markdown("""
Welcome to my air traffic analysis project around Vancouver Airport (CYVR).

Data:
- AirLabs (real-time flights & flight information)
- Open-Meteo (departure/arrival weather conditions)
- Storage: Supabase
""")

st.success("🚀 Streamlit fonctionne correctement")
