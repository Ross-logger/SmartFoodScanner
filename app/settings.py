"""
Application Settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from app.services.llm_ingredient_extractor import GeminiProvider
from backend.services.llm_ingredient_extractor import GroqProvider

load_dotenv()

# =============================================================================
# Database
# =============================================================================

IS_LOCAL_DATABASE = os.getenv("IS_LOCAL_DATABASE", "false").lower() in ("true", "1", "yes")
LOCAL_DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smartfoodscanner")

# Supabase
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL", "")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY", "")
SUPABASE_DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
SUPABASE_DB_PORT = int(os.getenv("SUPABASE_DB_PORT", "5432"))
SUPABASE_DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
SUPABASE_DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")

if IS_LOCAL_DATABASE:
    DATABASE_URL = LOCAL_DATABASE_URL
else:
    DATABASE_URL = f"postgresql://{SUPABASE_DB_USER}:{SUPABASE_DB_PASSWORD}@{SUPABASE_DB_HOST}:{SUPABASE_DB_PORT}/{SUPABASE_DB_NAME}"

# =============================================================================
# JWT
# =============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "3000"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# =============================================================================
# File Upload
# =============================================================================

MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# =============================================================================
# OCR
# =============================================================================

IS_OCR_CONFIDENCE_FILTER = os.getenv("IS_OCR_CONFIDENCE_FILTER", "true").lower() in ("true", "1", "yes")

# =============================================================================
# Cookies
# =============================================================================

ACCESS_TOKEN_COOKIE_NAME = os.getenv("ACCESS_TOKEN_COOKIE_NAME", "access_token")
REFRESH_TOKEN_COOKIE_NAME = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

# =============================================================================
# LLM Configuration
# =============================================================================

USE_LLM_ANALYZER = os.getenv("USE_LLM_ANALYZER", "true").lower() in ("true", "1", "yes")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or None
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or None
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# LM Studio
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "mistral-7b-instruct-v0.2")
LMSTUDIO_JSON_MODE = os.getenv("LMSTUDIO_JSON_MODE", "false").lower() in ("true", "1", "yes")

# =============================================================================
# ML
# =============================================================================

ML_PATH = Path(__file__).parent / "ML"

ocr_corrector = None
try:
    from backend.ML.inference_hybrid import OcrCorrector
    ocr_corrector = OcrCorrector(model_dir=str(ML_PATH / "models" / "hybrid"))
    print("✅ ML OCR Corrector loaded successfully!")
except Exception as e:
    print(f"⚠️  ML OCR Corrector not available: {e}")
    print("   Falling back to rule-based correction")

# =============================================================================
# Startup Status
# =============================================================================


LLM_MODELS = {
            "groq": lambda: GroqProvider(
                api_key=GROQ_API_KEY,
                model=GROQ_MODEL,   
                temperature=LLM_TEMPERATURE
            ),
            "gemini": lambda: GeminiProvider(
                api_key=GEMINI_API_KEY,
                model=GEMINI_MODEL,
                temperature=LLM_TEMPERATURE
            ),
            "openai": lambda: OpenAIProvider(
                api_key=OPENAI_API_KEY,
                model=OPENAI_MODEL,
                temperature=LLM_TEMPERATURE
            ),  
            "ollama": lambda: OllamaProvider(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL,
                temperature=LLM_TEMPERATURE
            ),
            "lmstudio": lambda: LMStudioProvider(
                base_url=LMSTUDIO_BASE_URL,
                model=LMSTUDIO_MODEL,
                temperature=LLM_TEMPERATURE,
                use_json_mode=LMSTUDIO_JSON_MODE
            ),
            "anthropic": lambda: AnthropicProvider(
                api_key=ANTHROPIC_API_KEY,
                model=ANTHROPIC_MODEL,
                temperature=LLM_TEMPERATURE
            ),
}

if USE_LLM_ANALYZER:
    _provider = LLM_PROVIDER.lower()
    print(f"✅ {_provider} LLM configured (Model: {LLM_MODELS[_provider].model})")
else:
    print("ℹ️  LLM Analyzer disabled")

