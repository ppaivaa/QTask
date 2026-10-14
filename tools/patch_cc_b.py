#!/usr/bin/env python3
"""One-off patch of the control center (part B): Today, Projects, Search, Apps, Backup and sync,
adding things, the digest and the event wiring. Run once after part A."""
import sys

P = "src/suites/control-center/shell.html"
t = open(P, encoding="utf-8").read()


def rep(old, new, count=1):
    global t
    n = t.count(old)
    if n != count:
        sys.exit(f"expected {count}, found {n}: {old[:90]!r}")
    t = t.replace(old, new)


def cut(start, end, new):
    global t
    i = t.index(start)
    i = t.rfind("\n", 0, i) + 1
    j = t.index(end, i)
    j = t.rfind("\n", 0, j) + 1
    t = t[:i] + new + t[j:]


# ---------- chrome ----------
rep('''  D.jobs.forEach(j=>{const i=jobInfo(j,now);if(i.overdue||j.status==="failed")n++});
  D.allocs.forEach(a=>{if(allocWarn(a,allocInfo(a,now)))n++});
  return n;''', '''  D.tasks.forEach(x=>{if(taskOverdue(x))n++});
  return n;''')
rep('''  const bs=backupSummary(), dot=$("#bdBackup");
  dot.classList.toggle("hidden",!(bs.err.length||bs.changed.length||bs.never.length));
  dot.style.background=bs.err.length?"var(--danger)":"var(--gold)";''', '''  const dot=$("#bdBackup"), ss=SYNC()?SYNC().status():null;
  if(SRV.ok){
    const bs=backupSummary();
    dot.classList.toggle("hidden",!(bs.err.length||bs.changed.length||bs.never.length));
    dot.style.background=bs.err.length?"var(--danger)":"var(--gold)";
  }else{
    /* hosted copy: red when sync fails, gold when there is neither sync nor a recent download */
    const err=ss&&ss.configured&&ss.state==="error";
    const stale=!(ss&&ss.configured)&&DATA_APPS.some(a=>keysOf(a).length)&&Date.now()-(+LS.get("controlcenter.lastBundle")||0)>7*DAY;
    dot.classList.toggle("hidden",!(err||stale));
    dot.style.background=err?"var(--danger)":"var(--gold)";
  }''')
rep('''  }else if(VIEW==="backup") sub=SRV.ok?"Backups go to "+(SRV.dir||"the suites folder"):STATIC_HOST?"Hosted copy: back up by downloading":SRV.http?"Backup server not found":"Opened as a file";''',
    '''  }else if(VIEW==="backup") sub=SRV.ok?"Backups go to "+(SRV.dir||"the suites folder"):SRV.http?(ss&&ss.configured?"Synced through GitHub, plus backup files":"Sync through GitHub, or back up to a file"):"Opened as a file";''')
rep('''    if(SRV.ok===false&&SRV.http&&!STATIC_HOST) sub+=" · backup server not running";''', '')

# ---------- activity ----------
cut('  for(const j of D.jobs){\n    if(!P(j.proj)) continue;\n    const meta=[j.proj', '  for(const i of D.ideas){', '''  for(const x of D.tasks){
    if(!P(x.proj)) continue;
    const l=href(A.tasks,{find:x.title.slice(0,40),pick:x.done?"done":"all"});
    add(x.added,A.tasks,"Task added: "+x.title,esc(x.proj||""),l);
    if(x.done&&x.doneAt) add(x.doneAt,A.tasks,"Task done: "+x.title,esc(x.proj||""),l);
  }
  for(const s of D.saved){
    if(m&&!T(s.title,s.topic)) continue;
    add(s.saved,A.radar,"Saved to read: "+s.title,[firstAuthor(s.authors),s.venue,(s.date||"").slice(0,4)].filter(Boolean).map(esc).join(" · "),s.doi?"https://doi.org/"+encodeURI(s.doi):href(A.radar,{pick:"saved"}));
  }
''')
cut('  for(const r of D.runs){ if(m&&!T(r.sys,r.notes)) continue;', '  return out.sort((a,b)=>b.t-a.t);', '')

# ---------- TODAY ----------
cut('function renderToday(){', '/* ---------------- PROJECTS ---------------- */', r'''function renderToday(){
  const M=D, now=Date.now(), t=todayStr(), st=settings(), mine=st.mine;
  const wantAct=x=>!mine||isMe(x.a.owner);
  /* needs attention */
  const att=[];
  for(const i of M.deadlines) if(!i.done&&dlWhen(i)<now) att.push({t:dlWhen(i),h:dlRow(i,now)});
  for(const x of M.actions) if(!x.a.done&&actDue(x.a)==="overdue"&&wantAct(x)) att.push({t:dayMs(x.a.due),h:actRow(x)});
  for(const x of M.tasks) if(taskOverdue(x)) att.push({t:dayMs(x.due),h:taskRow(x)});
  att.sort((a,b)=>a.t-b.t);
  /* next 14 days */
  const end=now+14*DAY, endD=localDate(end), ag=[];
  for(const i of M.deadlines){const w=dlWhen(i); if(!i.done&&w>=now&&w<end) ag.push({d:i.date,t:w,h:dlRow(i,now)})}
  for(const x of M.actions) if(!x.a.done&&x.a.due&&x.a.due>=t&&x.a.due<=endD&&wantAct(x)) ag.push({d:x.a.due,t:dayMs(x.a.due)-1,h:actRow(x)});
  for(const x of M.tasks) if(!x.done&&x.due&&x.due>=t&&x.due<=endD) ag.push({d:x.due,t:dayMs(x.due)-2,h:taskRow(x)});
  ag.sort((a,b)=>a.t-b.t);
  const days=[...new Set(ag.map(x=>x.d))];
  const tomorrow=localDate(now+DAY);
  const agHTML=days.map(d=>`<div class="day"><div class="dayh ${d===t?"today":""}"><span>${d===t?"Today":d===tomorrow?"Tomorrow":esc(longDate(d))}</span></div><div class="rows">${ag.filter(x=>x.d===d).map(x=>x.h).join("")}</div></div>`).join("");
  /* tasks */
  const open=M.tasks.filter(x=>!x.done);
  const todayTasks=open.filter(x=>taskToday(x)&&!taskOverdue(x)).sort(byUrgency);
  const overdueN=open.filter(taskOverdue).length;
  const doneToday=M.tasks.filter(x=>doneOn(x)===t);
  const urgentN=open.filter(x=>taskUrgency(x).s>=35).length;
  const suggested=open.filter(x=>!taskToday(x)&&taskUrgency(x).s>=35).sort(byUrgency).slice(0,3);
  const totalToday=todayTasks.length+overdueN+doneToday.length;
  /* literature */
  const unseen=[...M.unseen].sort((a,b)=>(b.date||"").localeCompare(a.date||"")||(b.found||0)-(a.found||0));
  const toRead=M.saved.filter(s=>!s.read);
  const A_=M.author, lastSnap=M.snaps.length>1?M.snaps[M.snaps.length-2]:null, dC=A_&&lastSnap?(A_.cites||0)-(lastSnap.cites||0):0;
  const gained=M.cworks.filter(w=>w.prev!=null&&w.cites>w.prev).sort((a,b)=>(b.cites-b.prev)-(a.cites-a.prev)).slice(0,3);
  /* in progress */
  const doing=M.ideas.filter(i=>i.stage==="doing").sort((a,b)=>(b.updated||0)-(a.updated||0));
  const exploring=M.ideas.filter(i=>i.stage==="explore").length;
  const building=M.plans.filter(p=>p.status==="building"), planning=M.plans.filter(p=>p.status==="planning");
  const pinned=M.entries.filter(e=>e.pin).sort((a,b)=>(b.date||"").localeCompare(a.date||"")).slice(0,4);
  /* tiles */
  const end7=localDate(now+7*DAY);
  const next7=M.deadlines.filter(i=>!i.done&&dlWhen(i)>=now&&dlWhen(i)<now+7*DAY).length
    +M.actions.filter(x=>!x.a.done&&x.a.due&&x.a.due>=t&&x.a.due<=end7&&wantAct(x)).length
    +open.filter(x=>x.due&&x.due>=t&&x.due<=end7).length;
  const tile=(n,label,op,col,txt)=>`<button class="tile ${!n&&!txt?"zero":""}" data-op="${op}" style="${col&&n?`--tc:${col}`:""}"><b>${txt||n}</b><span>${label}</span></button>`;
  const ss=SYNC()?SYNC().status():null;
  let syncTile;
  if(SRV.ok){
    const bs=backupSummary(), pendingBk=bs.changed.length+bs.never.length;
    syncTile=tile(pendingBk,pendingBk?"not backed up":bs.ok.length?"all backed up":"nothing to back up","goto-backup",bs.err.length?"var(--red)":"var(--gold)",!bs.ok.length&&!pendingBk?"-":pendingBk?String(pendingBk):"✓");
  }else if(ss&&ss.configured){
    syncTile=ss.state==="error"?tile(1,"sync failed","goto-backup","var(--red)","!")
      :ss.state==="offline"?tile(1,"offline, will sync later","goto-backup","var(--gold)","…")
      :ss.pending?tile(ss.pending,ss.busy?"syncing":"waiting to sync","goto-backup","var(--gold)")
      :tile(0,ss.last?"synced "+ago(ss.last):"not synced yet","goto-backup","",ss.last?"✓":"-");
  }else syncTile=tile(0,"set up sync","goto-backup","","-");
  const tiles=`<div class="tiles">
    ${tile(att.length,"need attention","goto-attn","var(--red)")}
    ${tile(next7,"due in 7 days","goto-agenda","var(--gold)")}
    ${tile(todayTasks.length+overdueN,"tasks for today","goto-tasks","var(--green)")}
    ${tile(urgentN,"urgent tasks","goto-tasks","var(--accent)")}
    ${tile(unseen.length,"new in radar","goto-lit","var(--teal)")}
    ${syncTile}
  </div>`;
  const mineToggle=`<button class="lk" data-op="toggle-mine" style="background:none">${mine?"My actions":"Everyone's actions"}</button>`;
  const taskBody=[
    totalToday?`<div class="prog" style="margin:0 0 6px"><div class="track"><div class="fill" style="width:${(doneToday.length/totalToday*100).toFixed(1)}%"></div></div><div class="plab"><span>${doneToday.length} of ${totalToday} done today</span>${overdueN?`<span class="over">${overdueN} overdue, under Needs attention</span>`:""}</div></div>`:"",
    todayTasks.length?`<div class="rows">${todayTasks.map(x=>taskRow(x)).join("")}</div>`:"",
    suggested.length?`<h3>Suggested for today</h3><div class="rows">${suggested.map(x=>taskRow(x,{plan:true})).join("")}</div>`:"",
    doneToday.length?`<p class="muted" style="font-size:.82rem;margin:8px 0 0">Done today: ${doneToday.slice(0,6).map(x=>esc(x.title)).join(", ")}${doneToday.length>6?` and ${doneToday.length-6} more`:""}.</p>`:""
  ].join("")||empty(M.tasks.length?`Nothing planned for today. Plan a task in <a href="${esc(href(A.tasks,{pick:"upcoming"}))}">Tasks</a> or add one with +.`:`Add your tasks with + or in <a href="${esc(href(A.tasks))}">Tasks</a>. Give them a priority and a due date and the most urgent rise to the top.`);
  const litBody=[
    M.topics.length?`<h3>Radar${unseen.length?`, ${unseen.length} new`:""}</h3>
      <div class="m muted" style="font-size:.8rem;margin-bottom:4px">${M.radarRun?`Checked ${esc(ago(M.radarRun))}`:"Not checked yet"}${M.radarRun&&Date.now()-M.radarRun>7*DAY?` · <a href="${esc(href(A.radar))}" style="color:var(--accent)">check again</a>`:""}</div>
      <div class="rows">${unseen.slice(0,5).map(workRow).join("")||empty("Nothing new with your current filters.")}</div>${unseen.length>5?`<a class="more" href="${esc(href(A.radar))}">${unseen.length-5} more in the radar</a>`:""}`:"",
    M.saved.length?`<h3>Reading list</h3><div class="kv"><span><b>${toRead.length}</b> to read</span><span><b>${M.saved.length}</b> saved</span></div>
      ${toRead.length?`<div class="rows" style="margin-top:6px">${toRead.slice(0,3).map(savedRow).join("")}</div>`:""}${toRead.length>3?`<a class="more" href="${esc(href(A.radar,{pick:"saved"}))}">${toRead.length-3} more to read</a>`:""}`:"",
    A_?`<h3>Citations</h3><div class="kv"><span><b>${(A_.cites||0).toLocaleString("en-GB")}</b> citations${dC>0?` <span class="ok">+${dC}</span>`:""}</span><span>h-index <b>${A_.h||0}</b></span><span><b>${A_.works||0}</b> works</span><span>${M.citeRun?"updated "+esc(ago(M.citeRun)):""}</span></div>
      ${gained.length?`<div class="rows" style="margin-top:6px">${gained.map(w=>evRow(A.citations,w.title,`<span class="ok">+${w.cites-w.prev}</span><span>${w.cites} total</span>${w.year?`<span>${w.year}</span>`:""}`,w.doi?"https://doi.org/"+encodeURI(w.doi):href(A.citations))).join("")}</div>`:""}`:""
  ].join("")||empty(`Set up topics in the <a href="${esc(href(A.radar))}">literature radar</a> to see new papers here.`);
  const progBody=[
    doing.length?`<h3>Ideas you're doing${exploring?`, ${exploring} being explored`:""}</h3><div class="rows">${doing.slice(0,6).map(i=>`<div class="row" style="--cc:var(--violet)"><span class="bar"></span><div class="main"><div class="t"><a href="${esc(href(A.ideas,{find:i.title.slice(0,40),pick:"doing"}))}">${esc(i.title)}</a></div><div class="m"><span class="app">${esc((IDEA_CATS.find(c=>c.id===i.cat)||{}).name||"")}</span>${arr(i.tags).length?`<span>${esc(i.tags.map(x=>"#"+x).join(" "))}</span>`:""}</div></div><div class="side"><button class="txtbtn" data-op="idea-move" data-id="${esc(i.id)}" data-to="done" ${disabled(A.ideas)}>Done</button></div></div>`).join("")}</div>`:"",
    building.length||planning.length?`<h3>Script plans</h3><div class="rows">${[...building,...planning].slice(0,6).map(p=>{const op=arr(p.checks).filter(c=>!c.done).length;return evRow(A.plans,p.name,`<span class="app">${esc(PLAN_STATUS[p.status]||p.status)}</span>${p.purpose?`<span>${esc(clip(p.purpose,70))}</span>`:""}${op?`<span class="soon">${plural(op,"open check")}</span>`:""}`,href(A.plans,{find:p.name.slice(0,40)}))}).join("")}</div>`:"",
    pinned.length?`<h3>Pinned in the log</h3><div class="rows">${pinned.map(logRow).join("")}</div>`:""
  ].join("")||empty("Ideas you move to Doing and script plans you're building show up here.");
  const recent=activity(now-7*DAY);
  const actBody=recent.length?`<div class="rows">${actRowsHTML(recent.slice(0,10))}</div>${recent.length>10?`<button class="more" data-op="digest">${recent.length-10} more, see the digest</button>`:""}`:empty("Nothing recorded in the last 7 days.");

  const empties=!M.entries.length&&!M.tasks.length&&!M.deadlines.length&&!M.ideas.length&&!M.topics.length&&!M.saved.length;
  const welcome=empties&&SRC.mode==="auto"&&SRV.http?`<div class="infobox"><b>Welcome to {{APP_NAME}}.</b> Add a task with +, or open the <a href="${esc(href(A.tasks))}">Tasks</a>, <a href="${esc(href(A.log))}">Lab notebook</a> and <a href="${esc(href(A.radar))}">Literature radar</a>. ${ss&&ss.configured?"Sync is on: data from your other devices appears here after the first sync.":`Already using {{APP_NAME}} on another device? <button class="linkbtn" data-op="sync-setup" style="color:var(--accent)">Turn on sync</button> to bring your data here.`}</div>`:"";
  $("#v-today").innerHTML=tiles+welcome+
  `<div class="masonry">
    ${card("Needs attention",att.length?`<div class="rows">${att.map(x=>x.h).join("")}</div>`:empty("Nothing overdue."),{id:"s-attn",right:mineToggle})}
    ${card("Today's tasks",taskBody,{id:"s-tasks",right:`<a class="lk" href="${esc(href(A.tasks))}">Tasks</a>`})}
    ${card("Next 14 days",agHTML||empty("Nothing due in the next two weeks."),{id:"s-agenda"})}
    ${card("Literature",litBody,{id:"s-lit",right:`<a class="lk" href="${esc(href(A.radar))}">Radar</a>`})}
    ${card("In progress",progBody)}
    ${card("Last 7 days",actBody,{right:`<button class="lk" data-op="digest" style="background:none">Digest</button>`})}
  </div>`;
}

''')

# ---------- PROJECTS ----------
rep('''  D.entries.forEach(e=>add(e.proj,e.updated||e.added||0));
  D.jobs.forEach(j=>add(j.proj,j.updated||j.added||0));''', '''  D.entries.forEach(e=>add(e.proj,e.updated||e.added||0));
  D.tasks.forEach(x=>add(x.proj,x.updated||x.added||0));''')
cut('function projectData(name){', 'function renderProjects(){', '''function projectData(name){
  const m=matcher(name);
  const entries=D.entries.filter(e=>m.proj(e.proj)).sort((a,b)=>(b.date||"").localeCompare(a.date||"")||(b.added||0)-(a.added||0));
  const tasks=D.tasks.filter(x=>m.proj(x.proj));
  const P={m,entries,
    logs:entries.filter(e=>e.kind!=="meeting"),
    meetings:entries.filter(e=>e.kind==="meeting"),
    actions:D.actions.filter(x=>m.proj(x.m.proj)&&!x.a.done).sort((a,b)=>(a.a.due||"9").localeCompare(b.a.due||"9")),
    tasks:tasks.filter(x=>!x.done).sort(byUrgency),
    tasksDone:tasks.filter(x=>x.done).sort((a,b)=>(b.doneAt||0)-(a.doneAt||0)),
    deadlines:D.deadlines.filter(i=>!i.done&&m.text(i.title,i.notes)).sort((a,b)=>dlWhen(a)-dlWhen(b)),
    ideas:D.ideas.filter(i=>i.stage!=="done"&&m.text(i.title,i.notes,arr(i.tags).join(" "))),
    plans:D.plans.filter(p=>m.text(p.name,p.purpose,p.desc)),
    saved:D.saved.filter(s=>m.text(s.title,s.topic)).sort((a,b)=>(b.saved||0)-(a.saved||0)),
    topics:D.topics.filter(tp=>m.text(tp.q)),
    schemes:D.schemes.filter(s=>m.text(s.name))
  };
  P.last=Math.max(0,...entries.map(e=>e.updated||e.added||0),...tasks.map(x=>x.updated||x.added||0));
  return P;
}
''')
cut('function renderProjects(){', '/* ---------------- SEARCH ---------------- */', r'''function renderProjects(){
  const list=projectList();
  let cur=UI.get("proj","");
  if(!list.some(p=>p.key===cur)) cur=list[0]?list[0].key:"";
  const chips=`<div class="chips">${list.map(p=>`<button class="chip" data-op="proj" data-key="${esc(p.key)}" aria-pressed="${p.key===cur}">${esc(p.name)}${p.n?`<span class="c">${p.n}</span>`:""}</button>`).join("")}<button class="chip" data-op="proj-new" style="color:var(--accent)">+ Project</button></div>`;
  if(!list.length){
    $("#v-projects").innerHTML=chips+`<div class="infobox">Projects come from the <b>Project</b> field of tasks and of research log entries. Give a task or an entry a project, or add one here with a few keywords, and everything related across your apps collects on one page: open tasks and actions, deadlines, log entries, ideas, script plans, radar topics, papers to read and schemes.</div>`;
    return;
  }
  const p=list.find(x=>x.key===cur), P=projectData(p.name), now=Date.now();
  const head=`<div class="projhead"><div style="min-width:0"><h2>${esc(p.name)}</h2>
    <div class="kv" style="margin-top:4px"><span>${plural(P.tasks.length,"open task")}</span><span>${plural(P.tasksDone.length,"task")} done</span><span>${plural(P.logs.length,"log entry","log entries")}</span><span>${plural(P.meetings.length,"meeting")}</span><span>${plural(P.actions.length,"open action")}</span><span>last activity ${esc(ago(P.last))}</span></div>
    ${P.m.kw.length?`<div class="kv" style="margin-top:4px"><span>Also matching: ${esc(P.m.kw.join(", "))}</span></div>`:""}</div>
    <div class="btnrow"><button class="btn" data-op="cap" data-kind="task" data-proj="${esc(p.name)}" ${disabled(A.tasks)}>Task</button><button class="btn" data-op="cap" data-kind="log" data-proj="${esc(p.name)}" ${disabled(A.log)}>Log entry</button><button class="btn" data-op="digest" data-proj="${esc(p.name)}">Digest</button><button class="btn ghost" data-op="proj-kw" data-key="${esc(p.key)}">Keywords</button></div></div>`;
  const lit=[
    P.topics.length?`<h3>Radar topics</h3><div class="rows">${P.topics.map(tp=>{const n=D.unseen.filter(w=>w.topic===tp.id).length;return evRow(A.radar,tp.q,`<span class="app">Literature radar</span>${n?`<span class="soon">${n} new</span>`:"<span>nothing new</span>"}`,href(A.radar))}).join("")}</div>`:"",
    P.saved.length?`<h3>Reading list</h3><div class="rows">${P.saved.slice(0,6).map(savedRow).join("")}</div>${P.saved.length>6?`<p class="muted" style="font-size:.82rem;margin:6px 0 0">${P.saved.length-6} more</p>`:""}`:""
  ].join("")||empty("No radar topic or saved paper mentions this project.");
  const other=[
    P.ideas.length?`<h3>Ideas</h3><div class="rows">${P.ideas.map(i=>evRow(A.ideas,i.title,`<span class="app">${esc((IDEA_STAGES.find(s=>s.id===i.stage)||{}).name||"")}</span>`,href(A.ideas,{find:i.title.slice(0,40),pick:i.stage}))).join("")}</div>`:"",
    P.plans.length?`<h3>Script plans</h3><div class="rows">${P.plans.map(pl=>evRow(A.plans,pl.name,`<span class="app">${esc(PLAN_STATUS[pl.status]||"")}</span>${pl.purpose?`<span>${esc(clip(pl.purpose,70))}</span>`:""}`,href(A.plans,{find:pl.name.slice(0,40)}))).join("")}</div>`:"",
    P.schemes.length?`<h3>Schemes</h3><div class="rows">${P.schemes.map(s=>`<div class="row" style="--cc:var(--pink)"><span class="bar"></span><div class="main"><div class="t"><button class="txtbtn" style="padding:0;min-height:0;color:var(--ink)" data-op="scheme" data-id="${esc(s.id)}">${esc(s.name)}</button></div><div class="m"><span class="app">Mechanism scheme</span><span>${esc(ago(s.updated))}</span></div></div></div>`).join("")}</div>`:""
  ].join("")||empty("No ideas, script plans or schemes mention this project. Add keywords to widen the match.");
  $("#v-projects").innerHTML=chips+head+`<div class="grid two">
    ${card("Open tasks",P.tasks.length?`<div class="rows">${P.tasks.map(x=>taskRow(x,{noProj:true})).join("")}</div>`:empty("No open tasks in this project."),{right:`<a class="lk" href="${esc(href(A.tasks,{find:p.name}))}">Tasks</a>`})}
    ${card("Open actions",P.actions.length?`<div class="rows">${P.actions.map(x=>actRow(x)).join("")}</div>`:empty("No open actions from this project's meetings."))}
    ${card("Deadlines",P.deadlines.length?`<div class="rows">${P.deadlines.map(i=>dlRow(i,now)).join("")}</div>`:empty("No upcoming deadline mentions this project."))}
    ${card("Research log",P.entries.length?`<div class="rows">${P.entries.slice(0,8).map(logRow).join("")}</div>${P.entries.length>8?`<a class="more" href="${esc(href(A.log,{find:p.name}))}">${P.entries.length-8} more in the log</a>`:""}`:empty("No log entries or meetings with this project yet."))}
    ${card("Literature",lit)}
    ${card("Ideas, plans and schemes",other)}
  </div>`;
}

''')

# ---------- SEARCH ----------
rep('''  for(const i of D.deadlines) add(A.deadlines,i.title,''', '''  for(const x of D.tasks) add(A.tasks,x.title,`Task${x.done?" (done)":""} · ${(TPRIO[x.prio]||TPRIO.medium).n} priority${x.due?" · due "+shortDate(x.due):""}${x.proj?" · "+x.proj:""}`,[x.notes,x.proj,arr(x.subs).map(s=>s&&s.text).join(" ")].join(" "),href(A.tasks,{find:x.title.slice(0,40),pick:x.done?"done":"all"}));
  for(const i of D.deadlines) add(A.deadlines,i.title,''')
cut('  for(const j of D.jobs) add(A.jobs,j.name,', '  for(const w of D.works){', '''  for(const s of D.saved) add(A.radar,s.title,`Reading list${s.read?"":" (to read)"}${s.venue?" · "+s.venue:""}${s.date?" · "+s.date.slice(0,4):""}`,[s.authors,s.venue,s.doi,s.topic].join(" "),s.doi?"https://doi.org/"+encodeURI(s.doi):href(A.radar,{pick:"saved"}),{doi:s.doi});
''')
cut('  for(const h of D.whits) add(A.watch,h.title,', '  return out;\n}\nfunction renderSearch(){', '''  for(const s of D.schemes) add(A.schemes,s.name,`Mechanism scheme · edited ${ago(s.updated)}`,"","",{scheme:s});
''')
rep('''Searches the research log (entries, meetings and actions), ideas, script plans, deadlines, calculations, allocations, job presets, benchmarks, commands, papers, radar results, your cited works, schemes and journals. Tap a result to open that app filtered to it.''',
    '''Searches your tasks, the research log (entries, meetings and actions), ideas, script plans, deadlines, radar results, the reading list, your cited works and schemes. Tap a result to open that app filtered to it.''')
rep('''  if(x.cmd) side.push(`<button class="txtbtn" data-op="cmd-fill" data-id="${esc(x.cmd.id)}">${cmdVars(x.cmd.cmd).length?"Fill and copy":"Copy"}</button>`);
''', '')
rep('''  if(x.work&&!x.work.seen) side.push(`<button class="txtbtn" data-op="radar-save" data-id="${esc(x.work.id)}" data-topic="${esc(x.work.topic)}" ${canWrite(A.radar)&&canWrite(A.papers)?"":"disabled"}>Save</button>`);
  if(x.job&&D.cmds.length) side.push(`<button class="txtbtn" data-op="job-cmds" data-id="${esc(x.job.id)}">Commands</button>`);''',
    '''  if(x.work&&!x.work.seen) side.push(`<button class="txtbtn" data-op="radar-save" data-id="${esc(x.work.id)}" data-topic="${esc(x.work.topic)}" ${canWrite(A.radar)?"":"disabled"}>Save</button>`);''')

# ---------- APPS ----------
cut('    case "lab-notebook/log":{', '    default:return esc(a.blurb||"");', '''    case "lab-notebook/log":{const o=M.actions.filter(x=>!x.a.done).length;return `${plural(M.entries.length-M.meetings.length,"entry","entries")}, ${plural(M.meetings.length,"meeting")}${o?`, ${o} open actions`:""}`}
    case "lab-notebook/tasks":{const o=M.tasks.filter(x=>!x.done);return `${o.length} open, ${o.filter(taskToday).length} for today`}
    case "lab-notebook/ideas":return `${plural(M.ideas.length,"idea")}, ${M.ideas.filter(i=>i.stage==="doing").length} doing`;
    case "lab-notebook/plans":return `${plural(M.plans.length,"plan")}, ${M.plans.filter(p=>p.status==="building").length} building`;
    case "lab-notebook/deadlines":{const o=M.deadlines.filter(i=>!i.done&&dlWhen(i)>=now).sort((x,y)=>dlWhen(x)-dlWhen(y));return o.length?`${o.length} upcoming, next in ${dlCountdown(o[0],now).t}`:"Nothing upcoming"}
    case "literature-hub/radar":return M.topics.length?`${M.unseen.length} new, ${plural(M.topics.length,"topic")}, ${M.saved.filter(s=>!s.read).length} to read`:"No topics yet";
    case "literature-hub/citations":return M.author?`${(M.author.cites||0).toLocaleString("en-GB")} citations, h ${M.author.h||0}`:"Not set up";
    case "structure-studio/viewer":return `<span id="recentCount">Recent structures on this device</span>`;
    case "paper-kit/schemes":return `${plural(M.schemes.length,"scheme")}`;
''')
rep('''    const st=suiteState(s.id), dataApps=s.apps.filter(a=>a.file);
    const last=Math.max(0,...dataApps.map(a=>obj(st.apps[a.file]).at||0));
    const note=dataApps.length?(st.on?"Automatic backups on":"Automatic backups off")+(last?`, last ${ago(last)}`:""):"Calculators, nothing stored";''',
    '''    const dataApps=s.apps.filter(a=>a.file), ssc=SYNC()&&SYNC().configured();
    const note=dataApps.length?(ssc?"Synced between your devices":"Kept on this device"):"Nothing stored";''')

# ---------- BACKUP ----------
rep('''  "research-log":j=>arr(obj(j["researchlog.v1"]).entries).length,''', '''  "research-log":j=>arr(obj(j["researchlog.v1"]).entries).length,
  "task-list":j=>arr(obj(j["tasks.v1"]).items).length,''')
cut('  "paper-library":j=>arr(obj(j["paperlib.v1"]).papers).length,', '  "citation-tracker":', '''  "literature-radar":j=>arr(obj(j["litradar.v1"]).topics).length+arr(obj(j["litradar.v1"]).saved).length,
''')
cut('  "hpc-tracker":j=>', '  "structure-viewer":', '')
rep('''  "journal-selector":j=>{const o=obj(j["bench.journals"]);return arr(o.added).length+Object.keys(obj(o.over)).length+arr(o.deleted).length},
''', '')
rep('''  "settings":j=>j["controlcenter.v1"]?1:0,
  "structure-watcher":j=>arr(obj(j["structwatch.v1"]).searches).length
};''', '''  "settings":j=>j["controlcenter.v1"]?1:0
};''')
rep('''const UNIT={"research-log":["entry","entries"],"idea-board":["idea"],"script-planner":["plan"],"deadline-tracker":["deadline"],"paper-library":["paper"],
  "literature-radar":["topic"],"citation-tracker":["work"],"hpc-tracker":["job or allocation","jobs and allocations"],"job-script-generator":["preset"],"benchmark-log":["run"],
  "command-vault":["command"],"structure-watcher":["search","searches"],"structure-viewer":["preference set"],"mechanism-scheme-editor":["scheme"],"journal-selector":["change"],"settings":["settings file"]};''',
    '''const UNIT={"research-log":["entry","entries"],"task-list":["task"],"idea-board":["idea"],"script-planner":["plan"],"deadline-tracker":["deadline"],
  "literature-radar":["topic or saved paper","topics and saved papers"],"citation-tracker":["work"],"structure-viewer":["preference set"],"mechanism-scheme-editor":["scheme"],"settings":["settings file"]};''')

cut('function renderBackup(){', '/* =====================================================================\n   Sheets:', r'''function syncCard(){
  const S=SYNC();
  if(!S) return card("Sync between your devices",empty("suite-sync.js is missing next to this page, so sync is not available."),{cls:"span2"});
  const ss=S.status();
  if(!ss.configured) return card("Sync between your devices",`<p style="margin:0 0 8px">Off. {{APP_NAME}} keeps your data in this browser only. Turn on sync to have the same tasks, notes, papers and schemes on your Mac and your iPhone: each device keeps a copy and they meet in a <b>private</b> GitHub repository that only you can read.</p>
    <div class="btnrow"><button class="btn primary" data-op="sync-setup">Set up sync</button></div>
    <p class="muted" style="font-size:.82rem;margin:10px 0 0">You need a private repository for the data (it can be empty) and a GitHub token that can change only that repository. The set-up explains both.</p>`,{cls:"span2",id:"s-sync"});
  const dot=ss.state==="error"?`<span class="over">●</span>`:ss.state==="offline"||ss.pending?`<span class="soon">●</span>`:`<span class="ok">●</span>`;
  const line=ss.busy?"Syncing...":ss.state==="error"?`Last sync failed: ${esc(ss.error)}`:ss.state==="offline"?esc(ss.error||"Offline"):
    ss.pending?`${plural(ss.pending,"change")} waiting to sync`:ss.last?`In sync. Last sync ${esc(ago(ss.last))}${ss.pulled||ss.pushed?` (${ss.pushed} sent, ${ss.pulled} received)`:""}.`:"Not synced yet.";
  const conf=S.conflicts();
  const nameOf=k=>{const a=DATA_APPS.find(x=>owned(x,k));return a?a.name:k==="suite.me"?"Your names":k};
  const confHTML=conf.length?`<h3>Versions replaced by a sync</h3><p class="muted" style="font-size:.82rem;margin:0 0 6px">When the same app changed on two devices before they synced, the newer edit was kept. The other version is here in case you need it.</p>
    <div class="rows">${conf.map(c=>`<div class="row" style="--cc:var(--gold)"><span class="bar"></span><div class="main"><div class="t">${esc(nameOf(c.key))}</div><div class="m"><span>version from ${esc(c.from)}</span>${c.t?`<span>edited ${esc(fmtWhen(c.t))}</span>`:""}<span>replaced ${esc(ago(c.at))}</span><span>${size(c.size*2)}</span></div></div>
      <div class="side"><button class="txtbtn" data-op="sync-restore" data-i="${c.i}">Restore</button><button class="txtbtn" data-op="sync-drop" data-i="${c.i}">Dismiss</button></div></div>`).join("")}</div>`:"";
  return card("Sync between your devices",`<p style="margin:0 0 4px">${dot} ${line}</p>
    <div class="kv" style="margin:6px 0 12px"><span>Repository <b>${esc(ss.repo)}</b></span><span>This device <b>${esc(ss.device)}</b></span>${ss.auto?"<span>Automatic</span>":"<span class=\"soon\">Automatic sync off</span>"}</div>
    <div class="btnrow"><button class="btn primary" data-op="sync-now" ${ss.busy?"disabled":""}>Sync now</button><button class="btn" data-op="sync-settings">Settings</button><a class="btn ghost" href="https://github.com/${esc(ss.repo)}/commits" target="_blank" rel="noopener">History on GitHub</a></div>
    <p class="muted" style="font-size:.82rem;margin:10px 0 0">Changes sync a few seconds after you make them, when you open {{APP_NAME}} and every few minutes while it is open. Every sync is a commit in the repository, so its history is also a complete backup.</p>${confHTML}`,{cls:"span2",id:"s-sync"});
}
function renderBackup(){
  const bs=backupSummary(), lastB=+LS.get("controlcenter.lastBundle")||0, last=+LS.get("controlcenter.lastAll")||0;
  const st=settings();
  const suitesWithData=SUITES.filter(s=>!s.hidden&&s.apps.some(a=>a.file));
  const onCount=suitesWithData.filter(s=>suiteState(s.id).on).length;
  const fileCard=card("Back up to a file",`<div class="kv" style="margin:0 0 12px"><span>Last download ${esc(ago(lastB))}</span>${SRV.ok?`<span>Last full backup to the server ${esc(ago(last))}</span>`:""}</div>
    <div class="btnrow"><button class="btn primary" data-op="bundle" ${STORAGE_OK&&SRV.http?"":"disabled"}>Download everything as one file</button>${SRV.ok?`<button class="btn" data-op="backup-all" ${STORAGE_OK&&SRC.mode==="auto"?"":"disabled"}>Back up all apps to the server</button>`:""}<button class="btn" data-op="restore-open">Restore…</button></div>
    <p class="muted" style="font-size:.82rem;margin:10px 0 0">One JSON file with every app. On an iPhone, choose <b>Save to Files</b> and pick iCloud Drive; on a Mac it goes to Downloads (move it to iCloud Drive if you like). Restore it here, on this or any other device. Your GitHub token and OpenAlex key are never written into it.</p>`,{cls:"span2"});
  const auto=SRV.ok?card("Automatic backups to the server",`<div class="bkgrid">
      <label class="sw"><span>Back up changes while the control center is open<small>Every 2 minutes and when you leave the page, only apps that changed.</small></span><input type="checkbox" role="switch" data-op="auto" ${st.auto?"checked":""}></label>
      <label class="sw"><span>Automatic backups inside every suite<small>${onCount} of ${suitesWithData.length} suites have it on.</small></span><input type="checkbox" role="switch" data-op="auto-suites" ${onCount===suitesWithData.length?"checked":""}></label>
    </div>`):"";
  const total=LS.keys().reduce((n,k)=>n+bytesOfKey(k),0), quota=5*1048576;
  const loose=LS.keys().filter(k=>!ownedByAny(k)&&!isPrivate(k));
  const big=DATA_APPS.map(a=>({a,b:bytesOf(a)})).filter(x=>x.b).sort((x,y)=>y.b-x.b).slice(0,4);
  const storage=card("Storage on this device",`<div class="meter"><div style="width:${Math.min(100,total/quota*100).toFixed(1)}%"></div></div>
    <div class="kv"><span><b>${size(total)}</b> of about 5 MB that browsers usually allow per site</span></div>
    ${big.length?`<div class="kv" style="margin-top:6px">${big.map(x=>`<span>${esc(x.a.name)} <b>${size(x.b)}</b></span>`).join("")}</div>`:""}
    <p class="note" id="persistLine" style="font-size:.8rem;margin:8px 0 0;color:var(--muted)">${plural(loose.length,"other key")} (reminders, suite settings, open tabs) go into the single-file download. Recent structures in the viewer are kept in a separate database, only on this device.</p>`);
  const S=SYNC(), ss=S?S.status():null, pend=new Set(ss&&ss.configured?S.pendingKeys():[]);
  const groups=SUITES.filter(s=>s.apps.some(a=>a.file)).map(s=>{
    const rows=s.apps.filter(a=>a.file).map(a=>{
      const ks=keysOf(a), live=ks.length?COUNT[a.file](snapshot(a).json):0;
      let pill;
      if(!ks.length) pill=["none","Empty"];
      else if(SRV.ok){const k=bkState(a);pill={ok:["ok","Saved"],changed:["chg","Changed"],never:["chg","Not backed up"],err:["err","Failed"],none:["none","Empty"]}[k.k]}
      else if(ss&&ss.configured) pill=ks.some(k=>pend.has(k))?["chg","Waiting to sync"]:["ok","Synced"];
      else pill=["none","This device only"];
      const bits=ks.length?[`${unitOf(a,live)}, ${size(bytesOf(a))}`]:[];
      return `<div class="bkapp" style="--cc:${cc(a)}"><div class="main"><b>${esc(a.name)}</b> <span class="state ${pill[0]}">${pill[1]}</span><div class="m">${bits.join(" · ")||"Nothing stored on this device"}</div></div>
        ${SRC.mode==="file"||(SRV.ok&&SRV.filesOf(a).length)?`<button class="txtbtn" data-op="restore-open" data-files="${esc(a.file)}">Restore</button>`:""}</div>`;
    }).join("");
    return `<h3>${esc(s.title)}</h3><div class="bkgrid">${rows}</div>`;
  }).join("");
  const appsCard=card("Apps on this device",groups,{cls:"span2"});
  $("#v-backup").innerHTML=`<div class="grid two">${syncCard()}${fileCard}${auto}${storage}${appsCard}</div>`;
}

/* ---------------- sync: set up and settings ---------------- */
function openSyncSetup(){
  const S=SYNC(); if(!S){toast("Sync is not available here");return}
  let choice=null, info=null;
  openSheet(`<h2 id="dlgTitle">Sync between your devices</h2>
    <p class="note">Each device keeps its own copy of your data and they meet in a private GitHub repository. Do this once on every device (Mac, iPhone, iPad), with the same repository and token.</p>
    <ol class="note" style="margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px">
      <li>A <b>private</b> repository on GitHub for the data. It can be empty; {{APP_NAME}} creates a <code>data</code> folder in it.</li>
      <li>A token: on GitHub, Settings › Developer settings › Fine-grained tokens › <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener" style="color:var(--accent2)">Generate new token</a>. Repository access: <b>only</b> the data repository. Permissions: <b>Contents, read and write</b>. Pick an expiry you are happy with (you can make a new one later).</li>
    </ol>
    <label>Data repository<input id="syRepo" value="{{SYNC_REPO}}" placeholder="owner/name" autocomplete="off" autocapitalize="off" spellcheck="false"></label>
    <label>Token<input id="syTok" type="password" placeholder="github_pat_..." autocomplete="off" autocapitalize="off" spellcheck="false"></label>
    <label>Name of this device<input id="syDev" value="${esc(S.defaultDevice())}" maxlength="40" autocomplete="off"></label>
    <div id="syChoice"></div>
    <p class="note">The token is kept only on this device and is never synced or written into backup files. Anyone who can use this browser could read it, so use a token limited to the data repository.</p>
    <p class="hint" id="sheetHint"></p>
    <div class="sbar"><button type="button" class="btn ghost" data-close>Cancel</button><button type="submit" class="btn primary" id="syGo">Check and connect</button></div>`,async()=>{
    const go=$("#syGo"), repo=val("syRepo"), tok=$("#syTok").value.trim(), dev=val("syDev");
    hint(""); go.disabled=true; go.innerHTML=`<span class="spin"></span>${info?"Connecting":"Checking"}`;
    try{
      if(!info||info.repo.toLowerCase()!==(S.cleanRepo(repo)||"").toLowerCase()){
        info=await S.inspect(repo,tok);
        if(!info.private){hint("That repository is public, so anyone could read your notes. Make it private on GitHub (Settings › General › Danger zone › Change visibility) and try again.");info=null;return}
        if(info.remoteKeys&&info.localKeys){
          $("#syChoice").innerHTML=`<h4>Both sides already have data</h4><div class="picklist" style="max-height:none">
            <label class="pick"><input type="radio" name="syPref" value="remote" checked><div><b>Use the data in GitHub on this device</b><div class="m">Right for a second device. Where both have the same app, this device takes the GitHub copy; this device's version is kept under Versions replaced by a sync.</div></div></label>
            <label class="pick"><input type="radio" name="syPref" value="local"><div><b>Keep this device's data</b><div class="m">This device's apps replace the GitHub copy where both have them; the GitHub version stays in the repository history and under Versions replaced.</div></div></label></div>`;
          go.textContent="Connect"; return;
        }
      }
      choice=(sheet.querySelector('input[name="syPref"]:checked')||{}).value||(info.remoteKeys?"remote":"local");
      const st=await S.connect({repo:info.repo,token:tok,device:dev,prefer:choice});
      dlg.close();
      await refresh(false);
      toast(st.state==="ok"?`Sync is on: ${st.pushed} sent, ${st.pulled} received`:st.error||"Sync is on, but the first sync failed");
    }catch(e){hint(e&&e.message?e.message:String(e))}
    finally{if(go.isConnected){go.disabled=false;if(!/Connect$/.test(go.textContent))go.textContent=info&&$("#syChoice").innerHTML?"Connect":"Check and connect"}}
  });
  const r=$("#syRepo"); if(r&&!r.value) r.focus(); else { const tk=$("#syTok"); if(tk) tk.focus(); }
}
function openSyncSettings(){
  const S=SYNC(); if(!S) return; const c=S.config(); if(!c){openSyncSetup();return}
  openSheet(`<h2 id="dlgTitle">Sync settings</h2>
    <div class="kv"><span>Repository <b>${esc(c.repo)}</b></span><span>Folder <b>${esc(c.dir)}</b></span>${c.since?`<span>Connected ${esc(fmtWhen(c.since))}</span>`:""}</div>
    <label>Name of this device<input id="syDev" value="${esc(c.device)}" maxlength="40" autocomplete="off"></label>
    <label class="sw"><span>Sync automatically<small>When off, sync only runs when you tap Sync now.</small></span><input type="checkbox" role="switch" id="syAuto" ${c.auto?"checked":""}></label>
    <p class="note">To use a new token (they expire), turn sync off here and set it up again with the same repository; nothing is lost.</p>
    <div class="sbar"><button type="button" class="btn danger" id="syOff">Turn sync off</button><button type="submit" class="btn primary">Save</button></div>`,()=>{
    S.update({device:val("syDev")||c.device,auto:$("#syAuto").checked}); dlg.close(); render(); toast("Saved");
  });
  $("#syOff").addEventListener("click",()=>{
    if(!confirm("Turn sync off on this device? Your data stays here and in the repository; the token is removed from this device.")) return;
    S.disconnect(); dlg.close(); render(); toast("Sync is off on this device");
  });
}

''')

# ---------- adding things ----------
rep('''const CAP_TYPES=[["log","Log entry","log"],["idea","Idea","ideas"],["deadline","Deadline","deadlines"],["job","Calculation","jobs"],["cmd","Command","commands"],["paper","Paper","papers"]];''',
    '''const CAP_TYPES=[["task","Task","tasks"],["log","Log entry","log"],["idea","Idea","ideas"],["deadline","Deadline","deadlines"],["paper","Paper","radar"]];''')
rep('''  kind=kind||UI.get("capKind","log");''', '''  kind=kind||UI.get("capKind","task");''')
rep('''  go.textContent={log:"Add to log",idea:"Add idea",deadline:"Add deadline",job:"Add calculation",cmd:"Save command",paper:"Save paper"}[kind];
  if(kind==="log"){''', '''  go.textContent={task:"Add task",log:"Add to log",idea:"Add idea",deadline:"Add deadline",paper:"Save to reading list"}[kind];
  if(kind==="task"){
    box.innerHTML=`<label>Task<input id="tTitle" maxlength="200" value="${esc(pre.title||"")}" placeholder="What needs doing"></label>
      <div class="f2"><label>Project<input id="tProj" list="dlProjects" value="${esc(pre.proj||"")}" autocomplete="off"></label><label>Priority<select id="tPrio"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label></div>
      <div class="f2"><label>Do on<input id="tPlan" type="date" value="${esc(pre.plan??todayStr())}"></label><label>Due (optional)<input id="tDue" type="date" value="${esc(pre.due||"")}"></label></div>
      <label>Notes<textarea id="tNotes" placeholder="Optional. Subtasks can be added in Tasks.">${esc(pre.notes||"")}</textarea></label>`;
    $("#tTitle").focus();
  }else if(kind==="log"){''')
cut('  }else if(kind==="job"){', '  }else if(kind==="paper"){', '')
rep('''      <div class="f3"><label>Journal<input id="pVenue"></label><label>Year<input id="pYear" inputmode="numeric"></label><label>DOI<input id="pDoi" class="mono" autocapitalize="off"></label></div>
      <label>Collection<select id="pColl"><option value="">Unsorted</option>${D.colls.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("")}</select></label>`;''',
    '''      <div class="f3"><label>Journal<input id="pVenue"></label><label>Year<input id="pYear" inputmode="numeric"></label><label>DOI<input id="pDoi" class="mono" autocapitalize="off"></label></div>
      <p class="note">Goes to the reading list in the literature radar.</p>`;''')
rep('''    const have=doi=>!!doi&&D.papers.some(p=>(p.doi||"").toLowerCase()===doi);''',
    '''    const have=doi=>!!doi&&D.saved.some(p=>(p.doi||"").toLowerCase()===doi);''')
rep('''already in your library''', '''already in your reading list''')
rep('''  const dup=h.doi&&D.papers.find(p=>(p.doi||"").toLowerCase()===h.doi.toLowerCase());''',
    '''  const dup=h.doi&&D.saved.find(p=>(p.doi||"").toLowerCase()===h.doi.toLowerCase());''')
cut('function jobCalc(){', 'async function submitCapture(){', '')
rep('''  const k=CAP.kind; let ok=false;
  if(k==="log"){
    const text=$("#cText").value.trim(); if(!text){hint("Write something first.");return}
    const jobId=CAP.pre.jobId, markDone=jobId&&$("#cJobDone")&&$("#cJobDone").checked;
    ok=await OPS.addLog({text,kind:CAP.logKind,proj:val("cProj"),date:val("cDate")||todayStr(),pin:$("#cPin").checked});
    if(ok&&markDone) await OPS.jobStatus(jobId,"analysed");
  }else if(k==="idea"){''', '''  const k=CAP.kind; let ok=false;
  if(k==="task"){
    const title=val("tTitle"); if(!title){hint("What is the task?");return}
    ok=await OPS.addTask({title,proj:val("tProj"),prio:val("tPrio"),plan:val("tPlan"),due:val("tDue"),notes:val("tNotes")});
  }else if(k==="log"){
    const text=$("#cText").value.trim(); if(!text){hint("Write something first.");return}
    ok=await OPS.addLog({text,kind:CAP.logKind,proj:val("cProj"),date:val("cDate")||todayStr(),pin:$("#cPin").checked});
  }else if(k==="idea"){''')
cut('  }else if(k==="job"){\n    const name=val("jName");', '  }else if(k==="paper"){', '')
rep('''    ok=await OPS.addPaper({title,doi,authors:val("pAuthors"),venue:val("pVenue"),year:val("pYear"),coll:val("pColl")});''',
    '''    ok=await OPS.addPaper({title,doi,authors:val("pAuthors"),venue:val("pVenue"),year:val("pYear")});''')
rep('''      ${pre.jobId?`<label class="check"><input type="checkbox" id="cJobDone" ${pre.jobStatus==="done"?"checked":""}> Mark the calculation as analysed</label>`:""}`;''', '''`;''')
cut('/* ---------------- commands, filled from a calculation ---------------- */', '/* ---------------- digest ---------------- */', '')

# ---------- digest ----------
cut('  const js=D.jobs.filter(j=>P(j.proj)), fin=', '  const acts=D.actions.filter(x=>!x.a.done&&P(x.m.proj))', '''  const tdone=D.tasks.filter(x=>x.done&&(x.doneAt||0)>=since&&P(x.proj)).sort((a,b)=>(a.doneAt||0)-(b.doneAt||0));
  if(tdone.length){L.push("## Tasks done","");tdone.forEach(x=>L.push(`- [x] ${x.title}${!proj&&x.proj?` (${x.proj})`:""}, ${localDate(x.doneAt)}`));L.push("")}
  const topen=D.tasks.filter(x=>!x.done&&P(x.proj)).sort(byUrgency);
  if(topen.length){L.push("## Open tasks","");topen.forEach(x=>L.push(`- [ ] ${x.title}${!proj&&x.proj?` (${x.proj})`:""}${x.due?`, due ${x.due}`:""}${x.prio==="high"?", high priority":""}`));L.push("")}
''')
cut('  const pps=D.papers.filter(p=>', '  const ids=D.ideas.filter(i=>', '''  const pps=D.saved.filter(p=>(p.saved||0)>=since&&(!m||T(p.title,p.topic)));
  if(pps.length){L.push("## Papers added to the reading list","");pps.forEach(p=>L.push(`- ${p.authors||"Unknown"} (${(p.date||"").slice(0,4)||"n.d."}). ${p.title}.${p.venue?" "+p.venue+".":""}${p.doi?" https://doi.org/"+p.doi:""}`));L.push("")}
''')
cut('  const rs=D.runs.filter(r=>', '  if(L.length<=4) L.push("Nothing recorded in this period.","");', '')
rep('''<p class="note">The research log and HPC tracker link by their Project field (these words count as the same project there). Deadlines, ideas, script plans, papers, benchmarks, radar topics and schemes link when their text mentions the name or any of these words (3 letters or more).</p>''',
    '''<p class="note">Tasks and the research log link by their Project field (these words count as the same project there). Deadlines, ideas, script plans, saved papers, radar topics and schemes link when their text mentions the name or any of these words (3 letters or more).</p>''')
rep('''<p class="note">The literature radar, the citation tracker and the journal selector search OpenAlex, which has asked for a free API key since February 2026.''',
    '''<p class="note">The literature radar and the citation tracker search OpenAlex, which has asked for a free API key since February 2026.''')
rep('''  const saveName=()=>{const v=val("meName");try{v?LS.set("suite.me",v):LS.del("suite.me")}catch(_){toast("Couldn't save the name")}if(D)render()};''',
    '''  const saveName=()=>{const v=val("meName");try{v?LS.set("suite.me",v):LS.del("suite.me")}catch(_){toast("Couldn't save the name")}if(SYNC())SYNC().changed();if(D)render()};''')
rep('''    try{k?LS.set("net.openalexKey",k):LS.del("net.openalexKey");m?LS.set("net.mailto",m):LS.del("net.mailto")}catch(_){toast("Couldn't save the online settings")}''',
    '''    try{k?LS.set("net.openalexKey",k):LS.del("net.openalexKey");m?LS.set("net.mailto",m):LS.del("net.mailto")}catch(_){toast("Couldn't save the online settings")}
    if(SYNC()) SYNC().changed();''')
rep('''function saveSettings(patch){const s={...settings(),...patch};try{LS.set(SET_KEY,JSON.stringify(s))}catch(_){toast("Couldn't save the setting")}return s}''',
    '''function saveSettings(patch){const s={...settings(),...patch};try{LS.set(SET_KEY,JSON.stringify(s))}catch(_){toast("Couldn't save the setting")}if(window.SuiteSync)window.SuiteSync.changed();return s}''')
rep('''<p class="note">One JSON file with ${plural(apps.length,"app")} and ${plural(loose.length,"other key")} (backup reminders, suite settings). Restore it here, on this or another device, with Restore, From a file. Each app inside it is a normal suite backup.</p>''',
    '''<p class="note">One JSON file with ${plural(apps.length,"app")} and ${plural(loose.length,"other key")} (backup reminders, suite settings). On an iPhone choose <b>Save to Files</b> (iCloud Drive). Restore it here, on this or another device, with Restore, From a file. Your GitHub token and OpenAlex key are not included.</p>''')
rep('''    if(saveFile(`suites-backup-${todayStr()}.json`,JSON.stringify(b))){''',
    '''    if(saveFile(`{{APP_SHORT}}-backup-${todayStr()}.json`,JSON.stringify(b))){''')
rep('''<p class="note">Choose a single download from the control center (suites-backup-DATE.json), or one or more dated app backups (DATE_suite_app.json).</p>''',
    '''<p class="note">Choose a single download from the control center ({{APP_SHORT}}-backup-DATE.json), a suite's backup file (suite-backup-DATE.json), or one or more dated app backups.</p>''')

# ---------- events ----------
rep('''    case "goto-calc": scrollToId("s-calc"); break;''', '''    case "goto-tasks": scrollToId("s-tasks"); break;''')
cut('    case "job-status": OPS.jobStatus(id,b.dataset.to); break;', '    case "idea-move": OPS.moveIdea(id,b.dataset.to); break;', '''    case "task-plan": OPS.planTask(id,b.dataset.day||todayStr()); break;
''')
rep('''    case "watch-seen": OPS.watchSeen(b.dataset.key); break;
''', '''    case "sync-setup": openSyncSetup(); break;
    case "sync-settings": openSyncSettings(); break;
    case "sync-now": if(SYNC()){b.disabled=true;b.innerHTML=`<span class="spin"></span>Syncing`;SYNC().syncNow().then(st=>{toast(st.state==="ok"?(st.pulled||st.pushed?`Synced: ${st.pushed} sent, ${st.pulled} received`:"Already in sync"):st.error||"Sync failed");render()})} break;
    case "sync-restore": if(SYNC()&&confirm("Bring back this version? It replaces the current data of that app on every device after the next sync.")){if(SYNC().restoreConflict(+b.dataset.i)){toast("Restored");refresh(false)}} break;
    case "sync-drop": if(SYNC()){SYNC().dropConflict(+b.dataset.i);render()} break;
''')
rep('''  if(op==="act-done") OPS.toggleAction(t.dataset.mid,t.dataset.aid,t.checked);''',
    '''  if(op==="act-done") OPS.toggleAction(t.dataset.mid,t.dataset.aid,t.checked);
  else if(op==="task-done") OPS.toggleTask(t.dataset.id,t.checked);''')
rep('''$("#fab").addEventListener("click",()=>openCapture(VIEW==="projects"?"log":undefined,VIEW==="projects"?{proj:(projectList().find(p=>p.key===UI.get("proj",""))||{}).name}:undefined));''',
    '''$("#fab").addEventListener("click",()=>openCapture(VIEW==="projects"?"task":undefined,VIEW==="projects"?{proj:(projectList().find(p=>p.key===UI.get("proj",""))||{}).name}:undefined));''')
rep('''window.addEventListener("pageshow",e=>{if(e.persisted)refresh(false)});''',
    '''window.addEventListener("pageshow",e=>{if(e.persisted)refresh(false)});
/* data that came in from another device, and sync state changes */
window.addEventListener("suite-sync-applied",()=>{if(!dlg.open)refresh(false);else loadData()});
let _sy=null;
if(window.SuiteSync) window.SuiteSync.onStatus(()=>{clearTimeout(_sy);_sy=setTimeout(()=>{if(D&&!dlg.open&&(VIEW==="today"||VIEW==="backup"||VIEW==="apps"))render();else if(D)renderChrome()},150)});''')

open(P, "w", encoding="utf-8").write(t)
print("part B applied")
