from fastapi import HTTPException
import re

from app.db.db import users_collection, ngo_collection
from app.core.security import hash_password, verify_password, create_access_token


def _build_ngo_id_prefix(name: str) -> str:
    normalized_name = re.sub(r"\s+", "_", name.strip())
    normalized_name = re.sub(r"[^A-Za-z0-9_]", "", normalized_name)
    normalized_name = re.sub(r"_+", "_", normalized_name).strip("_")
    return normalized_name or "NGO"


async def _generate_next_ngo_id(name: str) -> str:
    prefix = _build_ngo_id_prefix(name)
    id_pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)

    existing_ngos = await ngo_collection.find(
        {"ngo_id": {"$regex": rf"^{re.escape(prefix)}_\d+$", "$options": "i"}}
    ).to_list(length=10000)

    max_number = 0
    for ngo in existing_ngos:
        current_ngo_id = str(ngo.get("ngo_id") or "")
        matched = id_pattern.match(current_ngo_id)
        if matched:
            max_number = max(max_number, int(matched.group(1)))

    return f"{prefix}_{max_number + 1:02d}"


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
    ngo_id = await _generate_next_ngo_id(data.name)

    # 2. create NGO with admin_id
    ngo = {
        "name": data.name,
        "address": data.address,
        "description": data.description,
        "admin_id": user_id,
        "ngo_id": ngo_id,
    }

    await ngo_collection.insert_one(ngo)

    return {
        "message": "NGO created with admin",
        "ngo_id": ngo_id,
    }