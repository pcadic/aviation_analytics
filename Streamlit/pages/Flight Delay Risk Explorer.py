import streamlit as st
import pandas as pd
import numpy as np

from supabase import create_client

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

from sklearn.metrics import (
    roc_auc_score,
    classification_report,
    confusion_matrix
)

import plotly.express as px
import plotly.graph_objects as go

# ============================
# PAGE CONFIG
# ============================
st.set_page_config(
    page_title="Delay Risk Prediction (ML)",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Flight Delay Risk Prediction")
st.caption("Machine Learning models trained on real operational and weather data")

# ============================
# SUPABASE CONNECTION
# ============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HUB = "CYVR"

# ============================
# LOAD DATA FROM VIEW
# ============================
@st.cache_data
def load_data():
    response = (
        supabase
        .table("v_flights_enriched")
        .select("*")
        .execute()
    )
    return pd.DataFrame(response.data)

df = load_data()

# ============================
# BASIC CLEANING
# ============================
df = df[df["dep_icao"] == HUB].copy()

df["dep_delay"] = df["dep_delayed"].fillna(0)
df["is_delayed"] = (df["dep_delay"] > 15).astype(int)

df["dep_hour"] = pd.to_datetime(df["dep_time_utc"]).dt.hour
df["day_of_week"] = pd.to_datetime(df["dep_time_utc"]).dt.dayofweek

df["is_domestic"] = (
    df["dep_country_ref"] == df["arr_country_ref"]
).astype(int)

# Drop rows missing critical features
df = df.dropna(subset=[
    "duration",
    "avg_pax_estimated",
    "aircraft_type",
    "airline_name",
    "dep_weather_severity"
])

# ============================
# FEATURE SET
# ============================
target = "is_delayed"

numeric_features = [
    "duration",
    "avg_pax_estimated",
    "aircraft_age",
    "dep_hour"
]

categorical_features = [
    "airline_name",
    "aircraft_type",
    "dep_continent",
    "arr_continent"
]

binary_features = [
    "is_domestic",
    "dep_is_rain",
    "dep_is_fog",
    "dep_is_icing",
    "dep_is_strong_wind",
    "dep_weather_severity"
]

features = numeric_features + categorical_features + binary_features

X = df[features]
y = df[target]

# ============================
# TRAIN / TEST SPLIT
# ============================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)

# ============================
# PREPROCESSING
# ============================
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ("bin", "passthrough", binary_features)
    ]
)

# ============================
# MODEL SELECTION
# ============================
model_choice = st.selectbox(
    "Select Machine Learning Model",
    [
        "Logistic Regression",
        "Random Forest",
        "Gradient Boosting"
    ]
)

if model_choice == "Logistic Regression":
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
elif model_choice == "Random Forest":
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=20,
        random_state=42
    )
else:
    model = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        random_state=42
    )

# ============================
# PIPELINE
# ============================
pipeline = Pipeline(
    steps=[
        ("preprocessing", preprocessor),
        ("model", model)
    ]
)

# ============================
# TRAIN MODEL
# ============================
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
y_proba = pipeline.predict_proba(X_test)[:, 1]

roc = roc_auc_score(y_test, y_proba)

# ============================
# KPI METRICS
# ============================
col1, col2, col3 = st.columns(3)

col1.metric("Training samples", len(X_train))
col2.metric("Test samples", len(X_test))
col3.metric("ROC AUC", round(roc, 3))

st.divider()

# ============================
# CONFUSION MATRIX
# ============================
cm = confusion_matrix(y_test, y_pred)

fig_cm = px.imshow(
    cm,
    text_auto=True,
    labels=dict(x="Predicted", y="Actual"),
    x=["On Time", "Delayed"],
    y=["On Time", "Delayed"],
    title="Confusion Matrix"
)

st.plotly_chart(fig_cm, width="stretch")

# ============================
# FEATURE IMPORTANCE
# ============================
st.subheader("Feature Importance")

if model_choice == "Logistic Regression":
    feature_names = (
        pipeline.named_steps["preprocessing"]
        .get_feature_names_out()
    )

    coefs = pipeline.named_steps["model"].coef_[0]

    importance = (
        pd.DataFrame({
            "feature": feature_names,
            "importance": np.abs(coefs)
        })
        .sort_values("importance", ascending=False)
        .head(15)
    )

else:
    feature_names = (
        pipeline.named_steps["preprocessing"]
        .get_feature_names_out()
    )

    importances = pipeline.named_steps["model"].feature_importances_

    importance = (
        pd.DataFrame({
            "feature": feature_names,
            "importance": importances
        })
        .sort_values("importance", ascending=False)
        .head(15)
    )

fig_imp = px.bar(
    importance.sort_values("importance"),
    x="importance",
    y="feature",
    orientation="h"
)

fig_imp.update_layout(
    xaxis_title="Importance",
    yaxis_title="",
    showlegend=False
)

st.plotly_chart(fig_imp, width="stretch")

# ============================
# INTERPRETATION
# ============================
st.info(
    """
**Model interpretation**
- Weather severity and operational context strongly influence delay risk.
- Aircraft type and airline effects are captured through categorical encoding.
- Model uses only pre-departure information (no data leakage).
"""
)
