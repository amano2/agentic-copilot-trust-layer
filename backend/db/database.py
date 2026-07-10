import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env variables from backend/.env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/copilot")

# Fallback mechanism: Check connection or URL type
try:
    if DATABASE_URL.startswith("postgresql"):
        # Quick check if Postgres is running/connectable
        from sqlalchemy import create_engine
        # set a short timeout for the connection check
        temp_engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
        temp_engine.connect().close()
        engine = temp_engine
        print("Connected to PostgreSQL database.")
    else:
        engine = create_engine(DATABASE_URL)
except Exception as e:
    print(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "copilot.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for DB models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
