/* Suite service worker: fresh files from the server whenever it answers (serve_apps.py, or the
   site the suites are hosted on), the last copy seen when it does not, so installed suites still
   open offline. Change CACHE when the file list changes. Files not listed here, for example a
   chem-calculators.html added later, are cached the first time they are opened. */
const CACHE="suites-2026-10-04a";
const SUITES=["control-center","lab-notebook","literature-hub","hpc-workbench","structure-studio","paper-kit"];
const CORE=["./index.html","./suite-theme.js"].concat(...SUITES.map(s=>[
  `./${s}.html`,`./${s}.webmanifest`,`./icons/${s}-192.png`,`./icons/${s}-512.png`,`./icons/${s}-512-maskable.png`]));
self.addEventListener("install",e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(CORE.map(u=>c.add(u).catch(()=>{})))));
  self.skipWaiting();
});
self.addEventListener("activate",e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith("suites-")&&k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim()));
});
self.addEventListener("fetch",e=>{
  const req=e.request, url=new URL(req.url);
  if(req.method!=="GET"||url.origin!==location.origin) return;           // online lookups go straight out
  if(url.pathname.includes("/api/")) return;                              // backup server calls
  if(/\/\d{4}-\d{2}-\d{2}_[^/]*\.json$/.test(url.pathname)) return;      // backup files
  e.respondWith(fetch(req).then(res=>{
    if(res.ok&&res.type==="basic"){const copy=res.clone();caches.open(CACHE).then(c=>c.put(req,copy));}
    return res;
  }).catch(()=>caches.match(req,{ignoreSearch:true}).then(r=>r||Response.error())));
});
