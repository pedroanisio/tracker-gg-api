from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean
# import hashlib
import os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os

load_dotenv()


Base = declarative_base()


# class APIKey(Base):
#     __tablename__ = "api_keys"
# 
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     key = Column(String, unique=True, nullable=False)
#     user = Column(String, nullable=False)
#     permission = Column(String, default="normal")
#     created_at = Column(DateTime, default=func.now(), nullable=False)
#     is_active = Column(Boolean, default=True, nullable=False)
#     last_used_at = Column(DateTime, nullable=True)


DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True, future=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# def hash_api_key(api_key: str) -> str:
#     """Hashes an API key using SHA256."""
#     # return hashlib.sha256(api_key.encode()).hexdigest()


def create_db() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


# def add_api_key(
#     db: Session, api_key: str, user: str, permission: str = "normal"
# ) -> APIKey:
#     """
#     Function to insert a new API key into the database.
#     Ensures the key is unique.
# 
#     Args:
#         db: The SQLAlchemy session.
#         api_key: The API key to add.
#         user: The associated user for the API key.
#         permission: The permission level for the API key ('normal' or 'admin').
# 
#     Returns:
#         The created APIKey object.
# 
#     Raises:
#         Exception: If the API key already exists in the database.
#     """
#     # hashed_key = hash_api_key(api_key)
#     # db_api_key = APIKey(key=hashed_key, user=user, permission=permission)
#     # db.add(db_api_key)
#     # try:
#     #     db.commit()
# 
#     # except IntegrityError as e:
#     #     db.rollback()
# 
#     #     # Note: The exception message will show the plaintext key that was attempted,
#     #     # but the uniqueness constraint in the DB is on the hashed key.
#     #     # This is generally fine as this function is called internally.
#     #     raise Exception(f"Hashed API Key for '{api_key[:8]}...' might already exist or another integrity error occurred.") from e
#     # return db_api_key
