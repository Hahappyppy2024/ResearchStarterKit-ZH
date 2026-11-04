import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
import {knowledgeApi as api} from './paper-knowledge.js';
import {openReader} from './paper-reader.js';
import {categoriesForTopic,timelineEntries} from './topic-timeline-model.mjs';
const $=id=>document.getElementById(id),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;},params=new URLSearchParams(location.search),topicId=params.get('topic'),kind=params.get('kind')==='solution'?'solution':'problem';
let categories=[],entries=[],selected='',failed=[];
function draw(){
 const q=$('search').value.trim().toLowerCase(),year=$('year').value,visible=entries.filter(p=>(!selected||p.categories.some(n=>n.id===selected))&&(!year||p.time.startsWith(year))&&(!q||(p.title+' '+p.authors).toLowerCase().includes(q)));
 $('status').textContent=visible.length+' 篇论文 · 从早到新'+(failed.length?'；'+failed.length+' 个分类加载失败，请刷新重试':'');
 $('timeline').replaceChildren();let group='';for(const p of visible){const year=p.time.slice(0,4)||'发表时间待补充';if(year!==group){group=year;$('timeline').append(el('h2',year));}const card=el('article'),date=el('time',p.time||'时间待补充'),h=el('h3'),title=paperTitle(p,'button');card.className='timeline-paper';title.onclick=()=>openReader(p.id,'tasks');h.append(title);card.append(date,h,el('p',Array.isArray(p.authors)?p.authors.join(', '):p.authors||'作者待补充'));const tags=el('div');tags.className='timeline-tags';for(const n of p.categories){const a=el('a',n.name);a.href='lineage.html?map='+encodeURIComponent(n.lineageId||'taxonomy-'+n.id)+'&view=timeline';tags.append(a);}card.append(tags);if(p.summary)card.append(el('p',p.summary));const read=el('button','打开阅读任务');read.onclick=()=>openReader(p.id,'tasks');card.append(read);$('timeline').append(card);}
 if(!visible.length)$('timeline').append(el('p',categories.length?'此筛选下还没有关联论文。点击左侧分类进入脉络页，可从 arXiv 或论文库添加。':'尚未关联分类。可返回 Topic 关联已有分类，或点击左侧新建。'));
 for(const b of $('categories').querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.id===selected));
}
async function load(){
 const {nodes}=await api('taxonomy'),topic=nodes.find(n=>n.id===topicId&&n.kind==='topic');if(!topic)throw Error('请从某个 Topic 的问题或方法时间线入口进入。');const topicName=({'Agent / LLM':'智能体与大语言模型',AIGC:'生成式人工智能'}[topic.name]||topic.name),label=kind==='problem'?'问题':'方法';document.title=topicName+' · '+label+'时间线';$('heading').textContent=topicName+' · '+label+'时间线';$('description').textContent='按关联论文的发表时间排列；同一篇论文跨分类去重，日期缺失时仅显示已知年份。';$('category-heading').textContent=label+'分类';$('back').href='lineage.html?map='+encodeURIComponent(topic.lineageId||'taxonomy-'+topic.id);$('create').href='taxonomy.html?kind='+kind+'&topicId='+encodeURIComponent(topicId);
 for(const [k,name] of [['problem','问题时间线'],['solution','方法时间线']]){const a=el('a',name);a.href='?topic='+encodeURIComponent(topicId)+'&kind='+k;a.setAttribute('aria-current',String(k===kind));$('kinds').append(a);}
 categories=categoriesForTopic(nodes,topicId,kind);const results=await Promise.allSettled(categories.map(async category=>({category,...await api('lineages?id='+encodeURIComponent(category.lineageId||'taxonomy-'+category.id))})));failed=results.filter(r=>r.status==='rejected');entries=timelineEntries(results.filter(r=>r.status==='fulfilled').map(r=>r.value));
 const all=el('button','全部'+label+' · '+entries.length+' 篇');all.dataset.id='';all.onclick=()=>{selected='';draw();};$('categories').append(all);
 for(const n of categories){const box=el('div'),b=el('button',n.name+' · '+entries.filter(p=>p.categories.some(c=>c.id===n.id)).length+' 篇'),a=el('a','进入脉络 ↗');b.dataset.id=n.id;b.onclick=()=>{selected=n.id;draw();};a.href='lineage.html?map='+encodeURIComponent(n.lineageId||'taxonomy-'+n.id)+'&view=timeline';box.append(b,a);$('categories').append(box);}
 for(const y of [...new Set(entries.map(p=>p.time.slice(0,4)).filter(Boolean))].sort().reverse())$('year').add(new Option(y,y));draw();
}
$('search').oninput=draw;$('year').onchange=draw;load().catch(e=>$('status').textContent=e.message);
