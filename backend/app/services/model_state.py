import joblib
from pathlib import Path
from threading import Lock

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "model_output" / "model.pkl"
SCALER_PATH = Path(__file__).resolve().parents[2] / "model" / "model_output" / "scaler.pkl"

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

lock = Lock()

UPDATE_EVERY = 10
_update_count = 0


def maybe_persist():
    global _update_count
    _update_count += 1

    if _update_count % UPDATE_EVERY == 0:
        joblib.dump(model, MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
