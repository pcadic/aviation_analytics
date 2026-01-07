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
# HUB FILTER (CYVR NETWORK)
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
# NORMALISE DESTINATIONS (FROM HUB)
# ============================
df["dest_city"] = df.apply(
    lambda r: r.arr_city if r.dep_icao == HUB else r.dep_city,
    axis=1
)

df["dest_icao"] = df.apply(
    lambda r: r.arr_icao if r.dep_icao == HUB else r.dep_icao,
    axis=1
)

df["dest_lat"] = df.apply(
    lambda r: r.arr_latitude if r.dep_icao == HUB else r.dep_latitude,
    axis=1
)

df["dest_lon"] = df.apply(
    lambda r: r.arr_longitude if r.dep_icao == HUB else r.dep_longitude,
    axis=1
)

# ============================
# UNIQUE DESTINATIONS ONLY
# ============================
destinations = (
    df[["dest_city", "dest_icao", "dest_lat", "dest_lon"]]
    .drop_duplicates()
)

# ============================
# MAP 1 — OSM AIRPORT MAP
# ============================
st.subheader("CYVR Route Network – Airports")

fig_map = px.scatter_mapbox(
    destinations,
    lat="dest_lat",
    lon="dest_lon",
    hover_name="dest_city",
    hover_data={"dest_icao": True},
    zoom=3,
    height=600
)

fig_map.update_layout(
    mapbox_style="open-street-map",
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)

st.plotly_chart(fig_map, use_container_width=True)

# ============================
# MAP 2 — HEATMAP (DESTINATION DENSITY)
# ============================
st.subheader("Destination Density Heatmap")

fig_heat = px.density_mapbox(
    df,
    lat="dest_lat",
    lon="dest_lon",
    radius=25,
    zoom=3,
    height=600
)

fig_heat.update_layout(
    mapbox_style="open-street-map",
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)

st.plotly_chart(fig_heat, use_container_width=True)

# ============================
# FOOTER
# ============================
st.caption(
    "Network visualization based on observed routes from Vancouver (CYVR). "
    "Visualization focuses on structure rather than volume."
)
