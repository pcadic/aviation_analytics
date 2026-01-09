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
            dep_weather_severity, arr_weather_severity,
            dep_is_rain, dep_is_fog, dep_is_icing, dep_is_strong_wind
        """)
        .execute()
    )
    return pd.DataFrame(response.data)

df = load_data()

# ============================
# FEATURE ENGINEERING
# ============================
st.title("🧠 Flight Delay Risk Explorer")
st.caption("Machine learning models predicting the probability of flight delays")

# Unified delay logic
df["delay_minutes"] = np.where(
    df["dep_delayed"].notna(),
    df["dep_delayed"],
    df["arr_delayed"]
).fillna(0)

df["delay_risk"] = (df["delay_minutes"] > 15).astype(int)

# Route type
df["route_type"] = np.where(
    df["dep_country_ref"] == df["arr_country_ref"],
    "Domestic",
    "International"
)

# Weather severity (max of dep/arr)
df["weather_severity"] = df[
    ["dep_weather_severity", "arr_weather_severity"]
].max(axis=1)

# ============================
# SELECT FEATURES
# ============================
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
# PREPROCESSING PIPELINE
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

numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features)
    ]
)

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

# Optional XGBoost
try:
    from xgboost import XGBClassifier
    models["XGBoost"] = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42
    )
    xgb_available = True
except ImportError:
    xgb_available = False

# ============================
# TRAIN & EVALUATE
# ============================
st.subheader("📊 Model Performance (ROC-AUC)")

roc_results = {}
roc_curves = {}

for name, model in models.items():
    pipe = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ])
    
    pipe.fit(X_train, y_train)
    y_proba = pipe.predict_proba(X_test)[:, 1]
    
    roc_results[name] = roc_auc_score(y_test, y_proba)
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_curves[name] = (fpr, tpr)

# ============================
# ROC CURVE
# ============================
fig_roc = go.Figure()

for name, (fpr, tpr) in roc_curves.items():
    fig_roc.add_trace(
        go.Scatter(
            x=fpr,
            y=tpr,
            mode="lines",
            name=f"{name} (AUC={roc_results[name]:.2f})"
        )
    )

fig_roc.add_trace(
    go.Scatter(
        x=[0, 1],
        y=[0, 1],
        mode="lines",
        line=dict(dash="dash"),
        showlegend=False
    )
)

fig_roc.update_layout(
    xaxis_title="False Positive Rate",
    yaxis_title="True Positive Rate",
    title="ROC Curve – Delay Risk Prediction"
)

st.plotly_chart(fig_roc, use_container_width=True)

# ============================
# FEATURE IMPORTANCE (TREE MODELS)
# ============================
st.subheader("🔍 Feature Importance")

selected_model = st.selectbox(
    "Select model",
    [m for m in models.keys() if m != "Logistic Regression"]
)

model = models[selected_model]

pipe = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("model", model)
])

pipe.fit(X_train, y_train)

# Extract feature names
feature_names = (
    pipe.named_steps["preprocessor"]
    .get_feature_names_out()
)

importances = pipe.named_steps["model"].feature_importances_

fi = (
    pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    })
    .sort_values("importance", ascending=False)
    .head(15)
)

fig_fi = px.bar(
    fi.sort_values("importance"),
    x="importance",
    y="feature",
    orientation="h"
)

fig_fi.update_layout(
    xaxis_title="Importance",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_fi, use_container_width=True)

# ============================
# FOOTER
# ============================
st.caption(
    "Models trained on real flight, aircraft and weather data. "
    "Missing values handled via preprocessing pipelines."
)
