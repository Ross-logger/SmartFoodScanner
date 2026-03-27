"""
Application Settings
"""

import os
import platform
from pathlib import Path
from dotenv import load_dotenv
from numpy._core.numeric import True_

load_dotenv()

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

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

# Minimum EasyOCR line confidence to keep when ``IS_OCR_CONFIDENCE_FILTER`` is on.
OCR_CONFIDENCE_FILTER_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_FILTER_THRESHOLD", "0.3"))

# Skip SymSpell on ingredient segments tied to EasyOCR lines at or above this confidence.
EASYOCR_SKIP_SYMSPELL_MIN_CONFIDENCE = float(os.getenv("EASYOCR_SKIP_SYMSPELL_MIN_CONFIDENCE", "0.9"))

# Automatic preprocessing before EasyOCR (contrast + resize); no user action required
OCR_PREPROCESS_ENABLED = os.getenv("OCR_PREPROCESS_ENABLED", "true").lower() in ("true", "1", "yes")
OCR_PREPROCESS_TARGET_SHORT_EDGE = int(os.getenv("OCR_PREPROCESS_TARGET_SHORT_EDGE", "1000"))
OCR_PREPROCESS_MAX_LONG_EDGE = int(os.getenv("OCR_PREPROCESS_MAX_LONG_EDGE", "2400"))

# EasyOCR: PyTorch + Apple Metal (MPS) can raise OSError errno 5 (EIO) during init or
# inference when the GPU/display stack is in certain states. Default macOS to CPU;
# set EASYOCR_USE_GPU=true to opt into GPU after verifying it is stable on your machine.
EASYOCR_USE_GPU = True

# Mistral OCR — cloud-based OCR via the Mistral AI API (mistral-ocr-latest).
# Per-user toggle lives in DietaryProfile.use_mistral_ocr.
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY") or None
MISTRAL_OCR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

# HuggingFace ingredient section detection model (NER-based). Scan OCR uses this
# by default; regex section helper is optional (tests/scripts only).
HF_INGREDIENT_DETECTION_MODEL = os.getenv(
    "HF_INGREDIENT_DETECTION_MODEL", "openfoodfacts/ingredient-detection"
)

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

# Provider to use (groq, gemini, openai, anthropic, ollama, lmstudio)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Task-specific model overrides (leave empty to use provider's default model)
# These allow using different models for extraction vs analysis
LLM_EXTRACTOR_MODEL = os.getenv("LLM_EXTRACTOR_MODEL", "")  # Model for ingredient extraction
LLM_ANALYZE_MODEL = os.getenv("LLM_ANALYZE_MODEL", "")  # Model for dietary analysis

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
# Startup Status
# =============================================================================

_provider = LLM_PROVIDER.lower()
if _provider == "groq":
    print(f"✅ Groq LLM configured (Model: {GROQ_MODEL})" if GROQ_API_KEY else "⚠️  GROQ_API_KEY not set")
elif _provider == "gemini":
    print(f"✅ Gemini LLM configured (Model: {GEMINI_MODEL})" if GEMINI_API_KEY else "⚠️  GEMINI_API_KEY not set")
elif _provider == "openai":
    print(f"✅ OpenAI LLM configured (Model: {OPENAI_MODEL})" if OPENAI_API_KEY else "⚠️  OPENAI_API_KEY not set")
elif _provider == "anthropic":
    print(f"✅ Anthropic LLM configured (Model: {ANTHROPIC_MODEL})" if ANTHROPIC_API_KEY else "⚠️  ANTHROPIC_API_KEY not set")
elif _provider == "ollama":
    print(f"✅ Ollama LLM configured (Model: {OLLAMA_MODEL})")
elif _provider == "lmstudio":
    print(f"✅ LM Studio configured (Model: {LMSTUDIO_MODEL} @ localhost:1234)")
else:
    print(f"⚠️  Unknown LLM provider: {LLM_PROVIDER}")