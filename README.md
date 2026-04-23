# Sakhi – Clinic Assistant API (FastAPI + Gemini)

A small FastAPI service that powers **Sakhi**, a clinic virtual assistant.

- **API**: `POST /test/response` → returns Sakhi’s reply
- **UI**: `GET /ui` → minimal chatbot page (no frontend build step)
- **Config**: all runtime settings come from **`.env`** (plug-and-play)
- **Token tracking**: logs per message + UI shows per-reply and total tokens

---

## Project structure

```
sakhi_api/
├── main.py           # FastAPI app + endpoints + UI
├── config.py         # pydantic-settings .env loader
├── context_data.py   # default clinic KB + system prompt
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### 1) Create a virtual environment (recommended)

```bash
cd "/home/stark/gynac medtech/sakhi_api"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Create your `.env`

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- `GEMINI_API_KEY=...`

Get a key from [Google AI Studio](https://aistudio.google.com/apikey).

---

## Run

### Option A: Run via `python main.py` (recommended)

This uses `UVICORN_HOST`, `UVICORN_PORT`, `UVICORN_RELOAD` from `.env`.

```bash
python main.py
```

### Option B: Run via Uvicorn directly

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Use

### UI (chatbot)

Open:

- `http://localhost:8000/ui`

The UI calls the API endpoint on the same server and shows:

- per-reply tokens (in/out/total)
- running totals in the header

### API docs

- `http://localhost:8000/docs`

### API request

```bash
curl -X POST "http://localhost:8000/test/response" \
  -H "Content-Type: application/json" \
  -d '{"text":"What are your clinic hours?","patient_name":"Priya"}'
```

Example response (fields may be `null` if the provider doesn’t return usage):

```json
{
  "response": "Hello Priya, I'm Sakhi... ",
  "model": "gemini-2.5-flash",
  "input_tokens": 123,
  "output_tokens": 45,
  "total_tokens": 168
}
```

---

## Configuration (`.env`)

All settings are optional except `GEMINI_API_KEY`.

### Gemini

- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `GEMINI_TEMPERATURE` (default: `0.6`)
- `GEMINI_MAX_OUTPUT_TOKENS` (default: `600`)

### Token usage logging

- `TOKEN_LOG_ENABLED` (default: `true`)
- `TOKEN_LOG_PATH` (default: `sakhi_tokens.jsonl`)

This appends **one JSON object per message** to the configured JSONL file.

### Optional: externalize the prompt / clinic context (no code edits)

If these are set, the app reads UTF‑8 text from the files instead of `context_data.py` defaults:

- `CLINIC_CONTEXT_PATH=/path/to/clinic_context.txt`
- `SYSTEM_PROMPT_PATH=/path/to/system_prompt.txt`

### Server (only when running `python main.py`)

- `UVICORN_HOST` (default: `0.0.0.0`)
- `UVICORN_PORT` (default: `8000`)
- `UVICORN_RELOAD` (default: `false`)

### OpenAPI metadata

- `APP_TITLE`
- `APP_DESCRIPTION`
- `APP_VERSION`

---

## Notes

- The current UI is **stateless** (each message is sent alone). If you want multi-turn memory, we can add server-side session chat history.
- `.env`, `.venv/`, caches, and token logs are excluded via `.gitignore`.

