from typing import Optional, List
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload # For eager loading relationships

from . import models

# Category CRUD operations
def get_category(session: Session, category_id: int) -> Optional[models.Category]:
    return session.get(models.Category, category_id)

def get_category_by_name(session: Session, name: str) -> Optional[models.Category]:
    statement = select(models.Category).where(func.lower(models.Category.name) == func.lower(name))
    return session.exec(statement).first()

def get_categories(session: Session, skip: int = 0, limit: int = 100) -> List[models.Category]:
    statement = select(models.Category).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_category(session: Session, category_in: models.CategoryCreate) -> models.Category:
    db_category = models.Category.model_validate(category_in) # SQLModel v0.0.14+
    # For older SQLModel: db_category = models.Category(**category_in.dict())
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category

def update_category(session: Session, db_category: models.Category, category_in: models.CategoryUpdate) -> models.Category:
    category_data = category_in.model_dump(exclude_unset=True)
    for key, value in category_data.items():
        setattr(db_category, key, value)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category

def delete_category(session: Session, db_category: models.Category) -> Optional[models.Category]:
    # Check if category has products associated.
    # The API layer (api.py) currently prevents deletion if products are associated.
    # If this CRUD function were called directly elsewhere, this check would be important.
    # For now, the API layer handles this business rule.
    if db_category.products:
        # This case should ideally be prevented by the calling logic (e.g., in API endpoint)
        # or handled by a specific strategy (e.g., unlinking products, cascade delete - not implemented).
        # Raising an error here if called directly and products exist might be appropriate.
        # However, api.py already checks this.
        print(f"Warning: Category '{db_category.name}' has products. API layer should prevent this deletion if not intended.")

    session.delete(db_category)
    session.commit()
    # db_category is no longer valid after delete and commit.
    return None # Indicating successful deletion, or raise error if deletion fails.

# Product CRUD operations
def get_product(session: Session, product_id: int, with_category: bool = False) -> Optional[models.Product]:
    if with_category:
        # Eager load the category
        statement = select(models.Product).options(selectinload(models.Product.category)).where(models.Product.id == product_id)
        return session.exec(statement).first()
    return session.get(models.Product, product_id)

def get_products(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    with_category: bool = False # If true, eager load categories for all products
) -> List[models.Product]:
    statement = select(models.Product)
    if with_category:
        statement = statement.options(selectinload(models.Product.category))
    if category_id is not None:
        statement = statement.where(models.Product.category_id == category_id)
    statement = statement.offset(skip).limit(limit)
    return session.exec(statement).all()

def create_product(session: Session, product_in: models.ProductCreate) -> models.Product:
    # Ensure category_id exists if provided
    if product_in.category_id:
        category = get_category(session, product_in.category_id)
        if not category:
            # This should be an HTTPException in the API layer, but good to check here too
            raise ValueError(f"Category with id {product_in.category_id} not found.")

    db_product = models.Product.model_validate(product_in)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

def update_product(session: Session, db_product: models.Product, product_in: models.ProductUpdate) -> models.Product:
    product_data = product_in.model_dump(exclude_unset=True)

    if "category_id" in product_data and product_data["category_id"] is not None:
        category = get_category(session, product_data["category_id"])
        if not category:
            raise ValueError(f"Category with id {product_data['category_id']} not found.")

    for key, value in product_data.items():
        setattr(db_product, key, value)

    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    # Eager load category if it was updated or for consistency
    if "category_id" in product_data:
        session.refresh(db_product, attribute_names=['category']) # Refresh the relationship
    return db_product

def delete_product(session: Session, db_product: models.Product):
    session.delete(db_product)
    session.commit()
    return None # Product deleted successfully
