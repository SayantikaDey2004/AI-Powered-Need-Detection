from pydantic import BaseModel

class userLoginSchema(BaseModel):
    email: str
    password: str