# Smart Ingredients Scanner

A full-stack application that reads food labels from photos or barcodes and checks ingredients against your dietary profile.

## Description

Smart Ingredients Scanner helps people make safer food choices when shopping or at home. Many packaged foods list long, technical ingredient names that are hard to parse quickly, and common allergens or dietary conflicts are easy to miss. This project combines optical character recognition (OCR) on label images with barcode lookup against a public product database, then analyzes the ingredient list against each user’s restrictions and preferences. The main goals are to reduce the effort of reading labels, surface clear safety warnings, and keep a personal history of scans for later reference. Users benefit from a mobile-friendly web app, optional AI-assisted extraction and analysis when configured, and a rule-based fallback so the app still works when cloud models are unavailable.

## Features

- **Photo scan (OCR)** — Extracts text from ingredient-label images using EasyOCR, with preprocessing and SymSpell-based cleanup; optional LLM-based extraction when enabled in the user profile.
- **Barcode scan** — Looks up products via the **Open Food Facts** API and uses returned ingredient and allergen data.
- **Dietary profiles** — Supports common flags (e.g. halal, gluten-free, vegetarian, vegan, nut-free, dairy-free) plus custom allergens and restrictions.
- **Ingredient analysis** — Rule-based matching with **LLM-based analysis** when a provider is configured, automatically falling back if the model call fails.
- **Flexible LLM backends** — Groq, Google Gemini, OpenAI, Anthropic, Ollama, or a **local OpenAI-compatible** server (e.g. LM Studio, vLLM).
- **Accounts and history** — JWT-based authentication, refresh tokens, and stored scan history.
- **Vue PWA frontend** — Mobile-first progressive web app with camera/upload and barcode scanning (Vite + Tailwind).
- **Optional ML pipeline** — Train an ingredient **box classifier** and related evaluation from the `training/` directory (`make training`, `make evaluation`).

## Technologies Used

- **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic, PostgreSQL (local or Supabase)
- **Auth:** JWT (python-jose), bcrypt/passlib, HTTP-only cookies (configurable)
- **OCR & vision:** EasyOCR, OpenCV, Pillow; optional Mistral OCR API when LLM profile features are enabled
- **NLP / heuristics:** SymSpell, scikit-learn, RapidFuzz, Levenshtein
- **LLM clients:** OpenAI-compatible SDK patterns, `groq`, `google-generativeai`, provider abstraction in `backend/services/llm/`
- **Frontend:** Vue 3, Pinia, Vue Router, Axios, Vite, Tailwind CSS, vite-plugin-pwa, html5-qrcode
- **Deep learning stack (dependencies):** PyTorch, Torchvision (used by EasyOCR and training scripts)

## Getting Started

### Prerequisites

- **Python 3.10+** (3.11 recommended; the project uses a `.venv` virtual environment)
- **Node.js** and **npm** (for the frontend)
- **Database:** **SQLite** (simplest — no server), **PostgreSQL** locally, **or** a **Supabase** project
- **Git**
- **Optional:** API keys for the LLM or OCR features you enable (e.g. Groq, Gemini, OpenAI, Anthropic); **Mistral OCR** needs `MISTRAL_API_KEY` when that path is enabled (prefer your own key; shared keys can expire or exceed limits)
- **Optional:** **Ollama**, **LM Studio**, or **vLLM** for local / OpenAI-compatible inference (`local_llm` in settings)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Ross-logger/SmartFoodScanner.git
   cd SmartFoodScanner
   ```

2. **Create and activate a virtual environment** (project convention: `.venv`)

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your database URL or Supabase fields, `SECRET_KEY`, and any LLM API keys. Set `LLM_PROVIDER` (e.g. `groq`, `gemini`, `openai`, `anthropic`, `ollama`, `local_llm`) as needed.

   **Database — pick one:**

   - **SQLite (simplest for local demos)** — No database server to install. In `.env` set `IS_LOCAL_DATABASE=True` and point `LOCAL_DATABASE_URL` at a file in the project directory, for example:

     ```bash
     LOCAL_DATABASE_URL=sqlite:///./smartfoodscanner.db
     ```

     Then run `make migrate` as usual. The schema is created/updated by Alembic; the `.db` file appears next to your repo root (patterns like `*.db` are gitignored). This is ideal for coursework, quick onboarding, and laptops without PostgreSQL. **Caveats:** SQLite uses a single file and one writer at a time; it is fine for development and light use, but PostgreSQL (local or Supabase) is a better fit if you expect many concurrent users or deploy to production.

   - **Local PostgreSQL** — Install and start PostgreSQL yourself (the project does not start the server for you). Typical steps: install PostgreSQL for your OS, start the service, and create an empty database (e.g. named `smartfoodscanner`). Use a database user and password you configure in Postgres. Then in `.env` set `IS_LOCAL_DATABASE=True` and update **`LOCAL_DATABASE_URL`** so it matches that server. After copying from `.env.example`, this is the `LOCAL_DATABASE_URL=...` line (usually **line 5**). The default value is only an example:

     ```text
     postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
     ```

     Replace `USER`, `PASSWORD`, `HOST` (often `localhost`), `PORT` (often `5432`), and `DATABASE_NAME` with your real settings. Homebrew installs on macOS often use your macOS username and no password in the URL for local trust/peer setups; Docker or Linux packages often use `postgres` / `postgres`. If this line does not match a running PostgreSQL instance, `make migrate` and the API will fail to connect.

   - **Supabase (hosted PostgreSQL)** — Create a project at [supabase.com](https://supabase.com), open **Project Settings → Database**, copy the host, database name, user, password, and port. In `.env` set `IS_LOCAL_DATABASE=False` and fill `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` (and optional `SUPABASE_PROJECT_URL` / `SUPABASE_API_KEY` if you use other Supabase features). The app builds `DATABASE_URL` from these values.

   For PostgreSQL and Supabase you must have the server reachable before migrations succeed. For SQLite, only the file path matters.

   **Mistral OCR API key (`MISTRAL_API_KEY`)** — Cloud **Mistral OCR** runs only when a user turns on the LLM-related option on their dietary profile (see `backend/settings.py` and the OCR service). Set `MISTRAL_API_KEY` in your `.env`. **Recommended:** create your own key in the [Mistral AI console](https://console.mistral.ai/) so you are not affected by anyone else’s usage. **If you do not create your own key**, you may use a key supplied by the project maintainer (for example shared in class or in private notes alongside the repo); that is only for convenience and is **not guaranteed**: the key can **expire**, be **revoked**, or hit **rate limits / quota**, and Mistral OCR will stop working until a valid key is configured. For production or demos you care about, always use your own key.

5. **Apply database migrations** (Alembic)

   ```bash
   make migrate
   ```

   Or run `alembic upgrade head` from the repo root with `PYTHONPATH` set to the project root (the Makefile does this for you).

6. **Install frontend dependencies**

   ```bash
   cd frontend && npm install && cd ..
   ```

7. **Optional — train the box classifier** (improves pipeline components that depend on `training/models/`)

   ```bash
   make training
   ```

## Quickstart

**Backend API** (interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)):

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload
```

**Frontend dev server:**

```bash
cd frontend
npm run dev
```

**Install everything and run backend + frontend** (backend in background, frontend in foreground):

```bash
make install
make run
```

**Run tests:**

```bash
make run-all-tests
```

**Optional local OpenAI-compatible server (example: vLLM via Makefile target):**

```bash
make vllm-mistral7B
```

Then set `LLM_PROVIDER=local_llm` and align `LOCAL_LLM_BASE_URL` / `LOCAL_LLM_MODEL` in `.env` with your server.

## How It Works

Users sign in and save a **dietary profile**. For a **photo scan**, the backend receives the image, runs **OCR** to obtain raw text, then **normalizes and splits** that text into ingredients (SymSpell and related heuristics by default; optional **LLM extraction** when enabled). For a **barcode scan**, the app fetches structured product data from **Open Food Facts** and derives an ingredient list from there. The **analysis** step compares ingredients to the user’s restrictions using **rules**, and can augment or replace parts of that logic with an **LLM** when configured, falling back to rules if the model is missing or errors. Results and metadata are stored so users can review **scan history** in the app.

## Project Structure

```
SmartFoodScanner/
├── backend/           # FastAPI app, routers, services (OCR, barcode, LLM, analysis)
├── frontend/          # Vue 3 PWA (Vite)
├── training/          # Box classifier training and evaluation scripts
├── scripts/           # Helper scripts
├── tests/             # Unit, integration, and performance tests
├── docs/              # Additional documentation
├── alembic/           # Database migrations
├── requirements.txt   # Python dependencies
├── Makefile           # Common dev commands
└── .env.example       # Environment template
```

## Results / Demo

- Use the running app to capture label photos or barcodes and inspect JSON responses in the API docs (`/docs`) or the PWA UI.
- Performance-oriented comparisons (e.g. SymSpell vs LLM extraction timing) are described in `docs/methodology-and-implementation.md` and can be reproduced with the project’s **performance** tests.
- **Screenshots / GIFs:** Add images here (e.g. `docs/images/scan-demo.png`) once you have captures from your own runs.

## Future Improvements

- Stronger **offline-first** behaviour and clearer degradation when Open Food Facts or LLM endpoints are slow.
- Richer **label understanding** (nutrition panels, “may contain” parsing) with evaluation on a fixed benchmark set.
- **Production hardening**: stricter CORS, rate limiting, automated upload lifecycle, and deployment guides for a chosen host.

## License

MIT License
