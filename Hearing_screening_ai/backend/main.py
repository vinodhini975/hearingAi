from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import numpy as np
import os

app = FastAPI(title="AI Hearing Screening API")

# Enable CORS so your React frontend can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from React frontend (localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained AI model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hearing_model.pkl")

try:
    model = joblib.load(MODEL_PATH)
    print("✅ Hearing AI Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

# Input schema matching the 10 frequency thresholds
class HearingTestInput(BaseModel):
    L_1000: float
    L_2000: float
    L_4000: float
    L_6000: float
    L_8000: float
    R_1000: float
    R_2000: float
    R_4000: float
    R_6000: float
    R_8000: float

@app.get("/")
def read_root():
    return {"status": "online", "message": "Hearing Assessment AI Engine Running"}

@app.post("/predict")
def predict_hearing_pattern(data: HearingTestInput):
    if model is None:
        raise HTTPException(status_code=500, detail="AI Model is not loaded.")

    # Convert input features to 2D array for scikit-learn
    features = np.array([[
        data.L_1000, data.L_2000, data.L_4000, data.L_6000, data.L_8000,
        data.R_1000, data.R_2000, data.R_4000, data.R_6000, data.R_8000
    ]])

    # Make prediction & probability confidence
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    confidence = float(np.max(probabilities)) * 100

    return {
        "predicted_pattern": prediction,
        "confidence_percentage": round(confidence, 2),
        "status": "success"
    }