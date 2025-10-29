from functools import lru_cache
from typing import List
from pydantic import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # APP
    APP_NAME: str = "Nola Analytics API"
    ENV: str = "development"
    DEBUG: bool = True

    # Banco de Dados
    DATABASE_URL: str = ( "postgresql+psycopg://postgres:postgres@localhost:5432/nola" )

    # Cube
    CUBE_API_URL: str = "http://localhost:4000/cubejs-api"
    CUBE_API_TOKEN: str = "YOUR_CUBE_API_TOKEN"

    # JWT
    JWT_SECRET: str = "your_jwt_secret"
    JWT_REFRESH_SECRET: str = "your_jwt_refresh_secret"
    JWT_SHARE_SECRET: str = "your_jwt_share_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_MINUTES: int = 60 * 24 * 7

    # CORS 
    CORS_ORIGINS: List[str] = ["*"]

    # CACHE HTTP 
    CACHE_MAX_AGE: int = 60 
    CACHE_SWR: int = 300

    @field_validator("JWT_SECRET", "JWT_REFRESH_SECRET", "JWT_SHARE_SECRET")
    @classmethod
    def _jwt_min_length(cls, v: str) -> str:
       if v is None or len(v) < 32:
           raise ValueError("JWT secret deve ter pelo menos 32 caracteres.")
       
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            parts = [s.strip() for s in v.split(",") if s.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

       
