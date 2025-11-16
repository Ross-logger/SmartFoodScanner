from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    # Database Selection
    IS_LOCAL_DATABASE: bool = False
    
    # Local Database
    LOCAL_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/foodscanner"
    
    # Supabase Configuration
    SUPABASE_PROJECT_URL: str = ""
    SUPABASE_API_KEY: str = ""
    SUPABASE_DB_HOST: str = ""
    SUPABASE_DB_PORT: int = 5432
    SUPABASE_DB_NAME: str = "postgres"
    SUPABASE_DB_USER: str = "postgres"
    SUPABASE_DB_PASSWORD: str = ""
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3000
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # File upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    # Cookies
    ACCESS_TOKEN_COOKIE_NAME: str = "access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"  # "lax" | "strict" | "none"
    COOKIE_DOMAIN: Optional[str] = None
    
    @property
    def DATABASE_URL(self) -> str:
        """
        Returns the appropriate database URL based on IS_LOCAL_DATABASE setting.
        If IS_LOCAL_DATABASE is True, uses local database.
        Otherwise, uses Supabase database.
        """
        if self.IS_LOCAL_DATABASE:
            return self.LOCAL_DATABASE_URL
        else:
            # Build Supabase PostgreSQL connection string
            return f"postgresql://{self.SUPABASE_DB_USER}:{self.SUPABASE_DB_PASSWORD}@{self.SUPABASE_DB_HOST}:{self.SUPABASE_DB_PORT}/{self.SUPABASE_DB_NAME}"
    
    class Config:
        env_file = ".env"


settings = Settings()

ML_PATH = Path(__file__).parent / "ML"
# Initialize ML OCR corrector
ocr_corrector = None
try:
    from app.ML.inference_hybrid import OcrCorrector
    ocr_corrector = OcrCorrector(model_dir=str(ML_PATH / "models" / "hybrid"))
    print("✅ ML OCR Corrector loaded successfully!")
except Exception as e:
    print(f"⚠️  ML OCR Corrector not available: {e}")
    print("   Falling back to rule-based correction")


