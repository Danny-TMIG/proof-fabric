"""Serve artifacts. Re-verify the cert on every read."""
from __future__ import annotations
import json
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from proof_fabric.cert import Certificate
from proof_fabric.verify import verify, VerifyError


class Fabric:
    def __init__(self, artifacts_dir: Path, certs_dir: Path,
                 allowlist: set[str] | None = None):
        self.artifacts_dir = Path(artifacts_dir)
        self.certs_dir = Path(certs_dir)
        self.allowlist = allowlist
        self.log: list[dict] = []

    def read(self, name: str) -> tuple[bool, bytes | str]:
        art_path = self.artifacts_dir / name
        cert_path = self.certs_dir / f"{name}.cert.json"
        if not art_path.exists():
            return False, "artifact not found"
        if not cert_path.exists():
            return False, "cert not found"
        art = art_path.read_bytes()
        cert = Certificate.from_dict(json.loads(cert_path.read_text()))
        with tempfile.TemporaryDirectory() as t:
            try:
                verify(art, cert,
                       certs_dir=self.certs_dir,
                       artifacts_dir=self.artifacts_dir,
                       tmp_dir=Path(t),
                       allowlist=self.allowlist)
            except VerifyError as e:
                self.log.append({"artifact": name, "ok": False, "reason": str(e)})
                return False, str(e)
        self.log.append({"artifact": name, "ok": True, "reason": "ok"})
        return True, art

    def serve(self, host: str = "127.0.0.1", port: int = 8765) -> HTTPServer:
        fabric = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/log":
                    body = json.dumps(fabric.log).encode()
                elif self.path == "/health":
                    body = b'{"ok":true}'
                elif self.path.startswith("/artifacts/"):
                    name = self.path[len("/artifacts/"):]
                    ok, result = fabric.read(name)
                    if not ok:
                        payload = json.dumps({"error": result}).encode()
                        self.send_response(403)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                    body = result
                else:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a): pass

        return HTTPServer((host, port), H)
