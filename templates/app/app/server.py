"""웹 서버 뼈대. 표준 라이브러리만(설치 없이 Docker 이미지에서 바로 뜬다).

실행: python3 -m app.server   (PORT 환경변수, 기본 8000)
라우트를 ROUTES 에 추가한다. 계산은 여기 말고 별도 모듈에 두고 여기서는 부르기만 한다.
"""
import json
import os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

STATIC = Path(__file__).parent / "static"
MAX_BODY = 5 * 1024 * 1024  # 업로드 상한(바이트)


def health(_body):
    return 200, {"ok": True}


# (메서드, 경로) > 함수(body) > (상태코드, JSON 으로 보낼 값)
ROUTES = {
    ("GET", "/api/health"): health,
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method):
        path = self.path.split("?", 1)[0]
        fn = ROUTES.get((method, path))
        if fn is None:
            if method == "GET":
                return self._static(path)
            return self._send(404, {"error": "없는 주소입니다"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._send(413, {"error": "파일이 너무 큽니다"})
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw and "json" in (self.headers.get("Content-Type") or "") else raw
            code, payload = fn(body)
        except ValueError as e:  # 입력 검증 실패는 400 으로 이유를 돌려준다
            code, payload = 400, {"error": str(e)}
        self._send(code, payload)

    def _static(self, path):
        target = (STATIC / (path.lstrip("/") or "index.html")).resolve()
        if STATIC.resolve() not in target.parents or not target.is_file():
            return self._send(404, {"error": "없는 주소입니다"})
        types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}
        self._send(200, target.read_bytes(), types.get(target.suffix, "application/octet-stream") + "; charset=utf-8")

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def make_server(port=None):
    # 0.0.0.0 이어야 컨테이너 밖에서 접속된다
    return ThreadingHTTPServer(("0.0.0.0", int(port if port is not None else os.getenv("PORT", "8000"))), Handler)


if __name__ == "__main__":
    srv = make_server()
    print(f"http://0.0.0.0:{srv.server_address[1]}")
    srv.serve_forever()
