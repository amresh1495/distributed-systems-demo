from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Standard form for username/password
from sqlmodel import Session
from typing import Annotated, List # List for potential future admin endpoints

from . import crud, models, auth
from .db import get_session
from .auth import create_access_token, get_current_active_user

router = APIRouter()

@router.post("/users/register", response_model=models.UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: models.UserCreate,
    session: Annotated[Session, Depends(get_session)]
):
    """
    Create a new user.
    """
    db_user_by_username = crud.get_user_by_username(session, username=user_in.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    db_user_by_email = crud.get_user_by_email(session, email=user_in.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = crud.create_user(session=session, user_in=user_in)
    return user

@router.post("/users/login", response_model=models.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Authenticate user and return JWT token.
    Takes form data: username and password.
    """
    user = crud.authenticate_user(session, username_or_email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token = create_access_token(
        data={"sub": user.username} # "sub" is the standard claim for subject (username)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=models.UserRead)
async def read_users_me(
    current_user: Annotated[models.User, Depends(get_current_active_user)]
):
    """
    Get current authenticated user's details.
    """
    return current_user

@router.put("/users/me", response_model=models.UserRead)
async def update_users_me(
    user_in: models.UserUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """
    Update current authenticated user's details.
    """
    # Check for username collision if username is being changed
    if user_in.username and user_in.username != current_user.username:
        db_user_by_username = crud.get_user_by_username(session, username=user_in.username)
        if db_user_by_username and db_user_by_username.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken by another user.",
            )

    # Check for email collision if email is being changed
    if user_in.email and user_in.email != current_user.email:
        db_user_by_email = crud.get_user_by_email(session, email=user_in.email)
        if db_user_by_email and db_user_by_email.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user.",
            )

    updated_user = crud.update_user(session=session, db_user=current_user, user_in=user_in)
    return updated_user


# Example of an admin-only endpoint (requires further role/permission system)
# @router.get("/users/", response_model=List[models.UserRead])
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     session: Session = Depends(get_session),
#     # current_admin: models.User = Depends(auth.get_current_admin_user) # Add admin check
# ):
#     """
#     Retrieve users (admin only).
#     """
#     users = crud.get_users(session, skip=skip, limit=limit)
#     return users

# @router.get("/users/{user_id}", response_model=models.UserRead)
# async def read_user_by_id(
#     user_id: int,
#     session: Session = Depends(get_session),
#     # current_admin: models.User = Depends(auth.get_current_admin_user) # Add admin check
# ):
#     db_user = crud.get_user(session, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user

# Remember to include this router in main.py:
# from . import api as user_api
# app.include_router(user_api.router, prefix="/api/v1", tags=["Users"])
