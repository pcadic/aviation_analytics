import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
import numpy as np

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Route Network",
    page_icon="🗺️",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    res = (
        supabase
        .table("v_flights_enriched")
        .select("""
            dep_icao, arr_icao,
            dep_latitude, dep_longitude,
            arr_latitude, arr_longitude,
            dep_country_ref, arr_country_ref,
            avg_pax
        """)
        .execute()
    )
    return pd.DataFrame(res.data)

df = load_data()

# ============================
# CLEANING
# ============================
df = df.dropna(subset=[
    "dep_icao", "arr_icao",
    "dep_latitude", "dep_longitude",
    "arr_latitude", "arr_longitude",
    "avg_pax"
])

# Focus CYVR hub
df = df[(df["dep_icao"] == "CYVR") | (df["arr_icao"] == "CYVR")]

# Domestic / International
df["is_domestic"] = (
    (df["dep_country_ref"] == "Canada") &
    (df["arr_country_ref"] == "Canada")
)

# Normalize routes (A-B == B-A)
df["a_icao"] = df[["dep_icao", "arr_icao"]].min(axis=1)
df["b_icao"] = df[["dep_icao", "arr_icao"]].max(axis=1)
df["route_id"] = df["a_icao"] + " – " + df["b_icao"]

# ============================
# USER FILTERS
# ============================
st.title("🗺️ CYVR Route Network")

col1, col2 = st.columns([2, 3])

with col1:
    route_type = st.radio(
        "Route type",
        ["All", "Domestic", "International"],
        horizontal=True
    )

with col2:
    min_flights = st.slider(
        "Minimum flights per route",
        min_value=1,
        max_value=20,
        value=2
    )

if route_type == "Domestic":
    df = df[df["is_domestic"]]
elif route_type == "International":
    df = df[~df["is_domestic"]]

# ============================
# ROUTE AGGREGATION
# ============================
routes = (
    df.groupby("route_id")
      .agg(
          flights=("route_id", "count"),
          avg_pax=("avg_pax", "mean"),
          dep_lat=("dep_latitude", "first"),
          dep_lon=("dep_longitude", "first"),
          arr_lat=("arr_latitude", "first"),
          arr_lon=("arr_longitude", "first"),
      )
      .reset_index()
)

routes = routes[routes["flights"] >= min_flights]

if routes.empty:
    st.warning("No routes match the selected filters.")
    st.stop()

# ============================
# COLOR SCALE (BLUE → RED)
# ============================
min_f, max_f = routes["flights"].min(), routes["flights"].max()
routes["color_scale"] = (routes["flights"] - min_f) / (max_f - min_f + 1e-6)

def traffic_color(x):
    return f"rgb({int(255*x)}, 0, {int(255*(1-x))})"

# ============================
# MAP
# ============================
fig = go.Figure()

for _, r in routes.iterrows():
    fig.add_trace(go.Scattergeo(
        lon=[r["dep_lon"], r["arr_lon"]],
        lat=[r["dep_lat"], r["arr_lat"]],
        mode="lines",
        line=dict(
            width=2,
            color=traffic_color(r["color_scale"])
        ),
        opacity=0.7,
        hoverinfo="skip",
        showlegend=False
    ))

fig.update_layout(
    showlegend=False,  # ✅ force removal
    geo=dict(
        projection_type="natural earth",
        showcountries=True,
        showland=True,
        landcolor="rgb(245,245,245)",
        center=dict(lat=49.195, lon=-123.177),
        projection_scale=3
    ),
    margin=dict(l=0, r=0, t=0, b=0)
)

st.plotly_chart(fig, width="stretch")

# ============================
# TOP 5 ROUTES TABLE
# ============================
st.subheader("Top 5 Routes by Estimated Passenger Capacity")

top_routes = (
    routes.assign(
        total_capacity=(routes["avg_pax"] * routes["flights"]).round(0)
    )
    .sort_values("total_capacity", ascending=False)
    .head(5)
    [["route_id", "flights", "avg_pax", "total_capacity"]]
)

top_routes.columns = [
    "Route",
    "Number of Flights",
    "Avg Passengers / Flight",
    "Estimated Total Passengers"
]

st.dataframe(
    top_routes,
    use_container_width=True,
    hide_index=True
)
