from pydantic import BaseModel

class loginSchema(BaseModel):
    email: str
    password: str