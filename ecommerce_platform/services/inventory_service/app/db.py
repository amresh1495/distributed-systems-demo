import os
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.exc import OperationalError
import time

DATABASE_URL = os.getenv("INVENTORY_SERVICE_DATABASE_URL", "sqlite:///./inventory_service.db")

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def ensure_database_connection(max_retries=5, delay_seconds=5):
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                print("Successfully connected to the Inventory Service database.")
                return True
        except OperationalError as e:
            print(f"Inventory Service DB connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                print("Max retries reached. Could not connect to the Inventory Service database.")
                return False

def create_db_and_tables():
    if not ensure_database_connection():
        print("Proceeding without guaranteed DB connection for Inventory Service. Table creation might fail.")

    try:
        SQLModel.metadata.create_all(engine)
        print("Inventory Service tables created successfully (if they didn't exist).")
    except OperationalError as e:
        print(f"Error creating Inventory Service tables: {e}")
        print("Please ensure the database server is running and the database specified in INVENTORY_SERVICE_DATABASE_URL exists.")
    except Exception as e:
        print(f"An unexpected error occurred during Inventory Service table creation: {e}")

def get_session():
    with Session(engine) as session:
        yield session
