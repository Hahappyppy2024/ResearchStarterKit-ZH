import {mountCatalogActions} from './paper-catalog-actions.js';
import {mountPaperProgress} from './paper-progress.js';
import {openPaperAffiliations} from './paper-labs.js';
import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
import {markPaperRead} from "./reading-history.mjs";
import {openReader,paperTaskProgress,paperTaskTotal} from "./paper-reader.js";
import {chinaTime} from "./schedule.mjs";
const $=id=>document.getElementById(id),KEY="daily-paper-reading-v1";
const PAGE_SIZE=3;
let topics=[];
let date=$("date").value||chinaTime().date,papers=[],states={},version=0,pages={};
try{const value=JSON.parse(localStorage.getItem(KEY)||"{}");if(value&&typeof value==="object"&&!Array.isArray(value))states=value}catch{}
function node(tag,cls,value){const n=document.createElement(tag);n.className=cls||"";if(value!==undefined)n.textContent=value;return n}
function progress(){const unique=[...new Map(papers.map(p=>[p.id,p])).values()],done=unique.filter(p=>states[p.id]==="read").length;$("daily-reading-count").textContent=`已读 ${done} / ${unique.length} 篇`;const pct=unique.length?Math.round(done/unique.length*100):0;$("daily-reading-fill").style.width=pct+"%";$("daily-reading-progress").setAttribute("aria-valuenow",pct)}
function render(){progress();$("daily-reading-lists").replaceChildren();for(const topic of topics){
 const index=pages[topic]||0;
 const list=papers.filter(p=>(p.topics||[]).includes(topic)),section=node("section","reading-topic"),h=node("h3","",`${topic} · ${list.length} 篇`),ul=node("ul","reading-items");section.dataset.topic=topic;section.append(h,ul);
 if(!list.length)ul.append(node("li","muted","这期清单暂无该方向的新论文。"));
 for(const p of list.slice(index*PAGE_SIZE,index*PAGE_SIZE+PAGE_SIZE)){
  const li=node("li","reading-item"),body=node("div","reading-body"),title=paperTitle(p,'a','reading-title');const url=p.pdf||p.source;if(url?.startsWith("https://")){title.href=url;title.target="_blank";title.rel="noopener"}
  title.onclick=e=>{e.preventDefault();openReader(p.id)};
  body.append(title,node("p","reading-authors","作者："+(Array.isArray(p.authors)?p.authors.join(", "):p.authors||"暂未提供")));
  const details=Array.isArray(p.authorDetails)?p.authorDetails:[];
  const known=details.filter(x=>Array.isArray(x.affiliations)&&x.affiliations.length);
  const units=known.map(x=>`${x.name}：${x.affiliations.join(" / ")}`).join("；");
  body.append(node("p","reading-affiliations","工作单位："+(units?units+(known.length<details.length?"；其余作者暂未提供":""):"暂未提供（arXiv 元数据无此信息）")));
  mountPaperProgress(body,p);mountCatalogActions(body,p);li.append(body);ul.append(li);
 }
 if(list.length){const nav=node("div","reading-pagination"),prev=node("button","button","上一组"),next=node("button","button","下一组"),count=node("span","",`${index+1} / ${Math.ceil(list.length/PAGE_SIZE)}`);prev.disabled=index===0;next.disabled=(index+1)*PAGE_SIZE>=list.length;prev.onclick=()=>{pages[topic]=index-1;render()};next.onclick=()=>{pages[topic]=index+1;render()};nav.append(prev,count,next);section.append(nav)}
 $("daily-reading-lists").append(section);
}}
async function refresh(){const current=++version;$("daily-reading-refresh").disabled=true;try{const [r,topicResponse]=await Promise.all([fetch("/api/papers?date="+encodeURIComponent(date),{cache:"no-store"}),fetch("/api/topics",{cache:"no-store"})]);if(!topicResponse.ok)throw Error();const configuration=await topicResponse.json();topics=configuration.topics.map(t=>t.name);if(!r.ok)throw Error();const data=await r.json();if(current!==version)return;const digest=data.exact?data.digest:null;papers=(digest?.papers||[]).filter(p=>(p.venue||"arXiv")==="arXiv");pages={};$("daily-reading-status").textContent=digest?`${date} 阅读任务 · 数据更新于 ${new Date(digest.checkedAt).toLocaleString("zh-CN",{timeZone:"Asia/Shanghai",hour12:false})}。本次自动检索覆盖近 7 天更新，并非全部于今天首次发布。`:`${date} 尚无论文更新清单，暂不以其他日期的论文充当当天任务。`;render()}catch{$("daily-reading-status").textContent="读取失败，请刷新重试。"}finally{if(current===version)$("daily-reading-refresh").disabled=false}}
$("daily-reading-refresh").onclick=refresh;window.addEventListener("schedule-date-change",e=>{date=e.detail;refresh()});window.addEventListener("storage",e=>{if(e.key===KEY){try{states=JSON.parse(e.newValue||"{}");render()}catch{}}});refresh();

window.addEventListener("research-topics-change",refresh);

window.addEventListener("paper-reading-tasks-change",e=>{for(const button of document.querySelectorAll("[data-paper-checklist]")){if(button.dataset.paperChecklist===e.detail.id)button.textContent=`阅读清单 ${paperTaskProgress(e.detail.id)}/${paperTaskTotal}`}});

window.addEventListener("paper-reading-status-change",()=>{try{states=JSON.parse(localStorage.getItem(KEY)||"{}");render()}catch{}});
