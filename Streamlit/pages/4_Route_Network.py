import streamlit as st
import pandas as pd
import plotly.express as px
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
st.caption("Visualization of flight routes and destination concentration")

# ============================
# SUPABASE
# ============================
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
            dep_icao,
            arr_icao,
            dep_city,
            arr_city,
            dep_latitude,
            dep_longitude,
            arr_latitude,
            arr_longitude,
            dep_country_ref,
            arr_country_ref
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
    "dep_city", "arr_city"
])

# Focus CYVR hub
df = df[(df["dep_icao"] == "CYVR") | (df["arr_icao"] == "CYVR")]

# ============================
# DOMESTIC / INTERNATIONAL
# ============================
df["route_type"] = df.apply(
    lambda r: "Domestic"
    if r["dep_country_ref"] == r["arr_country_ref"]
    else "International",
    axis=1
)

route_filter = st.selectbox(
    "Route type",
    ["All", "Domestic", "International"]
)

if route_filter != "All":
    df = df[df["route_type"] == route_filter]

# ============================
# BIDIRECTIONAL ROUTES
# ============================
df["route_id"] = df.apply(
    lambda r: "-".join(sorted([r["dep_icao"], r["arr_icao"]])),
    axis=1
)

routes = (
    df.groupby("route_id")
      .agg(
          flights=("route_id", "count"),
          dep_lat=("dep_latitude", "first"),
          dep_lon=("dep_longitude", "first"),
          arr_lat=("arr_latitude", "first"),
          arr_lon=("arr_longitude", "first"),
          dep_city=("dep_city", "first"),
          arr_city=("arr_city", "first"),
      )
      .reset_index()
)

# ============================
# MAP — ROUTES
# ============================
fig = go.Figure()

for _, r in routes.iterrows():
    fig.add_trace(
        go.Scattergeo(
            lat=[r.dep_lat, r.arr_lat],
            lon=[r.dep_longitude, r.arr_longitude],
            mode="lines",
            line=dict(
                width=2,
                color=r["color"]  # ✅ une seule couleur
            ),
            hoverinfo="skip",
            showlegend=False
        )
    )

fig.update_layout(
    geo=dict(
        projection_type="natural earth",
        center=dict(lat=49.1947, lon=-123.1792),
        projection_scale=5,
        showcountries=True,
        showland=True,
        landcolor="rgb(240,240,240)"
    ),
    margin=dict(l=0, r=0, t=0, b=0)
)

fig.add_trace(
    go.Scattergeo(
        lat=[None],
        lon=[None],
        mode="markers",
        marker=dict(
            size=0,
            colorscale="RdBu",
            showscale=True,
            cmin=routes["flight_count"].min(),
            cmax=routes["flight_count"].max(),
            colorbar=dict(
                title="Number of flights per route"
            )
        ),
        showlegend=False
    )
)


st.plotly_chart(fig, use_container_width=True)

# ============================
# BAR CHART — TOP DESTINATIONS
# ============================
st.subheader("Top Destinations by Number of Flights")

max_routes = len(routes)
top_n = st.slider(
    "Number of routes displayed",
    min_value=1,
    max_value=max_routes,
    value=min(10, max_routes)
)

destinations = (
    df.assign(
        destination=lambda d: d.apply(
            lambda r: r.arr_city if r.dep_icao == "CYVR" else r.dep_city,
            axis=1
        )
    )
    .groupby("destination")
    .size()
    .reset_index(name="flights")
    .sort_values("flights", ascending=False)
    .head(top_n)
)

fig_bar = px.bar(
    destinations,
    x="flights",
    y="destination",
    orientation="h",
    title="Most Frequent Destinations from CYVR"
)

fig_bar.update_layout(
    xaxis_title="Number of Flights",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_bar, use_container_width=True)

# ============================
# FOOTER
# ============================
st.caption(
    "Routes aggregated from v_flights_enriched · Bidirectional logic applied · CYVR hub focus"
)
