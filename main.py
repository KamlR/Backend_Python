from fastapi import FastAPI
import subprocess
from routers.predict import predict_router
from contextlib import asynccontextmanager
from model import train_model, save_model, load_model
import logging
from app.clients.kafka import KafkaClient
from db.connection import PostgresConnection


def run_migrations():
    subprocess.run(
    ["pgmigrate", "-d", "db/migrations", "-t", "latest", "migrate"],
    check=True
)
    
async def start_kafka():
    kafka = KafkaClient("localhost:9092")
    await kafka.start()
    app.state.kafka = kafka

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting moderation service...")

    # Миграции.
    print("🔧 Running DB migrations...")
    run_migrations()
    print("✅ Migrations completed")

     # Брокер сообщений.
    print("🔧 Starting kafka service...")
    await start_kafka()
    print("✅ Kafka started")

    # Работа с моделью.
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

    conn = await PostgresConnection.get()
    await conn.close()
    await app.state.kafka.stop()
    print("🛑 Shutting down service...")


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Moderation service is running"}

app.include_router(predict_router)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)