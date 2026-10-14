/* Service worker: fresh files from the site whenever it answers, the last copy seen when it does
   not, so the installed app still opens offline. Change CACHE when the file list changes.
   GitHub (sync) and the online lookups are never cached: they go straight to the network. */
const CACHE="QTask-1.0.0-1";
const SUITES=["control-center","lab-notebook","literature-hub","structure-studio","paper-kit"];
const CORE=["./","./index.html","./suite-theme.js","./suite-sync.js","./app.webmanifest","./icons/apple-touch-icon.png"].concat(...SUITES.map(s=>[
  `./${s}.html`,`./icons/${s}-192.png`,`./icons/${s}-512.png`,`./icons/${s}-512-maskable.png`]));
self.addEventListener("install",e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(CORE.map(u=>c.add(u).catch(()=>{})))));
  self.skipWaiting();
});
self.addEventListener("activate",e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim()));
});
self.addEventListener("fetch",e=>{
  const req=e.request, url=new URL(req.url);
  if(req.method!=="GET"||url.origin!==location.origin) return;           // GitHub and online lookups go straight out
  e.respondWith(fetch(req).then(res=>{
    if(res.ok&&res.type==="basic"){const copy=res.clone();caches.open(CACHE).then(c=>c.put(req,copy));}
    return res;
  }).catch(()=>caches.match(req,{ignoreSearch:true}).then(r=>r||Response.error())));
});
