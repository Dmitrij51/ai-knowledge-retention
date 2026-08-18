from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="AI Knowledge Retention",
    description="Локальная система сохранения и поиска знаний.",
    version="0.1.0",
)


app.include_router(router)
