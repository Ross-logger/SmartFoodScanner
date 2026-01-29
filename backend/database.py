from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend import settings

# Configure engine with appropriate settings for Supabase or local database
engine_kwargs = {
    "pool_pre_ping": True,  # Enable connection health checks
    "pool_recycle": 3600,   # Recycle connections after 1 hour
}

# Add SSL requirements for Supabase connections
if not settings.IS_LOCAL_DATABASE:
    engine_kwargs["connect_args"] = {
        "sslmode": "require"  # Supabase requires SSL connections
    }

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

