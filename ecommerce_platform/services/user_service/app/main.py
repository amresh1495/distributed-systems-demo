from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from . import api as user_api
from .db import create_db_and_tables, get_session # Assuming get_session might be used by some startup logic if needed

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("User Service starting up...")
    create_db_and_tables() # Create database tables if they don't exist
    yield
    # Shutdown logic (if any)
    print("User Service shutting down...")

app = FastAPI(
    title="User Service",
    description="Manages user accounts, authentication, and profiles.",
    version="0.1.0",
    lifespan=lifespan # Use the lifespan context manager
)

# Include the API router
# The prefix /api/v1 is standard, ensure Nginx gateway routes /api/users to this service's /api/v1/users
app.include_router(user_api.router, prefix="/api/v1", tags=["Users"])

@app.get("/", tags=["Health Check"])
async def root():
    """
    Basic health check endpoint.
    """
    return {"message": "User Service is running and healthy!"}

# Example of how to add another router if you had an admin part
# from .admin import admin_router # Hypothetical admin router
# app.include_router(admin_router, prefix="/api/v1/admin/users", tags=["Admin - Users"])


# Note on database initialization:
# `create_db_and_tables()` is called on startup.
# It's designed to be idempotent. It will create tables if they don't exist.
# It assumes the database itself (e.g., `user_service_db`) has already been created by an external process
# (like the K8s init job `11-postgres-init-job.yml` or Docker Compose's PostgreSQL init).
# The `db.py` includes a basic retry mechanism for DB connection.
