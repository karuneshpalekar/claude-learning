const D=window.DATA,$=s=>document.querySelector(s);
const store={get(k,d){try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
let prog=store.get('prog',{}); // slug -> {best, total, last}
const esc=s=>String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const md=s=>esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>').replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
const list=a=>a&&a.length?'<ul>'+a.map(x=>`<li>${md(x)}</li>`).join('')+'</ul>':'';
const link=u=>u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\//,''))}</a>`:'';
const shuffle=a=>{a=[...a];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a};
function side(){
  let h='<button class="nav" data-go="home"><span class="n">⌂</span><span class="t">Dashboard</span></button><button class="nav" data-go="mock"><span class="n">★</span><span class="t">Mock exam (all topics)</span></button><button class="nav" data-go="weak"><span class="n">!</span><span class="t">Weak-area drill</span></button><div class="sec-title">Objectives</div>';
  D.forEach((d,i)=>{const p=prog[d.slug];const t=p?`<span class="tag ${p.best>=90?'done':'mid'}">${p.best}%</span>`:'';
    h+=`<button class="nav" data-go="obj:${d.slug}"><span class="n">${i+1}</span><span class="t">${esc(d.title)}</span>${t}</button>`});
  $('#side').innerHTML=h;
  const done=Object.values(prog).filter(p=>p.best>=90).length;$('#overall').textContent=`${done}/${D.length} mastered (≥90%)`;
}
function go(r){location.hash=r}
function route(){
  const r=location.hash.slice(1)||'home';if(mq.matches)setSide(false);side();window.scrollTo(0,0);
  if(r==='home')home();else if(r==='mock')startQuiz('Mock exam',shuffle(D.flatMap(d=>d.quiz.map(q=>({...q,slug:d.slug})))).slice(0,60),null);
  else if(r==='weak')weak();else if(r.startsWith('obj:')){const[,s,tab]=r.split(':');obj(s,tab||'notes')}
  document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('on',b.dataset.go===r.split(':').slice(0,2).join(':')))
}
function home(){
  $('#main').innerHTML=`<h2>Your path to 1000</h2><p class="mut">Content is drawn only from Anthropic's official documentation (Claude docs, Claude Code docs, Anthropic engineering/research, MCP spec).</p>
  <div class="card"><h3>Suggested track</h3><ol><li>Work through the objectives in order, starting with the ones you feel least sure about.</li><li>For each: read the <b>Notes</b>, skim the <b>Takeaways</b>, then take the <b>Quiz</b> until you score ≥90%.</li><li>Run the <b>Weak-area drill</b> to re-ask questions you got wrong.</li><li>Finish with 2-3 <b>Mock exams</b>.</li></ol></div>
  <h3>All objectives</h3><div class="grid">${D.map((d,i)=>{const p=prog[d.slug];return `<button class="tile" data-go="obj:${d.slug}"><b>${i+1}. ${esc(d.title)}</b><div class="mut">${d.sections.length} topics · ${d.quiz.length} questions</div><div class="mut">${p?'Best quiz: '+p.best+'%':'Not started'}</div></button>`}).join('')}</div>
  <p class="mut" style="margin-top:28px">${D.reduce((a,d)=>a+d.quiz.length,0)} practice questions in total. <button class="btn" id="reset">Reset progress</button></p>`;
  $('#reset').onclick=()=>{if(confirm('Clear all saved quiz progress?')){prog={};store.set('prog',prog);store.set('wrong',[]);route()}};
}
function obj(slug,tab){
  const d=D.find(x=>x.slug===slug);if(!d)return;
  const tabs=[['notes','Notes'],['take','Takeaways'],['gloss','Glossary'],['flash','Flashcards'],['quiz','Quiz'],['src','Sources']];
  let body='';
  if(tab==='notes')body=d.sections.map((s,i)=>`<div class="card"><h3>${i+1}. ${esc(s.heading)}</h3>${list(s.notes)}${s.example?`<div class="ex"><b>Example${s.example.title?' · '+esc(s.example.title):''}</b>${s.example.code?`<pre><code>${esc(s.example.code)}</code></pre>`:''}</div>`:''}${s.examTips&&s.examTips.length?`<div class="tips"><b>Exam tips</b>${list(s.examTips)}</div>`:''}${s.source?`<div class="src">Source: ${link(s.source)}</div>`:''}</div>`).join('');
  else if(tab==='take')body=`<div class="card"><h3>Must-remember facts</h3>${list(d.keyTakeaways)}</div>`;
  else if(tab==='gloss')body=`<div class="card">${d.glossary.length?d.glossary.map(g=>`<p><b>${esc(g.term)}</b> — ${md(g.definition)}</p>`).join(''):'<p class="mut">No glossary for this objective.</p>'}</div>`;
  else if(tab==='src')body=`<div class="card"><ul>${d.sources.map(s=>`<li>${esc(s.title||'')} ${link(s.url)}</li>`).join('')}</ul></div>`;
  $('#main').innerHTML=`<h2>${esc(d.title)}</h2><p>${md(d.overview||'')}</p><div class="tabs">${tabs.map(([k,l])=>`<button data-go="obj:${slug}:${k}" class="${k===tab?'on':''}">${l}</button>`).join('')}</div><div id="body">${body}</div>`;
  if(tab==='flash')flash(d);
  if(tab==='quiz')startQuiz(d.title,shuffle(d.quiz.map(q=>({...q,slug}))),slug,$('#body'));
}
function flash(d){
  const cards=d.keyTakeaways.map((t,i)=>({q:'Key fact #'+(i+1)+' — recall it, then tap to reveal',a:t})).concat(d.glossary.map(g=>({q:g.term,a:g.definition})));
  let i=0,show=false;const el=$('#body');
  const draw=()=>{const c=cards[i];el.innerHTML=cards.length?`<p class="mut">${i+1} / ${cards.length}</p><div class="card flash" id="fc">${show?md(c.a):esc(c.q)}</div><button class="btn" id="pv">←</button> <button class="btn" id="sh">Flip</button> <button class="btn pri" id="nx">→</button>`:'<p class="mut">No cards.</p>';
    if(!cards.length)return;$('#fc').onclick=$('#sh').onclick=()=>{show=!show;draw()};$('#nx').onclick=()=>{i=(i+1)%cards.length;show=false;draw()};$('#pv').onclick=()=>{i=(i-1+cards.length)%cards.length;show=false;draw()}};
  draw();
}
function weak(){
  const w=store.get('wrong',[]);const qs=[];D.forEach(d=>d.quiz.forEach((q,i)=>{if(w.includes(d.slug+'#'+i))qs.push({...q,slug:d.slug})}));
  if(!qs.length){$('#main').innerHTML='<h2>Weak-area drill</h2><p>No missed questions yet. Take some objective quizzes first — anything you miss lands here.</p>';return}
  startQuiz('Weak-area drill',shuffle(qs),null);
}
function startQuiz(title,qs,slug,host){
  host=host||$('#main');let i=0,score=0,miss=[];
  if(!qs.length){host.innerHTML='<p class="mut">No questions available.</p>';return}
  const draw=()=>{
    if(i>=qs.length){const pct=Math.round(100*score/qs.length);
      if(slug){const p=prog[slug]||{best:0};prog[slug]={best:Math.max(p.best,pct),last:pct};store.set('prog',prog)}
      host.innerHTML=`<div class="card"><h3>${esc(title)} — ${score}/${qs.length} (${pct}%)</h3><p>${pct>=90?'Excellent — mastered.':pct>=75?'Good. Review the misses below.':'Re-read the notes, then retry.'}</p>${miss.length?'<h3>Review</h3>'+miss.map(m=>`<div class="card"><b>${md(m.q)}</b><p>✔ ${md(m.options[m.answer])}</p><div class="exp">${md(m.explanation||'')}</div></div>`).join(''):''}<button class="btn pri" id="again">Retry</button></div>`;
      $('#again').onclick=()=>startQuiz(title,shuffle(qs),slug,host);side();return}
    const q=qs[i];const order=shuffle(q.options.map((o,k)=>k));
    host.innerHTML=`<div class="bar"><i style="width:${100*i/qs.length}%"></i></div><div class="card"><p class="mut">${esc(title)} · Question ${i+1}/${qs.length}</p><h3>${md(q.q)}</h3>${order.map(k=>`<button class="opt" data-k="${k}">${md(q.options[k])}</button>`).join('')}<div id="fb"></div></div>`;
    host.querySelectorAll('.opt').forEach(b=>b.onclick=()=>{const k=+b.dataset.k,ok=k===q.answer;
      host.querySelectorAll('.opt').forEach(x=>{x.disabled=true;if(+x.dataset.k===q.answer)x.classList.add('ok')});if(!ok)b.classList.add('bad');
      const w=store.get('wrong',[]),d=D.find(x=>x.slug===q.slug),id=q.slug+'#'+d.quiz.findIndex(z=>z.q===q.q),at=w.indexOf(id);
      if(ok){score++;if(at>=0)w.splice(at,1)}else{miss.push(q);if(at<0)w.push(id)}store.set('wrong',w);
      $('#fb').innerHTML=`<div class="exp"><b>${ok?'Correct.':'Not quite.'}</b> ${md(q.explanation||'')}${q.source?`<div class="src">${link(q.source)}</div>`:''}</div><p><button class="btn pri" id="nq">${i+1<qs.length?'Next':'Finish'}</button></p>`;
      $('#nq').onclick=()=>{i++;draw()}});
  };draw();
}
document.addEventListener('click',e=>{const t=e.target.closest('[data-go]');if(t){go(t.dataset.go)}});
const mq=matchMedia('(max-width:900px)');
function setSide(open){document.body.classList.toggle('collapsed',!open);$('#menu').setAttribute('aria-expanded',open);if(!mq.matches)store.set('sideOpen',open)}
setSide(mq.matches?false:store.get('sideOpen',true));
$('#menu').onclick=()=>setSide(document.body.classList.contains('collapsed'));
$('#scrim').onclick=()=>setSide(false);
const isDark=()=>{const t=document.documentElement.dataset.theme;return t?t==='dark':matchMedia('(prefers-color-scheme:dark)').matches};
function paintTheme(){$('#theme').textContent=isDark()?'☀':'☾'}
$('#theme').onclick=()=>{const t=isDark()?'light':'dark';document.documentElement.dataset.theme=t;try{localStorage.setItem('theme',t)}catch(e){}paintTheme()};
paintTheme();
window.addEventListener('hashchange',route);route();
