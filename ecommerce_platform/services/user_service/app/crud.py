from typing import Optional, List
from sqlmodel import Session, select, func
from passlib.context import CryptContext


from . import models
from .auth import get_password_hash, verify_password

# Re-use pwd_context from auth.py or define it here if auth.py is not always imported.
# For consistency, it's better if auth.py is the source of truth for pwd_context.
# from .auth import pwd_context

def get_user(session: Session, user_id: int) -> Optional[models.User]:
    return session.get(models.User, user_id)

def get_user_by_username(session: Session, username: str) -> Optional[models.User]:
    statement = select(models.User).where(func.lower(models.User.username) == func.lower(username))
    return session.exec(statement).first()

def get_user_by_email(session: Session, email: str) -> Optional[models.User]:
    statement = select(models.User).where(func.lower(models.User.email) == func.lower(email))
    return session.exec(statement).first()

def get_users(session: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    statement = select(models.User).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_user(session: Session, user_in: models.UserCreate) -> models.User:
    hashed_password = get_password_hash(user_in.password)
    # `created_at` and `updated_at` are handled by default_factory in the model
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        is_active=True # Default to active
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def update_user(session: Session, db_user: models.User, user_in: models.UserUpdate) -> models.User:
    user_data = user_in.model_dump(exclude_unset=True) # Use model_dump for Pydantic v2+

    if "password" in user_data and user_data["password"]:
        hashed_password = get_password_hash(user_data["password"])
        db_user.hashed_password = hashed_password
        del user_data["password"] # Don't try to set it directly again

    for key, value in user_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def delete_user(session: Session, db_user: models.User) -> models.User:
    # Instead of deleting, we can deactivate the user.
    # This is often preferred to maintain data integrity (e.g., past orders).
    if db_user.is_active:
        db_user.is_active = False
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    # If actual deletion is needed:
    # session.delete(db_user)
    # session.commit()
    # return None # Or some confirmation
    return db_user


def authenticate_user(session: Session, username_or_email: str, password: str) -> Optional[models.User]:
    # Try fetching by username first, then by email
    user = get_user_by_username(session, username_or_email)
    if not user:
        user = get_user_by_email(session, username_or_email)

    if not user:
        return None # User not found
    if not user.is_active:
        return None # User is inactive
    if not verify_password(password, user.hashed_password):
        return None # Invalid password

    return user
