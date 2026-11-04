import {knowledgeApi as api} from './paper-knowledge.js';
import {renderNote} from './note-markdown.js';
const q=new URLSearchParams(location.search),kind=q.get('kind'),id=q.get('id');
const endpoints={method:'method-posts',blog:'blog-posts',news:'news-posts',idea:'research-ideas'};
try{let item;try{item=JSON.parse(localStorage.getItem('article-view:'+q.get('draft'))||'null');}catch{}
if(id&&endpoints[kind]){const data=await api(endpoints[kind]);item=[...(data.items||[]),...(data.archived||[])].find(p=>p.id===id)||item;}
if(!item)throw Error('文章未找到，请从列表重新打开。');
document.title=item.title||'文章阅读';document.querySelector('#title').textContent=item.title;document.querySelector('#meta').textContent=item.noteDate||item.newsDate||item.date||'';
const host=document.querySelector('#body');renderNote(host,item.content||item.idea||item.summary||'');
if(item.motivation){const h=document.createElement('h2');h.textContent='Motivation · 研究动机';const d=document.createElement('div');renderNote(d,item.motivation);host.prepend(h,d);}
if(item.source||item.outlet){const p=document.createElement('p');p.textContent='来源：'+(item.source||item.outlet);host.prepend(p);}
if(/^https?:\/\//.test(item.sourceUrl||'')){const a=document.createElement('a');a.href=item.sourceUrl;a.textContent='查看原始来源 ↗';a.target='_blank';a.rel='noopener';host.prepend(a);}
for(const c of item.cards||[]){const h=document.createElement('h2');h.textContent=c.question;const d=document.createElement('details'),s=document.createElement('summary'),b=document.createElement('div');s.textContent='查看答案';renderNote(b,c.answer||'暂未填写');d.append(s,b);host.append(h,d);}
const dims={strategy:'战略',campaign:'战役',tactics:'战术',intelligence:'情报与判断',adversary:'对手与博弈',resources:'资源与约束',review:'复盘与止损'},roles={researcher:'竞争科研者',ceo:'AI公司老板',industry:'工信部',user:'技术落地与用户',safety:'安全与社会影响',investment:'投资与产业链'};
for(const [role,comments] of Object.entries(item.comments||{})){const h=document.createElement('h2');h.textContent=(roles[role]||role)+' · 个人分析';host.append(h);for(const [dim,text] of Object.entries(comments)){if(!text)continue;const h3=document.createElement('h3'),b=document.createElement('div');h3.textContent=dims[dim]||dim;renderNote(b,text);host.append(h3,b);}}
const back=document.querySelector('#back');back.href=kind==='method'?'methods.html?category='+encodeURIComponent(item.category||'research'):'blog.html'+(kind==='news'?'?module=news':kind==='idea'?'?module=ideas':'');
}catch(e){document.querySelector('#title').textContent=e.message;}
