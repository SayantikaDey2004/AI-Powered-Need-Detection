from fastapi import HTTPException
from app.db.database import users_collection, ngo_collection
from app.core.security import hash_password, verify_password, create_access_token

async def login_user(data):

    user = await users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })

    return {"access_token": token}