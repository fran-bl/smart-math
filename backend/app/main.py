
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import health, test_db, ml_predict, ml_feedback
from .routers.auth import router as auth
from .routers.classroom_router import router as classroom_router
from .routers.game_router import router as game_router

import socketio


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)



app = FastAPI(title="SmartMath API", version="0.1.0")
socket_app = socketio.ASGIApp(sio)
app.mount("/ws", socket_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routeri
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(test_db.router, prefix="/test", tags=["test"])
app.include_router(ml_predict.router, prefix="/difficulty", tags=["ML Model - predict difficulty"])
app.include_router(ml_feedback.router, prefix="/difficulty", tags=["ML Model - get feedback and update model"])
app.include_router(auth)
app.include_router(classroom_router)
app.include_router(game_router)

@app.get("/")
def root():
    return "Backend is running!"

from .routers import socket_events