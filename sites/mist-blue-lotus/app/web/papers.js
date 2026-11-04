import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
import {chinaTime} from "./schedule.mjs";
const $=id=>document.getElementById(id),KEY="daily-paper-reading-v1";
const topics=["Agent","Object Detection","Agent OS","Agent Security","Agent Harness"];
let states={},digest=null,filter="全部",selected=$("date").value||chinaTime().date,requestNumber=0,visible=12;
try{states=cleanStates(JSON.parse(localStorage.getItem(KEY)||"{}"))}catch{}
function cleanStates(value){
  if(!value||typeof value!=="object"||Array.isArray(value))throw Error("格式错误");
  return Object.fromEntries(Object.entries(value).filter(([id,state])=>/^[a-zA-Z0-9._-]{1,100}$/.test(id)&&["unread","skimmed","read"].includes(state)));
}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function link(label,url,cls=""){const a=el("a",cls,label);try{if(new URL(url).protocol!=="https:")return el("span","",label)}catch{return el("span","",label)}a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a}
function save(){try{localStorage.setItem(KEY,JSON.stringify(states));return true}catch{$("paper-status").textContent="阅读状态保存失败，请先备份。";return false}}
function progress(){
  const papers=digest?.papers||[],done=papers.filter(p=>states[p.id]==="read").length,skim=papers.filter(p=>states[p.id]==="skimmed").length;
  $("reading-count").textContent=papers.length?`${done} / ${papers.length} 篇`:"暂无清单";
  $("reading-detail").textContent=papers.length?`已精读 · ${skim} 篇浏览过 · ${papers.length-done-skim} 篇未读`:"";
  const percent=papers.length?Math.round(done/papers.length*100):0;
  $("reading-fill").style.width=`${percent}%`;$("reading-track").setAttribute("aria-valuenow",percent);
}
function render(){
  progress();$("paper-topics").replaceChildren();$("paper-list").replaceChildren();
  for(const topic of ["全部",...topics]){
    const count=(digest?.papers||[]).filter(p=>topic==="全部"||p.topics.includes(topic)).length;
    const b=el("button",filter===topic?"selected":"",`${topic} · ${count}`);b.setAttribute("aria-pressed",String(filter===topic));
    b.onclick=()=>{filter=topic;visible=12;render()};$("paper-topics").append(b);
  }
  $("paper-coverage").textContent=filter==="全部"?"":digest?.coverage?.[filter]||"该日期暂无方向记录";
  if(!digest)return;
  const papers=digest.papers.filter(p=>filter==="全部"||p.topics.includes(filter));
  if(!papers.length){$("paper-list").append(el("p","empty-state","这个方向没有已核实的论文入选。可查看其他方向或切换日期。"));return}
  let group=null;
  papers.slice(0,visible).forEach(p=>{
    if(group!==p.section){group=p.section;$("paper-list").append(el("h3","paper-group",group==="recent"?"近期论文":"补读推荐 · 较早论文"))}
    const card=el("article","paper-card"),top=el("div","paper-meta"),title=el("h3","paper-title"),description=el("p","paper-description",p.summary);
    top.append(el("span",`priority ${p.priority}`,p.priority),el("span","author-tier",p.authorTier===1?"A · 影响力依据已核实":p.authorTier===2?"B · 相关研究积累":"作者影响力待核实"),el("span","paper-date",`更新 ${p.updated}`));
    const titleLink=link(p.title,p.source);setPaperTitle(titleLink,p);title.append(titleLink);
    const tags=el("div","paper-tags");p.topics.forEach(t=>tags.append(el("span","",t)));
    const details=el("details","paper-evidence");details.append(el("summary","", "作者与排序依据"));
    details.append(el("p","",`作者：${p.authors}`),el("p","",`首次发布：${p.published}；最近版本：${p.updated}`),el("p","",`阅读建议：${p.rankReason}`),el("p","",p.influenceEvidence));
    const refs=el("div","evidence-links");(p.evidenceSources||[]).forEach(s=>refs.append(link(s.label,s.url)));details.append(refs);
    const actions=el("div","paper-actions"),links=el("div","paper-links");links.append(link("打开 PDF ↗",p.pdf,"button primary"),link("原始页面 ↗",p.source,"small"));
    const label=el("label","reading-label","阅读状态 "),select=el("select");select.setAttribute("aria-label",`阅读状态：${p.title}`);
    [["unread","未读"],["skimmed","浏览过"],["read","已精读"]].forEach(([v,t])=>{const o=el("option","",t);o.value=v;select.append(o)});
    select.value=states[p.id]||"unread";card.classList.toggle("paper-read",select.value==="read");
    select.onchange=()=>{states[p.id]=select.value;save();card.classList.toggle("paper-read",select.value==="read");progress()};
    const abstract=el("details","paper-abstract");abstract.append(el("summary","","展开原文摘要"),description);
    label.append(select);actions.append(links,label);card.append(top,title,tags,abstract,details,actions);$("paper-list").append(card);
  });
  if(papers.length>visible){const more=el("button","button",`再显示 12 篇（剩余 ${papers.length-visible} 篇）`);more.onclick=()=>{visible+=12;render()};$("paper-list").append(more)}
}
async function refresh(){
  const request=++requestNumber;$("paper-refresh").disabled=true;
  $("paper-status").textContent="正在读取本机论文清单…";
  try{
    const res=await fetch(`/api/papers?date=${encodeURIComponent(selected)}`,{cache:"no-store"});if(!res.ok)throw Error("暂时无法获取清单");
    const data=await res.json();if(request!==requestNumber)return;
    digest=data.digest;visible=12;
    $("paper-date").textContent=digest?`清单 ${digest.date} · 更新于 ${new Date(digest.checkedAt).toLocaleString("zh-CN",{timeZone:"Asia/Shanghai",hour12:false})}（北京时间）`:`${selected} · 尚未生成清单`;
    $("paper-status").textContent=digest?`${data.exact?"":`所选日期 ${selected} 尚无清单，显示最近一期。`}${digest.note}`:"尚无清单；每日更新完成后会出现在这里。";
    render();
  }catch{if(request!==requestNumber)return;$("paper-status").textContent="获取清单失败。请稍后刷新；已显示的清单保留，核实日期以上方为准。"}
  finally{if(request===requestNumber)$("paper-refresh").disabled=false}
}
$("paper-refresh").onclick=refresh;
window.addEventListener("schedule-date-change",e=>{selected=e.detail;refresh()});
window.addEventListener("storage",e=>{if(e.key===KEY){try{states=cleanStates(JSON.parse(e.newValue||"{}"));render()}catch{}}});
$("paper-export").onclick=()=>{const a=document.createElement("a"),url=URL.createObjectURL(new Blob([JSON.stringify({version:1,type:"paper-reading",states},null,2)],{type:"application/json"}));a.href=url;a.download=`论文阅读状态-${chinaTime().date}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$("paper-import").onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  try{if(file.size>5e6)throw Error();const d=JSON.parse(await file.text());if(d.version!==1||d.type!=="paper-reading")throw Error();const clean=cleanStates(d.states);
    if(Object.keys(clean).some(id=>states[id]&&states[id]!==clean[id])&&!confirm("部分论文已有阅读状态。用备份中的状态覆盖这些论文？"))return;
    states={...states,...clean};if(save())$("paper-status").textContent=`已导入 ${Object.keys(clean).length} 篇论文的阅读状态。`;render();
  }catch{$("paper-status").textContent="导入失败，请选择此网页导出的论文阅读状态备份。"}finally{e.target.value=""}
};
render();refresh();
