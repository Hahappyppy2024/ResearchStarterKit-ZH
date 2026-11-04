import {renderTaijiGalaxy} from './taiji-galaxy.js';
import {familyGroups,TOPIC_FAMILIES} from './topic-families.mjs';
import {mountTopicTimeline} from './paper-topic-timeline.js';
import {isPaperRead} from './reading-history.mjs';
import {chinaTime} from './schedule.mjs';
import {paperTitle} from './paper-title.js';
import {openReader} from './paper-reader.js';
import {mountPaperPlanButtons} from './paper-catalog-actions.js';
import {paperPdfUrl} from './catalog-actions.mjs';
import {weekOf,paperDay,direction,uniquePapers,groupsFor,starPoints,weeklySummary,archiveDisplayDate} from './arxiv-observatory-model.mjs';
const $=id=>document.getElementById(id),el=(t,text,cls)=>{const n=document.createElement(t);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const host=$('arxiv-observatory');if(!host)throw Error('论文观测台容器缺失');
const directionLabel=name=>({'Agent':'智能体','Object Detection':'目标检测','Video Understanding':'视频理解','Video Generation':'视频生成','Video Editing':'视频编辑','Video Retrieval':'视频查找','Agent Security':'智能体安全','Agent OS':'智能体操作系统','Agent Harness':'智能体运行框架'}[name]||name);
function translated(p){try{return {...p,...JSON.parse(localStorage.getItem('paper-title-cache:'+p.title)||'{}')};}catch{return p;}}
let safetyOnly=false,followingToday=true;
const today=()=>chinaTime().date,dayCache=new Map();let daysIndex=[],all=[],daily=[],visible=[],groups=[],selected='',selectedDate=today(),page=0,points=[],hits=[],version=0,yaw=.18,pitch=1.06,paused=matchMedia('(prefers-reduced-motion: reduce)').matches,lastScan=performance.now(),lastFrame=0,onScreen=true,drag=null;
$('obs-date').value=selectedDate;$('obs-date').max=today();
async function api(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('本机论文归档暂未读取成功');return r.json();}
async function load(date=today(),latest=false,force=false){
 const stamp=++version,requestedDate=date;followingToday=date===today()||latest;
 $('obs-refresh').disabled=true;selectedDate=date;$('obs-date').value=date;daily=[];visible=[];groups=[];points=[];render();
 $('obs-day-summary').textContent=date+' · 正在读取';$('obs-status').textContent='正在读取本机每日归档…';
 try{
  const index=await api('/api/arxiv/days');if(stamp!==version)return;
  daysIndex=index.days;date=archiveDisplayDate(date,daysIndex,today(),latest);
  if(force||!dayCache.has(date))dayCache.set(date,await api('/api/arxiv/day?date='+encodeURIComponent(date)));
  if(stamp!==version)return;
  const result=dayCache.get(date);all=uniquePapers(result.papers||[],today());selectedDate=date;$('obs-date').value=date;
  daily=all.filter(p=>paperDay(p)===date);groups=groupsFor(daily);
  const control=$('obs-direction'),prior=control.value;control.replaceChildren(new Option('全部方向',''));
  for(const family of TOPIC_FAMILIES){const section=document.createElement('optgroup');section.label=family.name;for(const name of family.topics){const count=groups.find(g=>g.name===name)?.count||0;section.append(new Option(name+' · '+count+' 篇',name));}control.append(section);}
  control.value=groups.some(g=>g.name===prior)?prior:'';
  const archive=$('obs-archive');archive.replaceChildren(new Option('每日归档 · 选择日期',''));
  for(const d of daysIndex)archive.add(new Option(d.date+' · '+d.count+' 篇',d.date));
  archive.value=daysIndex.some(d=>d.date===date)?date:'';page=0;render();
  const checked=result.dailyCheck?.checkedAt||result.meta?.checkedAt||result.meta?.updatedAt;
  const fallback=requestedDate===today()&&date!==today()&&!latest;
  $('obs-status').textContent=(fallback?'今天 '+today()+' 暂无已采集的新论文，自动显示最近有论文的日期 '+date+' · '+daily.length+' 篇。':'北京时间今天 '+today()+'；当前论文首版日期 '+date+' · '+daily.length+' 篇。')+'论文按真实首版日期归档，补收论文仍归原日期。'+(checked?' 最近检查：'+new Date(checked).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'');
  if(result.dailyCheck?.status==='partial')$('obs-status').textContent+=' 今日检索部分失败：'+result.dailyCheck.errors.join('；');
  drawDates();loadWeek(date);
 }catch(e){$('obs-status').textContent=e.message+'，保留已有日期记录，可稍后刷新。';}
 finally{if(stamp===version)$('obs-refresh').disabled=false;}
}

function render(){const word=$('obs-search').value.trim().toLowerCase(),group=$('obs-direction').value;visible=daily.filter(p=>(!safetyOnly||p.safetyTopics?.length)&&(!group||direction(p)===group)&&(!word||[p.title,translated(p).titleZh,translated(p).titleEn,p.authors].join(' ').toLowerCase().includes(word)));if(!visible.some(p=>p.id===selected))selected=visible[0]?.id||'';points=starPoints(visible,groupsFor(visible));$('obs-day-summary').textContent='今天 '+today()+' · 首版 '+selectedDate+' · '+visible.length+' / '+daily.length+' 篇';$('obs-canvas-empty').hidden=!!visible.length;for(const id of ['obs-prev','obs-next'])$(id).disabled=visible.length<2;drawCard();drawList();drawGroups();drawFlow();draw();}
function drawCard(){const card=$('obs-paper-card');card.replaceChildren();const p=visible.find(p=>p.id===selected);if(!p){card.append(el('p','当天暂无已采集的首版论文。新采到的历史论文会归回真实首版日期，可点击“最新已采集”查看最近有论文的日期。','obs-empty'));return;}const index=visible.indexOf(p),meta=el('div',undefined,'obs-paper-meta');meta.append(el('span',directionLabel(direction(p))),el('span',(index+1)+' / '+visible.length));card.append(meta,paperTitle(p,'h3'));if(p.safetyTopics?.length){card.append(el('p','阅读切入点：'+p.safetyTopics[0].question,'obs-reading-hook'));const tags=el('p',p.safetyTopics.map(t=>t.name).join(' · '),'small muted');card.append(tags);}card.append(el('p',Array.isArray(p.authors)?p.authors.join(', '):p.authors||'作者待补充','obs-authors'));const abstract=(p.summary||'').replace(/\s+/g,' ');if(abstract)card.append(el('p',abstract.slice(0,240)+(abstract.length>240?'…':''),'obs-abstract'));const actions=el('div',undefined,'obs-paper-actions'),read=el('button','开始阅读');read.type='button';read.onclick=()=>openReader(p.id);actions.append(read);const pdf=paperPdfUrl(p);if(pdf){const a=el('a','原文 PDF 🔗');a.href=new URL('paper.html?id='+encodeURIComponent(p.id),import.meta.url).href;a.target='_blank';a.rel='noopener';actions.append(a);}mountPaperPlanButtons(actions,p);card.append(actions,el('small','首版提交：'+paperDay(p)+' · arXiv','obs-publication'));}
function pick(id){selected=id;lastScan=performance.now();const i=visible.findIndex(p=>p.id===id);page=Math.max(0,Math.floor(i/8));drawCard();drawList();drawFlow();draw();}
function cycle(delta){if(!visible.length)return;const i=visible.findIndex(p=>p.id===selected);pick(visible[(i+delta+visible.length)%visible.length].id);}
function drawList(){const host=$('obs-paper-list');host.replaceChildren();const total=Math.max(1,Math.ceil(visible.length/8));page=Math.min(page,total-1);for(const p of visible.slice(page*8,page*8+8)){const b=el('button',undefined,'obs-paper-row'+(p.id===selected?' selected':''));b.type='button';b.append(el('i',undefined,'obs-row-dot'),paperTitle(p,'span'));b.onclick=()=>pick(p.id);host.append(b);}if(!visible.length)host.append(el('p','暂无论文。','obs-empty'));$('obs-list-page').textContent=(page+1)+' / '+total;$('obs-list-prev').disabled=page===0;$('obs-list-next').disabled=page===total-1;}
const expandedDistribution=new Set();
function drawGroups(){
 const legend=$('obs-legend'),bars=$('obs-bars');legend.replaceChildren();bars.replaceChildren();
 const filter=name=>{$('obs-direction').value=$('obs-direction').value===name?'':name;page=0;render();};
 const bar=(name,count,color,max)=>{const row=el('div',undefined,'obs-bar'),label=el('span',name),track=el('i'),fill=el('b');fill.style.width=count/max*100+'%';fill.style.background=color;track.append(fill);row.append(label,track,el('small',String(count)));return row;};
 for(const g of groups){const b=el('button',directionLabel(g.name)+' '+g.count);b.type='button';b.style.setProperty('--group-color',g.color);b.setAttribute('aria-pressed',String($('obs-direction').value===g.name));b.onclick=()=>filter(g.name);legend.append(b);}
 const families=familyGroups(groups),max=Math.max(1,...families.map(f=>f.count));
 for(const family of families){
  const section=el('details',undefined,'obs-distribution-family'),summary=el('summary');section.open=expandedDistribution.has(family.id);summary.append(bar(family.name,family.count,family.color,max));section.append(summary);
  section.ontoggle=()=>{if(section.open)expandedDistribution.add(family.id);else expandedDistribution.delete(family.id);};
  const children=el('div',undefined,'obs-distribution-children'),childMax=Math.max(1,...family.groups.map(g=>g.count));
  for(const g of family.groups){const button=el('button',undefined,'obs-distribution-filter');button.type='button';button.setAttribute('aria-pressed',String($('obs-direction').value===g.name));button.append(bar(directionLabel(g.name),g.count,g.color,childMax));button.onclick=()=>filter(g.name);children.append(button);}
  section.append(children);bars.append(section);
 }
 if(!families.length)bars.append(el('p','暂无方向分布。','obs-empty'));
}

function drawDates(){const strip=$('obs-date-strip');strip.replaceChildren();const dates=daysIndex.slice(0,14).reverse(),max=Math.max(1,...dates.map(d=>d.count));for(const item of dates){const b=el('button',undefined,'obs-date-column');b.type='button';b.setAttribute('aria-pressed',String(item.date===selectedDate));const bar=el('i');bar.style.height=(8+item.count/max*62)+'px';b.append(el('small',String(item.count)),bar,el('span',item.date.slice(5)));b.onclick=()=>load(item.date);strip.append(b);}if(!dates.length)strip.append(el('p','本机归档中尚无论文。'));}
function drawFlow(){const active=[$('obs-direction').value?directionLabel($('obs-direction').value):'',safetyOnly?'仅 AI / Agent 安全':'',$('obs-search').value.trim()?'搜索：'+$('obs-search').value.trim():''].filter(Boolean);$('obs-flow-filter').textContent=active.length?'当前筛选：'+active.join(' · ')+' · '+visible.length+' 篇（点击“显示全部类别”恢复）':'当天全部类别 · '+visible.length+' 篇；点击类别标题可展开／收起。';drawFlowPreview();$('obs-flow-label').textContent=selectedDate+' · 按大类分色 · 每颗珍珠是一篇论文';mountTopicTimeline({box:$('obs-flow'),date:selectedDate,papers:visible,groups:groupsFor(visible),selected,label:directionLabel,paperTitle,onPick:id=>{pick(id);$('obs-flow').openPaperPreview?.(id);},onOpen:p=>openReader(p.id),onFilter:name=>{$('obs-direction').value=name;page=0;render();}});}


const canvas=$('obs-canvas'),ctx=canvas.getContext('2d');let width=600,height=470;
function draw(){if(!ctx)return;hits=renderTaijiGalaxy(ctx,{width,height,yaw,pitch,points,selected,time:paused?0:performance.now()});canvas.dataset.paperCount=String(points.length);canvas.dataset.selectedPaper=selected;}
new ResizeObserver(entries=>{const box=entries[0].contentRect;width=box.width;height=box.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx?.setTransform(dpr,0,0,dpr,0,0);draw();}).observe(canvas);
canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={x:e.clientX,y:e.clientY,yaw,pitch,moved:false};canvas.setPointerCapture(e.pointerId);lastScan=performance.now();});canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.moved=drag.moved||Math.abs(dx)+Math.abs(dy)>5;yaw=drag.yaw+dx*.008;pitch=Math.max(.15,Math.min(1.3,drag.pitch+dy*.008));draw();});canvas.addEventListener('pointerup',e=>{if(!drag)return;const click=!drag.moved;drag=null;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);if(click){const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,near=hits.map(p=>({p,d:(p.sx-x)**2+(p.sy-y)**2})).filter(v=>v.d<v.p.hitRadius**2).sort((a,b)=>a.d-b.d)[0];if(near)pick(near.p.paper.id);}});canvas.addEventListener('pointercancel',()=>drag=null);canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();cycle(e.key==='ArrowLeft'?-1:1);}});
function motion(){host.classList.toggle('obs-motion-paused',paused); $('obs-motion').textContent=paused?'播放动效':'暂停动效';$('obs-motion').setAttribute('aria-pressed',String(paused));}$('obs-motion').onclick=()=>{paused=!paused;lastScan=performance.now();motion();};motion();
new IntersectionObserver(entries=>{onScreen=entries[0].isIntersecting;},{threshold:0}).observe(host);
function frame(now){if(!document.hidden&&onScreen&&!paused&&!drag){const delta=Math.min(50,now-lastFrame);yaw+=delta*.000045;if(now-lastScan>10000&&visible.length>1)cycle(1);draw();}lastFrame=now;requestAnimationFrame(frame);}requestAnimationFrame(frame);
$('obs-prev').onclick=()=>cycle(-1);$('obs-next').onclick=()=>cycle(1);$('obs-search').oninput=()=>{page=0;render();lastScan=performance.now();};$('obs-direction').onchange=()=>{page=0;render();};$('obs-date').onchange=()=>load($('obs-date').value);$('obs-archive').onchange=()=>{if($('obs-archive').value)load($('obs-archive').value);};$('obs-today').onclick=()=>load(today(),false,true);$('obs-latest').onclick=()=>load(today(),true,true);$('obs-refresh').onclick=refreshFromSource;$('obs-list-prev').onclick=()=>{page--;drawList();};$('obs-list-next').onclick=()=>{page++;drawList();};
setInterval(()=>{if(!document.hidden&&onScreen)load(followingToday?today():selectedDate,false,true);},300000);load(today(),false);

let weekVersion=0,weekPapers=[],weekDate=today();
function drawWeek(){const stats=weeklySummary(weekPapers,weekDate,today(),isPaperRead);$('obs-week-totals').textContent='新增论文 '+stats.total+' 篇 · 当前已读 '+stats.read+' 篇 · 未读 '+(stats.total-stats.read)+' 篇';const days=$('obs-week-days');days.replaceChildren();for(const [i,d] of stats.days.entries()){const b=el('button',undefined,'obs-week-day');b.type='button';b.append(el('small',['周一','周二','周三','周四','周五','周六','周日'][i]+' '+d.date.slice(5)),el('strong',d.date>today()?'—':String(d.count)),el('small',d.date>today()?'尚未开始':'篇'));b.disabled=d.date>today();b.onclick=()=>load(d.date);days.append(b);}const group=$('obs-week-groups');group.replaceChildren();for(const g of stats.groups)group.append(el('span',directionLabel(g.name)+' '+g.count+' 篇','tag'));$('obs-week-next').disabled=stats.end>=today();return stats;}
async function loadWeek(date){const stamp=++weekVersion;weekDate=date;$('obs-week-date').value=date;weekPapers=[];drawWeek();$('obs-week-status').textContent='正在读取每周统计…';try{const data=await api('/api/arxiv/week?week='+weekOf(date));if(stamp!==weekVersion)return;weekPapers=data.papers||[];const stats=drawWeek();$('obs-week-status').textContent=stats.start+' — '+stats.end+' · '+(stats.complete?'已结束周':'本周持续更新')+' · 本机已采集数据'+(data.meta?.checkedAt?' · 最近检索 '+new Date(data.meta.checkedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):' · 尚未完成整周检索')+(data.meta?.error?' · 最近检索失败，保留已有数据':'');}catch(e){if(stamp===weekVersion)$('obs-week-status').textContent=e.message;}}
$('obs-week-date').value=today();$('obs-week-date').max=today();$('obs-week-date').onchange=()=>{if($('obs-week-date').value)loadWeek($('obs-week-date').value);};
for(const [id,delta] of [['obs-week-prev',-7],['obs-week-next',7]])$(id).onclick=()=>{const d=new Date(weekOf(weekDate)+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);loadWeek(d.toISOString().slice(0,10));};
window.addEventListener('paper-reading-status-change',()=>{drawWeek();drawFlow();});window.addEventListener('storage',()=>drawWeek());

function drawFlowPreview(p=visible.find(p=>p.id===selected)){const host=$('obs-flow-preview');host.replaceChildren();if(!p)return;const text=el('div');text.append(el('small',directionLabel(direction(p))),paperTitle(p,'div'));const read=el('button','开始阅读 · 10 分钟');read.type='button';read.onclick=()=>openReader(p.id);host.append(text,read);}
$('obs-safety').onclick=()=>{safetyOnly=!safetyOnly;$('obs-safety').setAttribute('aria-pressed',String(safetyOnly));$('obs-direction').value='';page=0;render();};
$('obs-surprise').onclick=()=>{const unread=visible.filter(p=>!isPaperRead(p.id)&&p.id!==selected),pool=unread.length?unread:visible.filter(p=>p.id!==selected);if(pool.length)pick(pool[Math.floor(Math.random()*pool.length)].id);};

async function loadSafetyStarters(){const host=$('obs-security-starters');try{const data=await api('/api/arxiv/safety-starters');for(const p of data.papers||[]){const card=el('article',undefined,'obs-starter-card');card.append(paperTitle(p,'h3'),el('small',paperDay(p)+' · '+(p.safetyTopics?.[0]?.name||'安全研究')),el('p',p.readingGuide||'阅读摘要，明确威胁模型与评测对象。'));const actions=el('div',undefined,'obs-paper-actions'),read=el('button','开始阅读');read.type='button';read.onclick=()=>openReader(p.id);const source=el('a','arXiv 原文 🔗');source.href=new URL('paper.html?id='+encodeURIComponent(p.id),import.meta.url).href;source.target='_blank';source.rel='noopener';actions.append(read,source);mountPaperPlanButtons(actions,p);card.append(actions);host.append(card);}if(!data.papers?.length)host.append(el('p','安全论文题录尚未导入。'));}catch(e){host.textContent=e.message;}}loadSafetyStarters();

async function refreshFromSource(){const button=$('obs-refresh');button.disabled=true;$('obs-status').textContent='正在重新检索 arXiv 官方来源，保留现有论文；完成后自动显示最新结果。';try{const response=await fetch('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'morning',id:weekOf(today())})});if(!response.ok)throw Error('启动检索失败');const started=await response.json();if(!started.started){$('obs-status').textContent='已有本地更新任务正在运行，请稍后再试。';return;}for(;;){await new Promise(resolve=>setTimeout(resolve,4000));const job=(await api('/api/topics')).job;if(job.running)continue;dayCache.clear();await load(today(),false,true);let success=false;try{success=JSON.parse(job.message).status==='complete';}catch{}if(!success)$('obs-status').textContent+=' 最近检索未完成：'+job.message;break;}}catch(e){$('obs-status').textContent=e.message+'，已有归档保留。';}finally{button.disabled=false;}}



$('obs-flow-show-all').onclick=()=>{safetyOnly=false;$('obs-safety').setAttribute('aria-pressed','false');$('obs-direction').value='';$('obs-search').value='';$('obs-flow').dataset.collapsedFamilies='[]';delete $('obs-flow').dataset.previewOpen;page=0;render();};
$('obs-flow-expand-all').onclick=()=>{$('obs-flow').dataset.collapsedFamilies='[]';drawFlow();};
