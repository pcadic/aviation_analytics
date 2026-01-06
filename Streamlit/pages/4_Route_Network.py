import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
# BASIC CLEANING
# ============================
df = df.dropna(subset=[
    "dep_latitude", "dep_longitude",
    "arr_latitude", "arr_longitude",
    "dep_city", "arr_city"
])

# ============================
# FILTER — HUB ONLY
# ============================
df = df[(df["dep_icao"] == HUB) | (df["arr_icao"] == HUB)]

df["route_type"] = df.apply(
    lambda r: "Domestic"
    if r["dep_country_ref"] == r["arr_country_ref"]
    else "International",
    axis=1
)

route_filter = st.radio(
    "Route type",
    ["All", "Domestic", "International"],
    horizontal=True
)

if route_filter != "All":
    df = df[df["route_type"] == route_filter]

# ============================
# ROUTE AGGREGATION
# ============================
routes = (
    df.assign(
        route_id=lambda x: x.apply(
            lambda r: "-".join(sorted([r.dep_icao, r.arr_icao])),
            axis=1
        )
    )
    .groupby(
        ["route_id",
         "dep_city", "arr_city",
         "dep_latitude", "dep_longitude",
         "arr_latitude", "arr_longitude"],
        as_index=False
    )
    .size()
    .rename(columns={"size": "flight_count"})
)

# ============================
# COLOR SCALE (BLUE → RED)
# ============================
min_f = routes["flight_count"].min()
max_f = routes["flight_count"].max()

def color_scale(v):
    if max_f == min_f:
        return "rgb(30, 144, 255)"
    ratio = (v - min_f) / (max_f - min_f)
    r = int(255 * ratio)
    g = int(80 * (1 - ratio))
    b = int(255 * (1 - ratio))
    return f"rgb({r},{g},{b})"

routes["color"] = routes["flight_count"].apply(color_scale)

# ============================
# MAP
# ============================
fig = go.Figure()

for _, r in routes.iterrows():
    fig.add_trace(
        go.Scattergeo(
            lat=[r.dep_latitude, r.arr_latitude],
            lon=[r.dep_longitude, r.arr_longitude],
            mode="lines",
            line=dict(
                width=2,
                color=r.color
            ),
            hoverinfo="skip",
            showlegend=False
        )
    )

fig.update_layout(
    title="CYVR Route Network",
    geo=dict(
        scope="north america",
        projection_type="natural earth",
        showland=True,
        landcolor="rgb(243,243,243)",
        showcountries=True,
        countrycolor="rgb(200,200,200)"
    ),
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig, width="stretch")

# ============================
# TOP DESTINATIONS (BAR CHART)
# ============================
st.subheader("Top Destinations by Route Frequency")

destinations = (
    routes.assign(
        destination=lambda x: x.apply(
            lambda r: r.arr_city if r.dep_icao == HUB else r.dep_city,
            axis=1
        )
    )
    .groupby("destination")["flight_count"]
    .sum()
    .sort_values(ascending=False)
)

top_n = st.slider(
    "Number of destinations",
    min_value=1,
    max_value=len(destinations),
    value=min(10, len(destinations))
)

fig_bar = go.Figure()

fig_bar.add_trace(
    go.Bar(
        x=destinations.head(top_n),
        y=destinations.head(top_n).index,
        orientation="h",
        marker_color="steelblue",
        hoverinfo="skip"
    )
)

fig_bar.update_layout(
    xaxis_title="Number of flights",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_bar, width="stretch")
