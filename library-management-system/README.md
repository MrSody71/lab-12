# Library Management System

REST API for managing a library built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- JWT authentication (register / login)
- Book catalog (CRUD, admin-only write access)
- Borrowing and returning books with availability tracking
- Automatic fine calculation for overdue returns
- Admin analytics: popular books, overdue borrowings, fines summary

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

API docs available at `http://localhost:8000/docs`.

## Running Tests

```bash
pip install -r requirements.txt
pytest --cov=app
```

## Project Structure

```
app/
├── core/        # Config, security, dependencies
├── models/      # SQLAlchemy ORM models
├── routers/     # FastAPI route handlers
├── schemas/     # Pydantic request/response schemas
└── services/    # Business logic (auth, fines, analytics)
tests/           # Pytest test suite
alembic/         # Database migrations
```
