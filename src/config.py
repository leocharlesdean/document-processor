import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):

    load_dotenv()
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # ML Model settings
    OPENAI_API_KEY: str = ""
    MODEL_CACHE_DIR: str = "models"
    
    # Storage settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"

settings = Settings()