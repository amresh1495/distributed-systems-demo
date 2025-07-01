from typing import Optional, List, Tuple
from sqlmodel import Session, select, func
from sqlalchemy.orm import Session as SQLAlchemySession # For using with_for_update
from sqlalchemy.exc import SQLAlchemyError # More general DB errors
import logging

from . import models

logger = logging.getLogger(__name__)

def get_stock_item_by_id(session: Session, stock_item_id: int) -> Optional[models.StockItem]:
    return session.get(models.StockItem, stock_item_id)

def get_stock_item_by_product_id(session: Session, product_id: int, for_update: bool = False) -> Optional[models.StockItem]:
    statement = select(models.StockItem).where(models.StockItem.product_id == product_id)
    if for_update and session.get_bind().dialect.name == "postgresql": # Check if DB supports FOR UPDATE
        # Use with_for_update for pessimistic locking if supported and requested
        # Need to use SQLAlchemy session for this method
        if isinstance(session, SQLAlchemySession):
             statement = statement.with_for_update()
        else: # SQLModel session might not directly expose it, or needs specific handling
            logger.warning("Session is not a SQLAlchemySession, cannot use with_for_update directly. Proceeding without lock.")

    return session.exec(statement).first()


def get_all_stock_items(session: Session, skip: int = 0, limit: int = 100) -> List[models.StockItem]:
    statement = select(models.StockItem).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_stock_item(session: Session, stock_item_in: models.StockItemCreate) -> models.StockItem:
    # Check if stock item for this product_id already exists
    existing_item = get_stock_item_by_product_id(session, product_id=stock_item_in.product_id)
    if existing_item:
        raise ValueError(f"Stock item for product_id {stock_item_in.product_id} already exists.")

    db_stock_item = models.StockItem(
        product_id=stock_item_in.product_id,
        quantity=stock_item_in.quantity,
        reserved_quantity=0 # Initial reserved quantity is 0
    )
    session.add(db_stock_item)
    session.commit()
    session.refresh(db_stock_item)
    return db_stock_item

def adjust_stock_quantity(session: Session, product_id: int, change_in_quantity: int) -> Optional[models.StockItem]:
    """
    Adjusts the physical stock quantity.
    Positive change_in_quantity for restocking, negative for reduction (e.g., damage, loss).
    This does NOT affect reserved_quantity directly.
    """
    # Use for_update to lock the row during transaction
    db_stock_item = get_stock_item_by_product_id(session, product_id=product_id, for_update=True)
    if not db_stock_item:
        return None # Or raise error: Product not found in inventory

    new_quantity = db_stock_item.quantity + change_in_quantity
    if new_quantity < 0:
        # This means we are trying to reduce stock more than available physical stock.
        # This check is important. If new_quantity < db_stock_item.reserved_quantity, it's also problematic.
        raise ValueError("Cannot reduce stock below zero or below reserved quantity through direct adjustment.")

    if new_quantity < db_stock_item.reserved_quantity:
        raise ValueError("New quantity would be less than current reserved quantity. Release reservations first or adjust reservations accordingly.")

    db_stock_item.quantity = new_quantity
    session.add(db_stock_item)
    session.commit()
    session.refresh(db_stock_item)
    return db_stock_item

def reserve_stock(session: Session, product_id: int, quantity_to_reserve: int) -> models.StockReservation:
    """
    Attempts to reserve stock for a given product_id.
    Returns a StockReservation object indicating success/failure and quantity reserved.
    """
    if quantity_to_reserve <= 0:
        return models.StockReservation(
            product_id=product_id,
            requested_quantity=quantity_to_reserve,
            reserved_quantity=0,
            sufficient_stock=False,
            message="Quantity to reserve must be positive."
        )

    # Lock the row for update
    db_stock_item = get_stock_item_by_product_id(session, product_id=product_id, for_update=True)

    if not db_stock_item:
        return models.StockReservation(
            product_id=product_id,
            requested_quantity=quantity_to_reserve,
            reserved_quantity=0,
            sufficient_stock=False,
            message="Product not found in inventory."
        )

    available_to_reserve = db_stock_item.quantity - db_stock_item.reserved_quantity

    if available_to_reserve >= quantity_to_reserve:
        db_stock_item.reserved_quantity += quantity_to_reserve
        session.add(db_stock_item)
        session.commit()
        session.refresh(db_stock_item)
        return models.StockReservation(
            product_id=product_id,
            requested_quantity=quantity_to_reserve,
            reserved_quantity=quantity_to_reserve,
            sufficient_stock=True,
            message="Stock reserved successfully."
        )
    else:
        # Not enough stock to reserve the full quantity
        # Option 1: Reserve available (if any) - current implementation does not do partial
        # Option 2: Reserve none - current implementation
        return models.StockReservation(
            product_id=product_id,
            requested_quantity=quantity_to_reserve,
            reserved_quantity=0, # No stock was reserved
            sufficient_stock=False,
            message=f"Insufficient stock. Available to reserve: {max(0, available_to_reserve)}."
        )


def release_stock(session: Session, product_id: int, quantity_to_release: int) -> Optional[models.StockItem]:
    """
    Releases previously reserved stock for a product_id.
    This typically happens if an order is cancelled or payment fails.
    """
    if quantity_to_release <= 0:
        raise ValueError("Quantity to release must be positive.")

    db_stock_item = get_stock_item_by_product_id(session, product_id=product_id, for_update=True)
    if not db_stock_item:
        # Or raise error: Product not found in inventory
        return None

    if db_stock_item.reserved_quantity < quantity_to_release:
        # Trying to release more than was reserved. This indicates an issue.
        # Log this, and perhaps clamp to 0 or raise an error.
        # For now, set reserved_quantity to 0 if this happens, effectively releasing all.
        logger.warning(f"Attempted to release {quantity_to_release} for product {product_id}, but only {db_stock_item.reserved_quantity} was reserved. Releasing all reserved.")
        db_stock_item.reserved_quantity = 0
    else:
        db_stock_item.reserved_quantity -= quantity_to_release

    session.add(db_stock_item)
    session.commit()
    session.refresh(db_stock_item)
    return db_stock_item


def fulfill_stock(session: Session, product_id: int, quantity_to_fulfill: int) -> Optional[models.StockItem]:
    """
    Fulfills (decrements) stock that was previously reserved.
    This means the order has been processed (e.g., paid and shipped).
    It reduces both physical quantity and reserved quantity.
    """
    if quantity_to_fulfill <= 0:
        raise ValueError("Quantity to fulfill must be positive.")

    db_stock_item = get_stock_item_by_product_id(session, product_id=product_id, for_update=True)
    if not db_stock_item:
        return None # Or raise error

    if db_stock_item.reserved_quantity < quantity_to_fulfill:
        # This is a critical error: trying to fulfill more than reserved.
        # Indicates a logic flaw or data inconsistency.
        raise ValueError(f"Cannot fulfill {quantity_to_fulfill} for product {product_id}; only {db_stock_item.reserved_quantity} reserved.")

    if db_stock_item.quantity < quantity_to_fulfill:
        # Also a critical error: not enough physical stock, even though it was reserved.
        # This implies stock was somehow reduced after reservation without adjusting reservation.
        raise ValueError(f"Cannot fulfill {quantity_to_fulfill} for product {product_id}; only {db_stock_item.quantity} physical stock, despite {db_stock_item.reserved_quantity} reserved.")

    db_stock_item.quantity -= quantity_to_fulfill
    db_stock_item.reserved_quantity -= quantity_to_fulfill

    session.add(db_stock_item)
    session.commit()
    session.refresh(db_stock_item)
    return db_stock_item

def update_stock_item_details(session: Session, product_id: int, stock_item_in: models.StockItemUpdate) -> Optional[models.StockItem]:
    """
    Manually update stock item details like quantity or reserved_quantity.
    This is more of an admin/system adjustment tool. Use with caution.
    """
    db_stock_item = get_stock_item_by_product_id(session, product_id=product_id, for_update=True)
    if not db_stock_item:
        return None

    update_data = stock_item_in.model_dump(exclude_unset=True)

    # Validate new values if provided
    new_quantity = update_data.get("quantity", db_stock_item.quantity)
    new_reserved_quantity = update_data.get("reserved_quantity", db_stock_item.reserved_quantity)

    if new_quantity < 0 or new_reserved_quantity < 0:
        raise ValueError("Quantity and Reserved Quantity cannot be negative.")
    if new_reserved_quantity > new_quantity:
        raise ValueError("Reserved quantity cannot exceed physical quantity.")

    for key, value in update_data.items():
        setattr(db_stock_item, key, value)

    session.add(db_stock_item)
    session.commit()
    session.refresh(db_stock_item)
    return db_stock_item

# Note on Concurrency:
# The `for_update=True` in `get_stock_item_by_product_id` (when used with PostgreSQL)
# helps in locking the specific row during a transaction, preventing race conditions
# for critical operations like reserve, release, fulfill.
# This is a form of pessimistic locking.
# For databases not supporting `SELECT ... FOR UPDATE` or for different strategies,
# optimistic concurrency control (e.g., using version numbers) would be an alternative.
# The current implementation of `for_update` is basic and relies on SQLAlchemy session behavior.
# A robust implementation would ensure the session is indeed a SQLAlchemy session type.
# The check `session.get_bind().dialect.name == "postgresql"` is a simple way to apply it conditionally.
# If using SQLite for dev, these locks won't apply in the same way (SQLite has more coarse-grained locking).
# This means testing concurrency aspects thoroughly requires a PostgreSQL environment.
#
# Transactions: Each CRUD function that modifies data commits its own transaction.
# For complex operations involving multiple stock items (e.g., reserving for a whole order),
# the calling service (Order Service) would need to manage a broader transaction or use
# compensating transactions (Saga pattern) if operations are distributed.
# The `reserve_stock_batch` or similar would be needed if an atomic reservation for multiple items is desired.
# For now, `reserve_stock` handles one product at a time.
# Order service will call this multiple times. If one call fails, Order service needs to decide how to compensate (e.g., release previously reserved items).
# This is a key area for distributed transaction patterns like Sagas.
#
# The logger is imported but not extensively used yet. Adding more logging, especially for warnings/errors, is good practice.
# Example: `logger.error(f"Critical stock discrepancy for product {product_id}...")`
#
# The `SQLAlchemySession` import and check is a bit of a workaround.
# SQLModel's Session is a wrapper. For `with_for_update`, direct SQLAlchemy mechanisms are usually needed.
# If `session.exec(statement.with_for_update())` works directly with SQLModel's session, the check can be simplified.
# Based on SQLModel docs, `session.exec(select(Hero).with_for_update().where(Hero.name == "Spider-Boy"))` should work.
# So, the `isinstance` check might be overly cautious or could be removed if `session.exec` handles it.
# Let's assume `session.exec(statement.with_for_update())` is the SQLModel way.
# I will simplify the `get_stock_item_by_product_id` to use this directly.

def get_stock_item_by_product_id_simplified(session: Session, product_id: int, for_update: bool = False) -> Optional[models.StockItem]:
    statement = select(models.StockItem).where(models.StockItem.product_id == product_id)
    if for_update:
        # Assuming session.exec() supports with_for_update() correctly with SQLModel
        # This is generally true for PostgreSQL backend.
        statement = statement.with_for_update()
    return session.exec(statement).first()

# Replace previous `get_stock_item_by_product_id` with the simplified one for internal use.
# The public API might still call the original if more complex logic for `for_update` is needed.
# For now, let's use the simplified one internally.
get_stock_item_by_product_id = get_stock_item_by_product_id_simplified
# This change means the `isinstance` check and specific SQLAlchemy session import are removed.
# It relies on SQLModel's session to pass `with_for_update` to the underlying SQLAlchemy execution.
# This is generally expected to work with PostgreSQL.
# If issues arise with other DBs or specific SQLModel versions, the more verbose check might be reinstated.
