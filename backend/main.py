import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import base64
import traceback

from ai_service import analyze_code, ask_followup, extract_code_from_image

app = FastAPI(title="CodeVision (Gemini)", version="4.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend ─────────────────────────────────────────────────────────
FRONTEND = Path(__file__).parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse(FRONTEND / "index.html")

@app.get("/index.html", response_class=HTMLResponse)
async def index():
    return FileResponse(FRONTEND / "index.html")

if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


# ── Models ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    code:             Optional[str] = None
    image_base64:     Optional[str] = None
    image_media_type: Optional[str] = "image/png"
    language:         str           = "python"

class AskRequest(BaseModel):
    question:             str
    code:                 str
    language:             str
    conversation_history: list = []


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    key = os.getenv("GEMINI_API_KEY", "")
    ok  = bool(key and len(key) > 10)
    return JSONResponse({
        "ok":         ok,
        "key_prefix": key[:12] + "…" if ok else "NOT SET",
        "model":      "gemini-1.5-flash",
        "version":    "4.1.0",
    })


# ── /analyze ────────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    code = (req.code or "").strip()

    if not code and req.image_base64:
        try:
            raw = base64.b64decode(req.image_base64)
            code = await extract_code_from_image(raw, req.image_media_type or "image/png")
            if not code.strip():
                raise HTTPException(400, "Could not extract code. Use a high-contrast screenshot.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Image extraction failed: {e}")

    if not code:
        raise HTTPException(400, "No code provided.")

    try:
        result = await analyze_code(code, req.language)
        result["extracted_code"] = code if req.image_base64 else None
        return JSONResponse(result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis error: {e}")


# ── /ask ────────────────────────────────────────────────────────────────────

@app.post("/ask")
async def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "Empty question.")
    if not req.code.strip():
        raise HTTPException(400, "No code context.")
    try:
        answer = await ask_followup(
            req.question.strip(),
            req.code.strip(),
            req.language,
            req.conversation_history,
        )
        return JSONResponse({"answer": answer})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Q&A error: {e}")
