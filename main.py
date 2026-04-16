from fastapi import FastAPI
from app.db.db import AsyncIOMotorClient
app = FastAPI()
app_include_router = (auth_router)
@app.get("/")
def root():
    return {"message": "API is working!"}