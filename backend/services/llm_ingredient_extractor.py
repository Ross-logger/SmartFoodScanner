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
        
        Args:
            text: Raw text containing ingredient information
            
        Returns:
            Dictionary with ingredients, detected_language, confidence or None if failed
        """
        if not self.is_available():
            logger.debug(f"{self.name} provider is not available")
            return None
        
        try:
            prompt = self._build_extraction_prompt(text)
            response = self._call_api(prompt)
            
            if not response:
                return None
            
            result = self._parse_response(response)
            if result:
                logger.info(f"{self.name} extraction completed: {len(result['ingredients'])} ingredients found")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} extraction failed: {e}", exc_info=True)
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


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio local LLM provider (FREE, OpenAI-compatible API)."""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:1234/v1", 
        model: str = "local-model",
        temperature: float = 0.1,
        use_json_mode: bool = False  # LM Studio may not support JSON mode
    ):
        # LM Studio doesn't require an API key but OpenAI client needs a placeholder
        super().__init__(
            model, 
            api_key="lm-studio",  # Placeholder, LM Studio ignores this
            base_url=base_url,
            temperature=temperature,
            use_json_mode=use_json_mode
        )
    
    @property
    def name(self) -> str:
        return "LMStudio"
    
    def is_available(self) -> bool:
        """Check if LM Studio server is reachable."""
        try:
            import requests
            response = requests.get(f"{self.base_url.rstrip('/v1')}/v1/models", timeout=2)
            return response.status_code == 200
        except Exception:
            return False


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
        Create providers from application settings.
        Returns a list of providers in order of preference.
        """
        providers = []
        primary = settings.LLM_PROVIDER.lower() if hasattr(settings, 'LLM_PROVIDER') else "groq"
        
        # Build provider instances based on available configuration
        provider_configs = {
            "groq": lambda: GroqProvider(
                api_key=getattr(settings, 'GROQ_API_KEY', None),
                model=getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1)
            ),
            "gemini": lambda: GeminiProvider(
                api_key=getattr(settings, 'GEMINI_API_KEY', None),
                model=getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash-exp'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1)
            ),
            "openai": lambda: OpenAIProvider(
                api_key=getattr(settings, 'OPENAI_API_KEY', None),
                model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1)
            ),
            "ollama": lambda: OllamaProvider(
                base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                model=getattr(settings, 'OLLAMA_MODEL', 'llama3'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1)
            ),
            "lmstudio": lambda: LMStudioProvider(
                base_url=getattr(settings, 'LMSTUDIO_BASE_URL', 'http://localhost:1234/v1'),
                model=getattr(settings, 'LMSTUDIO_MODEL', 'local-model'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1),
                use_json_mode=getattr(settings, 'LMSTUDIO_JSON_MODE', False)
            ),
            "anthropic": lambda: AnthropicProvider(
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None),
                model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                temperature=getattr(settings, 'LLM_TEMPERATURE', 0.1)
            ),
        }
        
        # Order: primary provider first, then fallbacks
        fallback_order = ["groq", "gemini", "lmstudio", "ollama", "openai", "anthropic"]
        
        # Primary first
        if primary in provider_configs:
            providers.append(provider_configs[primary]())
        
        # Then fallbacks (excluding primary)
        for name in fallback_order:
            if name != primary and name in provider_configs:
                providers.append(provider_configs[name]())
        
        return providers


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
        
        if not providers:
            return {
                "ingredients": [],
                "success": False,
                "message": "No LLM providers configured"
            }
        
        for provider in providers:
            logger.debug(f"Trying LLM provider for extraction: {provider.name}")
            
            result = provider.extract(text)
            
            if result and result.get("ingredients"):
                logger.info(f"Successfully extracted ingredients with {provider.name}")
                return {
                    "ingredients": result["ingredients"],
                    "success": True,
                    "message": f"Extracted {len(result['ingredients'])} ingredients using {provider.name}",
                    "provider": provider.name,
                    "detected_language": result.get("detected_language", "unknown"),
                    "confidence": result.get("confidence", "unknown")
                }
        
        logger.warning("All LLM providers failed for ingredient extraction")
        return {
            "ingredients": [],
            "success": False,
            "message": "Failed to extract ingredients - all LLM providers unavailable or failed"
        }


# =============================================================================
# Backward-Compatible Function Interface
# =============================================================================

def extract_ingredients_with_llm(text: str) -> Dict[str, Any]:
    """
    Extract ingredients from text using LLM.
    Supports multiple providers: Groq (FREE), Gemini (FREE), OpenAI (Paid), 
    Ollama (FREE Local), LM Studio (FREE Local).
    
    This is a backward-compatible function that uses the class-based interface internally.
    
    Args:
        text: Raw text (possibly from OCR) containing ingredient information
        
    Returns:
        Dictionary with:
        - ingredients: List of extracted ingredient names in English
        - success: Boolean indicating if extraction was successful
        - message: Optional message about the extraction
    """
    from backend import settings
    
    if not settings.USE_LLM_ANALYZER:
        return {
            "ingredients": [],
            "success": False,
            "message": "LLM analyzer is disabled in settings"
        }
    
    extractor = LLMIngredientExtractor.from_settings(settings)
    return extractor.extract(text)
