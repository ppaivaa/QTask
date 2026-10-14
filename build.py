#!/usr/bin/env python3
"""Build the web app into dist/.

Each suite page is a shell (src/suites/<suite>/shell.html) that carries its apps as
complete HTML documents in `const APPS=[...]`; the shell shows each app in its own frame.
This script puts the apps (src/suites/<suite>/apps/<id>.html) and the shared libraries
(src/suites/<suite>/shared/<NAME>.js) into the shells, replaces the {{APP_NAME}} style
placeholders everywhere and copies the static files.

    python3 build.py            # writes dist/
    python3 build.py --serve    # builds, then serves dist/ on http://127.0.0.1:8765

To rename the app, change NAME below (or pass --name "New name") and rebuild.
"""
import argparse, http.server, json, os, re, shutil, socketserver, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")

NAME = "LabKit"                      # working name, decided later
SHORT = "LabKit"
TAGLINE = "Your research day in one place"
VERSION = "1.0.0"

# suite id -> (title, [(app id, label)]) in the order of the bottom bar
SUITES = {
    "control-center": ("Control center", []),
    "lab-notebook": ("Lab notebook", [("log", "Log"), ("tasks", "Tasks"), ("ideas", "Ideas"),
                                      ("plans", "Script plans"), ("deadlines", "Deadlines")]),
    "literature-hub": ("Literature hub", [("radar", "Radar"), ("citations", "Citations")]),
    "structure-studio": ("Structure studio", [("viewer", "Viewer")]),
    "paper-kit": ("Paper kit", [("plots", "Plot guide"), ("schemes", "Schemes")]),
}

# bottom-bar icons (24x24, stroked)
ICONS = {
    "log": '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/><path d="M9 8h6"/>',
    "tasks": '<path d="M10 6h10M10 12h10M10 18h10"/><path d="M3.5 6l1.5 1.5L7.5 5"/><path d="M3.5 12l1.5 1.5L7.5 11"/><path d="M3.5 18l1.5 1.5L7.5 17"/>',
    "ideas": '<path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "plans": '<rect x="3" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="16" width="7" height="5" rx="1.5"/><path d="M6.5 8v5a3 3 0 0 0 3 3H14"/>',
    "deadlines": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M12 14v3l2 1"/>',
    "radar": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12l6-6"/><circle cx="12" cy="12" r="1"/>',
    "citations": '<path d="M7 7h4v4c0 3-1.5 5-4 6"/><path d="M14 7h4v4c0 3-1.5 5-4 6"/>',
    "viewer": '<circle cx="6" cy="17" r="2.5"/><circle cx="18" cy="17" r="2.5"/><circle cx="12" cy="6" r="2.5"/><path d="M8 15.5l2.8-7.3M16 15.5l-2.8-7.3M8.5 17h7"/>',
    "plots": '<path d="M4 20V4"/><path d="M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
    "schemes": '<path d="M5 17c0-6 4-10 11-10"/><path d="M13 4l3 3-3 3"/><circle cx="5" cy="19" r="1.5"/>',
}

# what each app keeps in localStorage (mirrors SUITES in the control center)
def _app(aid, file, label, keys=(), prefixes=(), reminder=""):
    return {"id": aid, "file": file, "label": label, "keys": list(keys), "prefixes": list(prefixes), "reminder": reminder}

BACKUP = {
    "lab-notebook": [_app("log", "research-log", "Log", ["researchlog.v1"], reminder="research-log"),
                     _app("tasks", "task-list", "Tasks", ["tasks.v1"], reminder="task-list"),
                     _app("ideas", "idea-board", "Ideas", ["ideaboard.v1"], reminder="idea-board"),
                     _app("plans", "script-planner", "Script plans", ["scriptplans.v1"], reminder="script-planner"),
                     _app("deadlines", "deadline-tracker", "Deadlines", ["deadlines.v1"], reminder="deadline-radar")],
    "literature-hub": [_app("radar", "literature-radar", "Radar", ["litradar.v1", "net.mailto"], reminder="lit-radar"),
                       _app("citations", "citation-tracker", "Citations", ["citedash.v1", "net.mailto"], reminder="cite-dash")],
    "structure-studio": [_app("viewer", "structure-viewer", "Viewer", ["structviewer.prefs"])],
    "paper-kit": [_app("schemes", "mechanism-scheme-editor", "Schemes", prefixes=["mech."])],
}
# apps reloaded when their data changes elsewhere (another tab, the control center, another device)
LIVE = {
    "lab-notebook": {"log": ["researchlog.v1"], "tasks": ["tasks.v1"], "ideas": ["ideaboard.v1"],
                     "plans": ["scriptplans.v1"], "deadlines": ["deadlines.v1"]},
    "literature-hub": {"radar": ["litradar.v1"], "citations": ["citedash.v1"]},
    "structure-studio": {},
    "paper-kit": {"schemes": ["mech."]},
}
# control-center links can open an app on one tab or filter: ?pick=NAME
PICKS = {
    "lab-notebook": {"log": {"actions": '#tabs [data-tab="actions"]', "meetings": '#tabs [data-tab="meetings"]'},
                     "ideas": {s: f'#tabs [data-stage="{s}"]' for s in ("spark", "explore", "doing", "done")},
                     "deadlines": {"done": "#showDone"},
                     "tasks": {s: f'#chips [data-f="{s}"]' for s in ("today", "upcoming", "someday", "all", "done")}},
}


def suite_shell(sid, title, apps, ctx):
    with open(os.path.join(SRC, "suites", "_suite-shell.html"), encoding="utf-8") as fh:
        shell = fh.read()
    with open(os.path.join(SRC, "suites", "_suite-backup.html"), encoding="utf-8") as fh:
        backup = fh.read()
    nav = "\n".join(
        f'  <button type="button" data-id="{aid}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[aid]}</svg></span><span class="lb">{label}</span></button>'
        for aid, label in apps)
    live = {aid: {"keys": [k for k in ks if not k.endswith(".")], "prefixes": [k for k in ks if k.endswith(".")]}
            for aid, ks in LIVE.get(sid, {}).items()}
    local = {"SUITE_ID": sid, "SUITE_TITLE": title, "NAV_BUTTONS": nav, "BACKUP_BLOCK": backup,
             "BACKUP_APPS": json.dumps(BACKUP.get(sid, [])), "SYNC_DEFS": json.dumps(live),
             "SEARCH_DEFS": "{}", "PICKS": json.dumps(PICKS.get(sid, {}))}
    shell = shell.replace("{{BACKUP_BLOCK}}", backup)
    return subst(subst(shell, local), ctx)


def subst(text, ctx):
    for k, v in ctx.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def js_literal(value):
    """JSON for a <script>: no '</script>' or '<!--' can appear inside it."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def build(out, ctx):
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    # static files
    st = os.path.join(SRC, "static")
    for dirpath, _, files in os.walk(st):
        rel = os.path.relpath(dirpath, st)
        os.makedirs(os.path.join(out, rel), exist_ok=True)
        for f in files:
            src_f, dst_f = os.path.join(dirpath, f), os.path.join(out, rel, f)
            if f.endswith((".js", ".html", ".webmanifest", ".md", ".txt", ".json", ".css")):
                with open(src_f, encoding="utf-8") as fh:
                    text = subst(fh.read(), ctx)
                with open(dst_f, "w", encoding="utf-8") as fh:
                    fh.write(text)
            else:
                shutil.copy2(src_f, dst_f)
    # suites
    for sid, (title, apps) in SUITES.items():
        d = os.path.join(SRC, "suites", sid)
        own = os.path.join(d, "shell.html")
        if os.path.exists(own):
            with open(own, encoding="utf-8") as fh:
                shell = subst(fh.read(), ctx)
        else:
            shell = suite_shell(sid, title, apps, ctx)
        app_list = []
        for aid, label in apps:
            with open(os.path.join(d, "apps", aid + ".html"), encoding="utf-8") as fh:
                app_list.append({"id": aid, "label": label, "html": subst(fh.read(), ctx)})
        shared = {}
        sd = os.path.join(d, "shared")
        if os.path.isdir(sd):
            for f in sorted(os.listdir(sd)):
                with open(os.path.join(sd, f), encoding="utf-8") as fh:
                    shared[os.path.splitext(f)[0]] = fh.read()
        if "/*APPS*/[]" in shell:
            shell = shell.replace("/*APPS*/[]", js_literal(app_list), 1)
        elif app_list:
            sys.exit(f"{sid}: shell has no /*APPS*/[] placeholder")
        if "/*SHARED*/{}" in shell:
            shell = shell.replace("/*SHARED*/{}", js_literal(shared), 1)
        left = re.findall(r"\{\{[A-Z_]+\}\}", shell)
        if left:
            sys.exit(f"{sid}: unreplaced placeholders {sorted(set(left))}")
        with open(os.path.join(out, sid + ".html"), "w", encoding="utf-8") as fh:
            fh.write(shell)
        print(f"  {sid}.html  {len(shell)/1024:.0f} KB, apps: {', '.join(a for a, _ in apps) or '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    ctx = {"APP_NAME": a.name, "APP_SHORT": a.name if a.name != NAME else SHORT,
           "APP_TAGLINE": TAGLINE, "APP_VERSION": VERSION}
    print(f"Building {a.name} {VERSION} into {a.out}")
    build(a.out, ctx)
    if a.serve:
        os.chdir(a.out)
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("127.0.0.1", a.port), handler) as httpd:
            print(f"Serving on http://127.0.0.1:{a.port}/control-center.html (Ctrl+C to stop)")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
