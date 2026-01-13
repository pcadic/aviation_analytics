# ✈️ Aviation Analytics & Flight Delay Intelligence

An end-to-end **aviation analytics and machine learning project** focused on flight operations, route networks, weather impact, and delay risk modeling.

This project combines **data engineering**, **interactive dashboards**, and **machine learning models**, using real-world aviation data enriched with aircraft, airport, and weather features.

---

## 🎯 Project Objectives

- Analyze airline operations and route networks  
- Understand the impact of weather and operational factors on delays  
- Build interpretable machine learning models to:
  - Predict **delay risk** (classification)
  - Estimate **delay severity** (regression / multiclass)
- Deliver insights through **interactive Streamlit dashboards**

This project is designed as a **portfolio-grade case study**, showcasing applied data analytics and ML skills in an aviation context.

---

## 🧱 Tech Stack

### Data & Backend
- **Supabase (PostgreSQL)**
  - Centralized data storage
  - SQL views for clean analytical layers
- **Custom SQL views**
  - `v_flights_enriched` (flights + aircraft + airports + weather)

### Analytics & Machine Learning
- **Python**
- **Pandas / NumPy**
- **scikit-learn**
  - Logistic Regression
  - Random Forest  
- *(XGBoost explored conceptually, unavailable in current environment)*

### Visualization & App
- **Streamlit**
- **Plotly**
- **OpenStreetMap (OSM)** for geospatial visualization

---

## Application Pages Overview

### Overview & Operational Insights
- Flight volume and operational KPIs
- Weather impact indicators (rain, wind, fog, icing)
- Delay-related metrics

---

### Route Network Analysis
- CYVR (Vancouver) hub-focused analysis
- Interactive **OSM heatmap** showing destination density
- Domestic vs International route filtering
- Top destinations visualization (without exposing raw flight counts)

---

### Flight Delay Risk Explorer (Machine Learning)

**Binary classification: Delay Risk (>15 minutes)**

**Models**
- Logistic Regression (baseline, interpretable)
- Random Forest (non-linear interactions)

**Key outputs**
- ROC curves & AUC comparison
- Predicted delay risk distribution
- Feature importance analysis

**Observed performance**
- Logistic Regression: ~0.52 AUC  
- Random Forest: ~0.72 AUC  

→ Indicates meaningful signal captured from weather and operational features.

---

### Delay Severity Prediction
- Regression / multiclass framing of delay duration
- Focus on **severity levels** rather than delayed vs not delayed
- Highlights escalation of operational risk under adverse conditions

---

### Executive Summary
- Key analytical findings
- Business interpretation
- Project limitations
- Strategic and technical next steps

---

## 🧠 Machine Learning Approach

### Target Engineering
- Delay minutes derived from departure or arrival delays
- Risk threshold: **>15 minutes**

### Feature Examples
- Weather severity (departure & arrival)
- Aircraft type
- Route type (Domestic / International)
- Estimated passenger capacity
- Flight duration

### Model Rationale
- **Logistic Regression**: transparency, baseline benchmark
- **Random Forest**: captures non-linear interactions common in aviation operations

---

## Project Limitations

- Data sourced from free-tier aviation APIs
- No real passenger load, crew scheduling, or ATC constraints
- Weather features are simplified proxies
- Class imbalance impacts baseline model performance

These limitations are explicitly acknowledged and reflected in model interpretation.

---

## Future Improvements

- Add temporal features (hour of day, seasonality)
- Integrate external weather APIs (METAR / TAF)
- Deploy gradient boosting models in a production environment
- Expand to airline-level or airport-level delay profiling


