from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.models import Book, Borrowing, Fine, User  # noqa: F401 — registers ORM tables
from app.routers import admin, auth, books, borrowings, readers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Schema is managed by Alembic migrations (`alembic upgrade head`).
    # Never call create_all() here — it bypasses migration history and causes
    # race conditions when multiple app instances start simultaneously.
    yield


app = FastAPI(
    title="Library Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(borrowings.router)
app.include_router(readers.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
