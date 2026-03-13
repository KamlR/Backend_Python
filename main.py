from fastapi import FastAPI
import subprocess
from routers.predict import predict_router
from routers.auth import auth_router
from contextlib import asynccontextmanager
from model import train_model, save_model, load_model
import logging
from app.clients.kafka import KafkaClient
from db.connection import PostgresConnection
import redis.asyncio as redis
from middleware import PrometheusMiddleware
from starlette.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os, sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from dotenv import load_dotenv

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment="development",
)

def run_migrations():
    subprocess.run(
    ["pgmigrate", "-d", "db/migrations", "-t", "latest", "migrate"],
    check=True
)

async def start_kafka():
    kafka = KafkaClient("localhost:9092")
    await kafka.start()
    app.state.kafka = kafka

async def connect_to_redis():
    redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True)
    app.state.redis_client = redis_client


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

    # Redis.
    print("🔧 Connecting to redis...")
    await connect_to_redis()
    print("✅ Successfully connected to redis")

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
app.add_middleware(PrometheusMiddleware)

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/sentry-debug")
async def trigger_error():
    1 / 0
    
app.include_router(predict_router)
app.include_router(auth_router)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)