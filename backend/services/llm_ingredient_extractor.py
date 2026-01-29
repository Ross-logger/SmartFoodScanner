"""
LLM-based Ingredient Extractor
Uses LLM to accurately extract and translate ingredients to English.

Supports multiple providers via a unified interface:
- Groq (FREE)
- Google Gemini (FREE)
- OpenAI (Paid)
- Ollama (FREE - Local)
- LM Studio (FREE - Local, OpenAI-compatible)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Base LLM Provider Interface
# =============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    SYSTEM_PROMPT = (
        "You are an expert food ingredient extractor. "
        "Extract ingredients accurately and translate them to English. "
        "Always respond with valid JSON only."
    )
    
    def __init__(self, model: str, temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    @abstractmethod
    def _call_api(self, prompt: str) -> Optional[str]:
        """Make the actual API call. Returns raw response text."""
        pass
    
    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract ingredients from text.
        """
        if not self.is_available():
            print(f"{self.name}: NOT AVAILABLE")
            return None
        
        try:
            prompt = self._build_extraction_prompt(text)
            response = self._call_api(prompt)
            
            if not response:
                print(f"{self.name}: Empty response from API")
                return None
            
            result = self._parse_response(response)
            if result:
                print(f"{self.name}: Extracted {len(result['ingredients'])} ingredients")
            else:
                print(f"{self.name}: Failed to parse response")
            return result
            
        except Exception as e:
            print(f"{self.name} ERROR: {type(e).__name__}: {e}")
            return None
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build the prompt for ingredient extraction."""
        return f"""You are an expert food ingredient extractor. Your task is to extract ALL ingredients from the given text, which may be from a food product label.

CRITICAL INSTRUCTIONS:
1. Extract ONLY the actual food ingredients - not packaging info, brand names, nutritional values, or marketing text
2. Translate ALL ingredients to English if they are in another language
3. Preserve scientific names in parentheses when present (e.g., "Vitamin C (Ascorbic Acid)")
4. Split compound ingredients appropriately (e.g., "vegetable oils (palm, sunflower)" becomes separate entries)
5. Include E-numbers with their names when identifiable (e.g., "E471" becomes "E471 (Mono- and Diglycerides)")
6. Normalize ingredient names to their common English form
7. Remove percentages, quantities, and "contains X%" type annotations - just extract the ingredient name
8. If no ingredients are found or the text doesn't contain ingredient information, return an empty array

INPUT TEXT:
{text}

Respond ONLY with valid JSON in this exact format:
{{
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
    "detected_language": "detected source language or 'english' if already in English",
    "confidence": "high/medium/low"
}}

EXAMPLES:
- Input: "Zutaten: Wasser, Zucker, Weizenmehl"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour"], "detected_language": "german", "confidence": "high"}}

- Input: "مكونات: ماء، سكر، دقيق القمح"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour"], "detected_language": "arabic", "confidence": "high"}}

- Input: "Ingredients: Water, Sugar (15%), Wheat Flour, Emulsifier (E471), Natural Flavoring"
  Output: {{"ingredients": ["Water", "Sugar", "Wheat Flour", "E471 (Mono- and Diglycerides)", "Natural Flavoring"], "detected_language": "english", "confidence": "high"}}"""

    def _parse_response(self, result_text: str) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM response for ingredient extraction."""
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Validate response structure
            if "ingredients" not in result:
                logger.warning("LLM response missing 'ingredients' field")
                return None
            
            # Ensure ingredients is a list
            if not isinstance(result["ingredients"], list):
                result["ingredients"] = []
            
            # Clean and validate ingredients
            cleaned_ingredients = []
            for ing in result["ingredients"]:
                if isinstance(ing, str):
                    cleaned = ing.strip()
                    if cleaned and len(cleaned) > 1:  # Filter out single characters
                        cleaned_ingredients.append(cleaned)
            
            result["ingredients"] = cleaned_ingredients
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None


# =============================================================================
# OpenAI-Compatible Base Provider (for OpenAI, LM Studio, etc.)
# =============================================================================

class OpenAICompatibleProvider(BaseLLMProvider):
    """Base class for OpenAI-compatible API providers."""
    
    def __init__(
        self, 
        model: str, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        use_json_mode: bool = True
    ):
        super().__init__(model, temperature)
        self.api_key = api_key
        self.base_url = base_url
        self.use_json_mode = use_json_mode
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                kwargs = {}
                if self.api_key:
                    kwargs["api_key"] = self.api_key
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                logger.warning("OpenAI library not installed. Run: pip install openai")
                return None
        return self._client
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """Make API call using OpenAI client."""
        client = self._get_client()
        if not client:
            return None
        
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
        }
        
        if self.use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


# =============================================================================
# Concrete Provider Implementations
# =============================================================================

class GroqProvider(BaseLLMProvider):
    """Groq LLM provider (FREE tier available)."""
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.1):
        super().__init__(model, temperature)
        self.api_key = api_key
        self._client = None
    
    @property
    def name(self) -> str:
        return "Groq"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _get_client(self):
        """Lazy initialization of Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq library not installed. Run: pip install groq")
                return None
        return self._client
    
    def _call_api(self, prompt: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider (FREE tier available)."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp", temperature: float = 0.1):
        super().__init__(model, temperature)
        self.api_key = api_key
        self._model_instance = None
    
    @property
    def name(self) -> str:
        return "Gemini"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _get_model(self):
        """Lazy initialization of Gemini model."""
        if self._model_instance is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._model_instance = genai.GenerativeModel(self.model)
            except ImportError:
                logger.warning("Google Generative AI library not installed. Run: pip install google-generativeai")
                return None
        return self._model_instance
    
    def _call_api(self, prompt: str) -> Optional[str]:
        model = self._get_model()
        if not model:
            return None
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "response_mime_type": "application/json"
            }
        )
        return response.text


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI LLM provider (Paid)."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, api_key=api_key, temperature=temperature, use_json_mode=True)
    
    @property
    def name(self) -> str:
        return "OpenAI"
    
    def is_available(self) -> bool:
        return bool(self.api_key)


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider (FREE)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", temperature: float = 0.1):
        super().__init__(model, temperature)
        self.base_url = base_url.rstrip("/")
    
    @property
    def name(self) -> str:
        return "Ollama"
    
    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def _call_api(self, prompt: str) -> Optional[str]:
        import requests
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{self.SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": self.temperature
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")


class LMStudioProvider(BaseLLMProvider):
    """LM Studio local LLM provider (FREE, OpenAI-compatible API)."""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:1234/v1", 
        model: str = "local-model",
        temperature: float = 0.1,
        use_json_mode: bool = False
    ):
        super().__init__(model, temperature)
        self.base_url = base_url.rstrip("/")
        self.use_json_mode = use_json_mode
        self._client = None
    
    @property
    def name(self) -> str:
        return "LMStudio"
    
    def is_available(self) -> bool:
        """Check if LM Studio server is reachable."""
        try:
            import requests
            url = f"{self.base_url}/models"
            print(f"LMStudio: Checking availability at {url}")
            response = requests.get(url, timeout=2)
            available = response.status_code == 200
            print(f"LMStudio: Available = {available} (status={response.status_code})")
            return available
        except Exception as e:
            print(f"LMStudio: Not available - {e}")
            return False
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key="lm-studio",
                    base_url=self.base_url
                )
            except ImportError:
                print("LMStudio: OpenAI library not installed!")
                return None
        return self._client
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """Make API call - no system role for Mistral compatibility."""
        client = self._get_client()
        if not client:
            print("LMStudio: Failed to get client")
            return None
        
        # Mistral only supports user/assistant roles - no system role!
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        
        print(f"LMStudio: Calling model={self.model} at {self.base_url}")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=self.temperature
        )
        
        print("LMStudio: Got response successfully")
        return response.choices[0].message.content


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider (Paid)."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.1):
        super().__init__(model, temperature)
        self.api_key = api_key
        self._client = None
    
    @property
    def name(self) -> str:
        return "Anthropic"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("Anthropic library not installed. Run: pip install anthropic")
                return None
        return self._client
    
    def _call_api(self, prompt: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        return response.content[0].text


# =============================================================================
# Provider Factory / Registry
# =============================================================================

class LLMProviderFactory:
    """Factory for creating and managing LLM providers."""
    
    _providers: Dict[str, type] = {
        "groq": GroqProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a custom provider class."""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get_provider_names(cls) -> List[str]:
        """Get list of registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def create_from_settings(cls, settings) -> List[BaseLLMProvider]:
        """
        Create provider from application settings.
        Only returns the configured provider.
        """
        provider = settings.LLM_PROVIDER.lower()
        
        providers = {
            "groq": lambda: GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                temperature=settings.LLM_TEMPERATURE
            ),
            "gemini": lambda: GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                temperature=settings.LLM_TEMPERATURE
            ),
            "openai": lambda: OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                temperature=settings.LLM_TEMPERATURE
            ),
            "ollama": lambda: OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=settings.LLM_TEMPERATURE
            ),
            "lmstudio": lambda: LMStudioProvider(
                base_url=settings.LMSTUDIO_BASE_URL,
                model=settings.LMSTUDIO_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                use_json_mode=settings.LMSTUDIO_JSON_MODE
            ),
            "anthropic": lambda: AnthropicProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL,
                temperature=settings.LLM_TEMPERATURE
            ),
        }
        print("Using Provider: ", provider)
        
        if provider not in providers:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        return [providers[provider]()]


# =============================================================================
# Main Extraction Interface
# =============================================================================

class LLMIngredientExtractor:
    """
    High-level interface for extracting ingredients using LLM.
    Handles provider selection and fallback logic.
    """
    
    def __init__(self, providers: Optional[List[BaseLLMProvider]] = None):
        """
        Initialize the extractor.
        
        Args:
            providers: List of LLM providers to use (in order of preference).
                      If None, will be created from settings when extract() is called.
        """
        self._providers = providers
        self._settings_providers = None
    
    @classmethod
    def from_settings(cls, settings) -> "LLMIngredientExtractor":
        """Create extractor with providers configured from settings."""
        providers = LLMProviderFactory.create_from_settings(settings)
        return cls(providers=providers)
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract ingredients from text using available LLM providers.
        
        Args:
            text: Raw text (possibly from OCR) containing ingredient information
            
        Returns:
            Dictionary with:
            - ingredients: List of extracted ingredient names in English
            - success: Boolean indicating if extraction was successful
            - message: Optional message about the extraction
            - provider: Name of the provider that succeeded (if any)
        """
        if not text or not text.strip():
            return {
                "ingredients": [],
                "success": False,
                "message": "No text provided for extraction"
            }
        
        providers = self._providers or []
        print("Providers: ", providers)
        
        if not providers:
            return {
                "ingredients": [],
                "success": False,
                "message": "No LLM providers configured"
            }
        
        for provider in providers:
            print(f"Trying LLM provider for extraction: {provider.name}")
            print(f"Text to extract ingredients from: {text}")
            
            result = provider.extract(text)
            print(f"Extracted ingredients by {provider.name}: {result}")
            
            if result:
                logger.info(f"Successfully extracted ingredients with {provider.name}")
                return {
                    "ingredients": result.get("ingredients", []),
                    "success": True,
                    "message": f"Extracted {len(result['ingredients'])} ingredients using {provider.name}",
                    "provider": provider.name,
                    "detected_language": result.get("detected_language", "unknown"),
                    "confidence": result.get("confidence", "unknown")
                }
        
        return {
            "ingredients": [],
            "success": False,
            "message": "Failed to extract ingredients."
        }


# =============================================================================
# Backward-Compatible Function Interface
# =============================================================================

def extract_ingredients_with_llm(text: str) -> Dict[str, Any]:
    """
    Extract ingredients from text using LLM.
    """
    from backend import settings
    
    if not settings.USE_LLM_ANALYZER:
        return {
            "ingredients": [],
            "success": False,
            "message": "LLM analyzer is disabled in settings"
        }
    
    logger.info(f"Using LLM provider: {settings.LLM_PROVIDER}")
    extractor = LLMIngredientExtractor.from_settings(settings)
    return extractor.extract(text)
