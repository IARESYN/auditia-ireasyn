import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

# Supabase (PostgreSQL) connection string handling
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback to local SQLite for development if no URL is provided
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./auditia.db"
    print("⚠️ Using local SQLite database.")
else:
    # Ensure the URL is compatible with SQLAlchemy (PostgreSQL)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("✅ Using Cloud Database (Supabase/PostgreSQL).")

engine = create_engine(
    DATABASE_URL, 
    # check_same_thread is only for SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True # Robustness for cloud connections
)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
