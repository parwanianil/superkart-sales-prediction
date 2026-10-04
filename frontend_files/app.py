
# Import the required libraries
import io
import os

import pandas as pd
import requests
import streamlit as st

# URL of the Flask backend
# (inside docker-compose the backend is reachable by its service name; it can be overridden with an environment variable)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:7860").rstrip("/")

# Reference year used to compute store age (current year, same as in model training)
from datetime import datetime
REFERENCE_YEAR = datetime.now().year

# Product types grouped as perishable (same grouping as in model training)
PERISHABLES = ["Dairy", "Meat", "Fruits and Vegetables", "Breakfast", "Breads", "Seafood"]

# Product types belonging to the Drinks (DR) and Non-Consumable (NC) groups; all others are Food (FD)
DRINKS = ["Soft Drinks", "Hard Drinks"]
NON_CONSUMABLES = ["Household", "Health and Hygiene", "Others"]

PRODUCT_TYPES = [
    "Fruits and Vegetables", "Snack Foods", "Frozen Foods", "Dairy", "Household", "Baking Goods",
    "Canned", "Health and Hygiene", "Meat", "Soft Drinks", "Breads", "Hard Drinks", "Others",
    "Starchy Foods", "Breakfast", "Seafood",
]

# Page setup
st.set_page_config(page_title="SuperKart Sales Prediction", page_icon="🛒")
st.title("SuperKart Sales Prediction App")
st.write("This tool forecasts the total sales revenue of a product in a store, based on the product and store details.")

tab_single, tab_batch = st.tabs(["Single Prediction", "Batch Prediction"])

# ---------------- Online (single) prediction ----------------
with tab_single:
    st.subheader("Enter the product details:")
    product_type = st.selectbox("Product Type", PRODUCT_TYPES)
    product_weight = st.number_input("Product Weight", min_value=0.0, max_value=50.0, value=12.66, step=0.1)
    product_sugar_content = st.selectbox("Product Sugar Content", ["Low Sugar", "Regular", "No Sugar"])
    product_allocated_area = st.number_input("Product Allocated Area (ratio of display area)", min_value=0.0, max_value=1.0, value=0.068, step=0.001, format="%.3f")
    product_mrp = st.number_input("Product MRP", min_value=0.0, max_value=500.0, value=147.0, step=1.0)

    st.subheader("Enter the store details:")
    store_establishment_year = st.number_input("Store Establishment Year", min_value=1950, max_value=REFERENCE_YEAR, value=2009, step=1)
    store_size = st.selectbox("Store Size", ["Medium", "High", "Small"])
    store_location_city_type = st.selectbox("Store Location City Type", ["Tier 2", "Tier 1", "Tier 3"])
    store_type = st.selectbox("Store Type", ["Supermarket Type2", "Supermarket Type1", "Departmental Store", "Food Mart"])

    # Derive the engineered features in the same way as in model training
    if product_type in DRINKS:
        Product_Cat_Code = "DR"
    elif product_type in NON_CONSUMABLES:
        Product_Cat_Code = "NC"
    else:
        Product_Cat_Code = "FD"
    product_type_category = "Perishables" if product_type in PERISHABLES else "Non Perishables"
    store_age_years = REFERENCE_YEAR - int(store_establishment_year)

    # Build the payload expected by the Flask API
    payload = {
        "Product_Weight": product_weight,
        "Product_Sugar_Content": product_sugar_content,
        "Product_Allocated_Area": product_allocated_area,
        "Product_MRP": product_mrp,
        "Store_Size": store_size,
        "Store_Location_City_Type": store_location_city_type,
        "Store_Type": store_type,
        "Product_Cat_Code": Product_Cat_Code,
        "Store_Age_Years": store_age_years,
        "Product_Type_Category": product_type_category,
    }

    if st.button("Predict Sales"):
        try:
            response = requests.post(f"{BACKEND_URL}/v1/predict", json=payload, timeout=30)
            if response.status_code == 200:
                predicted_sales = response.json()["Predicted Sales"]
                st.success(f"Predicted Product Store Sales Total: {predicted_sales:,.2f}")
            else:
                st.error(f"Error from the API ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as error:
            st.error(f"Could not connect to the backend API at {BACKEND_URL}: {error}")

# ---------------- Batch prediction ----------------
with tab_batch:
    st.subheader("Upload a CSV file for batch prediction")
    st.write(
        "Upload a file in the same format as the SuperKart data (e.g. Batch_Data_SuperKart.csv). "
        "The API derives the model features automatically. A file that already contains the 10 model "
        "features is also accepted."
    )
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None and st.button("Predict Batch"):
        file_bytes = uploaded_file.getvalue()
        try:
            response = requests.post(f"{BACKEND_URL}/v1/predictbatch", files={"file": file_bytes}, timeout=120)
            if response.status_code == 200:
                predictions = response.json()
                result_df = pd.read_csv(io.BytesIO(file_bytes))
                result_df["Predicted_Sales"] = [predictions[str(index)] for index in result_df.index]
                st.success(f"Predictions generated for {len(result_df)} rows.")
                st.dataframe(result_df)
                st.download_button(
                    "Download predictions as CSV",
                    result_df.to_csv(index=False).encode("utf-8"),
                    file_name="superkart_batch_predictions.csv",
                    mime="text/csv",
                )
            else:
                st.error(f"Error from the API ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as error:
            st.error(f"Could not connect to the backend API at {BACKEND_URL}: {error}")
