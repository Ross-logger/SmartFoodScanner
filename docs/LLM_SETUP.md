# LLM Provider Setup Guide

This document explains how to configure different LLM providers for dietary analysis, including **free options**.

## 🆓 Free LLM Providers (Recommended)

### 1. **Groq** (⭐ Recommended - Best Free Option)

**Why Groq?**
- ✅ **FREE** with generous limits (1,000-14,000 requests/day)
- ✅ Very fast inference
- ✅ High-quality models (Llama 3, Mixtral)
- ✅ Easy setup

**Setup Steps:**
1. Sign up at [https://console.groq.com](https://console.groq.com)
2. Get your free API key
3. Add to `.env`:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=your-groq-api-key-here
   GROQ_MODEL=llama-3.1-70b-versatile
   ```
4. Install package: `pip install groq`

**Available Models:**
- `llama-3.1-70b-versatile` (recommended)
- `mixtral-8x7b-32768`
- `gemma2-9b-it`

---

### 2. **Google Gemini** (⭐ Also Great)

**Why Gemini?**
- ✅ **FREE** with good limits
- ✅ Excellent for long context
- ✅ High-quality responses
- ✅ Google-backed reliability

**Setup Steps:**
1. Sign up at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create an API key
3. Add to `.env`:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your-gemini-api-key-here
   GEMINI_MODEL=gemini-2.0-flash-exp
   ```
4. Install package: `pip install google-generativeai`

**Available Models:**
- `gemini-2.0-flash-exp` (recommended - latest)
- `gemini-1.5-flash`
- `gemini-1.5-pro`

---

### 3. **Ollama** (100% Free - Local)

**Why Ollama?**
- ✅ **Completely FREE** (runs locally)
- ✅ No API limits
- ✅ Privacy-friendly (data stays local)
- ✅ No internet required after setup

**Setup Steps:**
1. Install Ollama: [https://ollama.ai](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull llama3
   # or
   ollama pull mistral
   # or
   ollama pull gemma2
   ```
3. Start Ollama server (usually runs automatically)
4. Add to `.env`:
   ```
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   ```
5. No additional package needed (uses `requests` which is already installed)

**Available Models:**
- `llama3` (recommended)
- `mistral`
- `gemma2`
- `llama3.2`

---

## 💰 Paid Option

### 4. **OpenAI** (Paid but High Quality)

**Setup Steps:**
1. Get API key from [https://platform.openai.com](https://platform.openai.com)
2. Add to `.env`:
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key-here
   OPENAI_MODEL=gpt-4o-mini
   ```
3. Install package: `pip install openai`

---

## Configuration

### Environment Variables (.env)

```bash
# Enable/disable LLM analysis
USE_LLM_ANALYZER=true

# Choose provider: "groq", "gemini", "ollama", or "openai"
LLM_PROVIDER=groq

# Temperature (0.0-1.0, lower = more consistent)
LLM_TEMPERATURE=0.3

# Groq (FREE)
GROQ_API_KEY=your-key-here
GROQ_MODEL=llama-3.1-70b-versatile

# Gemini (FREE)
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash-exp

# Ollama (FREE - Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# OpenAI (Paid)
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Provider Priority

The system will automatically try providers in this order:
1. Your selected `LLM_PROVIDER`
2. Other free providers as fallback
3. Rule-based analysis if all LLM providers fail

---

## Installation

Install all required packages:

```bash
pip install groq google-generativeai openai
```

Or install individually based on your chosen provider:
- Groq: `pip install groq`
- Gemini: `pip install google-generativeai`
- OpenAI: `pip install openai`
- Ollama: No installation needed (uses `requests`)

---

## Comparison Table

| Provider | Cost | Speed | Quality | Limits | Setup Difficulty |
|----------|------|-------|---------|--------|------------------|
| **Groq** | 🆓 Free | ⚡⚡⚡ Very Fast | ⭐⭐⭐⭐ Excellent | 1K-14K/day | ⭐ Easy |
| **Gemini** | 🆓 Free | ⚡⚡ Fast | ⭐⭐⭐⭐⭐ Excellent | Generous | ⭐ Easy |
| **Ollama** | 🆓 Free | ⚡⚡⚡ Fast (local) | ⭐⭐⭐ Good | Unlimited | ⭐⭐ Medium |
| **OpenAI** | 💰 Paid | ⚡⚡ Fast | ⭐⭐⭐⭐⭐ Excellent | Based on plan | ⭐ Easy |

---

## Recommendations

1. **For Production (Free)**: Use **Groq** - best balance of speed, quality, and free limits
2. **For Development**: Use **Gemini** - easy setup, good free tier
3. **For Privacy**: Use **Ollama** - runs locally, no data leaves your machine
4. **For Best Quality**: Use **OpenAI** - highest quality but costs money

---

## Troubleshooting

### Groq Issues
- Check API key is correct
- Verify model name is valid
- Check rate limits at console.groq.com

### Gemini Issues
- Ensure API key is enabled in Google AI Studio
- Check model name matches available models
- Verify API quotas

### Ollama Issues
- Ensure Ollama server is running: `ollama serve`
- Verify model is downloaded: `ollama list`
- Check port 11434 is accessible

### General Issues
- Check logs for specific error messages
- System automatically falls back to rule-based analysis
- Verify all required packages are installed

---

## Testing

After setup, test your configuration:

```python
from app.services.analysis import analyze_ingredients
from app.models import DietaryProfile

# Test with sample ingredients
ingredients = ["wheat flour", "milk", "sugar"]
profile = DietaryProfile(gluten_free=True, dairy_free=True)

result = analyze_ingredients(ingredients, profile)
print(result)
```

The system will automatically use your configured LLM provider!

