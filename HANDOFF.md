# CodeVision — Gemini Edition: Complete Handoff Document

## What Is This?

**CodeVision** is a local AI-powered code analysis web app. You paste code (or upload a screenshot), click Analyze, and get:
- Line-by-line explanations
- Bug detection with fixes
- Step-by-step dry-run execution trace
- Time & space complexity (Big-O)
- Optimization suggestions
- Follow-up Q&A chatbot

**This version uses Google Gemini (gemini-1.5-flash) — which has a generous FREE tier.**

---

## File Structure

```
codevision/
├── backend/
│   ├── main.py           ← FastAPI server (routes, health check)
│   ├── ai_service.py     ← All Gemini API calls (analysis, OCR, Q&A)
│   └── requirements.txt  ← Python dependencies
├── frontend/
│   └── index.html        ← Entire UI (single self-contained file)
├── start_windows.bat     ← Double-click to run on Windows
└── start_mac_linux.sh    ← Run on Mac/Linux
```

---

## Setup Instructions

### Step 1 — Get a FREE Gemini API Key

1. Go to **https://aistudio.google.com/apikey**
2. Sign in with a Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

### Step 2 — Add the Key

Create a file called `.env` inside the `backend/` folder:

```
GEMINI_API_KEY=AIzaYourActualKeyHere
```

### Step 3 — Run the App

**Windows:** Double-click `start_windows.bat`

**Mac/Linux:**
```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh
```

The app opens automatically at **http://localhost:8000**

---

## Dependencies (auto-installed by startup script)

```
google-generativeai>=0.7.0   ← Gemini SDK
Pillow>=10.0.0               ← Image handling for screenshot OCR
fastapi>=0.115.0             ← Web server framework
uvicorn[standard]>=0.30.0   ← ASGI server
python-dotenv>=1.0.0        ← Loads .env file
pydantic>=2.0.0             ← Request validation
python-multipart>=0.0.9     ← File upload support
```

---

## How It Works (Technical Summary)

### Backend (`ai_service.py`)

| Function | What it does |
|---|---|
| `analyze_code(code, lang)` | Runs 2 Gemini calls in parallel — one for explanations+bugs+fixes, one for dry-run+complexity+suggestions |
| `extract_code_from_image(bytes)` | Sends image to Gemini Vision to extract code text |
| `ask_followup(question, code, lang, history)` | Single Gemini call for Q&A with conversation history |

### Why 2 parallel calls?
The prompts are long and structured. Splitting them into two concurrent requests is faster than one giant prompt.

### API Used
- **Model:** `gemini-1.5-flash` (fast, free tier: 15 req/min, 1M tokens/day)
- **Endpoint:** via `google-generativeai` Python SDK
- **Vision:** Gemini natively handles `PIL.Image` objects for screenshot OCR

### Frontend (`index.html`)
- Pure HTML/CSS/JS — no framework, no build step
- Talks to FastAPI via `fetch()` on the same origin (no CORS issues)
- The frontend file is 100% self-contained

---

## What to Tell Another Claude Account

Paste this prompt:

---

> I have a code analysis web app called CodeVision that uses Gemini instead of Anthropic. Here are the 3 backend files. Please help me with [your question].
>
> **backend/ai_service.py:** [paste content]
> **backend/main.py:** [paste content]
> **backend/requirements.txt:** [paste content]
>
> The frontend is a single `frontend/index.html` file — let me know if you need that too.

---

## Common Issues

| Problem | Solution |
|---|---|
| "Backend not running" pill shows | Run the startup script first, then refresh browser |
| "API key missing" | Check `backend/.env` has `GEMINI_API_KEY=AIza...` (no quotes) |
| `ModuleNotFoundError: google.generativeai` | Run `pip install google-generativeai` in the venv |
| Pillow error on image upload | Run `pip install Pillow` |
| Port 8000 already in use | Change `--port 8000` to `--port 8001` in the startup script |
| Gemini rate limit (15 req/min free) | Wait a moment and retry; or upgrade to pay-as-you-go |

---

## Changing the Model

In `backend/ai_service.py`, line near the top:

```python
_model = genai.GenerativeModel("gemini-1.5-flash")   # fast, free
# or:
_model = genai.GenerativeModel("gemini-1.5-pro")     # smarter, slower
# or:
_model = genai.GenerativeModel("gemini-2.0-flash")   # newest fast model
```

---

## Free Tier Limits (as of 2025)

| Limit | Value |
|---|---|
| Requests per minute | 15 |
| Requests per day | 1,500 |
| Tokens per day | 1,000,000 |
| Cost | $0 |

For personal/learning use, the free tier is more than enough.
