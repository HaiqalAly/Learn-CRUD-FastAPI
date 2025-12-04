from sqlalchemy import Column, Integer, String, Boolean
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, index=True)
    hashed_pwd = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)