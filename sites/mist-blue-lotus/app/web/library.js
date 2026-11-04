import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
const $=id=>document.getElementById(id);
let page=0;
async function api(path,body){const r=await fetch(path,body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:{});if(!r.ok)throw Error("请求失败");return r.json()}
function text(tag,value){const n=document.createElement(tag);n.textContent=value;return n}
async function status(){
 try{const s=await api("/api/status");$("local-status").textContent=`本机文献库 ${s.total} 篇 · Zotero 已保存/已有 ${s.saved} 篇 · 待导入 ${s.pending} 篇`;
 $("zotero-status").textContent=s.zotero.message+(s.job.message?" · "+s.job.message:"");
 $("source-status").replaceChildren(...s.sources.map(x=>text("p",`${x.venue} ${x.year}：${x.count} 篇 · ${x.status} · ${x.note||""}`)));
 $("sync-zotero").disabled=s.job.running;$("update-arxiv").disabled=s.job.running;
 }catch{$("zotero-status").textContent="本机服务未连接。请运行“启动本地网站.ps1”。"}
}
async function load(){
 const q=new URLSearchParams({page,q:$("library-search").value,venue:$("library-venue").value,year:$("library-year").value,topic:$("library-topic").value});
 try{const d=await api("/api/library?"+q);$("library-list").replaceChildren();$("library-count").textContent=`${d.count} 篇 · 第 ${page+1} 页`;
 for(const p of d.papers){
  const row=document.createElement("article");row.className="library-row";
  const title=paperTitle(p),meta=text("p",`${p.venue||"arXiv"} ${p.year||""} · ${(p.topics||[]).join(" / ")} · ${p.authors||"作者信息待补全"}`);meta.className="small muted";
  const links=document.createElement("div");links.className="library-links";
  for(const [label,url] of [["原文",p.source],["PDF",p.pdf]]){if(!url||!url.startsWith("https://"))continue;const a=text("a",label+" ↗");a.href=url;a.target="_blank";a.rel="noopener";links.append(a)}
  const save=text("button",p.zoteroKey?"已在 Zotero":"保存到 Zotero");save.className="button";save.disabled=!!p.zoteroKey;
  save.onclick=async()=>{try{const result=await api("/api/jobs",{kind:"sync",id:p.id});save.textContent=result.started?"正在保存，请稍后刷新":"已有任务执行中";status()}catch{save.textContent="保存失败，点击重试"}};
  links.append(save);row.append(title,meta,links);$("library-list").append(row);
 }
 $("library-prev").disabled=page===0;$("library-next").disabled=(page+1)*30>=d.count;
 }catch{$("library-count").textContent="文献库读取失败"}
}
for(const id of ["library-search","library-venue","library-year","library-topic"])$(id).onchange=()=>{page=0;load()};
$("library-prev").onclick=()=>{page=Math.max(0,page-1);load()};$("library-next").onclick=()=>{page++;load()};
$("sync-zotero").onclick=async()=>{await api("/api/jobs",{kind:"sync"});status()};
$("update-arxiv").onclick=async()=>{await api("/api/jobs",{kind:"arxiv"});status()};
$("reload-library").onclick=async()=>{await api("/api/ingest",{});await status();load()};
status();load();setInterval(status,15000);
