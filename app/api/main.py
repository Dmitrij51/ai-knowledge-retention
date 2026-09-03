from contextlib import asynccontextmanager
from fastapi import FastAPI

# 1. Забираем watcher_manager из deps.py
from app.api.deps import watcher_manager

# 2. Забираем ТОЛЬКО router из routes.py
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[APP] Запуск AI Knowledge Retention...")

    try:
        started_count = watcher_manager.start()
        print(f"[APP] Watcher запущен. Активных папок: {started_count}")
    except Exception as exc:
        print(f"[APP ERROR] Не удалось запустить Watcher: {exc}")
        raise

    try:
        yield
    finally:
        print("[APP] Остановка AI Knowledge Retention...")
        try:
            watcher_manager.stop()
        except Exception as exc:
            print(f"[APP ERROR] Ошибка остановки Watcher: {exc}")
        print("[APP] Приложение остановлено.")


app = FastAPI(
    title="AI Knowledge Retention",
    description="Локальная система сохранения и поиска знаний.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
