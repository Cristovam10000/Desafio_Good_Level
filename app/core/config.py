from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # APP
    APP_NAME: str = "Nola Analytics API"
    ENV: str = "development"
    DEBUG: bool = True

    # Banco de Dados
    DATABASE_URL: str 

    # Cube
    CUBE_API_URL: str 
    CUBE_API_TOKEN: str 

    # JWT
    JWT_SECRET: str 
    JWT_REFRESH_SECRET: str 
    JWT_SHARE_SECRET: str 
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_MINUTES: int = 60 * 24 * 7

    # CORS (aceita string separada por vírgulas no .env)
    CORS_ORIGINS: Optional[str] = None

    # CACHE HTTP 
    CACHE_MAX_AGE: int = 60 
    CACHE_SWR: int = 300

    # IA / Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192  # Máximo para flash models

    @field_validator("JWT_SECRET", "JWT_REFRESH_SECRET", "JWT_SHARE_SECRET")
    @classmethod
    def _jwt_min_length(cls, v: str) -> str:
        if v is None or len(v) < 32:
            raise ValueError("JWT secret deve ter pelo menos 32 caracteres.")
        return v

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        v = self.CORS_ORIGINS
        if not v:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignora chaves extras no .env
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

       
