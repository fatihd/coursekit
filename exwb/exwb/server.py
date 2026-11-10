import json, os, re, subprocess, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import core, ocr
from .db import set_meta

STATIC = os.path.join(os.path.dirname(__file__), "static")
ENGINE = os.environ.get("EXWB_ENGINE_DIR") or os.path.join(os.path.dirname(__file__), "..", "..", "engine")
ENGINE_FILES = {"keyboard.js", "dom.js", "keyboards/he_IL.js"}

def render_pdf_page(pdf, page, cache):
    os.makedirs(cache, exist_ok=True)
    out = os.path.join(cache, f"{os.path.splitext(os.path.basename(pdf))[0]}-{page:04d}")
    if not os.path.exists(out + ".jpg"):
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "250", "-gray", "-jpeg", "-singlefile", pdf, out],
                       check=False, capture_output=True, timeout=60)
    return out + ".jpg" if os.path.exists(out + ".jpg") else None
LOCK = threading.Lock()

def make_handler(con, project):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json"):
            if not isinstance(body, (bytes, bytearray)): body = json.dumps(body, ensure_ascii=False).encode("utf8")
            self.send_response(code); self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype or "json" in ctype else ""))
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        def do_GET(self):
            u = urlparse(self.path); q = parse_qs(u.query); p = u.path
            with LOCK:
                if p == "/": return self._send(200, open(os.path.join(STATIC, "index.html"), "rb").read(), "text/html")
                if p == "/api/state": return self._send(200, core.state(con))
                m = re.fullmatch(r"/api/block/(\d+)", p)
                if m:
                    b = core.block(con, int(m.group(1))); return self._send(200 if b else 404, b or {"error": "no such block"})
                m = re.fullmatch(r"/api/page/([^/]+)/(\d+)", p)
                if m:
                    pg = core.page(con, m.group(1), int(m.group(2))); return self._send(200 if pg else 404, pg or {"error": "no such page"})
                m = re.fullmatch(r"/api/key/(\d+)", p)
                if m: return self._send(200, core.key_candidates(con, int(m.group(1))))
                if p == "/api/next":
                    a = q.get("after", [""])[0]; return self._send(200, {"id": core.next_unfinished(con, int(a) if a else None)})
                if p == "/api/export":
                    return self._send(200, core.export(con, q.get("only", ["done"])[0]))
                m = re.fullmatch(r"/engine/(.+)", p)
                if m and m.group(1) in ENGINE_FILES:
                    f = os.path.join(ENGINE, m.group(1))
                    if os.path.exists(f): return self._send(200, open(f, "rb").read(), "text/javascript")
                m = re.fullmatch(r"/img/([^/]+)/(\d+)", p)
                if m:
                    s = con.execute("SELECT images_dir, pdf, pdf_delta FROM source WHERE id=?", (m.group(1),)).fetchone()
                    d = s["images_dir"] if s else ""
                    if s and s["pdf"] and not d:
                        f = render_pdf_page(s["pdf"], int(m.group(2)) + (s["pdf_delta"] or 0), os.path.join(project, "cache"))
                        if f:
                            self.send_response(200); body = open(f, "rb").read()
                            self.send_header("Content-Type", "image/jpeg"); self.send_header("Cache-Control", "max-age=86400")
                            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
                    for ext in ("jpg", "jpeg", "png", "webp"):
                        f = os.path.join(d, f"{int(m.group(2)):04d}.{ext}") if d else ""
                        if f and os.path.exists(f):
                            return self._send(200, open(f, "rb").read(), {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext])
                return self._send(404, {"error": "not found"})
        def do_POST(self):
            p = urlparse(self.path).path
            try: d = self._body()
            except Exception: return self._send(400, {"error": "bad json"})
            with LOCK:
                m = re.fullmatch(r"/api/block/(\d+)", p)
                if m: core.update_block(con, int(m.group(1)), d); return self._send(200, {"ok": True})
                m = re.fullmatch(r"/api/block/(\d+)/items", p)
                if m: core.replace_items(con, int(m.group(1)), d.get("items", [])); return self._send(200, core.block(con, int(m.group(1))))
                m = re.fullmatch(r"/api/block/(\d+)/regenerate", p)
                if m: core.regenerate(con, int(m.group(1))); return self._send(200, core.block(con, int(m.group(1))))
                m = re.fullmatch(r"/api/block/(\d+)/ocr", p)
                if m:
                    st = ocr.available()
                    if not st["ok"]: return self._send(200, {"error": st["why"]})
                    try: n = ocr.ocr_block(con, int(m.group(1)), project, force=bool(d.get("force")), log=lambda *_: None)
                    except Exception as e: return self._send(200, {"error": str(e)})
                    for (ks,) in con.execute("SELECT id FROM source WHERE role='key'").fetchall(): core.rebuild_keysegs(con, ks)
                    if d.get("redetect"): core.regenerate(con, int(m.group(1)))
                    b = core.block(con, int(m.group(1))); b["ocr_lines"] = n; return self._send(200, b)
                m = re.fullmatch(r"/api/block/(\d+)/prefill", p)
                if m:
                    rep = core.prefill_answers(con, int(m.group(1)), bool(d.get("force"))); b = core.block(con, int(m.group(1)))
                    b["report"] = rep; return self._send(200, b)
                m = re.fullmatch(r"/api/block/(\d+)/merge", p)
                if m:
                    r = core.merge_with_next(con, int(m.group(1)))
                    return self._send(200, core.block(con, r) if r else {"error": "no next block"})
                m = re.fullmatch(r"/api/block/(\d+)/section", p)
                if m: core.set_section(con, int(m.group(1)), str(d.get("section", ""))); core.regenerate(con, int(m.group(1))); return self._send(200, core.block(con, int(m.group(1))))
                m = re.fullmatch(r"/api/block/(\d+)/delete", p)
                if m: return self._send(200, {"result": core.delete_block(con, int(m.group(1)))})
                if p == "/api/block":
                    bid = core.create_block(con, d["source"], int(d["start_scan"]), int(d["start_line"]), int(d["end_scan"]), int(d["end_line"]), d.get("section", ""), d.get("note", ""))
                    return self._send(200, {"id": bid})
                if p == "/api/settings":
                    if "leaf_delta" in d: set_meta(con, "leaf_delta", int(d["leaf_delta"]))
                    return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})
    return H

def serve(con, project, port=8765, host="127.0.0.1"):
    srv = ThreadingHTTPServer((host, port), make_handler(con, project))
    print(f"Exercise workbench: http://{host}:{port}   (Ctrl+C to stop; state is saved continuously)")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
