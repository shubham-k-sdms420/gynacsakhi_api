
## Project Type: FastAPI (Python)
## Architecture: Single-file FastAPI app with Pydantic models + Gemini client in lifespan


## Flow Summary
This endpoint enables: **Client sends user text** → **API injects system + clinic context** → **Gemini generates assistant reply** → **API returns reply + token usage**.

---

## Endpoint Handover Document — `POST /test/response`

### Overview
- **Service name**: Sakhi Clinic Assistant API
- **Endpoint**: `POST /test/response`
- **Purpose**: Generate a clinic-context-grounded reply from “Sakhi” (Gemini-backed) for a given user message.
- **Statelessness**: Each request is processed independently (no chat history stored/used by the API).
- **OpenAPI docs**: Served by FastAPI at `GET /docs` when the server is running.

### Base URL
- **Production**: `https://gynacsakhi.reviewtestlink.com`
- **Local default**: `http://localhost:8000`

### Authentication & Authorization
- **No HTTP auth is implemented** at the API layer.
- **Required secret**: Gemini API key is required server-side via environment variable (see “Configuration”).

### HTTP Request
- **Method**: `POST`
- **Path**: `/test/response`
- **Headers**
  - **Required**: `Content-Type: application/json`
  - **Optional**: `Accept: application/json`

### Request Body (JSON)
Schema (Pydantic `QueryRequest`):
- **text** *(string, required)*: User’s message/query.
  - Validation: `min_length = 1` (empty string will be rejected by FastAPI validation).
- **patient_name** *(string | null, optional)*: Patient name for personalization.

Example request:

```json
{
  "text": "What are your working hours on Saturday?",
  "patient_name": "Shreya"
}
```

Minimal example:

```json
{
  "text": "Do you provide ultrasound services?"
}
```

### Response Body (JSON)
Schema (Pydantic `QueryResponse`):
- **response** *(string)*: Generated assistant reply text.
- **model** *(string)*: Gemini model name used (from configuration).
- **input_tokens** *(integer | null)*: Prompt token count (if Gemini returns usage metadata).
- **output_tokens** *(integer | null)*: Completion/candidate token count (if returned).
- **total_tokens** *(integer | null)*: Total token count (if returned).

Successful response example (`200 OK`):

```json
{
  "response": "Hello Shreya, Shakti Women's Care Clinic is open Monday to Saturday from 10:00 AM to 7:00 PM. Would you like me to help you book an appointment?",
  "model": "gemini-2.5-flash",
  "input_tokens": 218,
  "output_tokens": 74,
  "total_tokens": 292
}
```

Notes:
- Token fields may be `null` if the upstream SDK response doesn’t include usage metadata.
- `response` is derived from `response.text.strip()` from the Gemini SDK.

---

## Behavior & Processing Rules (Server-Side)

### Context injection
The service builds a `system_instruction` string for Gemini as:
- **System prompt** (defaults from `context_data.SYSTEM_PROMPT`, optionally overridden by file path)
- **Clinic knowledge base** (defaults from `context_data.CLINIC_CONTEXT`, optionally overridden by file path)
- **Optional patient line** appended when `patient_name` is provided

### Generation parameters
Gemini generation is called with:
- `model`: from configuration `gemini_model` (default `gemini-2.5-flash`)
- `contents`: request `text`
- `temperature`: from configuration
- `max_output_tokens`: from configuration

### Logging / Observability (token usage)
If `token_log_enabled` is true:
- The service appends one JSON line per request to `token_log_path`
- Failures in logging are swallowed and **must not** break the request
- Log record shape:
  - `ts` (UTC ISO timestamp)
  - `model`
  - `patient_name`
  - `text`
  - `input_tokens`, `output_tokens`, `total_tokens`

---

## Status Codes & Error Handling

### `200 OK`
- Returned when Gemini generation succeeds and a response is produced.

### `422 Unprocessable Entity` (FastAPI validation)
Common causes:
- Missing required field `text`
- `text` is empty string
- Wrong JSON types (e.g., `patient_name` as object)

Example error response shape (FastAPI default):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "text"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### `503 Service Unavailable`
Cause:
- Gemini client not initialized (lifespan did not run or initialization failed)

Response:

```json
{
  "detail": "Model client not initialized"
}
```

### `500 Internal Server Error`
Cause:
- Any exception during content generation (Gemini SDK error, network error, invalid key, etc.)

Response:

```json
{
  "detail": "Generation failed: <error message>"
}
```

---

## Configuration (Required for Deployment)
Environment variables are loaded from `.env` by default (Pydantic Settings).

### Required
- **`GEMINI_API_KEY`**: Google AI Studio / Gemini API key

### Optional (with defaults)
- **`GEMINI_MODEL`**: default `gemini-2.5-flash`
- **`GEMINI_TEMPERATURE`**: default `0.6`
- **`GEMINI_MAX_OUTPUT_TOKENS`**: default `600`
- **`TOKEN_LOG_ENABLED`**: default `true`
- **`TOKEN_LOG_PATH`**: default `sakhi_tokens.jsonl`
- **`CLINIC_CONTEXT_PATH`**: if set, reads clinic KB from this UTF-8 file
- **`SYSTEM_PROMPT_PATH`**: if set, reads system prompt from this UTF-8 file
- **`UVICORN_HOST`**: default `0.0.0.0`
- **`UVICORN_PORT`**: default `8000`
- **`UVICORN_RELOAD`**: default `false`
- **`APP_TITLE`**: default `Sakhi Clinic Assistant API`
- **`APP_DESCRIPTION`**: default `AI-powered assistant for Shakti Women's Care Clinic`
- **`APP_VERSION`**: default `1.0.0`

Example `.env`:

```bash
GEMINI_API_KEY="replace_me"
GEMINI_MODEL="gemini-2.5-flash"
GEMINI_TEMPERATURE="0.6"
GEMINI_MAX_OUTPUT_TOKENS="600"
TOKEN_LOG_ENABLED="true"
TOKEN_LOG_PATH="sakhi_tokens.jsonl"
# Optional overrides:
# CLINIC_CONTEXT_PATH="/etc/sakhi/clinic_context.txt"
# SYSTEM_PROMPT_PATH="/etc/sakhi/system_prompt.txt"
UVICORN_HOST="0.0.0.0"
UVICORN_PORT="8000"
UVICORN_RELOAD="false"
```

---

## Non-Functional Considerations (for the dev team)
- **PII**: Requests can include patient names and free-text; treat request logs and token logs as sensitive. Decide whether to disable `TOKEN_LOG_ENABLED` in production or scrub/secure logs.
- **Rate limiting**: Not implemented. If exposed publicly, add gateway-level rate limits.
- **Timeouts/retries**: Not implemented at the API layer. Consider upstream client timeout settings or reverse proxy timeouts.
- **CORS**: Not configured. If a browser app will call this from another origin, add FastAPI CORS middleware.
- **Idempotency**: Not guaranteed (LLM generation is stochastic; repeated calls can vary).

---

## Quick Test (cURL)

```bash
curl -sS -X POST "http://localhost:8000/test/response" \
  -H "Content-Type: application/json" \
  -d '{"text":"What are your consultation fees?","patient_name":"Shreya"}'
```

---

## Related Endpoints (FYI)
- `GET /` → health/status JSON
- `GET /ui` → minimal HTML chat UI that calls `POST /test/response`
- `GET /docs` → Swagger UI (FastAPI)

