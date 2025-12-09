from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import health, test_db
from .routers.auth import router as auth
from .routers.classroom_router import router as classroom_router


app = FastAPI(title="SmartMath API", version="0.1.0")

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
app.include_router(auth)
app.include_router(classroom_router)

@app.get("/")
def root():
    return "Backend is running!"
