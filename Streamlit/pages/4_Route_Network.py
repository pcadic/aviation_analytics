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
# CLEAN
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
# DOMESTIC / INTERNATIONAL
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
# DESTINATION NORMALISATION
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
# AGGREGATION
# ============================
routes = (
    df.groupby(
        ["destination_city", "dest_lat", "dest_lon"],
        as_index=False
    )
    .size()
    .rename(columns={"size": "flight_count"})
)

# ============================
# COLOR SCALE (BLUE → RED)
# ============================
min_f = routes.flight_count.min()
max_f = routes.flight_count.max()

def color_scale(v):
    if max_f == min_f:
        return "rgb(0,120,255)"
    ratio = (v - min_f) / (max_f - min_f)
    r = int(255 * ratio)
    g = int(80 * (1 - ratio))
    b = int(255 * (1 - ratio))
    return f"rgb({r},{g},{b})"

routes["color"] = routes.flight_count.apply(color_scale)

# ============================
# MAP
# ============================
fig = go.Figure()

# HUB
hub_row = df[df.dep_icao == HUB].iloc[0]
hub_lat = hub_row.dep_latitude
hub_lon = hub_row.dep_longitude

fig.add_trace(
    go.Scattergeo(
        lat=[hub_lat],
        lon=[hub_lon],
        mode="markers+text",
        text=["Vancouver (CYVR)"],
        textposition="top center",
        marker=dict(size=12, color="black"),
        showlegend=False
    )
)

# ROUTES + DESTINATIONS
for _, r in routes.iterrows():
    fig.add_trace(
        go.Scattergeo(
            lat=[hub_lat, r.dest_lat],
            lon=[hub_lon, r.dest_lon],
            mode="lines",
            line=dict(width=2, color=r.color),
            showlegend=False,
            hoverinfo="skip"
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lat=[r.dest_lat],
            lon=[r.dest_lon],
            mode="markers",
            marker=dict(size=6, color=r.color),
            hovertext=f"{r.destination_city}<br>{r.flight_count} flights",
            hoverinfo="text",
            showlegend=False
        )
    )

fig.update_layout(
    title="CYVR Route Network",
    geo=dict(
        scope="north america",
        projection_type="natural earth",
        showland=True,
        landcolor="rgb(245,245,245)",
        showcountries=True,
        countrycolor="rgb(200,200,200)"
    ),
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig, width="stretch")

# ============================
# BAR CHART — TOP DESTINATIONS
# ============================
st.subheader("Top Destinations by Number of Flights")

routes_sorted = routes.sort_values("flight_count", ascending=False)

top_n = st.slider(
    "Number of destinations",
    min_value=1,
    max_value=len(routes_sorted),
    value=min(10, len(routes_sorted))
)

fig_bar = go.Figure(
    go.Bar(
        x=routes_sorted.flight_count.head(top_n),
        y=routes_sorted.destination_city.head(top_n),
        orientation="h",
        marker_color="steelblue"
    )
)

fig_bar.update_layout(
    xaxis_title="Number of flights",
    yaxis_title="",
    yaxis=dict(autorange="reversed"),
    showlegend=False
)

st.plotly_chart(fig_bar, width="stretch")
