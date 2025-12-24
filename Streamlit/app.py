import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Aviation Analytics", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=3600)
def load_flights(limit=2000):
    res = supabase.table("flights_airlabs") \
        .select("*") \
        .limit(limit) \
        .execute()
    return pd.DataFrame(res.data)

st.title("✈️ Aviation Analytics – Vancouver (CYVR)")

df = load_flights()

st.metric("Nombre de vols analysés", len(df))

st.dataframe(df.head(50), use_container_width=True)
