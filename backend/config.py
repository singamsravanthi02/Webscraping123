from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SPIP API"
    POSTGRES_USER: str = "spip_user"
    POSTGRES_PASSWORD: str = "spip_password"
    POSTGRES_DB: str = "spip_db"
    POSTGRES_SERVER: str = "localhost" # use 'db' in docker
    POSTGRES_PORT: str = "5432"
    GEMINI_API_KEY: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
