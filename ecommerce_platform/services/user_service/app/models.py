from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import EmailStr # For email validation

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    email: EmailStr = Field(index=True, unique=True) # Use Pydantic's EmailStr for validation
    full_name: Optional[str] = Field(default=None, max_length=100)

from datetime import datetime # Import datetime

class User(UserBase, table=True):
    __tablename__ = "users" # Explicit table name
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserRead(UserBase):
    id: int
    is_active: bool

class UserUpdate(SQLModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8)
    is_active: Optional[bool] = None

# For Authentication
class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    username: Optional[str] = None
    # You can add more fields to token data like user_id, roles etc.

class UserLogin(SQLModel):
    username: str # Can be username or email
    password: str

# Could add Address models here or in a separate file if they become complex
# class AddressBase(SQLModel):
#     street: str
#     city: str
#     state: str
#     zip_code: str
#     country: str
#     user_id: int = Field(foreign_key="users.id")

# class Address(AddressBase, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)

# class AddressCreate(AddressBase):
#     pass

# class AddressRead(AddressBase):
#     id: int
