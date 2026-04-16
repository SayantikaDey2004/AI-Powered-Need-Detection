from fastapi import HTTPException
from app.db.database import users_collection, ngo_collection
from app.core.security import hash_password, verify_password, create_access_token


# -------- USER SIGNUP --------
async def signup_user(data):

    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = {
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password)
    }

    await users_collection.insert_one(user)

    return {"message": "User created successfully"}