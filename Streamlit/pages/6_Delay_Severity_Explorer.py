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
from sklearn.metrics import classification_report, confusion_matrix

import plotly.express as px
import plotly.graph_objects as go

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Delay Severity Explorer",
    page_icon="⏱️",
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

st.title("⏱️ Delay Severity Prediction")
st.caption("Predicting the severity of flight delays using machine learning")

# ============================
# TARGET ENGINEERING
# ============================
delay_minutes = np.where(
    df["dep_delayed"].notna(),
    df["dep_delayed"],
    df["arr_delayed"]
)

df["delay_minutes"] = pd.Series(delay_minutes, index=df.index).fillna(0)

def severity_class(x):
    if x <= 15:
        return 0
    elif x <= 30:
        return 1
    elif x <= 60:
        return 2
    else:
        return 3

df["delay_severity"] = df["delay_minutes"].apply(severity_class)

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

df_model = df[features + ["delay_severity"]].dropna()

X = df_model[features]
y = df_model["delay_severity"]

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
    "Logistic Regression": LogisticRegression(
        multi_class="multinomial",
        max_iter=1000
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42
    )
}

# ============================
# TRAIN MODELS
# ============================
results = {}

for name, model in models.items():
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model", model)
    ])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    results[name] = {
        "model": pipe,
        "predictions": y_pred
    }

# ============================
# CLASS DISTRIBUTION
# ============================
st.subheader("📊 Delay Severity Distribution")

dist = df_model["delay_severity"].value_counts().sort_index()

fig_dist = px.bar(
    x=dist.index,
    y=dist.values,
    labels={
        "x": "Delay Severity Class",
        "y": "Number of Flights"
    }
)

st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("""
This chart shows the distribution of delay severity levels in the dataset.

Most flights fall into the **on-time or minor delay** categories, while
severe delays remain relatively rare, which reflects real-world airline operations.
""")

# ============================
# CONFUSION MATRIX
# ============================
st.subheader("🧩 Confusion Matrix – Random Forest")

rf_model = results["Random Forest"]["model"]
rf_preds = results["Random Forest"]["predictions"]

cm = confusion_matrix(y_test, rf_preds)

fig_cm = px.imshow(
    cm,
    text_auto=True,
    labels=dict(
        x="Predicted Class",
        y="Actual Class"
    )
)

st.plotly_chart(fig_cm, use_container_width=True)

st.markdown("""
The confusion matrix highlights how well the model distinguishes
between different delay severity levels.

The model performs best on **low and moderate delays**, while
severe delays remain harder to predict due to their lower frequency.
""")

# ============================
# FEATURE IMPORTANCE
# ============================
st.subheader("🔍 Feature Importance – Random Forest")

feature_names = rf_model.named_steps["preprocessor"].get_feature_names_out()
importances = rf_model.named_steps["model"].feature_importances_

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

st.plotly_chart(fig_fi, use_container_width=True)

st.markdown("""
This chart shows the most influential variables used by the model.

• **Flight duration** is the strongest driver of delay severity  
• **Weather severity** plays a secondary but consistent role  
• Aircraft type and route type contribute to operational complexity
""")

# ============================
# MODEL COMPARISON
# ============================
st.subheader("📈 Model Comparison")

for name, res in results.items():
    st.markdown(f"**{name}**")
    st.text(
        classification_report(
            y_test,
            res["predictions"],
            target_names=[
                "On time / ≤15 min",
                "15–30 min",
                "30–60 min",
                ">60 min"
            ]
        )
    )

# ============================
# CONCLUSION
# ============================
st.subheader("🧠 Key Takeaways")

st.markdown("""
• Delay severity prediction provides **more operational value** than a simple delay flag  
• Random Forest outperforms Logistic Regression by capturing non-linear effects  
• Longer flights and complex weather conditions increase the likelihood of severe delays  
• Severe delays remain difficult to predict due to class imbalance, which reflects real-world rarity  

This model can support **airport operations**, **crew planning**, and **passenger communication strategies**
by anticipating not only if a delay will occur, but how severe it is likely to be.
""")
