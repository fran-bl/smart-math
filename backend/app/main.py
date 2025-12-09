from fastapi import FastAPI
from .routers import health, test_db, ml_predict

app = FastAPI(title="SmartMath API", version="0.1.0")

# Routeri
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(test_db.router, prefix="/test", tags=["test"])
app.include_router(ml_predict.router, prefix="/difficulty", tags=["ML Model - predict difficulty"])

@app.get("/")
def root():
    return "Backend is running!"

