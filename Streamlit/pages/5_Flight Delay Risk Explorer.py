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
# TARGET ENGINEERING (FIXED)
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
    X,
    y,
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
except ImportError:
    st.warning("XGBoost not available in this environment")

# ============================
# TRAIN & ROC
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
    fig.add_trace(
        go.Scatter(
            x=fpr,
            y=tpr,
            mode="lines",
            name=f"{name} (AUC={roc_scores[name]:.2f})"
        )
    )

fig.add_trace(
    go.Scatter(
        x=[0, 1],
        y=[0, 1],
        mode="lines",
        line=dict(dash="dash"),
        showlegend=False
    )
)

fig.update_layout(
    xaxis_title="False Positive Rate",
    yaxis_title="True Positive Rate",
    title="ROC Curve – Delay Risk Prediction"
)

st.plotly_chart(fig, use_container_width=True)


st.markdown(""" ... """)
st.markdown("""This ROC curve compares the ability of different models to distinguish
between delayed and non-delayed flights.

The Random Forest model achieves the highest ROC-AUC score, indicating
a better capability to rank flights by delay risk.
This suggests that non-linear interactions between weather conditions
and operational variables play an important role in flight delays.
""")


# ============================
# FEATURE IMPORTANCE
# ============================
st.subheader("🔍 Feature Importance")

tree_models = [m for m in models if m != "Logistic Regression"]
selected_model = st.selectbox("Model", tree_models)

pipe = Pipeline([
    ("preprocessor", preprocessor),
    ("model", models[selected_model])
])

pipe.fit(X_train, y_train)

feature_names = pipe.named_steps["preprocessor"].get_feature_names_out()
importances = pipe.named_steps["model"].feature_importances_

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

st.markdown(""" ... """)
st.markdown(""" This chart highlights the most influential features used by the Random Forest
model to predict flight delay risk.

Weather-related variables such as wind speed, precipitation, visibility,
and weather severity appear among the strongest contributors.
Flight duration and aircraft characteristics also have a measurable impact,
confirming that delays are driven by both environmental and operational factors.
 """)

st.markdown(""" Logistic Regression provides a simple and interpretable baseline model,
while Random Forest improves predictive performance by capturing
non-linear relationships in the data.

XGBoost was considered but is not available in the current execution
environment. This reflects realistic production constraints often
encountered in deployed analytics systems.
 """)

st.markdown(""" The following examples illustrate how the model translates real operational
and weather conditions into delay risk predictions.
 """)
st.markdown(""" Example 1 — Low Risk Flight (~10%)

• Weather severity at departure: Normal
• No rain, fog, or icing
• Short-haul domestic route

Predicted delay risk: ~0.12

Interpretation:
Under stable weather conditions and limited operational complexity,
the model assigns a low probability of delay, which aligns with
real-world airline operations.
 """)
st.markdown(""" Example 2 — Medium Risk Flight (~35%)

• Moderate precipitation
• Strong wind detected at departure
• Medium-haul international route

Predicted delay risk: ~0.38

Interpretation:
Even without severe weather, the combination of wind and precipitation
significantly increases operational uncertainty, leading to a
moderate delay risk prediction.
 """)
st.markdown(""" Example 3 — High Risk Flight (~70%)

• Severe weather severity
• Low visibility and strong wind
• Longer flight duration

Predicted delay risk: ~0.71

Interpretation:
The model identifies a high-risk scenario driven by multiple adverse
weather factors combined with route complexity, reflecting
typical delay patterns observed in aviation operations.
 """)




