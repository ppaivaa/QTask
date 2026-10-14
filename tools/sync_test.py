#!/usr/bin/env python3
"""End-to-end test of GitHub sync between two simulated devices, against an in-memory fake of the
GitHub contents API. Needs Playwright with Chromium.   python3 tools/sync_test.py"""
import base64, hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke import serve  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "ppaivaa/QTask-data"
TOKEN = "github_pat_test"


class FakeGitHub:
    def __init__(self):
        self.files = {}          # path -> (bytes, sha)
        self.commits = 0
        self.private = True

    def sha(self, b):
        return hashlib.sha1(b + str(time.time_ns()).encode()).hexdigest()

    def handle(self, route):
        req = route.request
        cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
                "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=cors)
        if req.headers.get("authorization") != "Bearer " + TOKEN:
            return route.fulfill(status=401, headers=cors, json={"message": "Bad credentials"})
        path = re.sub(r"^https://api\.github\.com", "", req.url).split("?")[0]
        m = re.match(r"^/repos/([^/]+)/([^/]+)(?:/contents/(.*))?$", path)
        if not m or f"{m.group(1)}/{m.group(2)}" != REPO:
            return route.fulfill(status=404, headers=cors, json={"message": "Not Found"})
        sub = m.group(3)
        if sub is None:
            return route.fulfill(status=200, headers=cors, json={"full_name": REPO, "private": self.private})
        from urllib.parse import unquote
        sub = unquote(sub)
        if req.method == "GET":
            if sub in self.files:
                body, sha = self.files[sub]
                if "raw" in (req.headers.get("accept") or ""):
                    return route.fulfill(status=200, headers=cors, body=body)
                return route.fulfill(status=200, headers=cors, json={"sha": sha, "content": base64.b64encode(body).decode()})
            kids = [p for p in self.files if p.startswith(sub.rstrip("/") + "/")]
            if not kids:
                return route.fulfill(status=404, headers=cors, json={"message": "Not Found"})
            return route.fulfill(status=200, headers=cors, json=[{"type": "file", "name": p.split("/")[-1], "path": p, "sha": self.files[p][1], "size": len(self.files[p][0])} for p in kids])
        if req.method == "PUT":
            data = json.loads(req.post_data or "{}")
            cur = self.files.get(sub)
            if cur and data.get("sha") != cur[1]:
                return route.fulfill(status=409 if data.get("sha") else 422, headers=cors, json={"message": "sha mismatch"})
            body = base64.b64decode(data["content"])
            sha = self.sha(body)
            self.files[sub] = (body, sha)
            self.commits += 1
            return route.fulfill(status=201 if not cur else 200, headers=cors, json={"content": {"sha": sha, "path": sub}})
        return route.fulfill(status=405, headers=cors, json={"message": "no"})

    def doc(self, key):
        b = self.files.get("data/" + key + ".json")
        return json.loads(b[0]) if b else None


def main():
    gh = FakeGitHub()
    seed = json.load(open(os.path.join(ROOT, "tools", "fixtures", "demo.json")))
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + msg)
        ok = ok and cond

    with serve(8792) as base, sync_playwright() as p:
        b = p.chromium.launch()

        def device(name, phone=False):
            ctx = b.new_context(**(dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True) if phone else {}))
            ctx.route("https://api.github.com/**", gh.handle)
            ctx.route(re.compile(r"^https://(?!api\.github\.com).*"), lambda r: r.abort())
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: print(f"   [{name}] pageerror: {e}"))
            pg.on("dialog", lambda d: d.accept())
            return ctx, pg

        def ls(pg, k):
            return pg.evaluate("k=>localStorage.getItem(k)", k)

        def setup_sync(pg, device_name, choose=None):
            pg.goto(base + "/control-center.html#backup")
            pg.wait_for_selector('#v-backup [data-op="sync-setup"]')
            pg.click('#v-backup [data-op="sync-setup"]')
            pg.fill("#syRepo", REPO)
            pg.fill("#syTok", TOKEN)
            pg.fill("#syDev", device_name)
            pg.click("#syGo")
            if choose:
                pg.wait_for_selector(f'input[name="syPref"][value="{choose}"]')
                pg.check(f'input[name="syPref"][value="{choose}"]')
                pg.click("#syGo")
            pg.wait_for_function("()=>!document.getElementById('dlg').open", timeout=15000)
            pg.wait_for_timeout(500)

        # ---------- device A: a Mac with data ----------
        ctxA, A = device("Mac")
        A.goto(base + "/suite-theme.js")
        A.evaluate("s=>{for(const [k,v] of Object.entries(s))localStorage.setItem(k,typeof v==='string'?v:JSON.stringify(v))}", seed)
        A.evaluate("()=>localStorage.setItem('net.openalexKey','SECRET-KEY')")
        setup_sync(A, "Mac")
        check(gh.doc("tasks.v1") is not None, "Mac uploaded tasks.v1 on the first sync")
        check(gh.doc("tasks.v1")["value"] == ls(A, "tasks.v1"), "uploaded tasks match the Mac's data exactly")
        names = sorted(f.split("/")[-1] for f in gh.files)
        check(not any("sync." in n or "openalexKey" in n for n in names), f"no token, sync state or OpenAlex key uploaded ({len(names)} files)")
        check(all(gh.doc(k)["device"] == "Mac" for k in ["tasks.v1", "researchlog.v1"]), "files record the device name")

        # ---------- device B: an iPhone, empty ----------
        ctxB, B = device("iPhone", phone=True)
        B.goto(base + "/control-center.html")
        B.wait_for_timeout(800)
        setup_sync(B, "iPhone")
        check(ls(B, "tasks.v1") == ls(A, "tasks.v1"), "iPhone received the tasks")
        check(ls(B, "researchlog.v1") == ls(A, "researchlog.v1"), "iPhone received the research log")
        check(ls(B, "net.openalexKey") is None, "OpenAlex key did not travel")
        B.goto(base + "/control-center.html#today")
        B.wait_for_timeout(1500)
        check("Rerun umbrella windows" in B.inner_text("#v-today"), "iPhone's Today shows the Mac's tasks")

        # ---------- a change on the iPhone, inside the Tasks app ----------
        B.goto(base + "/lab-notebook.html#tasks")
        B.wait_for_timeout(1500)
        fr = [f for f in B.frames if f.url == "about:srcdoc" and f.query_selector("#quick")][0]
        fr.fill("#quick", "Book the lab meeting room !")
        fr.press("#quick", "Enter")
        B.wait_for_timeout(9000)   # storage event -> sync a few seconds later
        doc = gh.doc("tasks.v1")
        check(doc and "Book the lab meeting room" in doc["value"] and doc["device"] == "iPhone", "the iPhone's new task reached GitHub on its own")

        # ---------- the Mac picks it up while the Tasks app is open ----------
        A.goto(base + "/lab-notebook.html#tasks")
        A.wait_for_timeout(2500)   # first sync runs 1.2 s after the page opens
        check("Book the lab meeting room" in (ls(A, "tasks.v1") or ""), "the Mac received the iPhone's task")
        A.wait_for_timeout(2500)
        frA = [f for f in A.frames if f.url == "about:srcdoc" and f.query_selector("#quick")][0]
        check("Book the lab meeting room" in frA.inner_text("#list"), "the open Tasks app on the Mac reloaded and shows it")

        # ---------- conflict: both change tasks.v1 before syncing ----------
        for pg, title in ((A, "Edited on the Mac"), (B, "Edited on the iPhone")):
            pg.goto(base + "/suite-theme.js")
            pg.evaluate("""t=>{const m=JSON.parse(localStorage.getItem('sync.github'));m.auto=false;localStorage.setItem('sync.github',JSON.stringify(m));
                const d=JSON.parse(localStorage.getItem('tasks.v1'));d.items[0].title=t;localStorage.setItem('tasks.v1',JSON.stringify(d))}""", title)
        A.goto(base + "/control-center.html#backup"); A.wait_for_timeout(600)
        A.evaluate("()=>SuiteSync.changed()"); A.wait_for_timeout(300)
        A.evaluate("()=>SuiteSync.syncNow()"); A.wait_for_timeout(1500)
        B.goto(base + "/control-center.html#backup"); B.wait_for_timeout(600)
        B.evaluate("()=>SuiteSync.changed()"); B.wait_for_timeout(300)
        st = B.evaluate("()=>SuiteSync.syncNow()"); B.wait_for_timeout(800)
        tb = json.loads(ls(B, "tasks.v1"))["items"][0]["title"]
        check(st["state"] == "ok", f"conflicting sync finished cleanly ({st['state']} {st.get('error','')})")
        check(tb == "Edited on the iPhone", "the newer edit (iPhone) won on the iPhone")
        conf = B.evaluate("()=>SuiteSync.conflicts()")
        check(len(conf) == 1 and conf[0]["key"] == "tasks.v1" and conf[0]["from"] == "Mac", "the Mac's version is kept under Versions replaced")
        B.reload(); B.wait_for_timeout(1200)
        check("versions replaced by a sync" in B.inner_text("#v-backup").lower(), "Backup view lists the replaced version")
        A.evaluate("()=>SuiteSync.syncNow()"); A.wait_for_timeout(1500)
        check(json.loads(ls(A, "tasks.v1"))["items"][0]["title"] == "Edited on the iPhone", "the Mac converged to the same data")

        # ---------- deleting a scheme travels as a removal ----------
        A.evaluate("()=>{localStorage.setItem('mech.s1',JSON.stringify({a:1}));localStorage.setItem('mech.index',JSON.stringify({s1:{name:'Test',updated:1}}))}")
        A.evaluate("()=>{SuiteSync.changed();return SuiteSync.syncNow()}"); A.wait_for_timeout(1500)
        B.evaluate("()=>SuiteSync.syncNow()"); B.wait_for_timeout(1500)
        check(ls(B, "mech.s1") is not None, "a new scheme reached the iPhone")
        A.evaluate("()=>localStorage.removeItem('mech.s1')")
        A.evaluate("()=>{SuiteSync.changed();return SuiteSync.syncNow()}"); A.wait_for_timeout(1500)
        B.evaluate("()=>SuiteSync.syncNow()"); B.wait_for_timeout(1500)
        check(ls(B, "mech.s1") is None, "deleting it on the Mac deleted it on the iPhone")

        # ---------- bad token and public repo ----------
        ctxC, C = device("Other")
        C.goto(base + "/control-center.html#backup"); C.wait_for_selector('#v-backup [data-op="sync-setup"]')
        C.click('#v-backup [data-op="sync-setup"]'); C.fill("#syRepo", REPO); C.fill("#syTok", "wrong"); C.click("#syGo")
        C.wait_for_timeout(1500)
        check("did not accept the token" in C.inner_text("#sheetHint"), "a wrong token is explained")
        gh.private = False
        C.fill("#syTok", TOKEN); C.click("#syGo"); C.wait_for_timeout(1500)
        check("public" in C.inner_text("#sheetHint"), "a public repository is refused")
        gh.private = True

        # ---------- backup file never holds secrets ----------
        A.goto(base + "/control-center.html#backup"); A.wait_for_timeout(800)
        with A.expect_download() as dl:
            A.click('[data-op="bundle"]'); A.click('#dlgBody button[type="submit"]')
        text = open(dl.value.path()).read()
        check("github_pat" not in text and "SECRET-KEY" not in text and "sync.meta" not in text, "the download has no token, key or sync state")
        check(json.loads(text)["format"] == "suite-bundle", "the download is a normal backup bundle")
        print(f"commits in the fake repository: {gh.commits}")
        b.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
