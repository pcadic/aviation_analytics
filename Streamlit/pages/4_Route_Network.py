import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Route Network",
    page_icon="🌍",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HUB = "CYVR"

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select(
            "dep_icao, arr_icao, "
            "dep_city, arr_city, "
            "dep_country_ref, arr_country_ref, "
            "dep_latitude, dep_longitude, "
            "arr_latitude, arr_longitude"
        )
        .execute()
    )
    return pd.DataFrame(response.data)

df = load_data()

# ============================
# CLEANING
# ============================
df = df.dropna(subset=[
    "dep_latitude", "dep_longitude",
    "arr_latitude", "arr_longitude",
    "dep_city", "arr_city"
])

# ============================
# HUB NETWORK ONLY
# ============================
df = df[(df.dep_icao == HUB) | (df.arr_icao == HUB)]

# ============================
# DOMESTIC / INTERNATIONAL FILTER
# ============================
df["route_type"] = df.apply(
    lambda r: "Domestic"
    if r.dep_country_ref == r.arr_country_ref
    else "International",
    axis=1
)

route_filter = st.radio(
    "Route type",
    ["All", "Domestic", "International"],
    horizontal=True
)

if route_filter != "All":
    df = df[df.route_type == route_filter]

# ============================
# NORMALISE DESTINATIONS
# ============================
df["dest_lat"] = df.apply(
    lambda r: r.arr_latitude if r.dep_icao == HUB else r.dep_latitude,
    axis=1
)

df["dest_lon"] = df.apply(
    lambda r: r.arr_longitude if r.dep_icao == HUB else r.dep_longitude,
    axis=1
)

# ============================
# HEATMAP — ROUTE DENSITY
# ============================
st.subheader("CYVR Route Network – Destination Density")

fig = px.density_mapbox(
    df,
    lat="dest_lat",
    lon="dest_lon",
    radius=25,
    zoom=3,
    height=650
)

fig.update_layout(
    mapbox_style="open-street-map",
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)

# ============================
# ADD CYVR HUB (STRATEGIC ANCHOR)
# ============================
hub_row = df[df.dep_icao == HUB].iloc[0]

fig.add_scattermapbox(
    lat=[hub_row.dep_latitude],
    lon=[hub_row.dep_longitude],
    mode="markers+text",
    marker=dict(size=14, color="black"),
    text=["Vancouver (CYVR)"],
    textposition="top center",
    hoverinfo="skip",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)
