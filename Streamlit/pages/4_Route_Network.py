import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="Route Network",
    layout="wide"
)

HUB = "CYVR"

# ======================
# LOAD DATA
# ======================
@st.cache_data(ttl=600)
def load_data():
    return (
        st.session_state.supabase
        .table("v_flights_enriched")
        .select(
            """
            dep_icao, dep_city, dep_country_ref, dep_latitude, dep_longitude,
            arr_icao, arr_city, arr_country_ref, arr_latitude, arr_longitude
            """
        )
        .or_(f"dep_icao.eq.{HUB},arr_icao.eq.{HUB}")
        .execute()
        .data
    )

df = pd.DataFrame(load_data())

# ======================
# GLOBAL FILTER
# ======================
st.title("Route Network Overview")

col1, col2 = st.columns([1, 3])

with col1:
    route_scope = st.radio(
        "Route scope",
        ["Domestic", "International", "Both"],
        horizontal=False
    )

# ======================
# FILTER LOGIC
# ======================
def is_domestic(row):
    return row.dep_country_ref == row.arr_country_ref

if route_scope == "Domestic":
    df = df[df.apply(is_domestic, axis=1)]
elif route_scope == "International":
    df = df[~df.apply(is_domestic, axis=1)]

# ======================
# DESTINATION NORMALISATION
# ======================
df["destination_city"] = df.apply(
    lambda r: r.arr_city if r.dep_icao == HUB else r.dep_city,
    axis=1
)

df["destination_lat"] = df.apply(
    lambda r: r.arr_latitude if r.dep_icao == HUB else r.dep_latitude,
    axis=1
)

df["destination_lon"] = df.apply(
    lambda r: r.arr_longitude if r.dep_icao == HUB else r.dep_longitude,
    axis=1
)

# ======================
# AGGREGATION (RELATIVE ONLY)
# ======================
destinations = (
    df.groupby(["destination_city", "destination_lat", "destination_lon"])
    .size()
    .reset_index(name="relative_intensity")
)

# Normalisation (0–1)
destinations["weight"] = (
    destinations["relative_intensity"] / destinations["relative_intensity"].max()
)

# ======================
# MAP — OSM HEATMAP
# ======================
st.subheader("Spatial Distribution of Destinations (Relative Intensity)")

heatmap_layer = pdk.Layer(
    "HeatmapLayer",
    data=destinations,
    get_position=["destination_lon", "destination_lat"],
    get_weight="weight",
    radiusPixels=60,
)

view_state = pdk.ViewState(
    latitude=49.1947,
    longitude=-123.1792,
    zoom=3,
    pitch=0
)

deck = pdk.Deck(
    layers=[heatmap_layer],
    initial_view_state=view_state,
    map_style="mapbox://styles/mapbox/light-v10",
    tooltip=None
)

st.pydeck_chart(deck, use_container_width=True)

# ======================
# TOP N DESTINATIONS (NO COUNTS)
# ======================
st.subheader("Top Destinations (Relative Ranking)")

max_n = min(15, len(destinations))

top_n = st.slider(
    "Number of destinations to display",
    min_value=1,
    max_value=max_n,
    value=min(5, max_n)
)

top_dest = (
    destinations
    .sort_values("weight", ascending=False)
    .head(top_n)
    .assign(
        ranking_score=lambda x: (x["weight"] * 100).round(0)
    )
)

fig = px.bar(
    top_dest.sort_values("ranking_score"),
    x="ranking_score",
    y="destination_city",
    orientation="h",
    labels={
        "ranking_score": "Relative Importance Index",
        "destination_city": "Destination"
    },
    title=None
)

fig.update_layout(
    xaxis_showticklabels=False,
    xaxis_title=None,
    yaxis_title=None,
    showlegend=False,
    height=400
)

st.plotly_chart(fig, use_container_width=True)
