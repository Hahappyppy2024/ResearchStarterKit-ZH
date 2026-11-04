import {knowledgeApi as api} from './paper-knowledge.js';
import {datasetEditor} from './dataset-ui.js';
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
export function renderTopicContext({current,nodes,maps,name}){
 let rail=document.getElementById('topic-context');if(!rail){rail=el('aside');rail.id='topic-context';rail.className='topic-context';document.querySelector('.shell').append(rail);}rail.replaceChildren();
 const byId=new Map(nodes.map(n=>[n.id,n])),node=nodes.find(n=>(n.lineageId||'taxonomy-'+n.id)===current.id);
 function linkedTopics(n){const ids=new Set();let current=n,seen=new Set();while(current&&!seen.has(current.id)){seen.add(current.id);for(const id of current.topicIds||[])ids.add(id);current=byId.get(current.parentId);}return ids;}
 if(!node||node.kind!=='topic'){const title=el('h3',node?'关联主题':'主题内的问题与方法');rail.append(title);if(node){const ids=linkedTopics(node);for(const id of ids){const t=byId.get(id);if(!t)continue;const a=el('a',name({id:t.lineageId||'taxonomy-'+t.id,name:t.name}));a.href='lineage.html?map='+encodeURIComponent(t.lineageId||'taxonomy-'+t.id);a.className='topic-context-link';rail.append(a);}if(!ids.size)rail.append(el('p','尚未关联 Topic，可在分类定义中设置。'));}else rail.append(el('p','选择左侧 Topic，查看该主题的问题树和方法树。'));const a=el('a','管理问题／方法与 Topic 关联 ↗');a.href='taxonomy.html?kind=problem';rail.append(a);return;}
 const topicIds=new Set([node.id]);for(let i=0;i<3;i++)for(const n of nodes)if(n.kind==='topic'&&topicIds.has(n.parentId))topicIds.add(n.id);
 rail.append(el('h3',name(current)),el('p','本主题及子主题的问题、方法与数据集；可关联多个主题。'));
 for(const kind of ['problem','solution']){
  const section=el('section'),header=el('div'),heading=el('a',kind==='problem'?'问题时间线 ↗':'方法时间线 ↗'),create=el('a','＋');header.className='topic-context-heading';heading.href='topic-timeline.html?topic='+encodeURIComponent(node.id)+'&kind='+kind;heading.className='topic-timeline-entry';create.href='taxonomy.html?kind='+kind+'&topicId='+encodeURIComponent(node.id);create.setAttribute('aria-label',kind==='problem'?'新建本主题的问题':'新建本主题的方法');header.append(heading,create);section.append(header);
  const relevant=nodes.filter(n=>n.kind===kind&&[...linkedTopics(n)].some(id=>topicIds.has(id)));
  section.append(el('p',relevant.length+' 个'+(kind==='problem'?'问题':'方法')+' · 按论文发表时间查看脉络'));
  const button=el('button','关联已有'+(kind==='problem'?'问题':'方法'));button.onclick=()=>chooseExisting(kind);section.append(button);rail.append(section);
 }

 renderDatasets();
 const unassigned=nodes.filter(n=>n.kind!=='topic'&&!linkedTopics(n).size);if(unassigned.length){const a=el('a',unassigned.length+' 个问题／方法尚未关联 Topic ↗');a.href='taxonomy.html?kind=problem';rail.append(a);}
 function chooseExisting(kind){const dialog=el('dialog'),form=el('form'),select=el('select'),status=el('p'),save=el('button','保存关联'),cancel=el('button','取消');dialog.className='topic-context-dialog';select.setAttribute('aria-label','选择已有'+(kind==='problem'?'问题':'方法'));for(const n of nodes.filter(n=>n.kind===kind))select.add(new Option(n.name+' · '+n.en,n.id));save.type='submit';cancel.type='button';cancel.onclick=()=>dialog.close();form.append(el('h3','关联已有'+(kind==='problem'?'问题':'方法')),select,save,cancel,status);dialog.append(form);document.body.append(dialog);dialog.onclose=()=>dialog.remove();dialog.showModal();if(!select.options.length){status.textContent='还没有已定义的分类，请使用 ＋ 新建。';save.disabled=true;}form.onsubmit=async event=>{event.preventDefault();const n=byId.get(select.value);save.disabled=true;try{await api('taxonomy',{...n,topicIds:[...new Set([...(n.topicIds||[]),node.id])]});dialog.close();location.reload();}catch(error){status.textContent=error.message;save.disabled=false;}};}
 async function renderDatasets(){
  const section=el('section'),header=el('div'),create=el('button','＋');header.className='topic-context-heading';create.setAttribute('aria-label','新建本主题的数据集');header.append(el('h4','数据集'),create);section.append(header);rail.append(section);
  create.onclick=()=>{const dialog=el('dialog'),host=el('div'),close=el('button','关闭');dialog.className='topic-context-dialog';close.onclick=()=>dialog.close();dialog.append(close,host);document.body.append(dialog);dialog.onclose=()=>dialog.remove();dialog.showModal();datasetEditor(host,{topicIds:[node.id]},()=>location.reload()).catch(e=>host.append(el('p',e.message)));};
  try{const data=(await api('datasets')).items;if(!section.isConnected)return;const relevant=data.filter(d=>(d.topicIds||[]).some(id=>topicIds.has(id)));for(const d of relevant){const a=el('a',d.name);a.className='topic-context-link';a.href='datasets.html?id='+encodeURIComponent(d.id);a.title=d.en||d.name;section.append(a);}if(!relevant.length)section.append(el('p','还没有关联的数据集。'));
   const choose=el('button','关联已有数据集');section.append(choose);choose.onclick=()=>{const dialog=el('dialog'),form=el('form'),select=el('select'),save=el('button','保存关联'),cancel=el('button','取消'),status=el('p');dialog.className='topic-context-dialog';select.setAttribute('aria-label','选择已有数据集');for(const d of data)select.add(new Option(d.name,d.id));save.type='submit';save.disabled=!data.length;cancel.type='button';cancel.onclick=()=>dialog.close();form.append(el('h3','关联已有数据集'),select,save,cancel,status);dialog.append(form);document.body.append(dialog);dialog.onclose=()=>dialog.remove();dialog.showModal();form.onsubmit=async e=>{e.preventDefault();save.disabled=true;const d=data.find(d=>d.id===select.value);try{await api('dataset-topics',{id:d.id,revision:d.revision,topicIds:[...new Set([...(d.topicIds||[]),node.id])]});location.reload();}catch(error){status.textContent=error.message;save.disabled=false;}};};
   const all=el('a','查看本主题数据集 ↗');all.href='datasets.html?topic='+encodeURIComponent(node.id);section.append(all);
  }catch(error){section.append(el('p',error.message));}
 }

}
