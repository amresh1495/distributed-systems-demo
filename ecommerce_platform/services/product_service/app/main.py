from fastapi import FastAPI
from contextlib import asynccontextmanager

from . import api as product_api # Renamed to avoid conflict if other 'api' modules exist
from .db import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Product Service starting up...")
    create_db_and_tables()
    yield
    print("Product Service shutting down...")

app = FastAPI(
    title="Product Service",
    description="Manages product catalog (products and categories).",
    version="0.1.0",
    lifespan=lifespan
)

# Include the API router
# The prefix /api/v1 is standard, ensure Nginx gateway routes /api/products to this service's /api/v1/products
# and /api/categories to /api/v1/categories
app.include_router(product_api.router, prefix="/api/v1") # Tags are defined within api.py

@app.get("/", tags=["Health Check"])
async def root():
    """
    Basic health check endpoint for Product Service.
    """
    return {"message": "Product Service is running and healthy!"}

# Note:
# The Product Service focuses on catalog data (name, description, price, category).
# Real-time stock levels are managed by the Inventory Service.
# Product images: A simple image_url field is included. More complex image management
# (multiple images, uploads) would require more features or a dedicated image service.
