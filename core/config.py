from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_LOCAL: str
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str

    class config:
        env_file = ".env"
        settings = Settings()