import joblib
from pathlib import Path as FilePath
from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd


class DifficultyRequest(BaseModel):
    accuracy: float
    avg_time: float
    hints_used: int

class DifficultyResponse(BaseModel):
    label: int
    probabilities: dict

# path do istreniranog modela
MODEL_PATH = FilePath(__file__).resolve().parents[2] / "model" / "model_output" / "mlr_model.pkl"

print("Path modela je:", MODEL_PATH)
model = joblib.load(MODEL_PATH)

router = APIRouter()

# endpoint za predikciju
@router.post("/predict", response_model=DifficultyResponse)
def predict_difficulty(data: DifficultyRequest):
    # preracunavamo u ispravan format
    X = pd.DataFrame([{
        "accuracy": data.accuracy,
        "avg_time": data.avg_time,
        "hints_used": data.hints_used
    }])

    # predikcija
    label = int(model.predict(X)[0])

    # vjerojatnosti svake labele
    proba = model.predict_proba(X)[0]
    prob_dict = {
        0: float(proba[0]),
        1: float(proba[1]),
        2: float(proba[2])
    }

    return DifficultyResponse(label=label, probabilities=prob_dict)
