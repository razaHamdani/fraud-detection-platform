from fastapi import FastAPI

app = FastAPI(title="Risk Scorer", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "risk-scorer"}
