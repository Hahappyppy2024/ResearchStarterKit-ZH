import {knowledgeApi as api} from './paper-knowledge.js';
import {openReader} from './paper-reader.js';
import {openPaperAffiliations} from './paper-labs.js';
import {mountQuizToggle} from './paper-quiz-ui.js';
import {notifyRequiredReading} from './required-reading-updates.js';
import {chinaTime} from './schedule.mjs';
import {paperPdfUrl,togglePaperTodo,paperTodoInDay} from './catalog-actions.mjs';
const widgets=new Set();let favoriteRequest=null,favoriteValues={},queueCache=new Map();
let issueRequest=null;
const issueWidgets=new Set();
function loadIssues(force=false){if(!issueRequest||force)issueRequest=api('paper-questions?mode=counts');return issueRequest;}
function mountIssueCounts(host,p){const group=document.createElement('span'),link=document.createElement('a');group.className='paper-issue-counts';link.className='button paper-issue-summary';link.href='http://127.0.0.1:8866/paper-questions.html?'+new URLSearchParams({paperId:p.id});link.textContent='问题 · 加载中';link.title='查看这篇论文的全部问题';group.append(link);const heading=host.querySelector('.paper-status-heading'),title=host.querySelector('.bilingual-paper-title');if(heading)heading.append(group);else if(title?.parentElement===host)title.after(group);else host.append(group);issueWidgets.add({host:group,id:p.id,link});loadIssues().then(paintIssues).catch(()=>{link.textContent='问题 · 点击查看';});}
function paintIssues(data){for(const w of issueWidgets){if(!w.host.isConnected){issueWidgets.delete(w);continue;}const count=data.byPaper?.[w.id]||{open:0,resolved:0};w.link.textContent='问题 · 未解决 '+count.open+' / 已解决 '+count.resolved;}}
function refreshIssues(){loadIssues(true).then(paintIssues).catch(()=>{});}
window.addEventListener('paper-questions-change',refreshIssues);window.addEventListener('focus',refreshIssues);window.addEventListener('storage',e=>{if(e.key==='paper-questions-updated')refreshIssues();});
const style=document.createElement('style');style.textContent='.paper-issue-counts{display:inline-flex;gap:8px;align-items:center}.paper-issue-open{color:#287d46!important}.paper-issue-resolved{color:#8055b5!important}.paper-catalog-actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px 18px;margin:12px 0}.paper-catalog-group{display:flex;align-items:center;flex-wrap:wrap;gap:8px}.paper-catalog-group+ .paper-catalog-group{border-left:1px solid var(--theme-line);padding-left:16px}.paper-catalog-actions button,.paper-catalog-actions a{font-size:12px;padding:7px 10px;border-radius:8px}.paper-catalog-actions .catalog-read{background:var(--theme-accent);border-color:var(--theme-accent);color:var(--theme-paper,#fff)}.paper-catalog-actions label{display:inline-flex;align-items:center;gap:5px;font-size:12px;white-space:nowrap;margin:0!important}.paper-catalog-actions input[type=checkbox]{width:17px;height:17px}.paper-catalog-actions [aria-pressed=true]{background:var(--theme-soft);border-color:var(--theme-accent)}.paper-catalog-actions [aria-disabled=true]{opacity:.5;cursor:default}.catalog-error:empty{display:none}.paper-catalog-actions .catalog-error{flex-basis:100%;font-size:11px;color:#a33e3e}@media(max-width:650px){.paper-catalog-group+ .paper-catalog-group{border-left:0;padding-left:0}}';document.head.append(style);
export function loadPaperFavorites(force=false){if(!favoriteRequest||force)favoriteRequest=api('paper-featured').then(values=>{favoriteValues=values;return values;}).catch(e=>{favoriteRequest=null;throw e;});return favoriteRequest;}
function toggleLabel(button,full,short){button.textContent=short==='精选'?'♥':full;button.title=full;button.setAttribute('aria-label',full);}
function celebrateFavorite(button){
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const r=button.getBoundingClientRect(),burst=document.createElement('span');burst.className='favorite-heart-burst';burst.setAttribute('aria-hidden','true');burst.style.left=(r.left+r.width/2)+'px';burst.style.top=(r.top+r.height/2)+'px';
 for(let i=0;i<12;i++){const heart=document.createElement('i'),angle=i*Math.PI/6,distance=35+(i%3)*11;heart.textContent='♥';heart.style.setProperty('--heart-x',Math.cos(angle)*distance+'px');heart.style.setProperty('--heart-y',Math.sin(angle)*distance+'px');heart.style.setProperty('--heart-turn',((i%2?1:-1)*24)+'deg');heart.style.setProperty('--heart-delay',(i%3)*18+'ms');burst.append(heart);}
 document.body.append(burst);button.animate?.([{transform:'scale(1)'},{transform:'scale(1.2)'},{transform:'scale(1)'}],{duration:300,easing:'ease-out'});setTimeout(()=>burst.remove(),950);
}
function paintFavorites(){for(const w of widgets){if(!w.host.isConnected){widgets.delete(w);continue;}if(!w.star)continue;const enabled=Object.hasOwn(favoriteValues,w.id)?favoriteValues[w.id]:w.initial;toggleLabel(w.star,enabled?'移出精选':'加入精选','精选');w.star.setAttribute('aria-pressed',String(enabled));}}
function todoContains(id){try{return paperTodoInDay(JSON.parse(localStorage.getItem('daily-practice-v1')||'{"days":{}}').days[chinaTime().date],id);}catch{return false;}}
function paintTodos(){for(const w of widgets){if(!w.host.isConnected){widgets.delete(w);continue;}const added=todoContains(w.id);toggleLabel(w.todo,added?'移除 Todo List':'加入 Todo List','Todo List');w.todo.setAttribute('aria-pressed',String(added));}}
export function mountCatalogActions(host,p,options={}){
 const wrap=document.createElement('div'),reading=document.createElement('div'),planning=document.createElement('div'),error=document.createElement('small');wrap.className='paper-catalog-actions';reading.className=planning.className='paper-catalog-group';reading.setAttribute('role','group');reading.setAttribute('aria-label','阅读与作者');planning.setAttribute('role','group');planning.setAttribute('aria-label','加入计划与精选');error.className='catalog-error';error.setAttribute('role','status');
 const button=(name,action)=>{const b=document.createElement('button');b.type='button';b.textContent=name;b.className='button';b.onclick=action;return b;};
 const pdf=document.createElement('a'),url=paperPdfUrl(p);pdf.className='button';pdf.textContent='原文 PDF 🔗';if(url){pdf.href=new URL('paper.html?id='+encodeURIComponent(p.id),import.meta.url).href;pdf.title='在阅读工作台中查看原文与笔记';pdf.target='_blank';pdf.rel='noopener';}else{pdf.setAttribute('aria-disabled','true');pdf.title='尚未收录公开 PDF，可在开始阅读中查看题录';}
 const read=button('开始阅读',()=>openReader(p.id)),lab=button('实验室学者',()=>openPaperAffiliations(p));read.classList.add('catalog-read');
 const {required,todo,widget,page}=mountPaperPlanButtons(planning,p,{...options,compact:true});
 const star=button(options.featured?'移出精选':'加入精选',async()=>{star.disabled=true;error.textContent='';try{await loadPaperFavorites();const enabled=!(Object.hasOwn(favoriteValues,p.id)?favoriteValues[p.id]:!!options.featured),saved=await api('paper-featured',{paperId:p.id,enabled});favoriteValues[p.id]=saved.enabled;paintFavorites();if(saved.enabled)celebrateFavorite(star);await options.onFavoriteChange?.(saved.enabled);localStorage.setItem('paper-featured-updated',Date.now()+':'+crypto.randomUUID());window.dispatchEvent(new CustomEvent('paper-featured-change',{detail:{id:p.id,enabled:saved.enabled}}));}catch(e){error.textContent=e.message;}finally{star.disabled=false;}});
 star.classList.add('catalog-plan-action','catalog-featured-heart');star.dataset.compact='true';toggleLabel(star,options.featured?'移出精选':'加入精选','精选');lab.textContent='学者';lab.title='实验室与学者';lab.setAttribute('aria-label','实验室与学者');todo.setAttribute('aria-pressed',String(todoContains(p.id)));reading.append(read);if(page)reading.append(page);reading.append(pdf,lab);mountQuizToggle(planning,p.id,{quiet:true,label:'加入 Quiz',actionLabel:'今日 Quiz'});planning.append(star);wrap.append(reading,planning);mountIssueCounts(host,p);wrap.append(error);host.append(wrap);window.dispatchEvent(new CustomEvent('paper-catalog-mounted',{detail:{host,id:p.id,button:read}}));Object.assign(widget,{host:wrap,star,initial:!!options.featured});
 loadPaperFavorites().then(paintFavorites).catch(e=>{error.textContent=e.message;});return wrap;
}
export function mountPaperPlanButtons(host,p,options={}){
 let page=null;if(!document.body.dataset.readerPage){page=document.createElement('a');page.className='button';page.href=new URL('paper.html?id='+encodeURIComponent(p.id),import.meta.url).href;page.target='_blank';page.rel='noopener';page.textContent='独立页面阅读 ↗';host.append(page);}
 const error=document.createElement('small');error.className='catalog-error';error.setAttribute('role','status');const button=(name,action)=>{const b=document.createElement('button');b.type='button';b.textContent=name;b.className='button';b.onclick=action;return b;};
 const requiredDate=options.requiredDate||chinaTime().date;let requiredValue=!!p.inToday;const required=button(requiredValue?'移除今日必读':'加入今日必读',async()=>{required.disabled=true;error.textContent='';try{const queueValues=await loadQueue(false,requiredDate);requiredValue=queueValues.has(p.id);await api(requiredValue?'queue-remove':'queue',{date:requiredDate,paperId:p.id});requiredValue=!requiredValue;p.inToday=requiredValue;if(requiredValue)queueValues.add(p.id);else queueValues.delete(p.id);paintQueue();notifyRequiredReading();}catch(e){error.textContent=e.message;}finally{required.disabled=false;}});
 const todo=button(todoContains(p.id)?'移除 Todo List':'加入 Todo List',()=>{error.textContent='';try{const db=JSON.parse(localStorage.getItem('daily-practice-v1')||'{"days":{}}'),result=togglePaperTodo(db,p,chinaTime().date,'todo-'+crypto.randomUUID());localStorage.setItem('daily-practice-v1',JSON.stringify(result.database));paintTodos();window.dispatchEvent(new Event('daily-todo-change'));}catch(e){error.textContent=e.message;}});

 required.classList.add('catalog-plan-action');todo.classList.add('catalog-plan-action');
 if(options.compact){required.dataset.compact=todo.dataset.compact='true';toggleLabel(required,requiredValue?'移除今日必读':'加入今日必读','今日必读');toggleLabel(todo,todoContains(p.id)?'移除 Todo List':'加入 Todo List','Todo List');}todo.setAttribute('aria-pressed',String(todoContains(p.id)));host.append(required,todo,error);const widget={host,id:p.id,todo,required,requiredDate,initial:false};widgets.add(widget);required.disabled=true;loadQueue(false,requiredDate).then(()=>{paintQueue();required.disabled=false;}).catch(e=>{required.disabled=false;error.textContent=e.message;});return {required,todo,widget,page};
}
window.addEventListener('storage',e=>{if(e.key==='paper-featured-updated')loadPaperFavorites(true).then(paintFavorites).catch(()=>{});if(e.key==='daily-practice-v1')paintTodos();});

function loadQueue(force=false,date=chinaTime().date){let entry=queueCache.get(date);if(!entry||force){entry={ids:new Set(),request:null};entry.request=api('reading-queue-status?date='+date).then(data=>{entry.ids=new Set(data.ids);return entry.ids;}).catch(e=>{if(queueCache.get(date)===entry)queueCache.delete(date);throw e;});queueCache.set(date,entry);}return entry.request;}
function paintQueue(){for(const w of widgets){if(!w.host.isConnected)continue;const entry=queueCache.get(w.requiredDate);if(!entry)continue;const enabled=entry.ids.has(w.id);toggleLabel(w.required,enabled?'移除今日必读':'加入今日必读','今日必读');w.required.setAttribute('aria-pressed',String(enabled));}}
function refreshQueues(){const dates=new Set([...widgets].filter(w=>w.host.isConnected).map(w=>w.requiredDate));for(const date of dates)loadQueue(true,date).then(paintQueue).catch(()=>{});}
window.addEventListener('required-reading-change',refreshQueues);
window.addEventListener('storage',e=>{if(e.key==='required-reading-updated')refreshQueues();});

const compactStyle=document.createElement('style');compactStyle.textContent=`
.paper-catalog-actions{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:10px 0;max-width:100%;min-width:0}
.paper-catalog-actions .paper-catalog-group{display:contents}
.paper-catalog-actions .paper-catalog-group+.paper-catalog-group{padding:0;border:0}
.paper-catalog-actions button,.paper-catalog-actions a{font-size:12px;line-height:1.5;padding:5px 8px;border-radius:9px;white-space:nowrap;min-height:30px}
.paper-catalog-actions .paper-issue-counts{gap:6px;margin:0}
.paper-catalog-actions .paper-issue-counts a{font-size:11px;padding:5px 7px}
.paper-catalog-actions small:empty{display:none}
.paper-catalog-actions .catalog-error{max-width:100%}
.paper-catalog-actions button,.paper-catalog-actions a{flex:0 0 auto}
body button.catalog-plan-action,body button.paper-daily-quiz-toggle{--catalog-plan-bg:#fff0f5;--catalog-plan-border:#e3afc2;--catalog-plan-ink:#85485f;--catalog-plan-hover:#fce1eb;--catalog-plan-selected-border:#cd8da6;--catalog-plan-selected:#f6cfde;--catalog-plan-selected-ink:#75354f;--catalog-plan-focus:#b9708c;}
body button.catalog-plan-action,body button.paper-daily-quiz-toggle{background:var(--catalog-plan-bg)!important;border-color:var(--catalog-plan-border)!important;color:var(--catalog-plan-ink)!important;white-space:nowrap}
body button.catalog-plan-action:hover,body button.paper-daily-quiz-toggle:hover{background:var(--catalog-plan-hover)!important;border-color:var(--catalog-plan-selected-border)!important}
body button.catalog-plan-action[aria-pressed=true],body button.paper-daily-quiz-toggle[aria-pressed=true]{background:var(--catalog-plan-selected)!important;border-color:var(--catalog-plan-selected-border)!important;color:var(--catalog-plan-selected-ink)!important}
body button.catalog-plan-action:focus-visible,body button.paper-daily-quiz-toggle:focus-visible{outline:2px solid var(--catalog-plan-focus);outline-offset:2px}

`;document.head.append(compactStyle);
