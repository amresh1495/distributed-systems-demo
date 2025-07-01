import os
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.exc import OperationalError
import time

# Default to SQLite for local dev if DB_URL is not set, but prefer PostgreSQL
DATABASE_URL = os.getenv("USER_SERVICE_DATABASE_URL", "sqlite:///./user_service.db")

# For PostgreSQL, you might want to add pool_recycle or other parameters
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def ensure_database_connection(max_retries=5, delay_seconds=5):
    """Tries to connect to the database with retries."""
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                # If connection is successful, break the loop
                print("Successfully connected to the database.")
                return True
        except OperationalError as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                print("Max retries reached. Could not connect to the database.")
                return False

def create_db_and_tables():
    """Creates database tables based on SQLModel metadata."""
    # First, ensure the database is connectable, especially for external DBs like Postgres
    if not ensure_database_connection():
        # Decide how to handle this - raise an error, exit, etc.
        # For now, it will print an error and might fail later if the app proceeds.
        # Depending on app setup, this might halt startup.
        print("Proceeding without guaranteed DB connection. Table creation might fail if DB is not accessible.")

    # Now, attempt to create tables
    # This function assumes the database itself (e.g., user_service_db) already exists.
    # It only creates tables within that database.
    # The K8s init job (11-postgres-init-job.yml) is responsible for creating the database itself.
    try:
        SQLModel.metadata.create_all(engine)
        print("Tables created successfully (if they didn't exist).")
    except OperationalError as e:
        print(f"Error creating tables: {e}")
        print("Please ensure the database server is running and the database specified in DATABASE_URL exists.")
        # Optionally, re-raise the exception or handle it as critical
        # raise
    except Exception as e:
        print(f"An unexpected error occurred during table creation: {e}")
        # raise

def get_session():
    with Session(engine) as session:
        yield session

# The actual creation of the database (e.g., 'user_service_db') is expected to be handled
# by PostgreSQL itself (on init for Docker Compose if it's the main DB) or
# by the Kubernetes init job (11-postgres-init-job.yml).
# This `create_db_and_tables` function only creates the tables within that database.
#
# If using SQLite, `create_db_and_tables` will also create the .db file if it doesn't exist.
#
# The `ensure_database_connection` is a basic retry mechanism. For robust production apps,
# consider more sophisticated health checks and startup procedures.
