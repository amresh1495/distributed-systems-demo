import pytest
from sqlmodel import Session
from pydantic import EmailStr

# Adjust imports based on your project structure
# Assumes tests are in services/user_service/tests and app code is in services/user_service/app
try:
    from ..app import crud, models
    from ..app.auth import get_password_hash
except ImportError:
    from app import crud, models
    from app.auth import get_password_hash


def test_create_user(db_session: Session):
    """Test creating a new user."""
    user_in = models.UserCreate(
        username="testuser_crud",
        email=EmailStr("test_crud@example.com"),
        password="testpassword123",
        full_name="Test CRUD User"
    )
    db_user = crud.create_user(session=db_session, user_in=user_in)

    assert db_user.id is not None
    assert db_user.username == user_in.username
    assert db_user.email == user_in.email
    assert db_user.full_name == user_in.full_name
    assert db_user.hashed_password is not None
    assert db_user.is_active is True

    # Verify it's in the DB by fetching it
    fetched_user = db_session.get(models.User, db_user.id)
    assert fetched_user is not None
    assert fetched_user.username == user_in.username

def test_get_user_by_username(db_session: Session):
    """Test fetching a user by username."""
    user_in = models.UserCreate(
        username="getuser_crud",
        email=EmailStr("get_crud@example.com"),
        password="password123",
        full_name="Get User CRUD"
    )
    created_user = crud.create_user(session=db_session, user_in=user_in)

    fetched_user = crud.get_user_by_username(db_session, username="getuser_crud")
    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.username == "getuser_crud"

    # Test case-insensitivity if your get_user_by_username implements it (it does via func.lower)
    fetched_user_lower = crud.get_user_by_username(db_session, username="GETUSER_CRUD")
    assert fetched_user_lower is not None
    assert fetched_user_lower.id == created_user.id

    non_existent_user = crud.get_user_by_username(db_session, username="nouser")
    assert non_existent_user is None

def test_get_user_by_email(db_session: Session):
    """Test fetching a user by email."""
    user_in = models.UserCreate(
        username="emailuser_crud",
        email=EmailStr("email_crud@example.com"),
        password="password123"
    )
    created_user = crud.create_user(session=db_session, user_in=user_in)

    fetched_user = crud.get_user_by_email(db_session, email=EmailStr("email_crud@example.com"))
    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.email == "email_crud@example.com"

    # Test case-insensitivity for email if implemented (it is via func.lower)
    fetched_user_upper = crud.get_user_by_email(db_session, email=EmailStr("EMAIL_CRUD@EXAMPLE.COM"))
    assert fetched_user_upper is not None
    assert fetched_user_upper.id == created_user.id

    non_existent_user = crud.get_user_by_email(db_session, email=EmailStr("noemail@example.com"))
    assert non_existent_user is None

def test_update_user(db_session: Session):
    """Test updating a user's information."""
    user_in = models.UserCreate(
        username="updateuser_crud",
        email=EmailStr("update_crud@example.com"),
        password="oldpassword"
    )
    db_user = crud.create_user(session=db_session, user_in=user_in)

    update_data = models.UserUpdate(
        full_name="Updated CRUD Name",
        email=EmailStr("new_update_crud@example.com"),
        is_active=False
    )
    updated_user = crud.update_user(session=db_session, db_user=db_user, user_in=update_data)

    assert updated_user.full_name == "Updated CRUD Name"
    assert updated_user.email == "new_update_crud@example.com"
    assert updated_user.is_active is False
    assert updated_user.username == "updateuser_crud" # Username not changed

    # Test password update
    password_update_data = models.UserUpdate(password="newpassword123")
    updated_user_pwd = crud.update_user(session=db_session, db_user=db_user, user_in=password_update_data)

    # Hashed password should change, verify by trying to authenticate with new password
    authenticated_user = crud.authenticate_user(db_session, username="updateuser_crud", password="newpassword123")
    assert authenticated_user is not None
    assert authenticated_user.id == updated_user_pwd.id

    authenticated_user_old_pwd = crud.authenticate_user(db_session, username="updateuser_crud", password="oldpassword")
    assert authenticated_user_old_pwd is None


def test_deactivate_user(db_session: Session): # CRUD's delete_user actually deactivates
    """Test deactivating a user."""
    user_in = models.UserCreate(username="deactivate_crud", email=EmailStr("deactivate@example.com"), password="password")
    db_user = crud.create_user(session=db_session, user_in=user_in)
    assert db_user.is_active is True

    crud.delete_user(session=db_session, db_user=db_user) # This deactivates

    fetched_user = db_session.get(models.User, db_user.id)
    assert fetched_user is not None
    assert fetched_user.is_active is False

    # Deactivating an already inactive user should not change anything
    crud.delete_user(session=db_session, db_user=fetched_user)
    fetched_again = db_session.get(models.User, db_user.id)
    assert fetched_again is not None
    assert fetched_again.is_active is False


def test_authenticate_user(db_session: Session):
    """Test user authentication."""
    user_in = models.UserCreate(
        username="authuser_crud",
        email=EmailStr("auth_crud@example.com"),
        password="authenticate_me"
    )
    crud.create_user(session=db_session, user_in=user_in)

    # Test successful authentication with username
    authenticated_user = crud.authenticate_user(db_session, username_or_email="authuser_crud", password="authenticate_me")
    assert authenticated_user is not None
    assert authenticated_user.username == "authuser_crud"

    # Test successful authentication with email
    authenticated_user_email = crud.authenticate_user(db_session, username_or_email="auth_crud@example.com", password="authenticate_me")
    assert authenticated_user_email is not None
    assert authenticated_user_email.email == "auth_crud@example.com"

    # Test wrong password
    wrong_password_user = crud.authenticate_user(db_session, username_or_email="authuser_crud", password="wrong_password")
    assert wrong_password_user is None

    # Test non-existent user
    non_existent_user = crud.authenticate_user(db_session, username_or_email="nouser_crud", password="password")
    assert non_existent_user is None

    # Test inactive user authentication
    user_inactive_in = models.UserCreate(
        username="inactive_crud",
        email=EmailStr("inactive@example.com"),
        password="password"
    )
    inactive_user = crud.create_user(session=db_session, user_in=user_inactive_in)
    inactive_user.is_active = False # Deactivate
    db_session.add(inactive_user)
    db_session.commit()
    db_session.refresh(inactive_user)

    auth_inactive = crud.authenticate_user(db_session, username_or_email="inactive_crud", password="password")
    assert auth_inactive is None


def test_get_users(db_session: Session):
    """Test fetching multiple users with pagination."""
    # Create a few users
    crud.create_user(session=db_session, user_in=models.UserCreate(username="user1_crud_list", email=EmailStr("u1cl@example.com"), password="p"))
    crud.create_user(session=db_session, user_in=models.UserCreate(username="user2_crud_list", email=EmailStr("u2cl@example.com"), password="p"))
    crud.create_user(session=db_session, user_in=models.UserCreate(username="user3_crud_list", email=EmailStr("u3cl@example.com"), password="p"))

    users_page1 = crud.get_users(db_session, skip=0, limit=2)
    assert len(users_page1) == 2
    assert users_page1[0].username == "user1_crud_list"
    assert users_page1[1].username == "user2_crud_list"

    users_page2 = crud.get_users(db_session, skip=2, limit=2)
    assert len(users_page2) == 1 # Only one user left
    assert users_page2[0].username == "user3_crud_list"

    all_users = crud.get_users(db_session, limit=10) # Assuming less than 10 total test users
    # The number of users can vary depending on other tests if db is not perfectly isolated per test,
    # but db_session fixture aims for isolation via rollback.
    # So, this should count users created in this test *plus* any from previous tests in this module if isolation failed.
    # Given the transactional db_session, it should be 3.
    assert len(all_users) >= 3 # Check at least the ones created here exist.
                               # With proper transaction rollback in db_session, this should be exactly 3.
                               # Let's make it exact.

    # To make it exact, we need to ensure the db_session is truly isolated.
    # The current conftest.py db_session fixture uses transaction rollback, so it should be isolated.
    # Let's count exactly.
    current_users_in_db = db_session.exec(models.select(models.User)).all()
    assert len(current_users_in_db) == 3
    # This confirms the transaction isolation for this test function.
    # So, `all_users` should also be 3.
    assert len(all_users) == 3
    assert {user.username for user in all_users} == {"user1_crud_list", "user2_crud_list", "user3_crud_list"}

# Note: These tests assume that the `db_session` fixture from `conftest.py`
# correctly handles setting up an in-memory database and rolling back transactions
# after each test, ensuring test isolation.
# EmailStr from Pydantic is used for email fields to ensure valid email format where appropriate.
# The tests cover basic success cases and some failure/edge cases for CRUD operations.
# More comprehensive testing would include more varied inputs and error conditions.
