import re

from fastapi import HTTPException
from app.db.db import users_collection, ngo_collection
from app.core.security import hash_password, verify_password, create_access_token


async def _generate_next_user_id() -> str:
    id_pattern = re.compile(r"^User_(\d+)$", re.IGNORECASE)

    existing_users = await users_collection.find(
        {"user_id": {"$regex": r"^User_\d+$", "$options": "i"}}
    ).to_list(length=100000)

    max_number = 0
    for user in existing_users:
        current_user_id = str(user.get("user_id") or "")
        matched = id_pattern.match(current_user_id)
        if matched:
            max_number = max(max_number, int(matched.group(1)))

    return f"User_{max_number + 1:02d}"


# -------- USER SIGNUP --------
async def signup_user(data):

    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user_id = await _generate_next_user_id()

    user = {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password)
    }

    await users_collection.insert_one(user)

    return {
        "message": "User created successfully",
        "user_id": user_id,
    }