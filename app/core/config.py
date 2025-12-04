from pathlib import Path

class Settings:
    PROJECT_NAME: str = "Learning FastAPI"
    PROJECT_VERSION: str = "1.0.0"
    
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database configuration
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DB_NAME = "users.db"
    DATABASE_URL = f"sqlite:///{BASE_DIR / DB_NAME}"

settings = Settings()