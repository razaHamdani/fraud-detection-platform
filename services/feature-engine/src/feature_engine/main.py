from fastapi import FastAPI

app = FastAPI(title="Feature Engine", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "feature-engine"}
