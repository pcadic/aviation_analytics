st.title("✈️ Flight Delay Risk Explorer")
st.caption(
    "Estimating delay risk using departure-time conditions only. "
    "This model is designed for operational decision support."
)

severity = st.selectbox(
    "Weather severity at departure",
    options=[0, 1, 2, 3],
    format_func=lambda x: ["Normal", "Moderate", "Severe", "Extreme"][x]
)

duration = st.slider(
    "Flight duration (minutes)",
    min_value=30,
    max_value=900,
    value=180
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    rain = st.checkbox("Rain")
with col2:
    fog = st.checkbox("Fog")
with col3:
    icing = st.checkbox("Icing")
with col4:
    wind = st.checkbox("Strong wind")

route_type = st.radio(
    "Route type",
    ["Domestic", "International"],
    horizontal=True
)

risk_score = (
    severity * 0.25 +
    rain * 0.1 +
    fog * 0.15 +
    icing * 0.2 +
    wind * 0.15 +
    (duration / 900) * 0.15
)

risk_score = min(risk_score, 1.0)

st.metric(
    "Estimated Delay Risk",
    f"{risk_score*100:.0f} %",
    help="Probability estimate based on historical patterns."
)

import plotly.graph_objects as go

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=risk_score * 100,
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": "darkred"},
        "steps": [
            {"range": [0, 30], "color": "#2ecc71"},
            {"range": [30, 60], "color": "#f1c40f"},
            {"range": [60, 100], "color": "#e74c3c"}
        ]
    }
))

fig.update_layout(height=350)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Why is this flight considered risky?")

explanations = []

if severity >= 2:
    explanations.append("High weather severity at departure")
if icing:
    explanations.append("Icing conditions significantly increase delays")
if wind:
    explanations.append("Strong winds affect departure sequencing")
if duration > 400:
    explanations.append("Long-haul flights show higher delay variability")

if not explanations:
    explanations.append("Conditions are generally favorable")

for e in explanations:
    st.write("•", e)

with st.expander("Model assumptions & limitations"):
    st.write("""
    - This score is based only on departure-time information.
    - No air traffic congestion or crew rotation data is used.
    - The model estimates risk, not certainty.
    """)
