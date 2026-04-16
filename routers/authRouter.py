from fastapi import APIRouter
from app.Schemas.Users.signUpSchema import UserSignUpSchema
from app.Schemas.NGO.signUpSchema import NgoSignUpSchema
from app.Schemas.logInSchema import loginSchema
from app.Schemas.token import Token
from app.auths.Users.userSignUp import signup_user
from app.auths.NGO.NgoSignUp import signup_ngo
from app.auths.LogIn import login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/user")
async def register_user(data: UserSignUpSchema):
    return await signup_user(data)


@router.post("/signup/ngo")
async def register_ngo(data: NgoSignUpSchema):
    return await signup_ngo(data)


@router.post("/login", response_model=Token)
async def login(data: loginSchema):
    return await login_user(data)