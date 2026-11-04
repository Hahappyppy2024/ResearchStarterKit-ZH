const sites={daily:{name:"每日努力",url:"http://127.0.0.1:8866/"},arxiv:{name:"arXiv 每周论文",url:"http://127.0.0.1:8866/arxiv.html"},atlas:{name:"论文脉络",url:"http://127.0.0.1:8866/lineage.html"},scholars:{name:"实验室与学者",url:"http://127.0.0.1:8866/labs.html"},library:{name:"论文库",url:"http://127.0.0.1:8866/library.html"},projects:{name:"项目实验本",url:"http://127.0.0.1:8870/"},learning:{name:"基础知识",url:"http://127.0.0.1:8870/learning"},poetry:{name:"毛主席诗词",url:"http://127.0.0.1:8868/"}};
Object.assign(sites,{blog:{name:"Blog",url:"http://127.0.0.1:8866/blog.html"},methods:{name:"科研方法",url:"http://127.0.0.1:8866/methods.html"},courses:{name:"我的课程",url:"http://127.0.0.1:8866/courses.html"},reading:{name:"今日必读",url:"http://127.0.0.1:8866/reading.html"}});
const $=id=>document.getElementById(id);let active="daily",services=[],pollVersion=0;
function show(){for(const id of Object.keys(sites)){const isActive=id===active;$("panel-"+id).hidden=!isActive;if($("tab-"+id)){$("tab-"+id).setAttribute("aria-selected",String(isActive));$("tab-"+id).tabIndex=isActive?0:-1}}const ready=services.find(x=>x.id===active)?.ready;$("offline").hidden=!!ready;const frame=active==="atlas"?$("frame-atlas-tools"):$("frame-"+active);if(ready&&!frame.getAttribute("src"))frame.src=active==="atlas"?"http://127.0.0.1:8866/lineage.html":sites[active].url;const count=services.filter(x=>x.ready).length;$("service-state").textContent=count===Object.keys(sites).length?`● ${sites[active].name} · 全部本地网站已连接`:`${sites[active].name} · ${count} / ${Object.keys(sites).length} 个本地网站已连接`;$("offline-title").textContent="正在连接 · "+sites[active].name;const error=services.find(x=>x.id===active)?.error;$("offline-message").textContent=error?"启动未完成："+error:"网站可能尚未启动。点击下方按钮启动，连接成功后会自动显示。"}
function notifyDailyActivation(){const frame=$('frame-daily');if(active==='daily'&&frame?.getAttribute('src'))frame.contentWindow.postMessage({type:'research-daily-activate'},'http://127.0.0.1:8866');}
function choose(id){const previous=active;active=sites[id]?id:"daily";show();if(active==='daily'&&previous!==active)notifyDailyActivation();}
$('frame-daily').addEventListener('load',notifyDailyActivation);
window.addEventListener('focus',notifyDailyActivation);window.addEventListener('pageshow',notifyDailyActivation);document.addEventListener('visibilitychange',()=>{if(!document.hidden)notifyDailyActivation();});
window.addEventListener("hashchange",()=>choose(location.hash.slice(1)));document.querySelectorAll("[data-site]").forEach(b=>{b.onclick=()=>{location.hash=b.dataset.site;choose(b.dataset.site)};b.onkeydown=e=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;e.preventDefault();const ids=[...document.querySelectorAll("[data-site]")].map(b=>b.dataset.site),i=ids.indexOf(active),next=e.key==="Home"?ids[0]:e.key==="End"?ids.at(-1):ids[(i+(e.key==="ArrowRight"?1:-1)+ids.length)%ids.length];location.hash=next;choose(next);$("tab-"+next).focus()}});
async function status(){const version=++pollVersion;try{const r=await fetch("/api/services",{cache:"no-store"});if(!r.ok)throw Error();const data=await r.json();if(version!==pollVersion)return;services=data.services;const arxiv=services.find(s=>s.id==="daily");if(arxiv){const atlasStatus=services.find(s=>s.id==="atlas");if(atlasStatus)Object.assign(atlasStatus,{ready:arxiv.ready,error:arxiv.error})}if(arxiv)for(const id of ["arxiv","methods","courses","reading","blog","library","scholars"]){services=services.filter(s=>s.id!==id);services.push({...arxiv,id,name:sites[id].name})};const notebook=services.find(s=>s.id==="projects");if(notebook)services.push({...notebook,id:"learning",name:"基础知识"});show()}catch{$("service-state").textContent="统一首页服务未连接，请双击“打开我的研究首页.cmd”。"}}
async function start(){try{$("retry-start").disabled=true;await fetch("/api/services/start",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});await status()}catch{$("service-state").textContent="启动请求未完成，请重试。"}finally{$("retry-start").disabled=false}}
$("retry-start").onclick=start;choose(location.hash.slice(1));status();setInterval(status,5000);

window.addEventListener("message",e=>{
  if(e.origin!=="http://127.0.0.1:8867"||e.source!==$("frame-library").contentWindow||e.data?.type!=="research-add-paper-task"||typeof e.data.paperId!=="string"||!(/^[a-zA-Z0-9._-]{1,200}$/).test(e.data.paperId))return;
  const frame=$("frame-daily"),message={type:"library-paper-task",paperId:e.data.paperId},deliver=()=>frame.contentWindow.postMessage(message,"http://127.0.0.1:8866");
  const loaded=!!frame.getAttribute("src");if(!loaded)frame.addEventListener("load",deliver,{once:true});
  location.hash="daily";choose("daily");if(loaded)deliver();
});

window.addEventListener("message",e=>{
 if(e.origin!=="http://127.0.0.1:8870"||(e.source!==$("frame-projects").contentWindow&&e.source!==$("frame-learning").contentWindow)||e.data?.type!=="research-add-project-task"||typeof e.data.taskId!=="string"||!(/^[a-zA-Z0-9-]{1,80}$/).test(e.data.taskId))return;
 const frame=$("frame-daily"),message={type:"project-task-request",taskId:e.data.taskId},deliver=()=>frame.contentWindow.postMessage(message,"http://127.0.0.1:8866");
 const loaded=!!frame.getAttribute("src");if(!loaded)frame.addEventListener("load",deliver,{once:true});location.hash="daily";choose("daily");if(loaded)deliver();
});

window.addEventListener("message",e=>{
 if(e.origin!=="http://127.0.0.1:8866"||!["arxiv","reading","courses","atlas-tools","library","scholars"].some(id=>e.source===$("frame-"+id).contentWindow)||e.data?.type!=="research-add-arxiv-task"||typeof e.data.paperId!=="string"||!(/^[a-zA-Z0-9._-]{1,200}$/).test(e.data.paperId))return;
 const frame=$("frame-daily"),message={type:"arxiv-paper-task",paperId:e.data.paperId},deliver=()=>frame.contentWindow.postMessage(message,"http://127.0.0.1:8866");
 const loaded=!!frame.getAttribute("src");if(!loaded)frame.addEventListener("load",deliver,{once:true});location.hash="daily";choose("daily");if(loaded)deliver();
});

window.addEventListener('message',e=>{
 if(!((e.origin==='http://127.0.0.1:8866'&&['arxiv','reading','courses','methods','atlas-tools','daily'].some(id=>e.source===$('frame-'+id)?.contentWindow))||(e.origin==='http://127.0.0.1:8867'&&e.source===$('frame-library').contentWindow)))return;
 let message;if(e.data?.type==='research-add-study-task'&&typeof e.data.paperId==='string'&&/^[a-zA-Z0-9._-]{1,200}$/.test(e.data.paperId)&&typeof e.data.taskId==='string'&&/^[a-z-]{1,60}$/.test(e.data.taskId))message={type:'study-task-request',paperId:e.data.paperId,taskId:e.data.taskId};
 if(e.data?.type==='research-add-practice-task'&&/^research-\d{4}-\d{2}-\d{2}-[1-3]$/.test(e.data.taskId)&&/^\d{4}-\d{2}-\d{2}$/.test(e.data.date))message={type:'practice-task-request',taskId:e.data.taskId,date:e.data.date};
 if(!message)return;const frame=$('frame-daily'),loaded=!!frame.getAttribute('src'),deliver=()=>frame.contentWindow.postMessage(message,'http://127.0.0.1:8866');if(!loaded)frame.addEventListener('load',deliver,{once:true});location.hash='daily';choose('daily');if(loaded)deliver();
});

window.addEventListener('message',e=>{if(e.origin!=='http://127.0.0.1:8867'||e.source!==$('frame-library').contentWindow||e.data?.type!=='research-paper-read'||typeof e.data.paperId!=='string'||!/^[a-zA-Z0-9._-]{1,200}$/.test(e.data.paperId))return;const f=$('frame-daily'),deliver=()=>f.contentWindow.postMessage({type:'paper-read-status',paperId:e.data.paperId},'http://127.0.0.1:8866');if(f.getAttribute('src'))deliver();else{f.addEventListener('load',deliver,{once:true});f.src=sites.daily.url}});
