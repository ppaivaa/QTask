#!/usr/bin/env python3
"""Smoke test: serve dist/, open every page and app in headless Chromium, report console errors
and save screenshots. Needs: pip install playwright (and a Chromium for it).

    python3 tools/smoke.py [--shots DIR] [--phone]
"""
import argparse, contextlib, functools, http.server, os, socketserver, sys, threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
PAGES = {
    "control-center": ["today", "projects", "search", "apps", "backup"],
    "lab-notebook": ["log", "tasks", "ideas", "plans", "deadlines"],
    "literature-hub": ["radar", "citations"],
    "structure-studio": ["viewer"],
    "paper-kit": ["plots", "schemes"],
}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@contextlib.contextmanager
def serve(port):
    handler = functools.partial(Quiet, directory=DIST)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="")
    ap.add_argument("--phone", action="store_true")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--seed", default="", help="JSON file of localStorage keys to load first")
    a = ap.parse_args()
    errors = []
    with serve(a.port) as base, sync_playwright() as p:
        b = p.chromium.launch()
        opts = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True) if a.phone \
            else dict(viewport={"width": 1280, "height": 860})
        ctx = b.new_context(**opts)
        # block online lookups so the test is quick and offline
        ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(base) else r.continue_())
        page = ctx.new_page()
        msgs = []
        page.on("console", lambda m: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
        if a.seed:
            import json
            seed = json.load(open(a.seed))
            page.goto(base + "/index.html")
            page.evaluate("s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,typeof v==='string'?v:JSON.stringify(v))}", seed)
        for suite, tabs in PAGES.items():
            for tab in tabs:
                msgs.clear()
                page.goto(f"{base}/{suite}.html#{tab}")
                page.wait_for_timeout(1500 if suite != "structure-studio" else 3000)
                if suite != "control-center":
                    # errors inside the app frames
                    for f in page.frames[1:]:
                        try:
                            f.evaluate("1")
                        except Exception as e:
                            msgs.append(f"frame: {e}")
                if a.shots:
                    os.makedirs(a.shots, exist_ok=True)
                    page.screenshot(path=os.path.join(a.shots, f"{suite}-{tab}.png"))
                bad = [m for m in msgs if "net::ERR_FAILED" not in m and "Failed to load resource" not in m]
                print(f"{suite}#{tab}: {'OK' if not bad else 'PROBLEMS'}")
                for m in bad:
                    print("   ", m[:300])
                errors += bad
        b.close()
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
