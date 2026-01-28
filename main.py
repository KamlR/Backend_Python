from fastapi import FastAPI
from routers.predict import router as predict_router
from contextlib import asynccontextmanager
from model import train_model, save_model, load_model
import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting moderation service...")

    model = load_model()
    if model is None:
        print("📚 No model found. Training new model...")
        model = train_model()
        save_model(model)
        print("✅ Model trained and saved")
    else:
        print("✅ Model loaded from disk")

    app.state.model = model

    yield

    print("🛑 Shutting down service...")


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Moderation service is running"}

app.include_router(predict_router, prefix="/predict", tags=["predict"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)