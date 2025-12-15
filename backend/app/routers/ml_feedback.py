import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.model_state import model, scaler, lock, maybe_persist

router = APIRouter()


class FeedbackRequest(BaseModel):
    accuracy: float
    avg_time: float
    hints_used: int
    true_label: int


@router.post("/feedback")
def feedback(data: FeedbackRequest):
    X = pd.DataFrame([{
        "accuracy": data.accuracy,
        "avg_time": data.avg_time,
        "hints_used": data.hints_used
    }])

    # zakljucavamo thread dok se model uci na novom primjeru (zbog mogucih race conditiona)
    with lock:
        scaler.partial_fit(X)
        X_scaled = scaler.transform(X)

        model.partial_fit(
            X_scaled,
            [data.true_label], # TODO: odredit pravu labelu po nekom kriteriju
            sample_weight=[5.0] # TODO: odredit dobar sample weight - zasad svaki pravi primjer 5x "vazniji" od sintetickog
        )

        maybe_persist()

    return {"status": "learned"}
