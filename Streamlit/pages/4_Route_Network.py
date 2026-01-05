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
st.caption("Bidirectional flight routes aggregated from enriched flight data")

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
    "dep_city", "arr_city"
])

# ============================
# BIDIRECTIONAL ROUTES
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
# FILTER — DOMESTIC / INTERNATIONAL
# ============================
route_filter = st.selectbox(
    "Route type",
    ["All", "Domestic", "International"]
)

if route_filter != "All":
    df = df[df["route_type"] == route_filter]

# ============================
# AGGREGATE ROUTES
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
          dep_city=("dep_city", "first"),
          arr_city=("arr_city", "first"),
      )
      .reset_index()
)

# ============================
# COLOR NORMALIZATION (ROBUST)
# ============================
min_f = routes["flights"].min()
max_f = routes["flights"].max()

if min_f == max_f:
    routes["norm"] = 0.5
else:
    routes["norm"] = (routes["flights"] - min_f) / (max_f - min_f)

# ============================
# MAP
# ============================
fig = go.Figure()

for _, row in routes.iterrows():
    # Blue → Red gradient
    red = int(255 * row["norm"])
    blue = int(255 * (1 - row["norm"]))

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
st.subheader("Top 5 Routes by Average Passenger Capacity")

top5 = (
    routes.sort_values("avg_pax", ascending=False)
          .head(5)
          .assign(
              route=lambda d: d["dep_city"] + " – " + d["arr_city"],
              avg_pax=lambda d: d["avg_pax"].round(0).astype(int)
          )
)

st.dataframe(
    top5[["route", "avg_pax"]]
    .rename(columns={
        "route": "Route",
        "avg_pax": "Avg passengers per flight"
    }),
    use_container_width=True
)

# ============================
# FOOTER
# ============================
st.caption(
    "Routes derived from v_flights_enriched · Passenger capacity estimated from aircraft reference data"
)
