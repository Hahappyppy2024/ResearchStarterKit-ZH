import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
import {mountQuizToggle} from './paper-quiz-ui.js';
import {openReader,paperTaskProgress,paperTaskTotal} from "./paper-reader.js";
const $=id=>document.getElementById(id),node=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n};
const params=new URLSearchParams(location.search);
let year=[2025,2026,2027].includes(Number(params.get("year")))?Number(params.get("year")):2026,venue=params.get("venue")||"CVPR",category=params.get("category")||"",subcategory=params.get("subcategory")||"",query=params.get("q")||"",page=0,request=0,taxonomy=[];
$("conference-search").value=query;
async function api(path){const response=await fetch(path,{cache:"no-store"});const data=await response.json();if(!response.ok)throw Error(data.error||"本地目录读取失败");return data}
function link(label,url){if(!/^https:\/\//.test(url||""))return null;const a=node("a","paper-link",label);a.href=url;a.target="_blank";a.rel="noopener";return a}
function updateUrl(){const p=new URLSearchParams({year,venue});if(category)p.set("category",category);if(subcategory)p.set("subcategory",subcategory);if(query)p.set("q",query);history.replaceState(null,"","?"+p+"#library")}
function selectCategory(c="",s=""){category=c;subcategory=s;page=0;load()}
async function navigation(refresh=false){const data=await api("/api/conferences"+(refresh?"?refresh=1":""));$("conference-years").replaceChildren();const available=data.years.flatMap(y=>y.conferences.map(c=>c.venue));if(!available.includes(venue))venue="CVPR";
 for(const group of data.years){const section=node("details","year-group"),summary=node("summary","",String(group.year));section.open=group.year>=2026||group.year===year;section.append(summary);for(const c of group.conferences){const button=node("button","conference-button"),label=node("span","",c.venue),count=node("span","conference-size",String(c.count));button.type="button";button.setAttribute("aria-label",`${group.year} ${c.venue}`);button.dataset.year=group.year;button.dataset.venue=c.venue;button.append(label,count);button.onclick=()=>{year=group.year;venue=c.venue;category="";subcategory="";page=0;load()};section.append(button)}$("conference-years").append(section)}markNavigation();
}
function markNavigation(){for(const b of document.querySelectorAll(".conference-button"))b.setAttribute("aria-current",String(Number(b.dataset.year)===year&&b.dataset.venue===venue))}
function renderTaxonomy(){const box=$("conference-taxonomy");box.replaceChildren();$("category-all").classList.toggle("selected",!category);
 for(const c of taxonomy){const group=node("details","category-group");group.open=c.id===category;const summary=node("summary",""),title=node("span","",c.label),count=node("span","category-size",String(c.count));summary.append(title,count);group.append(summary);
 const all=node("button","subcategory-button",`全部 ${c.count} 篇`);all.type="button";all.classList.toggle("selected",category===c.id&&!subcategory);all.onclick=()=>selectCategory(c.id);group.append(all);
 for(const s of c.children){const button=node("button","subcategory-button",`${s.label} · ${s.count}`);button.type="button";button.classList.toggle("selected",category===c.id&&subcategory===s.id);button.onclick=()=>selectCategory(c.id,s.id);group.append(button)}box.append(group)}
}
function renderPapers(data){$("library-list").replaceChildren();const parent=taxonomy.find(c=>c.id===category),child=parent?.children.find(s=>s.id===subcategory);$("conference-breadcrumb").textContent=child?parent.label+" / "+child.label:parent?.label||"全部论文";
 $("conference-count").textContent=`${data.count} 篇 · 30 篇／页`;
 for(const p of data.papers){const row=node("article","conference-paper"),title=paperTitle(p,'button','conference-paper-title');title.type="button";title.onclick=()=>openReader(p.id,"tasks");row.append(title);
 const authors=node("p","paper-authors","作者："+(Array.isArray(p.authors)?p.authors.join(", "):p.authors||"待补充"));row.append(authors);
 const tags=node("div","conference-paper-tags");for(const [cid,sid] of p.categories){const c=taxonomy.find(t=>t.id===cid),s=c?.children.find(t=>t.id===sid);if(!c||!s)continue;const tag=node("button","",s.label);tag.type="button";tag.title=c.label;tag.onclick=()=>selectCategory(cid,sid);tags.append(tag)}row.append(tags);
 const actions=node("div","conference-paper-actions"),tasks=node("button","button",`整理内容 ${paperTaskProgress(p.id)}/${paperTaskTotal}`),abstract=node("button","button","中英摘要"),notes=node("button","button","笔记");tasks.type=abstract.type=notes.type="button";tasks.dataset.paperChecklist=p.id;tasks.setAttribute("aria-label","整理论文："+p.title);tasks.onclick=()=>openReader(p.id,"tasks");abstract.onclick=()=>openReader(p.id,"abstract");notes.onclick=()=>openReader(p.id,"notes");const add=node("a","button","加入任务");add.href="http://127.0.0.1:8866/?addPaper="+encodeURIComponent(p.id)+"#daily";add.setAttribute("aria-label","加入今日任务："+p.title);add.onclick=e=>{
   if(window.parent!==window){e.preventDefault();window.parent.postMessage({type:"research-add-paper-task",paperId:p.id},"http://127.0.0.1:8869")}
 };actions.append(tasks,abstract,notes,add);
 for(const [label,url] of [["arXiv ↗",p.arxivUrl],["官方页面 ↗",p.source],["PDF ↗",p.pdf]]){const a=link(label,url);if(a)actions.append(a)}mountQuizToggle(actions,p.id);row.append(actions);$("library-list").append(row)}
 if(!data.papers.length){const empty=node("div","conference-empty");empty.append(node("h3","",data.total?"这个筛选下暂无论文":"本地尚无该会议的题录"),node("p","small muted",data.total?"可以换一个分类，或清空搜索。":"可切换其他年份浏览已有题录，后续补充该会议的正式来源与论文。"));$("library-list").append(empty)}
 $("library-prev").disabled=page===0;$("library-next").disabled=(page+1)*data.pageSize>=data.count;$("conference-page").textContent=`${page+1} / ${Math.max(1,Math.ceil(data.count/data.pageSize))}`;
}
async function load(){const version=++request;updateUrl();markNavigation();$("conference-title").textContent=`${venue} ${year}`;$("conference-count").textContent="正在读取…";$("library-list").setAttribute("aria-busy","true");
 try{const data=await api("/api/conference-library?"+new URLSearchParams({year,venue,category,subcategory,q:query,page}));if(version!==request)return;page=data.page;taxonomy=data.taxonomy;$("conference-total").textContent=`本地收录 ${data.total} 篇 · 可按多个类别交叉浏览`;$("conference-source-note").textContent=data.source?.note||"当前本地没有该年份、该会议的来源记录。";const source=$("conference-source-link");source.hidden=!/^https:\/\//.test(data.source?.url||"");if(!source.hidden)source.href=data.source.url;renderTaxonomy();renderPapers(data)
 }catch(e){if(version===request){$("conference-count").textContent=e.message;$("library-list").replaceChildren(node("p","muted","请点击“刷新本地目录”重试。"))}}finally{if(version===request)$("library-list").removeAttribute("aria-busy")}}
$("category-all").onclick=()=>selectCategory();let searchTimer;$("conference-search").oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{query=$("conference-search").value.trim();page=0;load()},250)};
$("library-prev").onclick=()=>{page=Math.max(0,page-1);load()};$("library-next").onclick=()=>{page++;load()};$("conference-refresh").onclick=async()=>{const b=$("conference-refresh");b.disabled=true;try{await navigation(true);await load()}catch(e){$("conference-count").textContent=e.message}finally{b.disabled=false}};
window.addEventListener("paper-reading-tasks-change",e=>{for(const button of document.querySelectorAll("[data-paper-checklist]"))if(button.dataset.paperChecklist===e.detail.id)button.textContent=`整理内容 ${paperTaskProgress(e.detail.id)}/${paperTaskTotal}`});
navigation().then(load).catch(e=>{$("conference-total").textContent=e.message});
