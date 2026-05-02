from fastapi import FastAPI
from app.routers import webhook

app = FastAPI(title="RutaHub Bot", version="0.1.0")

app.include_router(webhook.router)


@app.get("/")
def health():
    return {"status": "ok", "service": "RutaHub Bot"}
