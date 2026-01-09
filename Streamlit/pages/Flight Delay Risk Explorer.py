import streamlit as st
import plotly.graph_objects as go

# ============================
# PAGE CONFIG
# ============================
st.set_page_config(
    page_title="Flight Delay Risk Explorer",
    page_icon="🧠",
    layout="wide"
)

# ============================
# HEADER
# ============================
st.title("✈️ Flight Delay Risk Explorer")
st.caption(
    "Estimate delay risk using departure-time operational conditions only. "
    "This tool is designed for decision support, not exact prediction."
)

st.divider()

# ============================
# INPUTS — OPERATIONAL FACTORS
# ============================
st.subheader("Departure Conditions")

col1, col2 = st.columns(2)

with col1:
    severity = st.selectbox(
        "Weather severity at departure",
        options=[0, 1, 2, 3],
        format_func=lambda x: ["Normal", "Moderate", "Severe", "Extreme"][x]
    )

    duration = st.slider(
        "Flight duration (minutes)",
        min_value=30,
        max_value=900,
        value=180,
        step=10
    )

    route_type = st.radio(
        "Route type",
        ["Domestic", "International"],
        horizontal=True
    )

with col2:
    st.write("**Weather phenomena**")

    rain = st.checkbox("Rain")
    fog = st.checkbox("Fog")
    icing = st.checkbox("Icing")
    wind = st.checkbox("Strong wind")

st.divider()

# ============================
# RISK SCORE CALCULATION
# ============================
"""
Simple weighted risk score.
This is NOT a trained ML model.
It mimics a logistic-risk style approach for explainability.
"""

risk_score = (
    severity * 0.25 +
    (0.10 if rain else 0) +
    (0.15 if fog else 0) +
    (0.20 if icing else 0) +
    (0.15 if wind else 0) +
    (duration / 900) * 0.15 +
    (0.05 if route_type == "International" else 0)
)

risk_score = min(risk_score, 1.0)
risk_pct = round(risk_score * 100)

# ============================
# KPI
# ============================
st.metric(
    "Estimated Delay Risk",
    f"{risk_pct} %",
    help="Estimated probability based on historical operational patterns."
)

# ============================
# GAUGE VISUAL
# ============================
fig_gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=risk_pct,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkred"},
            "steps": [
                {"range": [0, 30], "color": "#2ecc71"},
                {"range": [30, 60], "color": "#f1c40f"},
                {"range": [60, 100], "color": "#e74c3c"},
            ],
        },
    )
)

fig_gauge.update_layout(height=350, margin=dict(t=20, b=0, l=0, r=0))
st.plotly_chart(fig_gauge, use_container_width=True)

# ============================
# EXPLANATION LOGIC
# ============================
st.subheader("Risk Interpretation")

explanations = []

if severity >= 2:
    explanations.append("High weather severity at departure")
if rain:
    explanations.append("Rain increases runway and taxi delays")
if fog:
    explanations.append("Fog reduces visibility and departure rate")
if icing:
    explanations.append("Icing requires de-icing procedures")
if wind:
    explanations.append("Strong winds affect takeoff sequencing")
if duration > 400:
    explanations.append("Long-haul flights show higher delay variability")
if route_type == "International":
    explanations.append("International routes are more exposed to downstream delays")

if not explanations:
    explanations.append("Operational conditions are generally favorable")

for e in explanations:
    st.write("•", e)

# ============================
# TRANSPARENCY / LIMITATIONS
# ============================
with st.expander("Model assumptions & limitations"):
    st.write(
        """
        - This score is **not** an exact prediction.
        - It is based only on departure-time conditions.
        - No air traffic congestion, crew rotation or airport capacity data is used.
        - The objective is interpretability, not maximized accuracy.
        """
    )
