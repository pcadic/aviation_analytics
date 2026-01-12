import streamlit as st

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Project Conclusion",
    page_icon="📌",
    layout="wide"
)

# ============================
# TITLE
# ============================
st.title("📌 Project Conclusion")
st.caption(
    "Summary, limitations, and future perspectives of the aviation analytics project"
)

st.divider()

# ============================
# PROJECT OVERVIEW
# ============================
st.header("🎯 Project Overview")

st.markdown("""
This project explores how aviation operational data can be transformed into
actionable insights using **data analytics and machine learning**.

The primary objectives were to:
- Understand flight delay patterns
- Evaluate delay risk and delay severity
- Build interpretable and deployable ML models
- Deliver insights through an interactive Streamlit application
""")

# ============================
# KEY TAKEAWAYS
# ============================
st.header("✅ Key Takeaways")

st.markdown("""
**1. Machine learning models can meaningfully capture delay patterns**  
Random Forest models consistently outperformed baseline models, achieving
ROC-AUC scores around **0.70–0.72**, which is solid given real-world data constraints.

**2. Flight delays are multi-factorial**  
Delays are driven by a combination of:
- Route characteristics (domestic vs international)
- Operational complexity
- Aircraft and network structure
rather than a single dominant variable.

**3. Interpretability matters**  
While more complex models exist, tree-based models provided the best balance
between performance and explainability for this dataset.
""")

# ============================
# MODEL PERFORMANCE CONTEXT
# ============================
st.header("📊 Interpreting Model Performance")

st.markdown("""
The observed performance levels should be interpreted in context:

- **AUC ≈ 0.52** indicates near-random performance (baseline)
- **AUC ≈ 0.72** reflects meaningful predictive signal in noisy operational data

In aviation analytics, where delays are influenced by many unobserved factors
(e.g. air traffic control, crew availability, cascading delays),
an AUC above **0.70** already represents valuable decision support.
""")

# ============================
# LIMITATIONS
# ============================
st.header("⚠️ Project Limitations")

st.markdown("""
**Data limitations**
- No real-time meteorological measurements (METAR)
- Passenger volumes are estimated, not actual
- No airline-specific operational data (crew, maintenance, rotations)

**Label quality**
- Delay labels are inferred from partial delay information
- Some delay causes remain unobservable

**Temporal limitations**
- No time-of-day, day-of-week, or seasonality features
- No modeling of delay propagation between flights

**Geographic scope**
- Network centered around **CYVR**
- Limited representation of ultra-congested global hubs
""")

# ============================
# DATA & ENGINEERING CHOICES
# ============================
st.header("🗂 Data & Engineering Choices")

st.markdown("""
- Data sourced primarily from **AirLabs API (free tier)**
- Extensive use of **database views** to centralize cleaning and enrichment
- Feature engineering focused on:
  - Operational realism
  - Robustness
  - Interpretability over raw performance

These decisions reflect a **production-oriented mindset** rather than a purely academic approach.
""")

# ============================
# FUTURE IMPROVEMENTS
# ============================
st.header("🚀 Future Improvements")

st.markdown("""
**Data enhancements**
- Integration of real METAR weather data
- Time-based features (hour, weekday, seasonality)
- Airline-level and aircraft age data

**Modeling improvements**
- Gradient Boosting (XGBoost / LightGBM)
- Multiclass delay severity modeling
- Time-series and delay propagation models

**Product extensions**
- Real-time delay risk scoring
- Route reliability benchmarking
- Scenario simulations under weather disruption
""")

# ============================
# FINAL MESSAGE
# ============================
st.divider()

st.header("🧠 Final Remarks")

st.markdown("""
This project demonstrates the ability to:
- Work with imperfect real-world data
- Design end-to-end ML pipelines
- Balance performance, interpretability, and realism
- Communicate uncertainty and limitations clearly
- Build deployable analytical applications

Overall, the project emphasizes **practical machine learning applied to aviation operations**,
rather than theoretical model optimization.
""")

st.caption("End of project")
