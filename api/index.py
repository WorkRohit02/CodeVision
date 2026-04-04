import os
import base64
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from mangum import Mangum

from ai_service import analyze_code, ask_followup, extract_code_from_image

app = FastAPI(title="CodeVision (Gemini)", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ── Helper: get API key from request header ─────────────────────────────────

def get_api_key(request: Request) -> Optional[str]:
    return request.headers.get("X-Api-Key", "")


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True, "version": "6.0.0"})


# ── /api/analyze ────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    api_key = get_api_key(request)
    if not api_key:
        raise HTTPException(401, "No API key provided.")

    code = (req.code or "").strip()

    if not code and req.image_base64:
        try:
            raw = base64.b64decode(req.image_base64)
            code = await extract_code_from_image(raw, req.image_media_type or "image/png", api_key)
            if not code.strip():
                raise HTTPException(400, "Could not extract code. Use a high-contrast screenshot.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Image extraction failed: {e}")

    if not code:
        raise HTTPException(400, "No code provided.")

    try:
        result = await analyze_code(code, req.language, api_key)
        result["extracted_code"] = code if req.image_base64 else None
        return JSONResponse(result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis error: {e}")


# ── /api/ask ────────────────────────────────────────────────────────────────

@app.post("/api/ask")
async def ask(req: AskRequest, request: Request):
    api_key = get_api_key(request)
    if not api_key:
        raise HTTPException(401, "No API key provided.")

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
            api_key,
        )
        return JSONResponse({"answer": answer})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Q&A error: {e}")


# ── Vercel handler ──────────────────────────────────────────────────────────
handler = Mangum(app)