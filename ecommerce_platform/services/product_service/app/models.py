from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from decimal import Decimal

# Category Models
class CategoryBase(SQLModel):
    name: str = Field(index=True, unique=True, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)

from datetime import datetime # Import datetime

class Category(CategoryBase, table=True):
    __tablename__ = "categories"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

    products: List["Product"] = Relationship(back_populates="category")

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int

class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)


# Product Models
class ProductBase(SQLModel):
    name: str = Field(index=True, max_length=100)
    description: Optional[str] = Field(default=None)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2) # Ensure price is positive
    # Stock will be managed by Inventory Service. Product service might store a reference or general availability.
    # For now, let's assume Product Service doesn't store stock directly.
    # We can add image_url or similar fields later.

    category_id: Optional[int] = Field(default=None, foreign_key="categories.id")

class Product(ProductBase, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)

    category: Optional[Category] = Relationship(back_populates="products")
    # Add created_at, updated_at fields later if needed

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: int
    # Optionally include category details when reading a product
    # category: Optional[CategoryRead] = None # This would require a resolver or careful query loading

class ProductReadWithCategory(ProductRead): # Example of a more detailed read model
    category: Optional[CategoryRead] = None

class ProductUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category_id: Optional[int] = None


# Relationship linking:
# Product.model_rebuild() # Not needed here as it's for forward refs resolution, SQLModel handles it.
# Category.model_rebuild()

# Notes:
# - Using Decimal for price is crucial for financial calculations to avoid floating point inaccuracies.
# - Relationships between Product and Category are defined.
# - `ProductReadWithCategory` shows how you can create different "views" of your data for API responses.
# - Stock management is explicitly deferred to the Inventory Service. The Product Service focuses on catalog information.
# - Timestamps (created_at, updated_at) can be added using `default_factory=datetime.utcnow` from `datetime`.
# - Images: Could be a simple `image_url: Optional[str]` or a separate `ProductImage` table for multiple images.
#   For simplicity, a single `image_url` on ProductBase might be a good start if needed.
#   Let's add a placeholder for it.

class ProductBaseWithImage(ProductBase): # Inherit from ProductBase
    image_url: Optional[str] = Field(default=None, max_length=255)

# Re-define Product, ProductCreate, ProductRead, ProductUpdate to use ProductBaseWithImage if image_url is desired now
class Product(ProductBaseWithImage, table=True): # Change inheritance
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

    category: Optional[Category] = Relationship(back_populates="products")

class ProductCreate(ProductBaseWithImage): # Change inheritance
    pass

class ProductRead(ProductBaseWithImage): # Change inheritance
    id: int

class ProductReadWithCategory(ProductRead): # No change here, it inherits from new ProductRead
    category: Optional[CategoryRead] = None

class ProductUpdate(SQLModel): # Keep this separate or also make it inherit if all fields are optional from a base
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category_id: Optional[int] = None
    image_url: Optional[str] = Field(default=None, max_length=255)

# Rebuild models to ensure relationships are correctly processed by SQLModel
# This is sometimes needed if you define models out of order or use string forward references extensively.
# However, SQLModel is generally good at resolving these automatically.
# If issues arise, uncommenting these can help.
# Category.model_rebuild()
# Product.model_rebuild()
