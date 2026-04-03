"""
Unified LLM Service
A generic interface for calling LLM providers with any prompt/task.

Supports multiple providers:
- Groq (FREE)
- Google Gemini (FREE)
- OpenAI (Paid)
- Anthropic (Paid)
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
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Make the actual API call. Returns raw response text."""
        pass
    
    def call(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        parse_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Call the LLM with a prompt.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context
            parse_json: If True, parse response as JSON
            
        Returns:
            Parsed JSON dict if parse_json=True, else raw response wrapped in dict
        """
        if not self.is_available():
            logger.debug(f"{self.name}: NOT AVAILABLE")
            return None
        
        try:
            response = self._call_api(prompt, system_prompt)
            
            if not response:
                logger.debug(f"{self.name}: Empty response from API")
                return None
            
            if parse_json:
                return self._parse_json_response(response)
            else:
                return {"response": response}
            
        except Exception as e:
            logger.error(f"{self.name} ERROR: {type(e).__name__}: {e}")
            return None
    
    def _parse_json_response(self, result_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response with robust handling of various formats.
        
        Handles:
        - Clean JSON responses
        - Markdown code blocks (```json ... ``` or ``` ... ```)
        - Multiple JSON objects (extracts first valid one)
        - Leading/trailing text around JSON
        - Nested objects and arrays
        """
        if not result_text:
            return None
        
        original_text = result_text
        
        try:
            # Strategy 1: Try direct parsing first (cleanest case)
            return json.loads(result_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        result_text = self._extract_from_code_blocks(original_text)
        if result_text != original_text:
            try:
                return json.loads(result_text.strip())
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find first complete JSON object using bracket matching
        extracted = self._extract_first_json_object(original_text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Try to find JSON array
        extracted = self._extract_first_json_array(original_text)
        if extracted:
            try:
                # Wrap array in object for consistent return type
                parsed = json.loads(extracted)
                if isinstance(parsed, list):
                    return {"items": parsed}
                return parsed
            except json.JSONDecodeError:
                pass
        
        # Strategy 5: Aggressive cleanup - remove common LLM additions
        cleaned = self._aggressive_cleanup(original_text)
        if cleaned:
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response after all strategies: {e}")
                logger.debug(f"Original response (first 500 chars): {original_text[:500]}")
        
        return None
    
    def _extract_from_code_blocks(self, text: str) -> str:
        """Extract content from markdown code blocks."""
        import re
        
        # Try ```json ... ``` first
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if json_block_match:
            return json_block_match.group(1).strip()
        
        # Try generic ``` ... ```
        generic_block_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if generic_block_match:
            return generic_block_match.group(1).strip()
        
        return text
    
    def _extract_first_json_object(self, text: str) -> Optional[str]:
        """
        Extract the first complete JSON object using bracket matching.
        This handles nested objects correctly.
        """
        # Find the first '{'
        start = text.find('{')
        if start == -1:
            return None
        
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        
        return None
    
    def _extract_first_json_array(self, text: str) -> Optional[str]:
        """
        Extract the first complete JSON array using bracket matching.
        """
        # Find the first '['
        start = text.find('[')
        if start == -1:
            return None
        
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        
        return None
    
    def _aggressive_cleanup(self, text: str) -> Optional[str]:
        """
        Aggressively clean up text to extract JSON.
        Last resort when other methods fail.
        """
        import re
        
        # Remove common LLM prefixes
        prefixes_to_remove = [
            r'^[Hh]ere\s+(is|are)\s+(the\s+)?(JSON|result|response|answer)[:\s]*',
            r'^[Ss]ure[,!]?\s*(here\s+(is|are)\s+(the\s+)?)?',
            r'^[Oo]kay[,!]?\s*',
            r'^[Cc]ertainly[,!]?\s*',
            r'^[Ii]\'ll\s+.*?:\s*',
            r'^\s*[Rr]esponse:\s*',
            r'^\s*[Oo]utput:\s*',
            r'^\s*[Jj][Ss][Oo][Nn]:\s*',
        ]
        
        cleaned = text.strip()
        for pattern in prefixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        # Remove trailing explanatory text after JSON
        # Find where JSON likely ends (after last } or ])
        last_brace = max(cleaned.rfind('}'), cleaned.rfind(']'))
        if last_brace != -1:
            cleaned = cleaned[:last_brace + 1]
        
        # Try to find JSON object/array in cleaned text
        obj = self._extract_first_json_object(cleaned)
        if obj:
            return obj
        
        arr = self._extract_first_json_array(cleaned)
        if arr:
            return arr
        
        return cleaned.strip() if cleaned.strip() else None


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
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
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
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        model = self._get_model()
        if not model:
            return None
        
        # Gemini doesn't have system prompt in the same way, prepend it
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = model.generate_content(
            full_prompt,
            generation_config={
                "temperature": self.temperature,
                "response_mime_type": "application/json"
            }
        )
        return response.text


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider (Paid)."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        self.api_key = api_key
        self._client = None
    
    @property
    def name(self) -> str:
        return "OpenAI"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("OpenAI library not installed. Run: pip install openai")
                return None
        return self._client
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
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
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "You are a helpful assistant. Always respond with valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        return response.content[0].text


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
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        import requests
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")


class LocalLLMProvider(BaseLLMProvider):
    """Local OpenAI-compatible chat API (e.g. LM Studio, llama.cpp server on :1234)."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",
        temperature: float = 0.1,
        use_json_mode: bool = False,
    ):
        super().__init__(model, temperature)
        self.base_url = base_url.rstrip("/")
        self.use_json_mode = use_json_mode
        self._client = None

    @property
    def name(self) -> str:
        return "local_llm"

    def is_available(self) -> bool:
        """Check if the local OpenAI-compatible server is reachable."""
        try:
            import requests
            url = f"{self.base_url}/models"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key="local",
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning("OpenAI library not installed. Run: pip install openai")
                return None
        return self._client
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Make API call - no system role for Mistral compatibility."""
        client = self._get_client()
        if not client:
            return None
        
        # Mistral only supports user/assistant roles - no system role!
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=self.temperature
        )
        return response.choices[0].message.content


# =============================================================================
# Provider Factory
# =============================================================================

class LLMProviderFactory:
    """Factory for creating LLM providers from settings."""
    
    PROVIDER_CLASSES = {
        "groq": GroqProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "local_llm": LocalLLMProvider,
    }
    
    @classmethod
    def get_provider_names(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls.PROVIDER_CLASSES.keys())
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        settings,
        model_override: Optional[str] = None
    ) -> Optional[BaseLLMProvider]:
        """
        Create a single provider instance.
        
        Args:
            provider_name: Name of the provider (groq, gemini, openai, etc.)
            settings: Application settings module
            model_override: Optional model name to override the default
            
        Returns:
            Provider instance or None if not available
        """
        provider_name = provider_name.lower()
        if provider_name == "lmstudio":
            provider_name = "local_llm"

        if provider_name == "groq":
            return GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model=model_override or settings.GROQ_MODEL,
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider_name == "gemini":
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=model_override or settings.GEMINI_MODEL,
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider_name == "openai":
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=model_override or settings.OPENAI_MODEL,
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                model=model_override or settings.ANTHROPIC_MODEL,
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider_name == "ollama":
            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=model_override or settings.OLLAMA_MODEL,
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider_name == "local_llm":
            return LocalLLMProvider(
                base_url=settings.LOCAL_LLM_BASE_URL,
                model=model_override or settings.LOCAL_LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                use_json_mode=settings.LOCAL_LLM_JSON_MODE,
            )
        else:
            logger.warning(f"Unknown provider: {provider_name}")
            return None


# =============================================================================
# Unified LLM Service
# =============================================================================

class LLMService:
    """
    Unified service for calling LLM with any prompt.
    Handles provider selection and fallback logic.
    """
    
    def __init__(self, providers: Optional[List[BaseLLMProvider]] = None):
        """
        Initialize the service.
        
        Args:
            providers: List of LLM providers to use (in order of preference).
        """
        self._providers = providers or []
    
    @classmethod
    def from_settings(
        cls,
        settings,
        model_override: Optional[str] = None
    ) -> "LLMService":
        """
        Create service with provider configured from settings.
        
        Args:
            settings: Application settings module
            model_override: Optional model name to override the default
        """
        provider = LLMProviderFactory.create_provider(
            settings.LLM_PROVIDER,
            settings,
            model_override
        )
        providers = [provider] if provider else []
        return cls(providers=providers)
    
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        parse_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM with the given prompt using available providers.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context
            parse_json: If True, parse response as JSON
            
        Returns:
            Response dict with '_provider' key added, or None if all providers fail
        """
        if not self._providers:
            logger.warning("No LLM providers configured")
            return None
        
        for provider in self._providers:
            logger.debug(f"Trying LLM provider: {provider.name}")
            
            result = provider.call(prompt, system_prompt, parse_json)
            
            if result is not None:
                logger.info(f"Successfully called {provider.name}")
                result["_provider"] = provider.name
                return result
        
        logger.warning("All LLM providers failed or unavailable")
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return any(p.is_available() for p in self._providers)
