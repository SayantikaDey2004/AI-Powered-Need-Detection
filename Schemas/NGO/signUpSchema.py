from pydantic import BaseModel

class NgoSignUpSchema(BaseModel):
    name: str
    email: str
    address: str
    password: str
    description: str