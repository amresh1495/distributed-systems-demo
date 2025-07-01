from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List, Optional, Annotated

from . import crud, models
from .db import get_session

router = APIRouter()

# --- Category Endpoints ---

@router.post("/categories/", response_model=models.CategoryRead, status_code=status.HTTP_201_CREATED, tags=["Categories"])
async def create_new_category(
    category_in: models.CategoryCreate,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new category. (Admin action typically)
    """
    db_category = crud.get_category_by_name(session, name=category_in.name)
    if db_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category with this name already exists")
    return crud.create_category(session=session, category_in=category_in)

@router.get("/categories/", response_model=List[models.CategoryRead], tags=["Categories"])
async def read_all_categories(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=200), # Add validation for limit
    session: Annotated[Session, Depends(get_session)]
):
    """
    Retrieve all categories with pagination.
    """
    categories = crud.get_categories(session, skip=skip, limit=limit)
    return categories

@router.get("/categories/{category_id}", response_model=models.CategoryRead, tags=["Categories"])
async def read_category_by_id(
    category_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Retrieve a specific category by its ID.
    """
    db_category = crud.get_category(session, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return db_category

@router.put("/categories/{category_id}", response_model=models.CategoryRead, tags=["Categories"])
async def update_existing_category(
    category_id: int,
    category_in: models.CategoryUpdate,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update an existing category. (Admin action typically)
    """
    db_category = crud.get_category(session, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category_in.name and category_in.name != db_category.name:
        existing_category_with_name = crud.get_category_by_name(session, name=category_in.name)
        if existing_category_with_name and existing_category_with_name.id != category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Another category with this name already exists")

    return crud.update_category(session=session, db_category=db_category, category_in=category_in)

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Categories"])
async def remove_category(
    category_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a category. (Admin action typically)
    Be cautious if categories have associated products.
    """
    db_category = crud.get_category(session, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if db_category.products:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with associated products. Please reassign or delete products first."
        )
    crud.delete_category(session=session, db_category=db_category)
    return None # For 204 No Content

# --- Product Endpoints ---

@router.post("/products/", response_model=models.ProductRead, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_new_product(
    product_in: models.ProductCreate,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new product. (Admin action typically)
    """
    try:
        product = crud.create_product(session=session, product_in=product_in)
        # To return with category info, explicitly query it or ensure create_product does
        return crud.get_product(session, product.id, with_category=True) # type: ignore
    except ValueError as e: # Catch specific error from CRUD for non-existent category
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/products/", response_model=List[models.ProductReadWithCategory], tags=["Products"])
async def read_all_products(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=200),
    category_id: Optional[int] = Query(default=None, description="Filter products by category ID"),
    session: Annotated[Session, Depends(get_session)]
):
    """
    Retrieve all products with pagination and optional category filtering.
    Includes category information.
    """
    products = crud.get_products(session, skip=skip, limit=limit, category_id=category_id, with_category=True)
    # Convert to ProductReadWithCategory. SQLModel should handle this if relationships are set up.
    # If direct conversion doesn't include category, manual mapping might be needed or ensure Product model has it.
    # The `with_category=True` in crud.get_products should eager load it.
    return products


@router.get("/products/{product_id}", response_model=models.ProductReadWithCategory, tags=["Products"])
async def read_product_by_id(
    product_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Retrieve a specific product by its ID, including category information.
    """
    db_product = crud.get_product(session, product_id=product_id, with_category=True)
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return db_product

@router.put("/products/{product_id}", response_model=models.ProductReadWithCategory, tags=["Products"])
async def update_existing_product(
    product_id: int,
    product_in: models.ProductUpdate,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update an existing product. (Admin action typically)
    """
    db_product = crud.get_product(session, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    try:
        updated_product = crud.update_product(session=session, db_product=db_product, product_in=product_in)
        # Fetch again to ensure category is loaded for the response model
        return crud.get_product(session, updated_product.id, with_category=True) # type: ignore
    except ValueError as e: # Catch specific error from CRUD for non-existent category
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
async def remove_product(
    product_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Delete a product. (Admin action typically)
    """
    db_product = crud.get_product(session, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    crud.delete_product(session=session, db_product=db_product)
    return None

# Remember to include this router in main.py:
# from . import api as product_api
# app.include_router(product_api.router, prefix="/api/v1", tags=["Products & Categories"]) # Or separate tags
