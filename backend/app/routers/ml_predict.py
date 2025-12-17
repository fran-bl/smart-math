from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd

from app.services.model_state import model, scaler


class DifficultyRequest(BaseModel):
    accuracy: float
    avg_time: float
    hints_used: int

class DifficultyResponse(BaseModel):
    label: int
    probabilities: dict

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

    # skaliranje
    X_scaled = scaler.transform(X)

    # predikcija
    label = int(model.predict(X_scaled)[0])

    # vjerojatnosti svake labele
    proba = model.predict_proba(X_scaled)[0]
    prob_dict = {int(c): float(p) for c, p in zip(model.classes_, proba)}

    return DifficultyResponse(label=label, probabilities=prob_dict)
