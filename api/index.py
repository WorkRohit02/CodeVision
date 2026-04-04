import os
import json
import base64
import asyncio
import traceback
from http.server import BaseHTTPRequestHandler
from ai_service import analyze_code, ask_followup, extract_code_from_image


def _get_header(headers, name):
    name = name.lower()
    for k, v in headers.items():
        if k.lower() == name:
            return v
    return ""


def _json(data, status=200):
    body = json.dumps(data).encode()
    return status, body


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _send(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, b"")

    def do_GET(self):
        if self.path == "/api/health":
            status, body = _json({"ok": True, "version": "6.0.0"})
            self._send(status, body)
        else:
            self._send(404, json.dumps({"detail": "Not found"}).encode())

    def do_POST(self):
        raw = self._read_body()
        api_key = _get_header(self.headers, "X-Api-Key")

        if not api_key:
            self._send(401, json.dumps({"detail": "No API key provided."}).encode())
            return

        try:
            req = json.loads(raw)
        except Exception:
            self._send(400, json.dumps({"detail": "Invalid JSON."}).encode())
            return

        try:
            if self.path == "/api/analyze":
                result = asyncio.run(self._analyze(req, api_key))
                status, body = _json(result)
                self._send(status, body)

            elif self.path == "/api/ask":
                answer = asyncio.run(ask_followup(
                    req.get("question", "").strip(),
                    req.get("code", "").strip(),
                    req.get("language", "python"),
                    req.get("conversation_history", []),
                    api_key
                ))
                status, body = _json({"answer": answer})
                self._send(status, body)

            else:
                self._send(404, json.dumps({"detail": "Not found"}).encode())

        except Exception as e:
            traceback.print_exc()
            self._send(500, json.dumps({"detail": str(e)}).encode())

    async def _analyze(self, req, api_key):
        code = (req.get("code") or "").strip()

        if not code and req.get("image_base64"):
            raw_img = base64.b64decode(req["image_base64"])
            code = await extract_code_from_image(
                raw_img,
                req.get("image_media_type", "image/png"),
                api_key
            )
            if not code.strip():
                raise ValueError("Could not extract code from image.")

        if not code:
            raise ValueError("No code provided.")

        result = await analyze_code(code, req.get("language", "python"), api_key)
        result["extracted_code"] = code if req.get("image_base64") else None
        return result