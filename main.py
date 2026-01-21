from fastapi import FastAPI
from routers.predict import router as predict_router

app = FastAPI(title="Moderation Service")

@app.get("/")
async def root():
    return {"message": "Moderation service is running"}

app.include_router(predict_router, prefix="/predict", tags=["predict"])