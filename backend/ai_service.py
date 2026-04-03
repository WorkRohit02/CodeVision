import os
import asyncio
from google import genai

_client = None

def get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Add it to backend/.env  →  GEMINI_API_KEY=AIza..."
            )
        _client = genai.Client(api_key=key)
    return _client


MODEL_NAME = "gemini-2.5-flash"


# ── Vision OCR ─────────────────────────────────────────────────────────────

async def extract_code_from_image(image_bytes: bytes, media_type: str = "image/png") -> str:
    import PIL.Image
    import io

    def _call():
        client = get_client()
        img = PIL.Image.open(io.BytesIO(image_bytes))
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                img,
                "Extract ALL code from this screenshot exactly as written. "
                "Preserve every character and indentation. "
                "Output ONLY the raw code — no explanation, no markdown fences."
            ]
        )
        return response.text.strip()

    return await asyncio.to_thread(_call)


# ── Language auto-detect ────────────────────────────────────────────────────

async def detect_language(code: str) -> str:
    def _call():
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="What programming language is this? Reply with ONLY the language name.\n\n"
            + code[:1500]
        )
        return response.text.strip()

    return await asyncio.to_thread(_call)


# ── Prompts ─────────────────────────────────────────────────────────────────

def _numbered(code: str) -> str:
    return "\n".join(f"Line {i+1}: {l}" for i, l in enumerate(code.split("\n")))


def prompt1(code: str, lang: str) -> str:
    return f"""You are a senior {lang} engineer and CS educator.
Analyze this {lang} code. Reply using ONLY the tagged sections — no extra text.

CODE:
{_numbered(code)}

LINE_EXPLANATIONS_START
Line 1: [exact code from line 1]
Explanation: [what this line does — 1 sentence, be specific and technical]
Line 2: [exact code]
Explanation: [explanation]
[...repeat for EVERY single line including blank lines and closing braces — never skip any]
LINE_EXPLANATIONS_END

BUG_DETECTION_START
[Strictly check for: syntax errors, undefined variables, off-by-one errors, missing returns,
type mismatches, memory leaks in C/C++, null/undefined access, infinite loops, wrong operators,
logic errors, missing imports, React hook rule violations, async/await misuse, SQL injection risks]

BUG_1: Line [N] — ERROR|WARNING|SUGGESTION
Code: [exact problematic code]
Issue: [clear explanation of the problem]
Fix: [corrected code or concrete approach]

[If no issues at all:]
BUG_NONE: No bugs detected.
BUG_DETECTION_END

CORRECTED_CODE_START
[If ANY bugs exist: output the COMPLETE corrected code with ALL fixes applied.
Mark each corrected line with a short inline comment:  // FIX: reason  (use # FIX: for Python/Ruby/Bash)]
[If no bugs: write exactly: CLEAN]
CORRECTED_CODE_END"""


def prompt2(code: str, lang: str) -> str:
    return f"""You are a senior {lang} engineer. Analyze this code. Reply using ONLY the tagged sections.

CODE:
{_numbered(code)}

DRY_RUN_START
Sample input: [state the sample input you chose — pick a simple realistic example]

STEP_1:
Line: [line number(s)]
Action: [exactly what executes — be specific]
Variables: [name=value, name=value — show ALL variables currently in scope]

STEP_2:
Line: [line number(s)]
Action: [what executes]
Variables: [complete current state of all variables]

[Continue for all key execution steps.
For loops: show iterations 1, 2, 3 fully, then write "...loop continues similarly for remaining items"
Maximum 15 steps total.]
RESULT: [the final return value or printed output]
DRY_RUN_END

TIME_COMPLEXITY_START
[State the Big-O notation. Then in 2 sentences explain which part of the code drives it.]
TIME_COMPLEXITY_END

SPACE_COMPLEXITY_START
[State the Big-O notation. Then in 2 sentences explain what data structure uses the space.]
SPACE_COMPLEXITY_END

SUGGESTIONS_START
1. [Specific actionable improvement with brief reason]
2. [Specific actionable improvement with brief reason]
3. [Specific actionable improvement with brief reason]
4. [Optional improvement]
5. [Optional improvement]
SUGGESTIONS_END"""


# ── Core analysis ───────────────────────────────────────────────────────────

def _extract(text: str, start: str, end: str) -> str:
    try:
        s = text.index(start) + len(start)
        e = text.index(end)
        return text[s:e].strip()
    except ValueError:
        return ""


def _sync_call(prompt: str) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text


async def analyze_code(code: str, language: str) -> dict:
    p1 = prompt1(code, language)
    p2 = prompt2(code, language)

    # Run both passes in parallel
    r1, r2 = await asyncio.gather(
        asyncio.to_thread(_sync_call, p1),
        asyncio.to_thread(_sync_call, p2),
    )

    return {
        "line_explanations": _extract(r1, "LINE_EXPLANATIONS_START", "LINE_EXPLANATIONS_END"),
        "bug_detection":     _extract(r1, "BUG_DETECTION_START",     "BUG_DETECTION_END"),
        "corrected_code":    _extract(r1, "CORRECTED_CODE_START",    "CORRECTED_CODE_END"),
        "dry_run":           _extract(r2, "DRY_RUN_START",           "DRY_RUN_END"),
        "time_complexity":   _extract(r2, "TIME_COMPLEXITY_START",   "TIME_COMPLEXITY_END"),
        "space_complexity":  _extract(r2, "SPACE_COMPLEXITY_START",  "SPACE_COMPLEXITY_END"),
        "suggestions":       _extract(r2, "SUGGESTIONS_START",       "SUGGESTIONS_END"),
    }


# ── Q&A ─────────────────────────────────────────────────────────────────────

async def ask_followup(question: str, code: str, language: str, history: list) -> str:
    system_ctx = (
        f"You are a senior {language} engineer helping a student understand their code.\n\n"
        f"Code:\n{code}\n\n"
        "Answer clearly. Reference line numbers when helpful. Max 6 sentences unless a walkthrough is needed."
    )

    # Build conversation as a single prompt with history
    convo_parts = [system_ctx, "\n\n--- Conversation History ---\n"]
    for t in history[-8:]:
        if t.get("question"):
            convo_parts.append(f"User: {t['question']}")
        if t.get("answer"):
            convo_parts.append(f"Assistant: {t['answer']}")
    convo_parts.append(f"\nUser: {question}\nAssistant:")

    full_prompt = "\n".join(convo_parts)

    def _call():
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt
        )
        return response.text.strip()

    return await asyncio.to_thread(_call)