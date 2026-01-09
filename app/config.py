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
    
    # OCR settings
    IS_OCR_CONFIDENCE_FILTER: bool = True  # Filter OCR results by confidence threshold
    
    # Cookies
    ACCESS_TOKEN_COOKIE_NAME: str = "access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"  # "lax" | "strict" | "none"
    COOKIE_DOMAIN: Optional[str] = None
    
    # LLM Configuration for Dietary Analysis
    USE_LLM_ANALYZER: bool = True  # Enable LLM-based dietary analysis
    LLM_PROVIDER: str = "groq"  # Options: "groq", "gemini", "openai", "ollama", "huggingface"
    LLM_TEMPERATURE: float = 0.3  # Lower temperature for more consistent analysis
    
    # OpenAI Configuration (paid)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Groq Configuration (FREE - Recommended)
    GROQ_API_KEY: Optional[str] = None  # Get free API key from https://console.groq.com
    GROQ_MODEL: str = "llama-3.1-70b-versatile"  # or "mixtral-8x7b-32768", "gemma2-9b-it"
    
    # Google Gemini Configuration (FREE)
    GEMINI_API_KEY: Optional[str] = None  # Get free API key from https://aistudio.google.com/app/apikey
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # or "gemini-1.5-flash", "gemini-1.5-pro"
    
    # Ollama Configuration (FREE - Local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # Local Ollama server
    OLLAMA_MODEL: str = "llama3"  # or "mistral", "gemma2", etc.
    
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

# Initialize LLM Analyzer
if settings.USE_LLM_ANALYZER:
    if settings.LLM_PROVIDER.lower() == "groq":
        if settings.GROQ_API_KEY:
            print(f"✅ Groq LLM Analyzer configured (Model: {settings.GROQ_MODEL})")
        else:
            print("⚠️  Groq API key not found. Add GROQ_API_KEY to .env file")
    elif settings.LLM_PROVIDER.lower() == "gemini":
        if settings.GEMINI_API_KEY:
            print(f"✅ Gemini LLM Analyzer configured (Model: {settings.GEMINI_MODEL})")
        else:
            print("⚠️  Gemini API key not found. Add GEMINI_API_KEY to .env file")
    elif settings.LLM_PROVIDER.lower() == "ollama":
        print(f"✅ Ollama LLM Analyzer configured (Model: {settings.OLLAMA_MODEL})")
    elif settings.LLM_PROVIDER.lower() == "openai":
        if settings.OPENAI_API_KEY:
            print(f"✅ OpenAI LLM Analyzer configured (Model: {settings.OPENAI_MODEL})")
        else:
            print("⚠️  OpenAI API key not found. Add OPENAI_API_KEY to .env file")
    else:
        print(f"⚠️  Unknown LLM provider: {settings.LLM_PROVIDER}")
else:
    print("ℹ️  LLM Analyzer disabled (USE_LLM_ANALYZER=false)")


