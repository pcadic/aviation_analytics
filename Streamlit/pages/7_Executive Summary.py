import streamlit as st

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Executive Summary",
    page_icon="📊",
    layout="wide"
)

# ============================
# TITLE
# ============================
st.title("📊 Executive Summary")
st.caption("Aviation Analytics — Key Findings & Takeaways")

st.divider()

# ============================
# PROBLEM STATEMENT
# ============================
st.header("✈️ Business Problem")

st.markdown("""
Flight delays significantly impact airline operations, passenger satisfaction,
and airport congestion.  
However, delays are difficult to anticipate due to the interaction of
weather conditions, route characteristics, and operational complexity.

**Objective:**  
Assess whether historical aviation data can be used to **estimate delay risk
and delay severity in a realistic operational context**.
""")

# ============================
# DATA
# ============================
st.header("🗂 Data Used")

st.markdown("""
- Real-world flight data sourced from **AirLabs API**
- Enriched airport and aircraft reference tables
- Weather indicators at departure and arrival
- Focus on flights connected to **Vancouver International Airport (CYVR)**

The dataset reflects **real production constraints**:
limited coverage, missing values, and imperfect labels.
""")

# ============================
# ANALYTICAL APPROACH
# ============================
st.header("🧠 Analytical Approach")

st.markdown("""
- Extensive **feature engineering** (routes, weather severity, aircraft type)
- Supervised machine learning models:
  - Logistic Regression (baseline)
  - Random Forest (non-linear modeling)
- Evaluation using **ROC-AUC** and model interpretability
- Deployment through an interactive **Streamlit application**
""")

# ============================
# KEY RESULTS
# ============================
st.header("📈 Key Results")

col1, col2 = st.columns(2)

with col1:
    st.metric("Baseline Model (Logistic Regression)", "AUC ≈ 0.52")

with col2:
    st.metric("Best Model (Random Forest)", "AUC ≈ 0.72")

st.markdown("""
The Random Forest model captured meaningful delay patterns despite
data limitations, demonstrating that **delay risk is predictable
to a useful degree even with partial information**.
""")

# ============================
# INSIGHTS
# ============================
st.header("🔍 Key Insights")

st.markdown("""
- Delays are **multi-factorial**, not driven by a single dominant variable
- Route characteristics and operational complexity matter as much as weather
- Interpretable models are essential for operational adoption
""")

# ============================
# LIMITATIONS & NEXT STEPS
# ============================
st.header("🚧 Limitations & Next Steps")

st.markdown("""
**Current limitations**
- No real-time METAR weather data
- No airline-specific operational constraints
- No delay propagation modeling

**Next steps**
- Integrate real-time weather feeds
- Model delay severity and cascading effects
- Deploy real-time delay risk scoring
""")

# ============================
# FINAL MESSAGE
# ============================
st.divider()

st.markdown("""
### 💡 Why this project matters

This project demonstrates the ability to:
- Work with real-world, imperfect data
- Build end-to-end ML pipelines
- Balance performance, interpretability, and realism
- Translate technical results into operational insights
""")

st.caption("End of Executive Summary")
