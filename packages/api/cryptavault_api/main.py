"""FastAPI entrypoint for CryptaVault API."""

from fastapi import FastAPI

app = FastAPI(
    title="CryptaVault API",
    version="0.1.0",
    description="FastAPI backend orchestrator and zero-knowledge storage coordinator",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
