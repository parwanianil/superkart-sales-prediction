
# Import the required libraries
import joblib
import pandas as pd
from flask import Flask, request, jsonify

# Initialize the Flask application
superkart_api = Flask("SuperKart Sales Predictor")
superkart_api.json.sort_keys = False  # keep batch predictions in the original row order

# Load the serialized model pipeline (preprocessing + tuned Random Forest)
model = joblib.load("superkart_sales_prediction_model_v1_0.joblib")

# Reference year and perishable product types (same as in model training, Sections 6 and 8)
from datetime import datetime
REFERENCE_YEAR = datetime.now().year
PERISHABLES = ["Dairy", "Meat", "Fruits and Vegetables", "Breakfast", "Breads", "Seafood"]

# Feature columns expected by the model (same as the features used in training)
FEATURES = [
    "Product_Weight",
    "Product_Allocated_Area",
    "Product_MRP",
    "Store_Age_Years",
    "Product_Cat_Code",
    "Product_Type_Category",
    "Product_Sugar_Content",
    "Store_Size",
    "Store_Location_City_Type",
    "Store_Type",
]


# Function to apply the same data cleaning and feature engineering as in training (Sections 6 and 8)
# (lets the API accept data in the raw SuperKart format as well as the model-ready format)
def prepare_features(df):
    df = df.copy()
    # Merge the abbreviated label 'reg' into 'Regular'
    if "Product_Sugar_Content" in df.columns:
        df["Product_Sugar_Content"] = df["Product_Sugar_Content"].replace({"reg": "Regular"})
    # Derive the product-group code from the first two letters of Product_Id
    if "Product_Cat_Code" not in df.columns and "Product_Id" in df.columns:
        df["Product_Cat_Code"] = df["Product_Id"].astype(str).str[:2]
    # Derive store age from the establishment year
    if "Store_Age_Years" not in df.columns and "Store_Establishment_Year" in df.columns:
        df["Store_Age_Years"] = REFERENCE_YEAR - df["Store_Establishment_Year"]
    # Group product types into Perishables and Non Perishables
    if "Product_Type_Category" not in df.columns and "Product_Type" in df.columns:
        df["Product_Type_Category"] = df["Product_Type"].isin(PERISHABLES).map({True: "Perishables", False: "Non Perishables"})
    return df


# Home route to check that the API is running
@superkart_api.get("/")
def home():
    return "Welcome to the SuperKart Sales Prediction API!"


# Endpoint for online (single) inference
@superkart_api.post("/v1/predict")
def predict_sales():
    # Read the JSON payload sent in the request
    data = request.get_json()

    # Check that all the required features are present
    missing = [feature for feature in FEATURES if feature not in data]
    if missing:
        return jsonify({"error": f"Missing features: {missing}"}), 400

    # Convert the input into a single-row DataFrame with the expected columns
    input_df = pd.DataFrame([{feature: data[feature] for feature in FEATURES}])

    # Predict the sales and return the result as JSON
    prediction = model.predict(input_df)[0]
    return jsonify({"Predicted Sales": round(float(prediction), 2)})


# Endpoint for batch inference (CSV file upload)
@superkart_api.post("/v1/predictbatch")
def predict_sales_batch():
    # Check that a file was uploaded under the key 'file'
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send the CSV file under the key 'file'."}), 400

    # Read the uploaded CSV file and apply the same feature engineering as in training
    input_df = prepare_features(pd.read_csv(request.files["file"]))

    # Check that all the required features are present
    missing = [feature for feature in FEATURES if feature not in input_df.columns]
    if missing:
        return jsonify({"error": f"Missing columns: {missing}"}), 400

    # Predict the sales for all rows
    predictions = model.predict(input_df[FEATURES])

    # Return the predictions as a dictionary of {row index: predicted sales}
    result = {str(index): round(float(pred), 2) for index, pred in zip(input_df.index, predictions)}
    return jsonify(result)


# Run the app locally (inside Docker, gunicorn is used instead)
if __name__ == "__main__":
    superkart_api.run(host="0.0.0.0", port=7860, debug=False)
