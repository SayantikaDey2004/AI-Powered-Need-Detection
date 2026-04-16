from fastapi import APIRouter
from app.schemas.auth import UserSignup, NGOSignup, LoginSchema, Token
from app.services.auth_service import signup_user, signup_ngo, login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/user")
async def register_user(data: UserSignup):
    return await signup_user(data)


@router.post("/signup/ngo")
async def register_ngo(data: NGOSignup):
    return await signup_ngo(data)


@router.post("/login", response_model=Token)
async def login(data: LoginSchema):
    return await login_user(data)