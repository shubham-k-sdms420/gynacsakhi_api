"""
Sakhi - Gynac Clinic AI Assistant API
FastAPI endpoint with pluggable inference provider (Gemini or OpenRouter).
Provider and model are controlled via INFERENCE_PROVIDER / INFERENCE_MODEL env vars.
"""

from contextlib import asynccontextmanager
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from config import get_settings
from context_data import CLINIC_CONTEXT, SYSTEM_PROMPT
from inference import InferenceProvider, build_provider

_provider: InferenceProvider | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _provider
    _provider = build_provider(get_settings())
    yield
    if _provider is not None:
        _provider.close()
    _provider = None


def _app() -> FastAPI:
    settings = get_settings()
    return FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )


app = _app()


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User's message / query")
    patient_name: str | None = Field(
        None, description="Optional patient name for personalization"
    )


class QueryResponse(BaseModel):
    response: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@app.get("/")
def root():
    return {"status": "ok", "service": "Sakhi Clinic Assistant"}


@app.get("/favicon.ico")
def favicon():
    # Avoid noisy 404s in logs for browsers.
    return Response(status_code=204)


@app.get("/ui", response_class=HTMLResponse)
def ui():
    settings = get_settings()
    title = settings.app_title
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} — Chat</title>
    <style>
      :root {{
        --bg: #0b1220;
        --card: rgba(255,255,255,0.06);
        --card2: rgba(255,255,255,0.10);
        --text: rgba(255,255,255,0.92);
        --muted: rgba(255,255,255,0.70);
        --border: rgba(255,255,255,0.14);
        --accent: #9b5cff;
        --accent2: #49d3ff;
        --danger: #ff5c7a;
        --me: rgba(155,92,255,0.22);
        --bot: rgba(73,211,255,0.14);
      }}
      body {{
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
        background: radial-gradient(1200px 600px at 15% 0%, rgba(155,92,255,0.35), transparent 65%),
                    radial-gradient(900px 500px at 85% 10%, rgba(73,211,255,0.25), transparent 60%),
                    var(--bg);
        color: var(--text);
      }}
      .wrap {{
        max-width: 920px;
        margin: 0 auto;
        padding: 22px 14px 40px;
      }}
      header {{
        display: flex;
        gap: 12px;
        align-items: baseline;
        justify-content: space-between;
        flex-wrap: wrap;
        margin-bottom: 18px;
      }}
      .brand {{
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}
      h1 {{
        font-size: 20px;
        line-height: 1.1;
        margin: 0;
        letter-spacing: 0.2px;
      }}
      .sub {{
        margin: 0;
        color: var(--muted);
        font-size: 13px;
      }}
      .pill {{
        font-size: 12px;
        color: rgba(255,255,255,0.82);
        background: rgba(255,255,255,0.08);
        border: 1px solid var(--border);
        padding: 6px 10px;
        border-radius: 999px;
      }}
      .card {{
        background: linear-gradient(180deg, var(--card), var(--card2));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 14px;
        box-shadow: 0 16px 36px rgba(0,0,0,0.30);
        backdrop-filter: blur(10px);
      }}
      .topbar {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }}
      label {{
        display: block;
        font-size: 12px;
        color: var(--muted);
        margin: 0 0 6px;
      }}
      input, textarea {{
        width: 100%;
        box-sizing: border-box;
        background: rgba(0,0,0,0.18);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 12px;
        padding: 10px 12px;
        outline: none;
      }}
      textarea {{
        min-height: 42px;
        max-height: 140px;
        resize: none;
        line-height: 1.4;
      }}
      input:focus, textarea:focus {{
        border-color: rgba(155,92,255,0.55);
        box-shadow: 0 0 0 4px rgba(155,92,255,0.15);
      }}
      .chat {{
        display: flex;
        flex-direction: column;
        gap: 10px;
        height: min(68vh, 640px);
      }}
      .messages {{
        flex: 1;
        overflow: auto;
        padding: 10px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: rgba(0,0,0,0.14);
      }}
      .msg {{
        display: flex;
        margin: 8px 0;
      }}
      .bubble {{
        max-width: 86%;
        padding: 10px 12px;
        border-radius: 14px;
        border: 1px solid var(--border);
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 14px;
        line-height: 1.45;
      }}
      .me {{ justify-content: flex-end; }}
      .me .bubble {{
        background: linear-gradient(180deg, rgba(155,92,255,0.22), rgba(155,92,255,0.12));
      }}
      .bot {{ justify-content: flex-start; }}
      .bot .bubble {{
        background: linear-gradient(180deg, rgba(73,211,255,0.14), rgba(73,211,255,0.08));
      }}
      .hint {{
        font-size: 12px;
        color: var(--muted);
        margin-top: 8px;
      }}
      .row {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-top: 12px;
      }}
      button {{
        appearance: none;
        border: 0;
        border-radius: 12px;
        padding: 10px 12px;
        font-weight: 650;
        cursor: pointer;
      }}
      .primary {{
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        color: #0b1220;
      }}
      .ghost {{
        background: rgba(255,255,255,0.08);
        border: 1px solid var(--border);
        color: var(--text);
      }}
      button:disabled {{
        opacity: 0.6;
        cursor: not-allowed;
      }}
      .meta {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-left: auto;
        color: var(--muted);
        font-size: 12px;
      }}
      .status {{
        margin-top: 8px;
        font-size: 12px;
        color: var(--muted);
      }}
      .err {{
        color: rgba(255,255,255,0.92);
        background: rgba(255,92,122,0.14);
        border: 1px solid rgba(255,92,122,0.35);
        padding: 10px 12px;
        border-radius: 12px;
        margin-bottom: 10px;
      }}
      a {{ color: rgba(155,92,255,0.95); text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <header>
        <div class="brand">
          <h1>{title} — Chat</h1>
          <p class="sub">A minimal chatbot UI for Sakhi (calls <code>/test/response</code>).</p>
        </div>
        <div class="pill">
          Model: <span id="modelPill">—</span>
          <span style="opacity:.85;"> • tokens: <span id="totalsPill">0</span></span>
        </div>
      </header>

      <section class="card chat">
        <div class="topbar">
          <div style="flex: 1; min-width: 220px;">
            <label for="patient_name">Patient name (optional)</label>
            <input id="patient_name" name="patient_name" placeholder="e.g., Shreya" autocomplete="given-name" />
          </div>
          <div class="meta" style="margin-left:auto;">
            <a href="/docs" target="_blank" rel="noreferrer">API docs</a>
            <button id="clearBtn" class="ghost" type="button">Clear chat</button>
          </div>
        </div>

        <div id="errorBox" class="err" style="display:none;"></div>

        <div id="messages" class="messages" aria-live="polite"></div>

        <form id="form" autocomplete="off">
          <label for="text">Message</label>
          <textarea id="text" name="text" placeholder="Type a message… (Enter to send, Shift+Enter for newline)"></textarea>
          <div class="row">
            <button id="sendBtn" class="primary" type="submit">Send</button>
            <div class="meta">
              <span id="loading" style="display:none;">Generating…</span>
              <span id="status" class="status"></span>
            </div>
          </div>
          <div class="hint">Tip: this is stateless; each message is sent alone (no chat memory yet).</div>
        </form>
      </section>
    </div>

    <script>
      const form = document.getElementById('form');
      const sendBtn = document.getElementById('sendBtn');
      const clearBtn = document.getElementById('clearBtn');
      const loading = document.getElementById('loading');
      const status = document.getElementById('status');
      const messages = document.getElementById('messages');
      const errorBox = document.getElementById('errorBox');
      const modelPill = document.getElementById('modelPill');
      const totalsPill = document.getElementById('totalsPill');
      const textEl = document.getElementById('text');
      const nameEl = document.getElementById('patient_name');
      let totals = {{ input: 0, output: 0, total: 0 }};

      function setLoading(isLoading) {{
        sendBtn.disabled = isLoading;
        loading.style.display = isLoading ? 'inline' : 'none';
      }}

      function showError(message) {{
        errorBox.textContent = message;
        errorBox.style.display = 'block';
      }}

      function clearError() {{
        errorBox.textContent = '';
        errorBox.style.display = 'none';
      }}

      function fmtTokens(n) {{
        if (n === null || n === undefined) return '—';
        return String(n);
      }}

      function renderTotals() {{
        const t = totals;
        totalsPill.textContent =
          'in:' + fmtTokens(t.input) +
          ' out:' + fmtTokens(t.output) +
          ' total:' + fmtTokens(t.total);
      }}

      function appendMessage(role, text, meta) {{
        const row = document.createElement('div');
        row.className = 'msg ' + (role === 'me' ? 'me' : 'bot');
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        const body = document.createElement('div');
        body.textContent = text;
        bubble.appendChild(body);
        row.appendChild(bubble);
        if (meta && role === 'bot') {{
          const m = document.createElement('div');
          m.className = 'hint';
          m.style.marginTop = '6px';
          m.textContent =
            'tokens in:' + fmtTokens(meta.input_tokens) +
            ' out:' + fmtTokens(meta.output_tokens) +
            ' total:' + fmtTokens(meta.total_tokens);
          bubble.appendChild(m);
        }}
        messages.appendChild(row);
        messages.scrollTop = messages.scrollHeight;
      }}

      function resetChat() {{
        messages.innerHTML = '';
        status.textContent = '';
        clearError();
        totals = {{ input: 0, output: 0, total: 0 }};
        renderTotals();
        appendMessage('bot', "Hello, my name is Sakhi. How can I help you?");
      }}

      clearBtn.addEventListener('click', () => {{
        nameEl.value = '';
        textEl.value = '';
        resetChat();
      }});

      textEl.addEventListener('keydown', (e) => {{
        if (e.key === 'Enter' && !e.shiftKey) {{
          e.preventDefault();
          form.requestSubmit();
        }}
      }});

      resetChat();

      form.addEventListener('submit', async (e) => {{
        e.preventDefault();
        clearError();

        const text = textEl.value.trim();
        const patient_name = nameEl.value.trim();

        if (!text) {{
          showError('Please type a message.');
          return;
        }}

        appendMessage('me', text);
        textEl.value = '';

        setLoading(true);
        status.textContent = 'Sending…';

        try {{
          const resp = await fetch('/test/response', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              text,
              patient_name: patient_name || null
            }})
          }});

          const data = await resp.json().catch(() => null);
          if (!resp.ok) {{
            const detail = data && data.detail ? data.detail : 'Request failed.';
            throw new Error(detail);
          }}

          modelPill.textContent = data.model || '—';
          if (data.input_tokens !== null && data.input_tokens !== undefined) totals.input += data.input_tokens;
          if (data.output_tokens !== null && data.output_tokens !== undefined) totals.output += data.output_tokens;
          if (data.total_tokens !== null && data.total_tokens !== undefined) totals.total += data.total_tokens;
          renderTotals();
          appendMessage('bot', data.response || '', data);
          status.textContent = 'Done.';
        }} catch (err) {{
          showError(err && err.message ? err.message : 'Something went wrong.');
          status.textContent = 'Error.';
        }} finally {{
          setLoading(false);
        }}
      }});
    </script>
  </body>
</html>"""


@app.post("/test/response", response_model=QueryResponse)
def generate_response(payload: QueryRequest):
    """
    Takes user text input and returns Sakhi's response.
    Provider and model are selected via INFERENCE_PROVIDER / INFERENCE_MODEL env vars.
    """
    if _provider is None:
        raise HTTPException(status_code=503, detail="Model client not initialized")

    settings = get_settings()
    clinic_kb = settings.load_clinic_context(CLINIC_CONTEXT)
    system_prompt = settings.load_system_prompt(SYSTEM_PROMPT)

    patient_line = (
        f"\nCurrent patient name: {payload.patient_name}"
        if payload.patient_name
        else ""
    )
    system_instruction = (
        f"{system_prompt}\n\n"
        f"=== CLINIC KNOWLEDGE BASE ===\n{clinic_kb}"
        f"{patient_line}"
    )

    try:
        result = _provider.generate(
            user_text=payload.text,
            system_instruction=system_instruction,
        )

        if settings.token_log_enabled:
            try:
                Path(settings.token_log_path).expanduser().parent.mkdir(
                    parents=True, exist_ok=True
                )
                record = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "model": result.model,
                    "patient_name": payload.patient_name,
                    "text": payload.text,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "total_tokens": result.total_tokens,
                }
                with open(
                    Path(settings.token_log_path).expanduser(),
                    "a",
                    encoding="utf-8",
                ) as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception:
                pass

        return QueryResponse(
            response=result.text,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Generation failed: {str(e)}"
        ) from e


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "main:app",
        host=s.uvicorn_host,
        port=s.uvicorn_port,
        reload=s.uvicorn_reload,
    )
