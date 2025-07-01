from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

# Using product_id as an integer. This assumes product IDs from Product Service are integers.
# If they are UUIDs or strings, this type should be changed accordingly.

class StockItemBase(SQLModel):
    product_id: int = Field(index=True, unique=True) # Each product has one stock record in this simple model
    quantity: int = Field(default=0, ge=0) # Total physical quantity
    reserved_quantity: int = Field(default=0, ge=0) # Quantity reserved for open orders
    # available_quantity can be derived: quantity - reserved_quantity

    # Optional: for multi-warehouse scenarios, add warehouse_id
    # warehouse_id: Optional[int] = Field(default=None, index=True)
    # If using warehouse_id, (product_id, warehouse_id) would be the unique key.

class StockItem(StockItemBase, table=True):
    __tablename__ = "stock_items"
    # id: Optional[int] = Field(default=None, primary_key=True) # Using product_id as PK for simplicity
    # If product_id is not the PK, then uncomment id and remove unique=True from product_id in StockItemBase
    # For this model, making product_id the primary key simplifies things, assuming one stock record per product.
    # To use an auto-incrementing ID as PK:
    id: Optional[int] = Field(default=None, primary_key=True)
    # product_id: int = Field(index=True, unique=True) # from StockItemBase, ensure unique if id is PK

    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

# --- Pydantic models for API requests/responses ---

class StockItemRead(StockItemBase):
    id: int # if using auto-incrementing PK
    available_quantity: int
    last_updated: datetime
    created_at: datetime
    # product_id: int # Already in StockItemBase

class StockItemCreate(SQLModel):
    product_id: int
    quantity: int = Field(ge=0)
    # reserved_quantity is typically managed internally, not set at creation

class StockItemUpdate(SQLModel): # For manual adjustments by admin perhaps
    quantity: Optional[int] = Field(default=None, ge=0)
    reserved_quantity: Optional[int] = Field(default=None, ge=0) # Should be used carefully

# Models for specific operations
class ReserveStockRequest(SQLModel):
    items: List[dict] # e.g., [{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}]

class StockAdjustmentRequest(SQLModel):
    product_id: int
    change_in_quantity: int # Positive to add stock (restock), negative to reduce (e.g., shrinkage)

class StockReservation(SQLModel): # Response for reservation attempt
    product_id: int
    requested_quantity: int
    reserved_quantity: int # Actual quantity reserved
    sufficient_stock: bool
    message: Optional[str] = None

# If product_id itself is the primary key (no separate 'id' field):
# class StockItem(StockItemBase, table=True):
#     __tablename__ = "stock_items"
#     product_id: int = Field(default=None, primary_key=True, index=True) # Override from base
#     # Timestamps
#     last_updated: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     @property
#     def available_quantity(self) -> int:
#         return self.quantity - self.reserved_quantity

# class StockItemRead(StockItemBase): # product_id is already the PK from StockItemBase
#     available_quantity: int
#     last_updated: datetime
#     created_at: datetime

# Let's stick with an auto-incrementing `id` for the `StockItem` table as it's more conventional,
# and `product_id` will be a unique indexed field.
# The current definition with `id` as PK and `product_id` as unique is good.
# StockItemRead should include `id` and `product_id`.

# Corrected StockItemRead if `id` is PK and `product_id` is a separate field from Base.
class StockItemReadRevised(StockItemBase): # product_id is in StockItemBase
    id: int # The PK of the stock_item record itself
    available_quantity: int
    last_updated: datetime
    created_at: datetime

# The current StockItemRead is actually fine as it is if StockItemBase contains product_id
# and StockItem (the table model) adds the 'id' primary key.
# Let's ensure StockItemRead reflects the table model accurately including its own PK.
# The initial StockItemRead was:
# class StockItemRead(StockItemBase):
#    id: int # This refers to StockItem.id
#    available_quantity: int
#    last_updated: datetime
#    created_at: datetime
# This seems correct.
# product_id is inherited from StockItemBase.
# id is the StockItem table's own primary key.
# This is good.
