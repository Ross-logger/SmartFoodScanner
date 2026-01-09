from typing import List, Optional
import json
import logging
from app.models import DietaryProfile
from app.config import settings

logger = logging.getLogger(__name__)


def _build_dietary_prompt(ingredients: List[str], dietary_profile: DietaryProfile) -> str:
    """Build the prompt for dietary analysis."""
    restrictions = []
    if dietary_profile.gluten_free:
        restrictions.append("gluten-free")
    if dietary_profile.dairy_free:
        restrictions.append("dairy-free")
    if dietary_profile.nut_free:
        restrictions.append("nut-free")
    if dietary_profile.halal:
        restrictions.append("halal")
    if dietary_profile.vegetarian:
        restrictions.append("vegetarian")
    if dietary_profile.vegan:
        restrictions.append("vegan")
    if dietary_profile.allergens:
        restrictions.append(f"allergic to: {', '.join(dietary_profile.allergens)}")
    if dietary_profile.custom_restrictions:
        restrictions.append(f"custom restrictions: {', '.join(dietary_profile.custom_restrictions)}")
    
    restrictions_text = ", ".join(restrictions) if restrictions else "no specific dietary restrictions"
    
    return f"""You are a dietary analysis expert. Analyze the following ingredients list against the user's dietary restrictions and provide a detailed assessment.

User's Dietary Restrictions: {restrictions_text}

Ingredients List:
{json.dumps(ingredients, indent=2)}

Please analyze these ingredients and provide:
1. Whether the product is SAFE (is_safe: true/false) for the user's dietary restrictions
2. Any specific warnings (warnings: array of warning messages) about ingredients that violate restrictions
3. A clear, user-friendly analysis result (analysis_result: string) explaining the safety assessment

Consider:
- Hidden ingredients and derivatives (e.g., whey contains dairy, lecithin may contain eggs)
- Cross-contamination risks
- Ambiguous ingredient names
- Common allergens and their variations

Respond ONLY with valid JSON in this exact format:
{{
    "is_safe": true/false,
    "warnings": ["warning1", "warning2"],
    "analysis_result": "Detailed explanation here"
}}"""


def _parse_llm_response(result_text: str) -> Optional[dict]:
    """Parse and validate LLM response."""
    try:
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        # Validate response structure
        if not all(key in result for key in ["is_safe", "warnings", "analysis_result"]):
            logger.warning("LLM response missing required fields")
            return None
        
        # Ensure warnings is a list
        if not isinstance(result["warnings"], list):
            result["warnings"] = []
        
        # Ensure is_safe is boolean
        result["is_safe"] = bool(result["is_safe"])
        
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None


def _analyze_with_groq(ingredients: List[str], dietary_profile: DietaryProfile) -> Optional[dict]:
    """Analyze using Groq API (FREE - Recommended)."""
    if not settings.GROQ_API_KEY:
        return None
    
    try:
        from groq import Groq
        
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = _build_dietary_prompt(ingredients, dietary_profile)
        
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a dietary analysis expert. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.LLM_TEMPERATURE,
            response_format={"type": "json_object"}
        )
        
        result = _parse_llm_response(response.choices[0].message.content)
        if result:
            logger.info(f"Groq analysis completed: is_safe={result['is_safe']}, warnings={len(result['warnings'])}")
        return result
        
    except ImportError:
        logger.warning("Groq library not installed. Install with: pip install groq")
        return None
    except Exception as e:
        logger.error(f"Groq analysis failed: {e}", exc_info=True)
        return None


def _analyze_with_gemini(ingredients: List[str], dietary_profile: DietaryProfile) -> Optional[dict]:
    """Analyze using Google Gemini API (FREE)."""
    if not settings.GEMINI_API_KEY:
        return None
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        prompt = _build_dietary_prompt(ingredients, dietary_profile)
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": settings.LLM_TEMPERATURE,
                "response_mime_type": "application/json"
            }
        )
        
        result = _parse_llm_response(response.text)
        if result:
            logger.info(f"Gemini analysis completed: is_safe={result['is_safe']}, warnings={len(result['warnings'])}")
        return result
        
    except ImportError:
        logger.warning("Google Generative AI library not installed. Install with: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}", exc_info=True)
        return None


def _analyze_with_openai(ingredients: List[str], dietary_profile: DietaryProfile) -> Optional[dict]:
    """Analyze using OpenAI API (Paid)."""
    if not settings.OPENAI_API_KEY:
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = _build_dietary_prompt(ingredients, dietary_profile)
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a dietary analysis expert. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.LLM_TEMPERATURE,
            response_format={"type": "json_object"}
        )
        
        result = _parse_llm_response(response.choices[0].message.content)
        if result:
            logger.info(f"OpenAI analysis completed: is_safe={result['is_safe']}, warnings={len(result['warnings'])}")
        return result
        
    except ImportError:
        logger.warning("OpenAI library not installed. Install with: pip install openai")
        return None
    except Exception as e:
        logger.error(f"OpenAI analysis failed: {e}", exc_info=True)
        return None


def _analyze_with_ollama(ingredients: List[str], dietary_profile: DietaryProfile) -> Optional[dict]:
    """Analyze using Ollama (FREE - Local)."""
    try:
        import requests
        
        prompt = _build_dietary_prompt(ingredients, dietary_profile)
        
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": f"You are a dietary analysis expert. Always respond with valid JSON only, no additional text.\n\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": settings.LLM_TEMPERATURE
                }
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = _parse_llm_response(response.json().get("response", ""))
        if result:
            logger.info(f"Ollama analysis completed: is_safe={result['is_safe']}, warnings={len(result['warnings'])}")
        return result
        
    except ImportError:
        logger.warning("Requests library not installed. Install with: pip install requests")
        return None
    except Exception as e:
        logger.error(f"Ollama analysis failed: {e}", exc_info=True)
        return None


def _analyze_with_llm(
    ingredients: List[str],
    dietary_profile: DietaryProfile
) -> Optional[dict]:
    """
    Analyze ingredients using LLM.
    Supports multiple providers: Groq (FREE), Gemini (FREE), OpenAI (Paid), Ollama (FREE Local).
    Returns None if LLM is not available or fails.
    """
    if not settings.USE_LLM_ANALYZER:
        return None
    
    provider = settings.LLM_PROVIDER.lower()
    
    # Try providers in order of preference
    providers_to_try = []
    
    if provider == "groq":
        providers_to_try = ["groq", "gemini", "openai", "ollama"]
    elif provider == "gemini":
        providers_to_try = ["gemini", "groq", "openai", "ollama"]
    elif provider == "openai":
        providers_to_try = ["openai", "groq", "gemini", "ollama"]
    elif provider == "ollama":
        providers_to_try = ["ollama", "groq", "gemini", "openai"]
    else:
        # Default: try all free options first
        providers_to_try = ["groq", "gemini", "ollama", "openai"]
    
    for provider_name in providers_to_try:
        logger.debug(f"Trying LLM provider: {provider_name}")
        
        if provider_name == "groq":
            result = _analyze_with_groq(ingredients, dietary_profile)
        elif provider_name == "gemini":
            result = _analyze_with_gemini(ingredients, dietary_profile)
        elif provider_name == "openai":
            result = _analyze_with_openai(ingredients, dietary_profile)
        elif provider_name == "ollama":
            result = _analyze_with_ollama(ingredients, dietary_profile)
        else:
            continue
        
        if result:
            logger.info(f"Successfully analyzed with {provider_name}")
            return result
    
    logger.warning("All LLM providers failed or unavailable")
    return None


def _analyze_with_rules(
    ingredients: List[str],
    dietary_profile: DietaryProfile
) -> dict:
    """
    Rule-based analysis (fallback method).
    """
    warnings = []
    is_safe = True  # Start with safe, mark unsafe if violations found
    
    # Common allergens and restricted ingredients
    allergens = {
        'gluten': ['wheat', 'barley', 'rye', 'oats', 'gluten'],
        'dairy': ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'lactose', 'whey'],
        'nuts': ['peanut', 'almond', 'walnut', 'cashew', 'hazelnut', 'pecan', 'pistachio'],
        'eggs': ['egg', 'albumin', 'lecithin'],
        'soy': ['soy', 'soya', 'tofu'],
        'halal_restricted': ['pork', 'gelatin', 'lard', 'bacon'],
        'vegetarian_restricted': ['meat', 'chicken', 'beef', 'pork', 'fish', 'gelatin'],
        'vegan_restricted': ['milk', 'cheese', 'butter', 'honey', 'egg', 'meat', 'chicken', 'beef', 'pork', 'fish']
    }
    
    ingredients_lower = [ing.lower() for ing in ingredients]
    
    # Check each restriction
    if dietary_profile.gluten_free:
        for item in allergens['gluten']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains gluten: {item}")
                is_safe = False
                break
    
    if dietary_profile.dairy_free:
        for item in allergens['dairy']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains dairy: {item}")
                is_safe = False
                break
    
    if dietary_profile.nut_free:
        for item in allergens['nuts']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Contains nuts: {item}")
                is_safe = False
                break
    
    if dietary_profile.halal:
        for item in allergens['halal_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not halal: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegetarian:
        for item in allergens['vegetarian_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegetarian: Contains {item}")
                is_safe = False
                break
    
    if dietary_profile.vegan:
        for item in allergens['vegan_restricted']:
            if any(item in ing for ing in ingredients_lower):
                warnings.append(f"Not vegan: Contains {item}")
                is_safe = False
                break
    
    # Check custom allergens
    if dietary_profile.allergens:
        for allergen in dietary_profile.allergens:
            if any(allergen.lower() in ing for ing in ingredients_lower):
                warnings.append(f"Contains your allergen: {allergen}")
                is_safe = False
    
    # Generate analysis result
    if is_safe:
        analysis_result = "This product is safe for your dietary preferences."
    else:
        if warnings:
            analysis_result = "This product is not suitable for your dietary preferences.\n" + "\n".join(warnings)
        else:
            analysis_result = "This product is not suitable for your dietary preferences."
    
    return {
        "is_safe": is_safe,
        "warnings": warnings,
        "analysis_result": analysis_result
    }


def analyze_ingredients(
    ingredients: List[str],
    dietary_profile: Optional[DietaryProfile]
) -> dict:
    """
    Analyze ingredients against dietary restrictions.
    Uses LLM-based analysis if available, falls back to rule-based analysis.
    """
    if not dietary_profile:
        return {
            "is_safe": False,
            "warnings": ["No dietary profile set"],
            "analysis_result": "Please set your dietary profile to get the analysis."
        }
    
    # Try LLM analysis first if enabled
    if settings.USE_LLM_ANALYZER:
        llm_result = _analyze_with_llm(ingredients, dietary_profile)
        if llm_result:
            return llm_result
        # Fall back to rule-based if LLM fails
        logger.info("Falling back to rule-based analysis")
    
    # Use rule-based analysis as fallback
    return _analyze_with_rules(ingredients, dietary_profile)

