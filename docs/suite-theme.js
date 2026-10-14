/* suite-theme.js: colour schemes shared by the control center, every suite and every app in it.
   (From CompChemKit by A. R. V. Pinto, MIT licence; the iPhone file sharing below was added for QTask.)

   The choice is kept in this browser as localStorage "suite.theme":
     {"mode": "dark" | "light" | "system", "palette": "orchid" | "ocean" | "forest" | "ember" | "graphite"}
   It is set from the control center (Settings) and applied live to every open page.

   Every page loads this file at the top of <head>. It defines CSS custom properties named --t-*;
   the pages use them with their original colours as fallbacks (patch_suites.py writes those
   var(--t-name, #original) references), so a page opened without this file keeps the built-in
   dark look. To add a palette, copy one entry of PALETTES and change its colours.

   Inside the Android app (which provides window.SuitesAndroid) this file also sends the files the
   apps download to the phone's Download folder, copies text through the app and colours the
   system bars to match. */
(function () {
  "use strict";
  var KEY = "suite.theme";
  var DEF = { mode: "dark", palette: "ocean" };

  /* surfaces, text and status colours, shared by every palette */
  var NEUTRAL = {
    dark: {
      bg: "#000000", surface: "#131316", raised: "#1D1D22", raised2: "#26262C", field: "#0F0F12",
      line: "#2E2E35", faint: "#28282E", edge: "#3B3B43", ink: "#F2F2F4", muted: "#9D9DA5", dim: "#7A7A83",
      knob: "#F2F2F4", fab: "#17171C", "on-grad": "#17161C", "on-accent": "#14161B",
      pinbg: "#2A2413", "danger-soft": "#3A1A1A", "info-bg": "#12141B", "info-line": "#232838", track: "#2A2A31",
      danger: "#EF5A50", red: "#F28B82", gold: "#E6C170", green: "#7DCB9C", violet: "#C3A6F0", pink: "#EE93AF",
      teal: "#8CC3CC", sky: "#A6CCF5", blue: "#9DB2FF",
      backdrop: "rgba(0,0,0,.6)", shadow: "rgba(0,0,0,.45)", glass: "rgba(19,19,22,.9)",
      "mol-cartoon": "#4A4A55", "mol-ctx": "#8A8A94", "mol-h": "#E8E8EC", viewer: "#000000"
    },
    light: {
      bg: "#F4F3F7", surface: "#FFFFFF", raised: "#FFFFFF", raised2: "#EAE8EF", field: "#F0EEF4",
      line: "#DCD8E3", faint: "#E7E4EC", edge: "#C5C0CE", ink: "#1D1B22", muted: "#5D5967", dim: "#706C7A",
      knob: "#FFFFFF", fab: "#FFFFFF", "on-grad": "#1D1B22", "on-accent": "#FFFFFF",
      pinbg: "#FBF1D6", "danger-soft": "#FCE4E2", "info-bg": "#EDF1FA", "info-line": "#D3DBEE", track: "#E2DFE8",
      danger: "#C42F26", red: "#B42318", gold: "#8A6300", green: "#1E7A47", violet: "#6942B4", pink: "#AD3466",
      teal: "#22707B", sky: "#2A68A6", blue: "#3553C6",
      backdrop: "rgba(25,22,32,.38)", shadow: "rgba(25,22,32,.16)", glass: "rgba(255,255,255,.92)",
      "mol-cartoon": "#A7A3B3", "mol-ctx": "#6A6676", "mol-h": "#CFCBD8", viewer: "#FFFFFF"
    }
  };

  /* accent colours. grad1-3: the gradient behind selected buttons (text on it uses on-grad);
     accent and accent2: links and highlighted text, so they keep good contrast on the page;
     head to headbar: the tinted band at the top of each page and the browser's theme colour;
     headicon: the tile behind the suite icons, dark in both modes so the pastel icons stay visible */
  var PALETTES = {
    orchid: { name: "Orchid",
      dark:  { grad1: "#F0A8DC", grad2: "#C9B6EF", grad3: "#A6CCF5", accent: "#EBA8E4", accent2: "#A7CBF4", focus: "#9C8BC0",
               "accent-soft": "#35263A", "fab-ink": "#D9B9EE", head: "#5A4360", head2: "#352C3F", head3: "#15121A", headbar: "#2A2432", headicon: "#241E2B" },
      light: { grad1: "#EE9AD5", grad2: "#BEA5EE", grad3: "#94BFF2", accent: "#A23A98", accent2: "#2F6CAE", focus: "#8E6BB8",
               "accent-soft": "#F6E2F2", "fab-ink": "#A23A98", head: "#E7D5EE", head2: "#EFE5F3", head3: "#F3EEF6", headbar: "#EADCF0", headicon: "#241E2B" } },
    ocean: { name: "Ocean",
      dark:  { grad1: "#8EE3D8", grad2: "#8FC9F4", grad3: "#A7B5F7", accent: "#8CCBF2", accent2: "#8EE3D8", focus: "#6E9CC2",
               "accent-soft": "#18303F", "fab-ink": "#A9D7F6", head: "#24475F", head2: "#1A3142", head3: "#0C151C", headbar: "#1D2E3B", headicon: "#182630" },
      light: { grad1: "#7FDCCF", grad2: "#86C1F0", grad3: "#9FAEF5", accent: "#1D6FA6", accent2: "#0E726D", focus: "#4C86B8",
               "accent-soft": "#DFEDF8", "fab-ink": "#1D6FA6", head: "#D3E6F2", head2: "#E3EFF6", head3: "#EDF3F8", headbar: "#D9E9F3", headicon: "#182630" } },
    forest: { name: "Forest",
      dark:  { grad1: "#C4E59A", grad2: "#92D7AE", grad3: "#7FC8C8", accent: "#9FDBB0", accent2: "#C4E59A", focus: "#7DAA8C",
               "accent-soft": "#1B3326", "fab-ink": "#B8E6C6", head: "#2C4D3C", head2: "#1F362B", head3: "#0E1913", headbar: "#213229", headicon: "#1A2820" },
      light: { grad1: "#B7DE86", grad2: "#83D0A2", grad3: "#6FC0C0", accent: "#2C7A4D", accent2: "#4D6E12", focus: "#4E946A",
               "accent-soft": "#E0F1E6", "fab-ink": "#2C7A4D", head: "#D6EADC", head2: "#E4F1E8", head3: "#EDF5EF", headbar: "#DCEDE1", headicon: "#1A2820" } },
    ember: { name: "Ember",
      dark:  { grad1: "#FAD08A", grad2: "#F6A88C", grad3: "#EE91AE", accent: "#F6B48C", accent2: "#FAD08A", focus: "#C08D6B",
               "accent-soft": "#3B2419", "fab-ink": "#F8CCA8", head: "#5B3727", head2: "#3C261C", head3: "#19100C", headbar: "#33241D", headicon: "#2B1E18" },
      light: { grad1: "#F9C576", grad2: "#F59A7E", grad3: "#EC84A3", accent: "#AF4E1C", accent2: "#8F5D00", focus: "#C0703F",
               "accent-soft": "#FBE6DA", "fab-ink": "#AF4E1C", head: "#F4DFD3", head2: "#F7E9E1", head3: "#F8F0EB", headbar: "#F3E2D8", headicon: "#2B1E18" } },
    graphite: { name: "Graphite",
      dark:  { grad1: "#E6E7EC", grad2: "#C9CCD5", grad3: "#AEB4C1", accent: "#C5CAD6", accent2: "#A9BCD8", focus: "#8C92A0",
               "accent-soft": "#2A2C33", "fab-ink": "#D8DBE3", head: "#3A3C44", head2: "#26272D", head3: "#111215", headbar: "#26272C", headicon: "#1F2024" },
      light: { grad1: "#DDDFE5", grad2: "#C3C7D0", grad3: "#A9AFBC", accent: "#3F4655", accent2: "#3B5A88", focus: "#6B7280",
               "accent-soft": "#E6E7EC", "fab-ink": "#3F4655", head: "#E1E2E7", head2: "#EAEBEE", head3: "#F0F0F3", headbar: "#E4E5E9", headicon: "#1F2024" } }
  };

  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
  var droid = window.SuitesAndroid || null;
  function read() {
    try {
      var v = JSON.parse(localStorage.getItem(KEY) || "null");
      if (v && typeof v === "object") {
        return { mode: /^(dark|light|system)$/.test(v.mode) ? v.mode : DEF.mode,
                 palette: Object.prototype.hasOwnProperty.call(PALETTES, v.palette) ? v.palette : DEF.palette };
      }
    } catch (e) { /* storage blocked: built-in look */ }
    return { mode: DEF.mode, palette: DEF.palette };
  }
  function resolve(t) { return t.mode === "system" ? (mq && mq.matches ? "light" : "dark") : t.mode; }
  function tokens(t) {
    var m = resolve(t), p = PALETTES[t.palette] || PALETTES[DEF.palette], out = {}, k;
    for (k in NEUTRAL[m]) out[k] = NEUTRAL[m][k];
    for (k in p[m]) out[k] = p[m][k];
    return out;
  }
  function css(t) {
    var tk = tokens(t), parts = [], k;
    for (k in tk) parts.push("--t-" + k + ":" + tk[k]);
    return "html:root{color-scheme:" + resolve(t) + ";" + parts.join(";") + "}";
  }
  function apply(doc, t) {
    doc = doc || document; t = t || read();
    var m = resolve(t), el = doc.getElementById("suite-theme"), c = css(t), root = doc.documentElement;
    if (!el) { el = doc.createElement("style"); el.id = "suite-theme"; (doc.head || root).appendChild(el); }
    if (el.textContent !== c) el.textContent = c;
    if (root.getAttribute("data-theme") !== m) root.setAttribute("data-theme", m);
    if (root.getAttribute("data-palette") !== t.palette) root.setAttribute("data-palette", t.palette);
    var tc = doc.querySelector('meta[name="theme-color"]'); if (tc) tc.setAttribute("content", tokens(t).head);
    var cs = doc.querySelector('meta[name="color-scheme"]'); if (cs) cs.setAttribute("content", m);
    if (droid && doc === document && window.top === window) {
      var tk = tokens(t);
      try { droid.setBars(tk.head, tk.bg, m === "light"); } catch (e) { /* older app version */ }
    }
  }
  var listeners = [];
  function fire(v) { for (var i = 0; i < listeners.length; i++) { try { listeners[i](v); } catch (e) { /* keep going */ } } }
  function set(t) {
    var v = { mode: /^(dark|light|system)$/.test(t.mode) ? t.mode : DEF.mode, palette: PALETTES[t.palette] ? t.palette : DEF.palette };
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { /* applies to this page only */ }
    apply(document, v); fire(v);
    return v;
  }

  window.SuiteTheme = { KEY: KEY, DEFAULT: DEF, NEUTRAL: NEUTRAL, PALETTES: PALETTES, read: read, resolve: resolve,
    tokens: tokens, css: css, apply: apply, set: set, onChange: function (f) { listeners.push(f); } };

  /* Android app: a WebView cannot save blob: or data: links, so hand them to the app instead */
  if (droid) {
    var isFile = function (a) {
      return !!a && a.hasAttribute && a.hasAttribute("download") && /^(blob:|data:)/.test(a.href || "");
    };
    var save = function (a) {
      var name = a.getAttribute("download") || "download";
      fetch(a.href).then(function (r) { return r.blob(); }).then(function (b) {
        var fr = new FileReader();
        fr.onload = function () {
          var s = String(fr.result);
          droid.saveFile(name, b.type || "application/octet-stream", s.slice(s.indexOf(",") + 1));
        };
        fr.onerror = function () { droid.toast("Could not save " + name); };
        fr.readAsDataURL(b);
      }).catch(function () { droid.toast("Could not save " + name); });
    };
    var nativeClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      if (isFile(this)) { save(this); return; }
      return nativeClick.apply(this, arguments);
    };
    document.addEventListener("click", function (e) {
      var a = e.target && e.target.closest ? e.target.closest("a[download]") : null;
      if (isFile(a)) { e.preventDefault(); save(a); }
    }, true);
    /* navigator.clipboard is not dependable in a WebView either: copy through the app */
    if (droid.copy) {
      var writeText = function (text) {
        try {
          return droid.copy(String(text)) === false ? Promise.reject(new Error("too long to copy")) : Promise.resolve();
        } catch (e) { return Promise.reject(e); }
      };
      try {
        if (navigator.clipboard) navigator.clipboard.writeText = writeText;
        else Object.defineProperty(navigator, "clipboard", { value: { writeText: writeText }, configurable: true });
      } catch (e) { /* keep the WebView's own */ }
    }
    /* a web link inside an app frame would open the site inside the frame: open it in the
       browser instead, like every other web link (registered on window, so the apps' own click
       handlers run first and can still cancel it) */
    if (window.top !== window) {
      window.addEventListener("click", function (e) {
        if (e.defaultPrevented || e.button !== 0) return;
        var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
        if (!a || a.hasAttribute("download")) return;
        var t = (a.getAttribute("target") || "").toLowerCase();
        if (t && t !== "_self") return;
        var u;
        try { u = new URL(a.href); } catch (err) { return; }
        if (!/^(https?|mailto|tel):$/.test(u.protocol)) return;
        /* location.origin is "null" in the srcdoc app frames; self.origin is the real one */
        if (/^https?:$/.test(u.protocol) && u.origin === (self.origin || location.origin)) return;
        e.preventDefault();
        window.open(u.href, "_blank");
      });
    }
  }

  /* iPhone and iPad: a file "downloaded" from a web app on the home screen has nowhere useful to
     go, so hand it to the share sheet, where Save to Files puts it in iCloud Drive (or AirDrop it
     to the Mac). The Blob behind each blob: link is remembered when it is created, so the share
     sheet opens inside the tap, as Safari requires. Anything it cannot share downloads as before. */
  var ua = navigator.userAgent || "";
  var ios = !droid && (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1));
  if (ios && navigator.canShare && navigator.share && window.File && window.Map) {
    var blobs = new Map(), mkURL = URL.createObjectURL, rmURL = URL.revokeObjectURL;
    URL.createObjectURL = function (o) { var u = mkURL.apply(URL, arguments); if (o instanceof Blob) blobs.set(u, o); return u; };
    URL.revokeObjectURL = function (u) { setTimeout(function () { blobs.delete(u); }, 60000); return rmURL.apply(URL, arguments); };
    var fromData = function (href) {
      var m = /^data:([^;,]*)((?:;[^;,]*)*?)(;base64)?,(.*)$/.exec(href); if (!m) return null;
      var bin = m[3] ? atob(m[4]) : decodeURIComponent(m[4]), u8 = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      return new Blob([u8], { type: m[1] || "application/octet-stream" });
    };
    var shareFile = function (a) {
      if (!a || !a.hasAttribute || !a.hasAttribute("download")) return false;
      var name = a.getAttribute("download") || "download", href = a.href || "", blob = null;
      try { blob = /^blob:/.test(href) ? blobs.get(href) : /^data:/.test(href) ? fromData(href) : null; } catch (e) { blob = null; }
      if (!blob) return false;
      var file; try { file = new File([blob], name, { type: blob.type || "application/octet-stream" }); } catch (e) { return false; }
      try { if (!navigator.canShare({ files: [file] })) return false; } catch (e) { return false; }
      navigator.share({ files: [file], title: name }).catch(function () { /* cancelled */ });
      return true;
    };
    var iosClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () { if (shareFile(this)) return; return iosClick.apply(this, arguments); };
    document.addEventListener("click", function (e) {
      var a = e.target && e.target.closest ? e.target.closest("a[download]") : null;
      if (a && shareFile(a)) e.preventDefault();
    }, true);
  }

  apply(document);
  /* other tabs, frames and the control center change the key: follow along */
  window.addEventListener("storage", function (e) {
    if (e.key === KEY || e.key === null) { var v = read(); apply(document, v); fire(v); }
  });
  if (mq) {
    var onSystem = function () { var v = read(); if (v.mode === "system") { apply(document, v); fire(v); } };
    if (mq.addEventListener) mq.addEventListener("change", onSystem); else if (mq.addListener) mq.addListener(onSystem);
  }
})();
