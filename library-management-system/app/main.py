from fastapi import FastAPI
from app.routers import auth, books, readers, borrowings, admin

app = FastAPI(title="Library Management System", version="1.0.0")

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(readers.router)
app.include_router(borrowings.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
