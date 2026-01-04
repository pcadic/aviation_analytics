import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client

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
# LOAD DATA (FROM VIEW)
# ============================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select(
            "dep_icao, arr_icao,"
            "dep_latitude, dep_longitude,"
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
    "dep_icao", "arr_icao",
    "dep_latitude", "dep_longitude",
    "arr_latitude", "arr_longitude"
])

# Normalize route (A-B == B-A)
df["a_icao"] = df[["dep_icao", "arr_icao"]].min(axis=1)
df["b_icao"] = df[["dep_icao", "arr_icao"]].max(axis=1)

df["route_id"] = df["a_icao"] + "-" + df["b_icao"]


# ============================
# BUILD ROUTES (UNDIRECTED)
# ============================
airports_dep = (
    df[[
        "dep_icao", "dep_latitude", "dep_longitude"
    ]]
    .drop_duplicates()
    .rename(columns={
        "dep_icao": "icao",
        "dep_latitude": "lat",
        "dep_longitude": "lon"
    })
)

airports_arr = (
    df[[
        "arr_icao", "arr_latitude", "arr_longitude"
    ]]
    .drop_duplicates()
    .rename(columns={
        "arr_icao": "icao",
        "arr_latitude": "lat",
        "arr_longitude": "lon"
    })
)

airports = pd.concat([airports_dep, airports_arr]).drop_duplicates("icao")

routes = (
    df.groupby("route_id")
      .agg(
          flights=("route_id", "count"),
          a_icao=("a_icao", "first"),
          b_icao=("b_icao", "first"),
      )
      .reset_index()
)

routes = (
    routes
    .merge(
        airports.rename(columns={"icao": "a_icao", "lat": "a_lat", "lon": "a_lon"}),
        on="a_icao",
        how="left"
    )
    .merge(
        airports.rename(columns={"icao": "b_icao", "lat": "b_lat", "lon": "b_lon"}),
        on="b_icao",
        how="left"
    )
)



# ============================
# PAGE TITLE
# ============================
st.title("🗺️ Flight Route Network")
st.caption(
    "Each line represents an undirected air route between two airports. "
    "Line thickness reflects how frequently the route is used."
)

# ============================
# MAP
# ============================
fig = go.Figure()

for _, r in routes.iterrows():
    fig.add_trace(
        go.Scattermapbox(
            mode="lines",
            lat=[r["a_lat"], r["b_lat"]],
            lon=[r["a_lon"], r["b_lon"]],
            line=dict(
                width=min(1 + r["flights"] * 0.6, 8),
                color="royalblue"
            ),
            hoverinfo="skip"
        )
    )


fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_zoom=2.5,
    mapbox_center={"lat": 50, "lon": -100},
    margin=dict(l=0, r=0, t=0, b=0),
)

st.plotly_chart(fig, width="stretch")

# ============================
# FOOTNOTE
# ============================
st.caption(
    "Routes are considered undirected: Montréal–Vancouver and Vancouver–Montréal "
    "are treated as the same route."
)
