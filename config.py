"""
config.py — Centralized settings via pydantic-settings
Reads from .env file automatically.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Google Gemini
    GOOGLE_API_KEY: str = Field(..., env="GOOGLE_API_KEY")
    GEMINI_MODEL: str = Field("gemini-1.5-flash", env="GEMINI_MODEL")
    GEMINI_EMBEDDING_MODEL: str = Field("models/embedding-001", env="GEMINI_EMBEDDING_MODEL")

    # Database
    SQLITE_DB_PATH: str = Field("./data/local_db.sqlite", env="SQLITE_DB_PATH")

    # App
    APP_HOST: str = Field("0.0.0.0", env="APP_HOST")
    APP_PORT: int = Field(5000, env="APP_PORT")
    DEBUG: bool = Field(True, env="DEBUG")
    LOG_LEVEL: str = Field("DEBUG", env="LOG_LEVEL")

    # Paths
    VECTOR_STORE_PATH: str = Field("./data/vector_store", env="VECTOR_STORE_PATH")
    PDF_UPLOAD_PATH: str = Field("./data/pdfs", env="PDF_UPLOAD_PATH")

    # Agent
    MAX_ITERATIONS: int = Field(10, env="MAX_ITERATIONS")
    TEMPERATURE: float = Field(0.1, env="TEMPERATURE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
