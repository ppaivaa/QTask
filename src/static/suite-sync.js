/* suite-sync.js: keeps the apps' data in step across devices (a Mac and an iPhone, say)
   through a private GitHub repository that only you can read.

   How it works
   - Every app keeps its data in this browser's localStorage under a few keys (TRACK_KEYS and
     TRACK_PREFIXES below). Each key is mirrored as one file, data/<key>.json, in the repository.
   - A sync lists that folder, downloads the files another device changed, uploads the keys this
     device changed, and remembers what it last saw (sync.meta) so it only moves what changed.
   - If the same key changed on both sides since the last sync, the most recent edit wins and the
     other version is kept on this device under sync.conflicts, from where the control center can
     bring it back. Every upload is a commit, so the repository history is a full backup too.
   - The token and the sync state are kept only on this device (sync.*). They are never synced
     and never written into backup files.

   The control center (Backup tab) sets it up; every suite page shows the state in its Backup sheet.
   Pages load this file once, at the top level; the app frames inside a suite never load it.

   Public API: window.SuiteSync = { configured, config, inspect, connect, disconnect, syncNow,
   changed, status, onStatus, pendingKeys, tracked, conflicts, restoreConflict, dropConflict } */
(function () {
  "use strict";
  if (window.top !== window || window.SuiteSync) return;

  var CFG_KEY = "sync.github", META_KEY = "sync.meta", LOCK_KEY = "sync.lock", CONF_KEY = "sync.conflicts";
  var TRACK_KEYS = ["researchlog.v1", "ideaboard.v1", "scriptplans.v1", "deadlines.v1", "tasks.v1",
    "litradar.v1", "citedash.v1", "structviewer.prefs", "controlcenter.v1", "suite.me", "net.mailto"];
  var TRACK_PREFIXES = ["mech."];
  /* the apps' "back up now" reminders: a good sync counts as a backup */
  var REMINDERS = ["research-log", "idea-board", "script-planner", "deadline-radar", "task-list", "lit-radar", "cite-dash"];
  var API = "https://api.github.com";
  var FORMAT = "qtask-sync";
  var ME = Math.random().toString(36).slice(2) + Date.now().toString(36);

  /* ---------- storage ---------- */
  var LS = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { localStorage.setItem(k, v); },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) { /* blocked */ } },
    json: function (k, fb) { try { var r = localStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch (e) { return fb; } },
    keys: function () { var out = []; try { for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k != null) out.push(k); } } catch (e) { /* blocked */ } return out; }
  };
  function tracked(k) {
    if (!k) return false;
    if (TRACK_KEYS.indexOf(k) >= 0) return true;
    for (var i = 0; i < TRACK_PREFIXES.length; i++) if (k.indexOf(TRACK_PREFIXES[i]) === 0) return true;
    return false;
  }
  function localKeys() { return LS.keys().filter(tracked); }
  function hash(s) {
    if (s == null) return "-";
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(36) + "." + s.length;
  }
  function cfg() {
    var c = LS.json(CFG_KEY, null);
    if (!c || typeof c !== "object" || !c.repo || !c.token) return null;
    if (!c.dir) c.dir = "data";
    if (!c.device) c.device = defaultDevice();
    if (c.auto === undefined) c.auto = true;
    return c;
  }
  function readMeta() {
    var m = LS.json(META_KEY, null);
    if (!m || typeof m !== "object") m = {};
    if (!m.keys || typeof m.keys !== "object") m.keys = {};
    return m;
  }
  function writeMeta(m) { try { LS.set(META_KEY, JSON.stringify(m)); } catch (e) { /* full: next sync redoes the work */ } }
  function defaultDevice() {
    var u = navigator.userAgent || "";
    if (/iPhone/.test(u)) return "iPhone";
    if (/iPad/.test(u) || (/Macintosh/.test(u) && navigator.maxTouchPoints > 1)) return "iPad";
    if (/Macintosh/.test(u)) return "Mac";
    if (/Android/.test(u)) return "Android";
    if (/Windows/.test(u)) return "Windows PC";
    return "Browser";
  }

  /* ---------- status ---------- */
  var ST = { state: "off", error: "", busy: false, pushed: 0, pulled: 0 };
  var listeners = [];
  function setStatus(state, error, extra) {
    ST.state = state; ST.error = error || "";
    if (extra) { ST.pushed = extra.pushed || 0; ST.pulled = extra.pulled || 0; }
    var m = readMeta();
    if (state === "error" || state === "offline") { m.err = ST.error; m.errAt = Date.now(); }
    else if (state === "ok") { m.err = ""; }
    writeMeta(m);
    fire();
  }
  function status() {
    var c = cfg(), m = readMeta();
    return { configured: !!c, state: c ? ST.state === "off" ? "idle" : ST.state : "off", busy: ST.busy,
      last: m.last || 0, error: ST.error || m.err || "", repo: c ? c.repo : "", device: c ? c.device : "",
      auto: c ? c.auto !== false : false, pending: c ? pendingKeys().length : 0, pushed: ST.pushed, pulled: ST.pulled,
      conflicts: conflicts().length };
  }
  function fire() { var s = status(); for (var i = 0; i < listeners.length; i++) { try { listeners[i](s); } catch (e) { /* keep going */ } } }

  /* ---------- GitHub ---------- */
  function err(msg, code, offline) { var e = new Error(msg); e.code = code || ""; e.offline = !!offline; return e; }
  async function gh(c, method, path, body, accept) {
    var ctl = new AbortController(), t = setTimeout(function () { ctl.abort(); }, 30000), r;
    var headers = { "Accept": accept || "application/vnd.github+json", "Authorization": "Bearer " + c.token };
    if (body) headers["Content-Type"] = "application/json";
    try {
      r = await fetch(API + path, { method: method, cache: "no-store", signal: ctl.signal, headers: headers,
        body: body ? JSON.stringify(body) : undefined });
    } catch (e) {
      throw err(e && e.name === "AbortError" ? "GitHub did not answer in time" : "No connection to GitHub", "net", true);
    } finally { clearTimeout(t); }
    return r;
  }
  async function fail(r, what) {
    var j = {}; try { j = await r.json(); } catch (e) { /* not JSON */ }
    var m = (j && j.message) || "";
    if (r.status === 401) return err("GitHub did not accept the token. It may have expired: make a new one and connect again.", "auth");
    if (r.status === 403) {
      if (r.headers.get("x-ratelimit-remaining") === "0") return err("GitHub's hourly request limit is used up. Sync will try again later.", "rate");
      return err("The token can't " + (what || "change") + " this repository. Give it Contents: read and write for the data repository.", "perm");
    }
    if (r.status === 404) return err("Repository not found, or the token can't see it. Check the name and that the token includes this repository.", "missing");
    if (r.status === 409 || r.status === 422) return err("Changed on another device at the same moment", "conflict");
    return err("GitHub answered " + r.status + (m ? ": " + m : ""), "http");
  }
  function repoPath(c) { return "/repos/" + c.repo.split("/").map(encodeURIComponent).join("/"); }
  function fileName(k) { return encodeURIComponent(k) + ".json"; }
  function keyOf(name) { try { return decodeURIComponent(name.replace(/\.json$/, "")); } catch (e) { return null; } }
  function filePath(c, name) { return repoPath(c) + "/contents/" + c.dir.split("/").map(encodeURIComponent).join("/") + "/" + encodeURIComponent(name); }
  function b64(str) {
    var bytes = new TextEncoder().encode(str), bin = "";
    for (var i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }
  async function listRemote(c) {
    var r = await gh(c, "GET", repoPath(c) + "/contents/" + c.dir.split("/").map(encodeURIComponent).join("/"));
    if (r.status === 404) {
      /* empty repository or no data folder yet, unless the repository itself is missing */
      var rr = await gh(c, "GET", repoPath(c));
      if (!rr.ok) throw await fail(rr, "read");
      return {};
    }
    if (!r.ok) throw await fail(r, "read");
    var list = await r.json(), out = {};
    if (!Array.isArray(list)) throw err("The data folder in the repository is not a folder", "shape");
    list.forEach(function (f) {
      if (!f || f.type !== "file" || !/\.json$/.test(f.name)) return;
      var k = keyOf(f.name);
      if (k && tracked(k)) out[k] = { sha: f.sha, name: f.name, size: f.size };
    });
    return out;
  }
  async function fetchDoc(c, k, r) {
    var res = await gh(c, "GET", filePath(c, r.name), null, "application/vnd.github.raw+json");
    if (!res.ok) throw await fail(res, "read");
    var doc; try { doc = JSON.parse(await res.text()); } catch (e) { throw err("A file in the repository is damaged: " + r.name, "shape"); }
    if (!doc || doc.format !== FORMAT || doc.key !== k) throw err("A file in the repository is not sync data: " + r.name, "shape");
    return doc;
  }
  async function pushDoc(c, k, value, sha) {
    var doc = { format: FORMAT, version: 1, key: k, updated: Date.now(), device: c.device, deleted: value == null };
    if (value != null) doc.value = value;
    var body = { message: (value == null ? "Remove " : "Update ") + k + " from " + c.device, content: b64(JSON.stringify(doc)) };
    if (sha) body.sha = sha;
    var r = await gh(c, "PUT", filePath(c, fileName(k)), body);
    if (!r.ok) throw await fail(r, "write to");
    var j = await r.json();
    return j && j.content && j.content.sha;
  }
  function applyDoc(k, doc) {
    if (doc.deleted) { LS.del(k); return null; }
    var v = String(doc.value);
    LS.set(k, v);
    return v;
  }

  /* ---------- a lock so that two open tabs never sync at the same time ---------- */
  function lock() {
    try {
      var l = JSON.parse(localStorage.getItem(LOCK_KEY) || "null");
      if (l && l.id !== ME && Date.now() - l.t < 90000) return false;
      localStorage.setItem(LOCK_KEY, JSON.stringify({ id: ME, t: Date.now() }));
      return JSON.parse(localStorage.getItem(LOCK_KEY)).id === ME;
    } catch (e) { return true; }
  }
  function unlock() {
    try { var l = JSON.parse(localStorage.getItem(LOCK_KEY) || "null"); if (l && l.id === ME) localStorage.removeItem(LOCK_KEY); } catch (e) { /* ignore */ }
  }

  /* ---------- versions replaced by a sync ---------- */
  function conflicts() { var l = LS.json(CONF_KEY, []); return Array.isArray(l) ? l : []; }
  function keepConflict(k, value, from, t) {
    var l = conflicts();
    l.unshift({ k: k, v: value, from: from, t: t || 0, at: Date.now() });
    while (l.length) {
      l = l.slice(0, 15);
      try { LS.set(CONF_KEY, JSON.stringify(l)); return; } catch (e) { l.pop(); if (!l.length) return; }
    }
  }
  function restoreConflict(i) {
    var l = conflicts(), c = l[i]; if (!c) return false;
    try { if (c.v == null) LS.del(c.k); else LS.set(c.k, c.v); } catch (e) { return false; }
    l.splice(i, 1); try { LS.set(CONF_KEY, JSON.stringify(l)); } catch (e) { /* ignore */ }
    announce([c.k]); changed(); fire();
    return true;
  }
  function dropConflict(i) {
    var l = conflicts(); l.splice(i, 1);
    try { l.length ? LS.set(CONF_KEY, JSON.stringify(l)) : LS.del(CONF_KEY); } catch (e) { /* ignore */ }
    fire();
  }

  /* ---------- noticing local changes ---------- */
  function pendingKeys() {
    var m = readMeta(), out = [], seen = {};
    localKeys().concat(Object.keys(m.keys)).forEach(function (k) {
      if (seen[k] || !tracked(k)) return; seen[k] = 1;
      if (hash(LS.get(k)) !== ((m.keys[k] || {}).h || "-")) out.push(k);
    });
    return out;
  }
  /* note when each key first differed from the synced copy: that time decides conflicts */
  function tick() {
    if (!cfg() || running) return 0;
    var m = readMeta(), now = Date.now(), dirty = false, keys = pendingKeys();
    keys.forEach(function (k) {
      var e = m.keys[k] || {}, h = hash(LS.get(k));
      if (e.ph !== h) { e.ph = h; e.lt = now; m.keys[k] = e; dirty = true; }
    });
    if (dirty) writeMeta(m);
    return keys.length;
  }
  function announce(keys) {
    try { window.dispatchEvent(new CustomEvent("suite-sync-applied", { detail: { keys: keys } })); } catch (e) { /* old browser */ }
  }
  function markBackedUp() {
    var now = String(Date.now());
    REMINDERS.forEach(function (r) { try { LS.set(r + ".lastBackup", now); LS.set(r + ".backupSnooze", "0"); } catch (e) { /* full */ } });
  }

  /* ---------- one sync ---------- */
  var running = false, again = false, timer = null;
  function schedule(ms) {
    var c = cfg(); if (!c || c.auto === false) return;
    clearTimeout(timer); timer = setTimeout(function () { run(); }, ms);
  }
  async function run(opts) {
    opts = opts || {};
    var c = cfg();
    if (!c) { setStatus("off"); return status(); }
    if (running) { again = true; return status(); }
    if (navigator.onLine === false) { setStatus("offline", "Offline. Changes will sync when you are back online."); return status(); }
    if (!lock()) { schedule(20000); return status(); }
    running = true; ST.busy = true; fire();
    var applied = [], pushed = 0, pulled = 0, retry = false;
    try {
      var meta = readMeta(), remote = await listRemote(c);
      var all = {}; localKeys().concat(Object.keys(remote), Object.keys(meta.keys)).forEach(function (k) { all[k] = 1; });
      for (var k in all) {
        if (!tracked(k)) continue;
        var lv = LS.get(k), lh = hash(lv), m = meta.keys[k] || {}, r = remote[k] || null;
        var lc = lh !== (m.h || "-"), rc = (r ? r.sha : null) !== (m.sha || null);
        if (!lc && !rc) continue;
        try {
          if (rc && !lc) {
            if (!r) {                                   /* the file went away on GitHub: put it back */
              if (lv == null) { delete meta.keys[k]; continue; }
              meta.keys[k] = { sha: await pushDoc(c, k, lv, null), h: lh }; pushed++;
            } else {
              var nv = applyDoc(k, await fetchDoc(c, k, r)); applied.push(k); pulled++;
              meta.keys[k] = { sha: r.sha, h: hash(nv) };
            }
          } else if (lc && !rc) {
            if (lv == null && !r) { delete meta.keys[k]; continue; }
            meta.keys[k] = { sha: await pushDoc(c, k, lv, r ? r.sha : null), h: lh }; pushed++;
          } else {
            var doc = r ? await fetchDoc(c, k, r) : null, rv = doc && !doc.deleted ? String(doc.value) : null;
            if (hash(rv) === lh) { if (r) meta.keys[k] = { sha: r.sha, h: lh }; else delete meta.keys[k]; continue; }
            var localWins = opts.prefer === "local" ? true : opts.prefer === "remote" ? false
              : (m.lt || 0) >= ((doc && doc.updated) || 0);
            if (localWins) {
              if (rv != null) keepConflict(k, rv, (doc && doc.device) || "another device", doc && doc.updated);
              meta.keys[k] = { sha: await pushDoc(c, k, lv, r ? r.sha : null), h: lh }; pushed++;
            } else {
              if (lv != null) keepConflict(k, lv, "this device", m.lt || Date.now());
              var nv2 = applyDoc(k, doc); applied.push(k); pulled++;
              meta.keys[k] = { sha: r.sha, h: hash(nv2) };
            }
          }
        } catch (e) {
          if (e.code === "conflict") { retry = true; continue; }
          throw e;
        } finally {
          writeMeta(meta);
          try { localStorage.setItem(LOCK_KEY, JSON.stringify({ id: ME, t: Date.now() })); } catch (e) { /* ignore */ }
        }
      }
      meta = readMeta(); meta.last = Date.now(); meta.err = ""; writeMeta(meta);
      markBackedUp();
      setStatus("ok", "", { pushed: pushed, pulled: pulled });
    } catch (e) {
      setStatus(e.offline ? "offline" : "error", (e && e.message) || String(e));
    } finally {
      running = false; ST.busy = false; unlock();
      if (applied.length) announce(applied);
      fire();
      if (retry && !opts.retried) setTimeout(function () { run({ retried: true }); }, 1500);
      else if (again) { again = false; schedule(1500); }
    }
    return status();
  }

  /* ---------- setting up ---------- */
  function cleanRepo(s) {
    s = String(s || "").trim().replace(/^https?:\/\/github\.com\//i, "").replace(/\.git$/i, "").replace(/\/+$/, "");
    return /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/.test(s) ? s : "";
  }
  /* check the repository and the token without saving anything */
  async function inspect(repo, token, dir) {
    repo = cleanRepo(repo); token = String(token || "").trim();
    if (!repo) throw err("Write the repository as owner/name, for example ppaivaa/QTask-data.", "input");
    if (!token) throw err("Paste the token from GitHub.", "input");
    var c = { repo: repo, token: token, dir: (dir || "data").replace(/^\/+|\/+$/g, "") || "data" };
    var r = await gh(c, "GET", repoPath(c));
    if (!r.ok) throw await fail(r, "read");
    var j = await r.json();
    var remote = await listRemote(c);
    return { repo: j.full_name || repo, private: !!j.private, remoteKeys: Object.keys(remote).length, localKeys: localKeys().length, dir: c.dir };
  }
  /* save the settings and run the first sync; prefer: "remote" | "local" when both sides have data */
  async function connect(o) {
    var repo = cleanRepo(o.repo);
    if (!repo || !o.token) throw err("Repository and token are needed", "input");
    var c = { repo: repo, token: String(o.token).trim(), dir: o.dir || "data", device: (o.device || "").trim() || defaultDevice(), auto: true, since: Date.now() };
    LS.set(CFG_KEY, JSON.stringify(c));
    LS.del(META_KEY);
    fire();
    return run({ prefer: o.prefer || "remote" });
  }
  function disconnect() { LS.del(CFG_KEY); LS.del(META_KEY); LS.del(LOCK_KEY); clearTimeout(timer); setStatus("off"); }
  function update(patch) {
    var c = cfg(); if (!c) return;
    for (var k in patch) if (Object.prototype.hasOwnProperty.call(patch, k)) c[k] = patch[k];
    try { LS.set(CFG_KEY, JSON.stringify(c)); } catch (e) { /* ignore */ }
    fire();
  }
  function config() { var c = cfg(); if (!c) return null; return { repo: c.repo, dir: c.dir, device: c.device, auto: c.auto !== false, since: c.since || 0 }; }
  function changed() { if (tick()) schedule(3000); fire(); }

  window.SuiteSync = { configured: function () { return !!cfg(); }, config: config, inspect: inspect, connect: connect,
    disconnect: disconnect, update: update, syncNow: function () { return run({ manual: true }); }, changed: changed,
    status: status, onStatus: function (f) { listeners.push(f); }, pendingKeys: pendingKeys, tracked: tracked,
    conflicts: function () { return conflicts().map(function (c, i) { return { i: i, key: c.k, from: c.from, t: c.t, at: c.at, size: c.v == null ? 0 : c.v.length }; }); },
    restoreConflict: restoreConflict, dropConflict: dropConflict, cleanRepo: cleanRepo, defaultDevice: defaultDevice };

  /* ---------- when to sync ---------- */
  window.addEventListener("storage", function (e) {
    if (e.key === CFG_KEY) { fire(); return; }
    if (e.key == null || tracked(e.key)) { if (tick()) schedule(4000); fire(); }
  });
  document.addEventListener("visibilitychange", function () {
    var c = cfg(); if (!c || c.auto === false) return;
    if (document.hidden) { if (tick()) run(); }
    else if (Date.now() - (readMeta().last || 0) > 30000) run();
  });
  window.addEventListener("online", function () { var c = cfg(); if (c && c.auto !== false) run(); });
  setInterval(function () { if (!document.hidden && tick()) schedule(2000); }, 15000);
  setInterval(function () { var c = cfg(); if (c && c.auto !== false && !document.hidden) run(); }, 180000);
  setTimeout(function () { var c = cfg(); if (c && c.auto !== false) run(); else fire(); }, 1200);
})();
