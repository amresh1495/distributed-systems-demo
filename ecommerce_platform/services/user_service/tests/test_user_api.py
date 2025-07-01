from fastapi.testclient import TestClient
from sqlmodel import Session
from pydantic import EmailStr

# Adjust imports as per your structure
try:
    from ..app import models
    from ..app.core.config import settings # If you have a settings module
except ImportError:
    from app import models
    # from app.core.config import settings # Placeholder if you add config


# --- Test User Registration ---
def test_register_user_success(client: TestClient, db_session: Session): # db_session can be used for setup/assertions
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "api_testuser",
            "email": "api_test@example.com",
            "password": "apipassword123",
            "full_name": "API Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "api_testuser"
    assert data["email"] == "api_test@example.com"
    assert data["full_name"] == "API Test User"
    assert "id" in data
    assert data["is_active"] is True # Default from model

    # Verify user is in DB (optional, client tests focus on API contract)
    # user_in_db = db_session.get(models.User, data["id"])
    # assert user_in_db is not None
    # assert user_in_db.username == "api_testuser"

def test_register_user_duplicate_username(client: TestClient):
    client.post(
        "/api/v1/users/register",
        json={"username": "duplicate_api", "email": "dup1@example.com", "password": "pw1"}
    ) # First registration
    response = client.post(
        "/api/v1/users/register",
        json={"username": "duplicate_api", "email": "dup2@example.com", "password": "pw2"}
    ) # Attempt duplicate username
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_register_user_duplicate_email(client: TestClient):
    client.post(
        "/api/v1/users/register",
        json={"username": "email_user1_api", "email": "duplicate_email_api@example.com", "password": "pw1"}
    )
    response = client.post(
        "/api/v1/users/register",
        json={"username": "email_user2_api", "email": "duplicate_email_api@example.com", "password": "pw2"}
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_register_user_invalid_data(client: TestClient):
    # Invalid email
    response = client.post(
        "/api/v1/users/register",
        json={"username": "invalid_email_user", "email": "not-an-email", "password": "pw"}
    )
    assert response.status_code == 422 # Pydantic validation error

    # Short password
    response = client.post(
        "/api/v1/users/register",
        json={"username": "shortpw_user", "email": "short@pw.com", "password": "pw"}
    )
    assert response.status_code == 422 # Pydantic validation error for password length

# --- Test User Login ---
def test_login_success(client: TestClient):
    username = "login_api_user"
    email = "login_api@example.com"
    password = "login_api_password"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password}
    )

    login_response = client.post(
        "/api/v1/users/login",
        data={"username": username, "password": password} # OAuth2PasswordRequestForm uses form data
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_login_success_with_email(client: TestClient):
    username = "login_email_api_user"
    email = "login_via_email_api@example.com"
    password = "login_api_password_email"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password}
    )

    login_response = client.post(
        "/api/v1/users/login",
        data={"username": email, "password": password} # Login with email
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data

def test_login_wrong_password(client: TestClient):
    username = "login_wrongpw_api"
    password = "correctpassword"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": "wrongpw@example.com", "password": password}
    )
    login_response = client.post(
        "/api/v1/users/login",
        data={"username": username, "password": "wrongpassword"}
    )
    assert login_response.status_code == 401
    assert "Incorrect username or password" in login_response.json()["detail"]

def test_login_user_not_found(client: TestClient):
    login_response = client.post(
        "/api/v1/users/login",
        data={"username": "nonexistentuser_api", "password": "password"}
    )
    assert login_response.status_code == 401 # Or 404, depends on how you want to signal
                                            # Usually 401 for security (don't reveal if user exists)

# --- Test Get Current User (/users/me) ---
def get_auth_headers(client: TestClient, username: str, password: str) -> dict:
    login_response = client.post(
        "/api/v1/users/login",
        data={"username": username, "password": password}
    )
    assert login_response.status_code == 200, f"Login failed for {username}: {login_response.text}"
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_current_user_me_success(client: TestClient):
    username = "me_user_api"
    email = "me_api@example.com"
    password = "me_password_api"
    full_name = "Me User API"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password, "full_name": full_name}
    )
    headers = get_auth_headers(client, username, password)

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["username"] == username
    assert data["email"] == email
    assert data["full_name"] == full_name
    assert data["is_active"] is True

def test_get_current_user_me_unauthorized(client: TestClient):
    response = client.get("/api/v1/users/me") # No auth header
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"] # FastAPI's default for missing token

def test_get_current_user_me_inactive(client: TestClient, db_session: Session):
    username = "inactive_me_api"
    password = "inactive_password"
    user_in_db = models.User(
        username=username,
        email=EmailStr("inactive_me@example.com"),
        hashed_password=get_password_hash(password), # Use your hash function
        is_active=False
    )
    db_session.add(user_in_db)
    db_session.commit()

    headers = get_auth_headers(client, username, password) # Login will succeed if user exists and pw is correct
                                                            # But get_current_active_user will fail

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 400 # From get_current_active_user
    assert "Inactive user" in me_response.json()["detail"]


# --- Test Update Current User (/users/me) ---
def test_update_current_user_me_success(client: TestClient):
    username = "update_me_api"
    email = "update_me_api@example.com"
    password = "update_me_password"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password, "full_name": "Original Name"}
    )
    headers = get_auth_headers(client, username, password)

    update_payload = {
        "full_name": "Updated Name API",
        "email": "new_update_me_api@example.com"
    }
    response = client.put("/api/v1/users/me", headers=headers, json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name API"
    assert data["email"] == "new_update_me_api@example.com"
    assert data["username"] == username # Username not changed

    # Verify change with a new /me call
    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.json()["full_name"] == "Updated Name API"

def test_update_current_user_me_change_password(client: TestClient):
    username = "update_me_pw_api"
    old_password = "old_password_api"
    new_password = "new_password_api"
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": "update_pw@example.com", "password": old_password}
    )
    headers = get_auth_headers(client, username, old_password)

    response = client.put("/api/v1/users/me", headers=headers, json={"password": new_password})
    assert response.status_code == 200

    # Try logging in with the new password
    new_headers = get_auth_headers(client, username, new_password)
    assert new_headers is not None

    # Try logging in with the old password (should fail)
    login_response_old_pw = client.post(
        "/api/v1/users/login",
        data={"username": username, "password": old_password}
    )
    assert login_response_old_pw.status_code == 401


def test_update_current_user_me_duplicate_email_on_update(client: TestClient):
    # User 1
    client.post("/api/v1/users/register", json={"username": "u1_dup_email_api", "email": "u1_dup@example.com", "password": "pw"})
    # User 2 (the one we will update)
    username2 = "u2_dup_email_api"
    password2 = "pw2"
    client.post("/api/v1/users/register", json={"username": username2, "email": "u2_dup@example.com", "password": password2})

    headers_user2 = get_auth_headers(client, username2, password2)

    # Attempt to update User 2's email to User 1's email
    response = client.put("/api/v1/users/me", headers=headers_user2, json={"email": "u1_dup@example.com"})
    assert response.status_code == 400
    assert "Email already registered by another user" in response.json()["detail"]

# Note: These API tests rely on the `client` fixture from `conftest.py` which handles
# TestClient setup, database initialization (in-memory SQLite via test_engine),
# and dependency overrides for `get_session`.
# The JWT secret and algorithm are taken from environment variables or defaults in `auth.py`.
# For more controlled tests, these could also be monkeypatched in `conftest.py`.
# (Added JWT related env vars to `set_test_env_vars_session_scoped` in conftest)
#
# The `db_session` fixture is also available if direct DB assertions are needed post-API call,
# but typically API tests should verify behavior through API responses.
# The `get_auth_headers` helper simplifies getting tokens for protected endpoints.
# These tests cover success and common failure scenarios for each endpoint.
# More edge cases (e.g., very long strings, special characters if not handled by Pydantic)
# could be added for robustness.
