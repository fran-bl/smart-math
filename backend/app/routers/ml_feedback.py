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
    sample_weight: float


@router.post("/feedback")
def feedback(data: FeedbackRequest):
    return feedback_function(data)


def feedback_function(data: FeedbackRequest):
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
            [data.true_label],
            sample_weight=[data.sample_weight]
        )

        maybe_persist()

    return {"status": "learned"}


def derive_true_label(prev_round, next_round, eps=0.1):
    delta_acc = next_round.accuracy - prev_round.accuracy

    if delta_acc > eps:
        return 2
    elif delta_acc < -eps:
        return 0
    else:
        return 1
