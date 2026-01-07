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
# HUB FILTER
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
df["destination_city"] = df.apply(
    lambda r: r.arr_city if r.dep_icao == HUB else r.dep_city,
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
# HEATMAP — DESTINATION DENSITY
# ============================
st.subheader("CYVR Route Network – Destination Density")

fig_map = px.density_mapbox(
    df,
    lat="dest_lat",
    lon="dest_lon",
    radius=25,
    zoom=3,
    height=650
)

fig_map.update_layout(
    mapbox_style="open-street-map",
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False
)

# ============================
# CYVR HUB — RED AIRCRAFT ICON
# ============================
hub_row = df[df.dep_icao == HUB].iloc[0]

fig_map.add_scattermapbox(
    lat=[hub_row.dep_latitude],
    lon=[hub_row.dep_longitude],
    mode="markers+text",
    marker=dict(
        size=22,
        color="red",
        symbol="airport"
    ),
    text=["Vancouver (CYVR)"],
    textposition="top center",
    hoverinfo="skip",
    showlegend=False
)

st.plotly_chart(fig_map, use_container_width=True)

# ============================
# TOP 10 ROUTES — NO NUMBERS
# ============================
st.subheader("Top Routes from CYVR")

df["route_name"] = df.apply(
    lambda r: (
        f"{r.dep_city} – {r.arr_city}"
        if r.dep_icao == HUB
        else f"{r.arr_city} – {r.dep_city}"
    ),
    axis=1
)

top_routes = (
    df["route_name"]
    .value_counts()
    .head(10)
    .sort_values(ascending=True)
)

fig_bar = px.bar(
    top_routes,
    x=top_routes.values,
    y=top_routes.index,
    orientation="h"
)

fig_bar.update_traces(
    hoverinfo="skip"
)

fig_bar.update_layout(
    xaxis=dict(visible=False),   # ← cache l’axe et les valeurs
    yaxis_title="",
    showlegend=False,
    margin=dict(l=0, r=0, t=30, b=0)
)

st.plotly_chart(fig_bar, use_container_width=True)
