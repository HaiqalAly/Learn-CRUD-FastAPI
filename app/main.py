from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path

from pydantic import BaseModel
from typing import List, Optional

# Authentication imports
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt

# Security configurations
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Learning FastAPI | Integration with Databases")

# Database setup
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "test.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, index=True)
    hashed_pwd = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

# API Pydantic Models
class UserCreate(BaseModel):
    name:str
    email:str
    role:str
    password:str

class UserResponse(BaseModel):
    id:int
    name:str
    email:str
    role:str
    is_active:bool

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Security functions
def verify_pwd(plain_pwd, hashed_pwd) -> bool:
    return pwd_context.verify(plain_pwd, hashed_pwd)

def get_hashed_pwd(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str, credentials_exception) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        enumerated_email: str = payload.get("sub")
        if enumerated_email is None:
            raise credentials_exception
        return TokenData(email=enumerated_email)
    except jwt.PyJWTError:
        raise credentials_exception

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth dependencies
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_access_token(token, credentials_exception)
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Authentication endpoint
@app.post("/register", response_model=UserResponse, status_code=201)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered!")
    
    hashed_password = get_hashed_pwd(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        role=user.role,
        hashed_pwd=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_pwd(form_data.password, user.hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
    
# Endpoint
@app.get("/")
def root():
    return {"message": "Welcome to FastAPI with Database Integration!"}

@app.get("/profile", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/verify-token")
def verify_token(current_user: User = Depends(get_current_active_user)):
    return {"message": "Token is valid!", "user": current_user.email}

# Get user by ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    return user

# Get all users
@app.get("/users/", response_model=List[UserResponse])
def get_users(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

# Create user
@app.post("/users/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered!")
    
    hashed_password = get_hashed_pwd(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        role=user.role,
        hashed_pwd=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Update user
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, update_user: UserCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found!")
    
    existing_user.name = update_user.name
    existing_user.email = update_user.email
    existing_user.role = update_user.role

    db.commit()
    db.refresh(existing_user)
    return existing_user

# Delete user
@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Users cannot delete themselves!")
    
    db.delete(user)
    db.commit()
    return