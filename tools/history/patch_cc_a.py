#!/usr/bin/env python3
"""One-off patch of the control center (part A): head, the app list, the data model, task rules,
writing operations and row templates. Run once from the repository root."""
import sys

P = "src/suites/control-center/shell.html"
t = open(P, encoding="utf-8").read()


def rep(old, new, count=1):
    global t
    n = t.count(old)
    if n != count:
        sys.exit(f"expected {count}, found {n}: {old[:90]!r}")
    t = t.replace(old, new)


def cut(start, end, new, include_end=False):
    """replace from the line containing `start` up to (not including) the one containing `end`"""
    global t
    i = t.index(start)
    i = t.rfind("\n", 0, i) + 1
    j = t.index(end, i)
    if include_end:
        j = t.index("\n", j) + 1
    else:
        j = t.rfind("\n", 0, j) + 1
    t = t[:i] + new + t[j:]


# ---------- head ----------
rep('''<script src="suite-theme.js" data-suite-theme></script>''',
    '''<script src="suite-theme.js" data-suite-theme></script>
<script src="suite-sync.js"></script>''')
rep('''<meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="control-center.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icons/control-center-192.png">
<link rel="apple-touch-icon" href="icons/control-center-192.png">
<title>CompChemKit</title>''',
    '''<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{{APP_SHORT}}">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="app.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icons/control-center-192.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<title>{{APP_NAME}}</title>''')
rep('''placeholder="Search every app: entries, jobs, papers, commands..."''',
    '''placeholder="Search every app: tasks, entries, ideas, papers..."''')
rep('''   CompChemKit control center
   Reads every app's data from this browser's storage (same server and
   port as the suites) or from the dated backups written by serve_apps.py,
   backs everything up at once, and hands work between apps.''',
    '''   {{APP_NAME}} control center (adapted from the CompChemKit control
   center by A. R. V. Pinto, MIT licence)
   Reads every app's data from this browser's storage, shows the day,
   projects and search across apps, syncs through GitHub (suite-sync.js)
   and backs everything up to a file.''')
rep('''document.title=(v==="today"?"":VIEWS[v]+" - ")+"CompChemKit";''',
    '''document.title=(v==="today"?"":VIEWS[v]+" - ")+"{{APP_NAME}}";''')

# ---------- the suites ----------
cut('const SUITES=[', 'const APPS=/*APPS*/[];', '''const SUITES=[
 {id:"lab-notebook",title:"Lab notebook",apps:[
  {id:"log",label:"Log",name:"Research log",file:"research-log",keys:["researchlog.v1"],reminder:"research-log",color:"--blue"},
  {id:"tasks",label:"Tasks",name:"Tasks",file:"task-list",keys:["tasks.v1"],reminder:"task-list",color:"--green"},
  {id:"ideas",label:"Ideas",name:"Idea board",file:"idea-board",keys:["ideaboard.v1"],reminder:"idea-board",color:"--violet"},
  {id:"plans",label:"Script plans",name:"Script planner",file:"script-planner",keys:["scriptplans.v1"],reminder:"script-planner",color:"--pink"},
  {id:"deadlines",label:"Deadlines",name:"Deadline tracker",file:"deadline-tracker",keys:["deadlines.v1"],reminder:"deadline-radar",color:"--gold"}]},
 {id:"literature-hub",title:"Literature hub",apps:[
  {id:"radar",label:"Radar",name:"Literature radar",file:"literature-radar",keys:["litradar.v1","net.mailto"],reminder:"lit-radar",color:"--teal"},
  {id:"citations",label:"Citations",name:"Citation tracker",file:"citation-tracker",keys:["citedash.v1","net.mailto"],reminder:"cite-dash",color:"--violet"}]},
 {id:"structure-studio",title:"Structure studio",apps:[
  {id:"viewer",label:"Viewer",name:"Structure viewer",file:"structure-viewer",keys:["structviewer.prefs"],color:"--sky"}]},
 {id:"paper-kit",title:"Paper kit",apps:[
  {id:"plots",label:"Plot guide",name:"Python plot guide",color:"--sky",blurb:"Pick a plot type and its code"},
  {id:"schemes",label:"Schemes",name:"Mechanism scheme editor",file:"mechanism-scheme-editor",keys:[],prefixes:["mech."],color:"--pink"}]},
 {id:"control-center",title:"Control center",hidden:true,apps:[
  {id:"settings",label:"Control center",name:"Control center settings",file:"settings",keys:["controlcenter.v1"],color:"--accent"}]}
];
''')
cut('const A={log:APP("lab-notebook","log")', 'const cc=a=>', '''const A={log:APP("lab-notebook","log"),tasks:APP("lab-notebook","tasks"),ideas:APP("lab-notebook","ideas"),plans:APP("lab-notebook","plans"),deadlines:APP("lab-notebook","deadlines"),
  radar:APP("literature-hub","radar"),citations:APP("literature-hub","citations"),
  viewer:APP("structure-studio","viewer"),schemes:APP("paper-kit","schemes"),
  settings:APP("control-center","settings")};
''')
cut('function watchLink(h){', '/* ---------------- browser storage ---------------- */', '')

# ---------- private keys: the OpenAlex key and everything about sync (the GitHub token) ----------
rep('''const PRIVATE_KEYS=new Set(["net.openalexKey"]);''',
    '''const PRIVATE_KEYS=new Set(["net.openalexKey"]);
const isPrivate=k=>PRIVATE_KEYS.has(k)||String(k).startsWith("sync.");
const SYNC=()=>window.SuiteSync||null;''')
rep('''const loose=LS.keys().filter(k=>!ownedByAny(k)&&!PRIVATE_KEYS.has(k));
  const big=''', '''const loose=LS.keys().filter(k=>!ownedByAny(k)&&!isPrivate(k));
  const big=''')
rep('''const apps=DATA_APPS.filter(a=>keysOf(a).length), loose=LS.keys().filter(k=>!ownedByAny(k)&&!PRIVATE_KEYS.has(k));''',
    '''const apps=DATA_APPS.filter(a=>keysOf(a).length), loose=LS.keys().filter(k=>!ownedByAny(k)&&!isPrivate(k));''')
rep('''if(restOn&&RST.file&&RST.file.rest) for(const [k,v] of Object.entries(RST.file.rest)) if(!ownedByAny(k)&&typeof v==="string") LS.set(k,v);''',
    '''if(restOn&&RST.file&&RST.file.rest) for(const [k,v] of Object.entries(RST.file.rest)) if(!ownedByAny(k)&&!isPrivate(k)&&typeof v==="string") LS.set(k,v);''')

# ---------- the model ----------
cut('function buildModel(){', '/* ---------------- app rules, kept the same as inside the apps ---------------- */', '''function buildModel(){
  const lg=obj(V("researchlog.v1")), rd=obj(V("litradar.v1")), cd=obj(V("citedash.v1")), idx=obj(V("mech.index")), tk=obj(V("tasks.v1"));
  const ok=x=>x&&typeof x==="object";
  const M={
    entries:arr(lg.entries).filter(ok), lastProj:lg.lastProj||"",
    ideas:arr(V("ideaboard.v1")).filter(ok),
    plans:arr(obj(V("scriptplans.v1")).plans).filter(ok),
    deadlines:arr(obj(V("deadlines.v1")).items).filter(ok),
    tasks:arr(tk.items).filter(x=>ok(x)&&x.title),
    topics:arr(rd.topics).filter(ok), works:arr(rd.works).filter(ok), rf:{...RADAR_DEF,...obj(rd.filters)}, radarRun:rd.lastRun||0,
    saved:arr(rd.saved).filter(x=>ok(x)&&x.title),
    author:ok(cd.author)?cd.author:null, cworks:arr(cd.works).filter(ok), snaps:arr(cd.snaps).filter(ok), citeRun:cd.lastRun||0,
    schemes:Object.entries(idx).map(([id,v])=>({id,name:(v&&v.name)||"Scheme",updated:(v&&v.updated)||0})).sort((a,b)=>b.updated-a.updated),
    mailto:String(V("net.mailto","")||"")
  };
  M.meetings=M.entries.filter(e=>e.kind==="meeting");
  M.actions=M.meetings.flatMap(m=>arr(m.actions).filter(ok).map(a=>({a,m})));
  M.unseen=M.works.filter(w=>!w.seen&&radarPasses(w,M.rf));
  return M;
}

''')

# ---------- rules: drop the HPC ones, add the task ones ----------
cut('const JOB_STATUS=[{id:"queued"', '/* "me" in action owners:', '''/* tasks: the same ranking as the Tasks app. points = priority (low 10, medium 20, high 35)
   + due date (overdue +45, today +35, tomorrow +28, 2-3 days +20, 4-7 days +12, 8-14 days +6)
   + 5 when planned for today or carried over; 60+ do now, 35+ urgent, 20+ normal */
const TPRIO={low:{n:"Low",w:10,c:"--muted"},medium:{n:"Medium",w:20,c:"--sky"},high:{n:"High",w:35,c:"--red"}};
const TLEVELS={critical:{n:"Do now",c:"--red"},urgent:{n:"Urgent",c:"--gold"},normal:{n:"Normal",c:"--sky"},low:{n:"Can wait",c:"--muted"}};
const daysTo=d=>Math.round((dayMs(d)-dayMs(todayStr()))/DAY);
function taskUrgency(t){
  const T=todayStr(), p=TPRIO[t.prio]||TPRIO.medium; let s=p.w; const why=[p.n.toLowerCase()+" priority"];
  if(t.due){const n=daysTo(t.due);
    if(n<0){s+=45;why.push(n===-1?"due yesterday":`${-n} days overdue`)}
    else if(n===0){s+=35;why.push("due today")}
    else if(n===1){s+=28;why.push("due tomorrow")}
    else if(n<=3){s+=20;why.push(`due in ${n} days`)}
    else if(n<=7){s+=12;why.push(`due in ${n} days`)}
    else if(n<=14){s+=6;why.push(`due in ${n} days`)}}
  if(t.plan&&t.plan<=T){s+=5;why.push(t.plan<T?"carried over":"planned for today")}
  return {s,lvl:s>=60?"critical":s>=35?"urgent":s>=20?"normal":"low",why:why.join(", ")};
}
const taskToday=t=>!t.done&&((t.plan&&t.plan<=todayStr())||(t.due&&t.due<=todayStr()));
const taskOverdue=t=>!t.done&&!!t.due&&t.due<todayStr();
const byUrgency=(a,b)=>taskUrgency(b).s-taskUrgency(a).s||(a.due||"9").localeCompare(b.due||"9")||(a.added||0)-(b.added||0);
const doneOn=t=>t.done&&t.doneAt?localDate(t.doneAt):"";
const firstAuthor=s=>String(s||"").split(/;|,\\s(?=[A-Z][^,]*\\s)/)[0].trim();

''')
cut('function jobInfo(j,now){', 'function radarPasses(w,f){', '')
cut('/* benchmark cost, as in the benchmark log', '/* ---------------- writing into the apps ----------------', '')

# ---------- operations ----------
rep('''  try{out=mutate(a,key,def,fn)}catch(e){toast(e&&e.message?e.message:"Couldn't save");return false}
  await refresh(false);''', '''  try{out=mutate(a,key,def,fn)}catch(e){toast(e&&e.message?e.message:"Couldn't save");return false}
  if(SYNC()) SYNC().changed();
  await refresh(false);''')
cut('  addJob(x){', '  addPaper(x){', '')
cut('  addPaper(x){', '  radarSeen(id,topic,quiet){', '''  addTask(x){
    return write(A.tasks,"tasks.v1",{items:[]},d=>{
      if(!Array.isArray(d.items)) d.items=[];
      const now=Date.now();
      d.items.push({id:uid(),title:x.title.trim().slice(0,200),notes:(x.notes||"").trim(),proj:(x.proj||"").trim(),prio:TPRIO[x.prio]?x.prio:"medium",
        plan:x.plan||"",due:x.due||"",done:false,doneAt:null,added:now,updated:now,subs:[]});
    },"Task added",{href:href(A.tasks,{find:x.title.trim().slice(0,40),pick:"all"}),label:"Open"});
  },
  toggleTask(id,done){
    return write(A.tasks,"tasks.v1",{items:[]},d=>{
      const t=arr(d.items).find(x=>x&&x.id===id); if(!t) throw new Error("That task is gone; it may have been deleted");
      t.done=done; t.doneAt=done?Date.now():null; t.updated=Date.now();
    },done?"Task done":"Task reopened");
  },
  planTask(id,day){
    return write(A.tasks,"tasks.v1",{items:[]},d=>{
      const t=arr(d.items).find(x=>x&&x.id===id); if(!t) throw new Error("That task is gone");
      t.plan=day; t.updated=Date.now();
    },day===todayStr()?"Planned for today":"Moved");
  },
  /* the reading list lives inside the literature radar's data */
  addPaper(x){
    return write(A.radar,"litradar.v1",{topics:[],works:[],saved:[]},d=>{
      if(!Array.isArray(d.saved)) d.saved=[];
      if(x.doi&&d.saved.some(p=>(p.doi||"").toLowerCase()===x.doi.toLowerCase())) throw new Error("Already in your reading list");
      d.saved.unshift({id:"m"+uid(),title:x.title,doi:x.doi||"",authors:x.authors||"",venue:x.venue||"",date:x.year?String(x.year):"",type:x.type||"",
        cites:x.cites||0,abs:"",topic:"",read:false,saved:Date.now(),notes:""});
    },"Saved to your reading list",{href:href(A.radar,{pick:"saved"}),label:"Open"});
  },
  radarSave(id,topic){
    const w=D.works.find(x=>x.id===id&&x.topic===topic); if(!w) return;
    return write(A.radar,"litradar.v1",{topics:[],works:[],saved:[]},d=>{
      if(!Array.isArray(d.saved)) d.saved=[];
      const ww=arr(d.works).find(x=>x.id===id&&x.topic===topic); if(ww) ww.seen=true;
      if(d.saved.some(s=>s.id===w.id||(w.doi&&(s.doi||"").toLowerCase()===w.doi.toLowerCase()))) return;
      const tq=(arr(d.topics).find(tp=>tp.id===w.topic)||{}).q||"";
      d.saved.unshift({id:w.id,title:w.title,doi:w.doi||"",authors:w.authors||"",venue:w.venue||"",date:w.date||"",type:w.type||"",
        cites:w.cites||0,abs:w.abs||"",topic:tq,read:false,saved:Date.now(),notes:""});
    },"Saved to your reading list",{href:href(A.radar,{pick:"saved"}),label:"Open"});
  },
''')
cut('  watchSeen(key){', '  openScheme(id){', '')

# ---------- row templates ----------
cut('function jobRow(j,i,now,opts){', 'function evRow(app,title,meta,link){', '''function taskRow(t,opts){
  opts=opts||{};
  const u=taskUrgency(t), p=TPRIO[t.prio]||TPRIO.medium, T=todayStr(), lv=TLEVELS[u.lvl], meta=[];
  if(t.proj&&!opts.noProj) meta.push(`<span style="color:var(--accent)">${esc(t.proj)}</span>`);
  if(t.due){const n=daysTo(t.due);meta.push(`<span class="${t.done?"":n<0?"over":n<=2?"soon":""}">${n<0&&!t.done?(n===-1?"due yesterday":`${-n} days overdue`):n===0?"due today":n===1?"due tomorrow":"due "+esc(shortDate(t.due))}</span>`)}
  if(!t.done&&t.plan&&t.plan<T) meta.push(`<span>carried over</span>`);
  else if(!t.done&&t.plan&&t.plan>T) meta.push(`<span>do ${esc(shortDate(t.plan))}</span>`);
  const subs=arr(t.subs); if(subs.length) meta.push(`<span>${subs.filter(s=>s&&s.done).length}/${subs.length} subtasks</span>`);
  if(!t.done&&(u.lvl==="critical"||u.lvl==="urgent")) meta.push(`<span class="tag" style="--cc:var(${lv.c})" title="${esc(u.why)}">${lv.n}</span>`);
  const side=opts.plan&&!t.done?`<div class="side"><button class="txtbtn" data-op="task-plan" data-id="${esc(t.id)}" data-day="${esc(T)}" ${disabled(A.tasks)}>Do today</button></div>`:"";
  return `<label class="row ${t.done?"done":""}" style="--cc:var(${p.c})"><input type="checkbox" data-op="task-done" data-id="${esc(t.id)}" ${t.done?"checked":""} ${disabled(A.tasks)} aria-label="Done">
    <div class="main"><div class="t"><a href="${esc(href(A.tasks,{find:t.title.slice(0,40),pick:t.done?"done":"all"}))}">${esc(t.title)}</a></div>${meta.length?`<div class="m">${meta.join("")}</div>`:""}</div>${side}</label>`;
}
''')
rep('''  const ok=canWrite(A.radar)&&canWrite(A.papers);
  return `<div class="row" style="--cc:var(--teal)">''', '''  const ok=canWrite(A.radar), kept=D.saved.some(s=>s.id===w.id||(w.doi&&(s.doi||"").toLowerCase()===w.doi.toLowerCase()));
  return `<div class="row" style="--cc:var(--teal)">''')
rep('''<button class="txtbtn" data-op="radar-save" data-id="${esc(w.id)}" data-topic="${esc(w.topic)}" ${ok?"":"disabled"}>Save to library</button>''',
    '''<button class="txtbtn" data-op="radar-save" data-id="${esc(w.id)}" data-topic="${esc(w.topic)}" ${ok&&!kept?"":"disabled"}>${kept?"In reading list":"Save to read"}</button>''')
cut('function watchRow(h){', 'function logRow(e){', '''function savedRow(s){
  const link=s.doi?"https://doi.org/"+encodeURI(s.doi):href(A.radar,{pick:"saved"});
  return evRow(A.radar,s.title,[firstAuthor(s.authors),s.venue&&clip(s.venue,40),(s.date||"").slice(0,4),s.read?"read":""].filter(Boolean).map(x=>`<span>${esc(x)}</span>`).join(""),link);
}
''')

open(P, "w", encoding="utf-8").write(t)
print("part A applied")
