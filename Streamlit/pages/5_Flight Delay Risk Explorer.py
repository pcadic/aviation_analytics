import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client

# ML
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, roc_curve

import plotly.express as px
import plotly.graph_objects as go

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Flight Delay Risk Explorer",
    page_icon="🧠",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# LOAD DATA
# ============================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select("""
            dep_icao, arr_icao,
            dep_country_ref, arr_country_ref,
            dep_delayed, arr_delayed,
            duration,
            aircraft_type,
            avg_pax_estimated,
            dep_weather_severity, arr_weather_severity
        """)
        .execute()
    )
    return pd.DataFrame(response.data)

df = load_data()

st.title("🧠 Flight Delay Risk Explorer")
st.caption("Predicting the probability of flight delays using machine learning")

# ============================
# TARGET ENGINEERING
# ============================
delay_minutes = np.where(
    df["dep_delayed"].notna(),
    df["dep_delayed"],
    df["arr_delayed"]
)

df["delay_minutes"] = pd.Series(delay_minutes, index=df.index).fillna(0)
df["delay_risk"] = (df["delay_minutes"] > 15).astype(int)

# ============================
# FEATURE ENGINEERING
# ============================
df["route_type"] = np.where(
    df["dep_country_ref"] == df["arr_country_ref"],
    "Domestic",
    "International"
)

df["weather_severity"] = df[
    ["dep_weather_severity", "arr_weather_severity"]
].max(axis=1)

features = [
    "duration",
    "avg_pax_estimated",
    "weather_severity",
    "aircraft_type",
    "route_type"
]

df_model = df[features + ["delay_risk"]].dropna(subset=["delay_risk"])

X = df_model[features]
y = df_model["delay_risk"]

# ============================
# TRAIN / TEST SPLIT
# ============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.25,
    random_state=42,
    stratify=y
)

# ============================
# PREPROCESSING
# ============================
numeric_features = [
    "duration",
    "avg_pax_estimated",
    "weather_severity"
]

categorical_features = [
    "aircraft_type",
    "route_type"
]

numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_features),
    ("cat", categorical_transformer, categorical_features)
])

# ============================
# MODELS
# ============================
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42
    )
}

# ============================
# TRAIN RANDOM FOREST ONCE
# ============================
rf_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("model", models["Random Forest"])
])

rf_pipeline.fit(X_train, y_train)

# ============================
# PREDICTED DELAY RISK DISTRIBUTION
# ============================
st.subheader("Predicted Delay Risk Distribution")

y_proba_rf = rf_pipeline.predict_proba(X_test)[:, 1]

proba_df = pd.DataFrame({
    "Predicted Delay Risk": y_proba_rf
})

fig_dist = px.histogram(
    proba_df,
    x="Predicted Delay Risk",
    nbins=20
)

fig_dist.update_layout(
    xaxis_title="Predicted Delay Probability",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("""
**What this chart shows**

This distribution represents the predicted probability of delay for each flight
in the test dataset, as estimated by the Random Forest model.

Most flights cluster around low to moderate delay risk, indicating that under
normal operational and weather conditions, delays are relatively unlikely.
A smaller but significant tail of flights exhibits high predicted risk.

**Interpretation**

High predicted delay probabilities are typically associated with:
• Higher weather severity (departure or arrival)
• Longer flight duration
• Specific aircraft categories operating under adverse conditions

This confirms that delays are not random events but can be anticipated
based on measurable operational and environmental factors.
""")


# ============================
# ROC CURVES
# ============================
st.subheader("📊 Model Performance – ROC AUC")

roc_curves = {}
roc_scores = {}

for name, model in models.items():
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model)
    ])
    pipe.fit(X_train, y_train)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    roc_scores[name] = roc_auc_score(y_test, y_proba)
    roc_curves[name] = roc_curve(y_test, y_proba)

fig = go.Figure()

for name, (fpr, tpr, _) in roc_curves.items():
    fig.add_trace(go.Scatter(
        x=fpr,
        y=tpr,
        mode="lines",
        name=f"{name} (AUC={roc_scores[name]:.2f})"
    ))

fig.add_trace(go.Scatter(
    x=[0, 1],
    y=[0, 1],
    mode="lines",
    line=dict(dash="dash"),
    showlegend=False
))

fig.update_layout(
    xaxis_title="False Positive Rate",
    yaxis_title="True Positive Rate",
    title="ROC Curve – Delay Risk Prediction"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("""
**What this chart shows**

The ROC curve evaluates each model’s ability to distinguish between delayed
and non-delayed flights across all possible classification thresholds.

The diagonal line represents a random classifier, while curves above this line
indicate predictive skill.

**Interpretation**

The Random Forest model achieves a higher ROC-AUC score than Logistic Regression,
demonstrating a stronger ability to rank flights by delay risk.

This suggests that non-linear relationships — especially interactions between
weather severity, route characteristics, and aircraft type — play a critical
role in delay occurrence, which linear models struggle to capture.
""")


# ============================
# FEATURE IMPORTANCE
# ============================
st.subheader("🔍 Feature Importance (Random Forest)")

feature_names = rf_pipeline.named_steps["preprocessor"].get_feature_names_out()
importances = rf_pipeline.named_steps["model"].feature_importances_

fi = (
    pd.DataFrame({
        "Feature": feature_names,
        "Importance": importances
    })
    .sort_values("Importance", ascending=False)
    .head(15)
)

fig_fi = px.bar(
    fi.sort_values("Importance"),
    x="Importance",
    y="Feature",
    orientation="h"
)

fig_fi.update_layout(
    xaxis_title="Importance",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_fi, use_container_width=True)

st.markdown("""
**What this chart shows**

This chart displays the most influential features used by the Random Forest
model to predict flight delay risk.

Feature importance reflects how much each variable contributes to reducing
prediction uncertainty across the ensemble of decision trees.

**Interpretation**

Weather severity emerges as one of the strongest predictors, confirming its
central role in operational disruption.

Flight duration and aircraft-related features also contribute meaningfully,
highlighting that both environmental conditions and operational complexity
drive delay risk.

This aligns with real-world airline operations, where delays are rarely caused
by a single factor but by the interaction of multiple constraints.
""")

