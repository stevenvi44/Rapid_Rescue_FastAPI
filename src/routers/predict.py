import os
import pickle
import numpy as np
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predict",
    tags=["AI Preventive Maintenance"]
)

# --- Schemas ---
class PredictionInput(BaseModel):
    engine_rpm: float
    lub_oil_pressure: float
    fuel_pressure: float
    coolant_pressure: float
    lub_oil_temp: float
    coolant_temp: float
    temp_difference: float

class PredictionResult(BaseModel):
    condition: str
    confidence: float
    is_normal: bool
    message: str

class FeatureRanges(BaseModel):
    engine_rpm: Tuple[float, float]
    lub_oil_pressure: Tuple[float, float]
    fuel_pressure: Tuple[float, float]
    coolant_pressure: Tuple[float, float]
    lub_oil_temp: Tuple[float, float]
    coolant_temp: Tuple[float, float]
    temp_difference: Tuple[float, float]

class FeatureDescriptions(BaseModel):
    engine_rpm: str
    lub_oil_pressure: str
    fuel_pressure: str
    coolant_pressure: str
    lub_oil_temp: str
    coolant_temp: str
    temp_difference: str

# --- Configuration ---
custom_ranges = {
    'engine_rpm': (61.0, 2239.0),
    'lub_oil_pressure': (0.003384, 7.265566),
    'fuel_pressure': (0.003187, 21.138326),
    'coolant_pressure': (0.002483, 7.478505),
    'lub_oil_temp': (71.321974, 89.580796),
    'coolant_temp': (61.673325, 195.527912),
    'temp_difference': (-22.669427, 119.008526)
}

feature_descriptions = {
    'engine_rpm': 'Revolution per minute of the engine.',
    'lub_oil_pressure': 'Pressure of the lubricating oil.',
    'fuel_pressure': 'Pressure of the fuel.',
    'coolant_pressure': 'Pressure of the coolant.',
    'lub_oil_temp': 'Temperature of the lubricating oil.',
    'coolant_temp': 'Temperature of the coolant.',
    'temp_difference': 'Temperature difference between components.'
}

# --- Model Loader ---
def get_model_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(base_dir)
    return os.path.join(src_dir, 'AI_model', 'models', 'model.pkl')

def load_model():
    model_path = get_model_path()
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    if not all(hasattr(model, attr) for attr in ['predict', 'predict_proba']):
        raise AttributeError("Model missing required methods: predict, predict_proba")
    logger.info("Model loaded successfully")
    return model

try:
    model = load_model()
except Exception as e:
    logger.error(f"Model initialization failed: {e}")
    model = None

# --- Prediction Route ---
@router.post("/engine_condition", response_model=PredictionResult)
async def predict_engine_condition(input_data: PredictionInput):
    if model is None:
        logger.error("Prediction attempted but model not loaded")
        raise HTTPException(status_code=503, detail="Model not loaded - check server logs")

    try:
        input_features = np.array([
            input_data.engine_rpm,
            input_data.lub_oil_pressure,
            input_data.fuel_pressure,
            input_data.coolant_pressure,
            input_data.lub_oil_temp,
            input_data.coolant_temp,
            input_data.temp_difference
        ]).reshape(1, -1)

        logger.info(f"Input array prepared with shape: {input_features.shape}")

        prediction = model.predict(input_features)[0]
        confidence_scores = model.predict_proba(input_features)[0]
        logger.info(f"Prediction: {prediction}, Confidence scores: {confidence_scores}")

        confidence = round(confidence_scores[0] * 100, 2)  # Always show confidence of class 0 (normal)
        condition = "normal" if prediction == 0 else "warning"
        is_normal = prediction == 0

        if is_normal:
            message = f"The engine is predicted to be in a normal condition. The Confidence level of the machine is: {confidence:.2f}%"
        else:
            message = f"Warning! Please investigate further. The Confidence level of the machine is: {confidence:.2f}%"

        return {
            "condition": condition,
            "confidence": confidence,
            "is_normal": is_normal,
            "message": message
        }

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")

# --- Info Routes ---
@router.get("/feature_ranges", response_model=FeatureRanges)
async def get_feature_ranges():
    return custom_ranges

@router.get("/feature_descriptions", response_model=FeatureDescriptions)
async def get_feature_descriptions():
    return feature_descriptions

@router.get("/model_status")
async def get_model_status():
    return {
        "loaded": model is not None,
        "location": get_model_path() if model else None
    }
