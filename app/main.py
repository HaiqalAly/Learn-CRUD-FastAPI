from fastapi import FastAPI
from app.core.config import settings
from app.database.database import engine, Base
from app.routers import auth, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth.router)
app.include_router(users.router)

@app.get("/")
def root():
    return {"message": "Welcome to the refactored FastAPI!"}