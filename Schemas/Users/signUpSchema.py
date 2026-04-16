from pydantic import BaseModel


class UserSignUpSchema(BaseModel):
    name: str
    email: str
    password: str
    