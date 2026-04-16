from fastapi import HTTPException
from app.db.database import users_collection, ngo_collection
from app.core.security import hash_password, verify_password, create_access_token

async def signup_ngo(data):

    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # 1. create user (admin)
    user = {
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password)
    }

    user_result = await users_collection.insert_one(user)
    user_id = str(user_result.inserted_id)

    # 2. create NGO with admin_id
    ngo = {
        "name": data.name,
        "description": data.description,
        "admin_id": user_id   # 🔥 IMPORTANT CHANGE
    }

    await ngo_collection.insert_one(ngo)

    return {"message": "NGO created with admin"}