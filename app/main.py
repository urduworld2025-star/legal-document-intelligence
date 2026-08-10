from fastapi import FastAPI

from app.api.routes.documents import router as documents_router

app = FastAPI(title="Legal Document Intelligence")
app.include_router(documents_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
