from backend.app.routers import game_router
from fastapi import FastAPI
from .routers import health, test_db
from .routers.auth import router as auth
from .routers.classroom_router import router as classroom_router
from app import  socketio



app = FastAPI(title="SmartMath API", version="0.1.0")

# Routeri
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(test_db.router, prefix="/test", tags=["test"])
app.include_router(auth)
app.include_router(classroom_router)
app.include_router(game_router)

@app.get("/")
def root():
    return "Backend is running!"

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

