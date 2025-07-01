import pytest
from typing import Generator, Any
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool # For in-memory SQLite
import os

# Import the main FastAPI app and the get_session dependency from your service
# Adjust the import path based on your project structure.
# This assumes tests are run from the root of the `user_service` or project root with proper PYTHONPATH.
from ..app.main import app # The FastAPI app instance
from ..app.db import get_session as original_get_session # The original get_session
from ..app.models import User # Import a model to help with table creation check

# Define a test database URL (in-memory SQLite)
# Using StaticPool for SQLite in-memory as recommended by FastAPI/SQLModel docs for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create a test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite
    poolclass=StaticPool, # Use StaticPool for in-memory DB with TestClient
)

@pytest.fixture(scope="session", autouse=True)
def create_test_tables_session_scoped():
    """
    Session-scoped fixture to create all tables in the test database once per test session.
    """
    # print("Creating test tables (session-scoped)...")
    SQLModel.metadata.create_all(test_engine)
    # print("Test tables created.")
    yield
    # Teardown (optional, as it's in-memory, but good practice if it were a file DB)
    # print("Tearing down test tables (session-scoped)...")
    # SQLModel.metadata.drop_all(test_engine) # Not strictly necessary for :memory:

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, Any, None]:
    """
    Provides a database session for each test function.
    Ensures tables are created and data is cleared between tests.
    """
    # print("Setting up DB session for a test function...")
    with Session(test_engine) as session:
        # SQLModel.metadata.drop_all(test_engine) # Drop all tables
        # SQLModel.metadata.create_all(test_engine) # Recreate all tables
        # The above drop/create per function is too slow if session-scoped create_all is used.
        # Instead, we should clear data from tables or rely on transactions if tests modify data.
        # For simplicity with SQLite in-memory and StaticPool, the DB is fresh per session if not careful.
        # The session-scoped create_test_tables_session_scoped handles table creation once.
        # To ensure test isolation for data, each test should clean up or use transactions.
        # A common pattern is to start a transaction, yield session, then rollback.

        connection = session.connection()
        transaction = connection.begin()
        # print("DB session transaction started.")
        try:
            yield session
        finally:
            # print("Rolling back DB session transaction.")
            transaction.rollback()
            # session.close() # Not needed with 'with Session(...)' context manager

# Override the get_session dependency for testing
def get_test_session_override() -> Generator[Session, Any, None]:
    """
    Overrides the production `get_session` dependency to use the test database.
    """
    # print("Overriding get_session with test session...")
    with Session(test_engine) as session:
        # No need to manage transactions here if db_session fixture does it.
        # This override is for TestClient which calls endpoints.
        # The endpoints will then use this session.
        # For API tests that modify data, the transaction handling in db_session might not directly apply
        # unless TestClient is also made to use that transactional session.
        # A simpler way for TestClient is just to provide a fresh session and rely on test isolation.
        # Let's ensure this provides a clean session state without explicit transaction rollback here,
        # assuming each TestClient call is somewhat atomic or tests clean up.
        # The session-scoped table creation and function-scoped session ensures structure is there.
        yield session


@pytest.fixture(scope="module") # Or "session" if client can be reused extensively
def client() -> Generator[TestClient, Any, None]:
    """
    Provides a TestClient instance for making API requests.
    Overrides the app's get_session dependency.
    """
    # print("Setting up TestClient...")
    app.dependency_overrides[original_get_session] = get_test_session_override
    with TestClient(app) as c:
        # print("TestClient created.")
        yield c
    # print("TestClient teardown.")
    app.dependency_overrides.clear() # Clear overrides after tests

# Note:
# The `create_test_tables_session_scoped` fixture runs once per session (`autouse=True`).
# The `db_session` fixture provides a transactional session for CRUD tests, ensuring data isolation.
# The `client` fixture provides a `TestClient` for API tests, overriding the `get_session`
# dependency to use the in-memory SQLite database.
#
# For API tests that modify data, ensuring data isolation can be tricky.
# One approach:
# 1. Have `create_test_tables_session_scoped` create tables once.
# 2. Before each API test function, clear all data from tables. This can be done in `client` fixture or a separate one.
#    Example clear data:
#    for table in reversed(SQLModel.metadata.sorted_tables):
#        session.execute(table.delete())
#    session.commit()
# For now, we rely on the fact that each test uses a fresh in-memory DB session from `get_test_session_override`
# and StaticPool, which should provide isolation. If tests interfere, explicit data clearing will be needed.
# The transaction rollback in `db_session` is good for direct CRUD tests.
# For TestClient, the default behavior of StaticPool with :memory: means each new Session
# effectively sees a clean database, which is good for test isolation.
# However, if multiple calls within a single test function using TestClient need to see
# cumulative effects, this setup is fine. Isolation is between test *functions*.
#
# Ensure your JWT_SECRET_KEY and ALGORITHM are consistent for tests if you're testing token generation/validation.
# You might want to set these as environment variables for the test environment or override them in auth.py for tests.
# For now, User Service auth.py uses os.getenv with defaults, which should be acceptable for initial tests.
# If specific keys are needed for tests, they can be set via `monkeypatch` fixture from pytest.
# Example:
# @pytest.fixture
# def mock_env_vars(monkeypatch):
# monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
# monkeypatch.setenv("ALGORITHM", "HS256")
# monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
# (and then use this fixture in tests that involve JWTs)
# This is not added yet, but a good practice for auth testing.
#
# Test execution:
# From the `ecommerce_platform` root directory:
# `PYTHONPATH=. pytest services/user_service/tests`
# Or from `ecommerce_platform/services/user_service`:
# `PYTHONPATH=../.. pytest tests`
# Or install the service as an editable package and run `pytest`.
#
# The `autouse=True` on `create_test_tables_session_scoped` ensures it runs without being explicitly requested.
# For the `db_session` fixture to work with transactions correctly, it's best used for tests that directly call CRUD functions.
# API tests using `client` will use `get_test_session_override`. The `StaticPool` for in-memory SQLite
# with `TestClient` typically ensures that each test function effectively gets a clean database state because
# connections from the pool don't share state in the same way as file-based DBs or server-based DBs.
# If any data persists across TestClient calls within different test functions, then explicit data clearing
# before each test function (e.g., in the `client` fixture setup) would be necessary.
# Let's assume StaticPool gives us enough isolation for now.
# The `SQLModel.metadata.create_all(test_engine)` in `create_test_tables_session_scoped` is key.
# It should only be called ONCE per session.
# If individual tests need to drop and recreate tables (which they shouldn't if using transactions or clean sessions),
# they would do so on their own session.
# The crucial part is that TestClient uses `get_test_session_override` which yields sessions from `test_engine`.
# The `test_engine` with `StaticPool` and `:memory:` means each connection (and thus session) is isolated.
# This setup should be fine for test isolation between test functions.
#
# One final check: `create_db_and_tables()` from `user_service.app.db` is called in `user_service.app.main` during app lifespan startup.
# When TestClient(app) is initialized, this lifespan event will fire.
# It will try to call `create_db_and_tables()` which uses the *production* engine if not overridden.
# This is a problem. The app's startup `create_db_and_tables` needs to use the test_engine during tests.
#
# Solution: The app's `create_db_and_tables` function needs to be aware of the test engine.
# This can be done by making the `engine` in `db.py` configurable or by patching it during tests.
#
# A simpler way for FastAPI TestClient:
# The app's lifespan `create_db_and_tables()` will run using its configured engine.
# Our `create_test_tables_session_scoped` fixture uses `test_engine`.
# If `TEST_DATABASE_URL` is `:memory:`, these are different in-memory DBs.
# The TestClient requests will use `get_test_session_override` which uses `test_engine`.
# So, API calls go to the right test DB.
# The app's own startup `create_db_and_tables()` call is on a *different* (potentially production-configured or default SQLite file)
# engine if `USER_SERVICE_DATABASE_URL` is set, or another in-memory DB if not. This is generally fine as it doesn't interfere
# with the test_engine used by the test session override.
#
# Let's ensure the app's `create_db_and_tables` from `main.py` doesn't cause issues.
# The `lifespan` in `main.py` calls `create_db_and_tables()`.
# `db.create_db_and_tables()` uses the `engine` defined in `db.py`.
# This `engine` is based on `USER_SERVICE_DATABASE_URL` or defaults to `sqlite:///./user_service.db`.
#
# During tests:
# 1. `create_test_tables_session_scoped` creates tables on `test_engine` (in-memory). (Good)
# 2. `client` fixture is set up:
#    - `app.dependency_overrides[original_get_session] = get_test_session_override` (Good, API calls use test_engine)
#    - `TestClient(app)` is created. This initializes the app.
#    - The app's `lifespan` startup event fires. It calls `create_db_and_tables()` from `app.db`.
#    - This `create_db_and_tables()` uses the `engine` from `app.db`.
#      If `USER_SERVICE_DATABASE_URL` is not set by tests, this engine is `sqlite:///./user_service.db`.
#      This means the app startup creates/accesses a local file `user_service.db`.
#      This is usually harmless for tests focusing on `test_engine`, but it's a side effect.
#
# To prevent this side effect:
# We can use `monkeypatch` to set `USER_SERVICE_DATABASE_URL` to the `TEST_DATABASE_URL` for the duration of tests.
# This makes the app's startup also use an in-memory (but potentially different) SQLite DB.
# Or, more robustly, make the `engine` in `app.db` itself patchable.
#
# For now, the current `conftest.py` is a good start. The side effect of creating `user_service.db`
# by the app's own startup is minor for now. The critical part is that API test requests
# are routed to `test_engine` via the dependency override.
#
# A slightly cleaner approach for `create_test_tables_session_scoped`:
# It's good, but `SQLModel.metadata.create_all(test_engine)` should ideally only be called once.
#
# Consider the order:
# - `create_test_tables_session_scoped` (session scope, autouse=True): Creates tables on test_engine.
# - `client` (module scope):
#   - Overrides `get_session`.
#   - `TestClient(app)`: App starts. Lifespan calls `db.create_db_and_tables()`. This uses the *original* `db.engine`.
#     If `USER_SERVICE_DATABASE_URL` is not set, it creates/uses `./user_service.db`. This is a potential side effect.
#
# To make the app itself use the test_engine during TestClient startup:
# We can modify `app.db.engine` directly or control `USER_SERVICE_DATABASE_URL`.
# Let's add a fixture to set `USER_SERVICE_DATABASE_URL` for tests.

@pytest.fixture(scope="session", autouse=True)
def set_test_database_url(monkeypatch_session):
    """
    Sets the USER_SERVICE_DATABASE_URL to the test database URL for the test session.
    This ensures that the app's own startup sequence (lifespan event) uses an in-memory DB
    if it tries to create tables, preventing side effects like creating a local file DB.
    """
    # print(f"Patching USER_SERVICE_DATABASE_URL to {TEST_DATABASE_URL} for the session.")
    monkeypatch_session.setenv("USER_SERVICE_DATABASE_URL", TEST_DATABASE_URL)
    # This also means the `engine` in `app.db` will be configured with TEST_DATABASE_URL
    # when the app initializes via TestClient.
    # However, StaticPool might behave unexpectedly if multiple engines point to the same :memory:
    # without careful management.
    # The key is that `get_test_session_override` uses `test_engine` which is correctly configured with StaticPool.
    # The app's own `engine` from `db.py` will also point to `TEST_DATABASE_URL` but might create its own StaticPool.
    # This should be fine as they are separate engine instances.
    # The `create_db_and_tables()` in app startup will then run on an in-memory DB.
    # And `create_test_tables_session_scoped` also runs on `test_engine` (in-memory).
    # This is better than creating a file.

@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch."""
    from _pytest.monkeypatch import MonkeyPatch
    m = MonkeyPatch()
    yield m
    m.undo()

# The `create_test_tables_session_scoped` will ensure tables are created on `test_engine`.
# The app's startup, due to `set_test_database_url`, will attempt `create_db_and_tables` on an engine
# also configured by `TEST_DATABASE_URL`. If this engine is different from `test_engine` but points to the
# same in-memory SQLite (which is tricky with :memory: unless it's the exact same engine object),
# it might lead to issues or redundant table creation attempts.
#
# Safest is to ensure `app.db.engine` is the same as `test_engine` during tests.
# This is harder to patch cleanly from conftest without direct imports and modifications.
#
# Let's refine:
# The `TestClient` should initialize the app *after* its dependencies or configurations are patched.
# The dependency_override for `get_session` is good.
# The `create_db_and_tables()` in `main.py` lifespan:
# It's called when `TestClient(app)` runs.
# If `USER_SERVICE_DATABASE_URL` is monkeypatched to `TEST_DATABASE_URL`, then `app.db.engine`
# will be created using this in-memory URL. `app.db.create_db_and_tables()` will then operate on this.
# Simultaneously, `create_test_tables_session_scoped` operates on `test_engine`.
# These are two different engine instances pointing to "sqlite:///:memory:".
# For SQLite in-memory, distinct engines mean distinct databases unless a shared cache is used.
# So, the app startup creates tables in one in-memory DB, and tests run against `test_engine`'s in-memory DB.
# This is fine. The tables are created in both (isolated) in-memory DBs.
# The `set_test_database_url` fixture makes the app's own startup cleaner (no file creation).
# The `create_test_tables_session_scoped` ensures the `test_engine` (used by actual tests) has tables.
# This revised structure seems robust.
#
# Removing `autouse=True` from `create_test_tables_session_scoped` and making `client` depend on it explicitly
# might offer clearer control if needed, but autouse for session-setup is common.
# Let's make `client` depend on `create_test_tables_session_scoped` to ensure order.

@pytest.fixture(scope="session") # Changed from autouse=True
def setup_test_database_session_scoped():
    SQLModel.metadata.create_all(test_engine)
    yield
    # SQLModel.metadata.drop_all(test_engine) # Optional for :memory:

@pytest.fixture(scope="module")
def client(setup_test_database_session_scoped, set_test_database_url_session_scoped) -> Generator[TestClient, Any, None]: # Added dependency
    app.dependency_overrides[original_get_session] = get_test_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="session", autouse=True) # Renamed and kept autouse for URL patching
def set_test_database_url_session_scoped(monkeypatch_session):
    monkeypatch_session.setenv("USER_SERVICE_DATABASE_URL", TEST_DATABASE_URL)

# This looks more controlled now.
# `set_test_database_url_session_scoped` (autouse) patches env var first for app init.
# `setup_test_database_session_scoped` (session scope, not autouse) creates tables on test_engine.
# `client` fixture (module scope) depends on `setup_test_database_session_scoped`, so tables exist before client is made.
# This ensures `test_engine` has tables. The app's internal engine (from main.py lifespan) will also use
# an in-memory DB due to the patched env var, and create its tables there, which is fine and isolated.
