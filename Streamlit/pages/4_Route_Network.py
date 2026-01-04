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
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client

# ============================
# PAGE CONFIG
# ============================
st.set_page_config(
    page_title="Route Network",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ CYVR Route Network")
st.caption("Flight routes aggregated from enriched flight view (bidirectional routes)")

# ============================
# SUPABASE
# ============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOAD DATA FROM VIEW
# ============================
@st.cache_data
def load_data():
    res = (
        supabase
        .table("v_flights_enriched")
        .select("""
            dep_icao,
            arr_icao,
            dep_latitude,
            dep_longitude,
            arr_latitude,
            arr_longitude,
            dep_country_ref,
            arr_country_ref,
            avg_pax_estimated
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
    "arr_latitude", "arr_longitude"
])

# ============================
# ROUTE NORMALIZATION (BIDIRECTIONAL)
# ============================
df["route_id"] = df.apply(
    lambda r: "-".join(sorted([r["dep_icao"], r["arr_icao"]])),
    axis=1
)

df["route_type"] = df.apply(
    lambda r: "Domestic"
    if r["dep_country_ref"] == r["arr_country_ref"]
    else "International",
    axis=1
)

# ============================
# FILTERS
# ============================
col1, col2 = st.columns([1, 2])

with col1:
    route_filter = st.selectbox(
        "Route type",
        ["All", "Domestic", "International"]
    )

if route_filter != "All":
    df = df[df["route_type"] == route_filter]

# ============================
# AGGREGATION BY ROUTE
# ============================
routes = (
    df.groupby("route_id")
      .agg(
          flights=("route_id", "count"),
          avg_pax=("avg_pax_estimated", "mean"),
          dep_lat=("dep_latitude", "first"),
          dep_lon=("dep_longitude", "first"),
          arr_lat=("arr_latitude", "first"),
          arr_lon=("arr_longitude", "first"),
      )
      .reset_index()
)

# ============================
# SLIDER: MIN FLIGHTS PER ROUTE
# ============================
with col2:
    min_flights = st.slider(
        "Minimum number of flights per route",
        min_value=1,
        max_value=int(routes["flights"].max()),
        value=2
    )

routes = routes[routes["flights"] >= min_flights]

# ============================
# KPI — TOP ROUTE BY PAX
# ============================
top_route = routes.sort_values("avg_pax", ascending=False).head(1)

if not top_route.empty:
    st.metric(
        "Top route – average passenger capacity",
        f"{int(top_route.iloc[0]['avg_pax'])} passengers / flight"
    )

# ============================
# MAP — ROUTE NETWORK
# ============================
fig = go.Figure()

# Normalize flights for color scale
norm = (
    (routes["flights"] - routes["flights"].min()) /
    (routes["flights"].max() - routes["flights"].min())
    if routes["flights"].nunique() > 1
    else routes["flights"]
)

for i, row in routes.iterrows():
    red = int(255 * norm.loc[i])
    blue = int(255 * (1 - norm.loc[i]))

    fig.add_trace(go.Scattergeo(
        lat=[row["dep_lat"], row["arr_lat"]],
        lon=[row["dep_lon"], row["arr_lon"]],
        mode="lines",
        line=dict(
            width=2,
            color=f"rgb({red},0,{blue})"
        ),
        hoverinfo="skip",
        showlegend=False
    ))

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    geo=dict(
        projection_type="natural earth",
        center=dict(lat=49.1947, lon=-123.1792),  # CYVR
        projection_scale=5,
        showcountries=True,
        showland=True,
        landcolor="rgb(240,240,240)",
    )
)

st.plotly_chart(fig, use_container_width=True)

# ============================
# TOP 5 ROUTES TABLE
# ============================
st.subheader("Top 5 Routes by Passenger Capacity")

top5 = (
    routes.sort_values("avg_pax", ascending=False)
          .head(5)
          .assign(
              avg_pax=lambda d: d["avg_pax"].round(0).astype(int)
          )
)

st.dataframe(
    top5[["route_id", "flights", "avg_pax"]]
    .rename(columns={
        "route_id": "Route",
        "flights": "Flights",
        "avg_pax": "Avg passengers / flight"
    }),
    use_container_width=True
)

# ============================
# FOOTER
# ============================
st.caption("Routes derived from v_flights_enriched | Passenger capacity estimated from aircraft reference data")

@st.cache_data
def load_data():
    res = (
        supabase
        .table("v_flights_enriched")
        .select("""
            dep_icao,
            arr_icao,
            dep_latitude,
            dep_longitude,
            arr_latitude,
            arr_longitude,
            dep_country_ref,
            arr_country_ref,
            avg_pax_estimated
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
