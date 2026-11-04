import {openReader} from './paper-reader.js';
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n};
export function mountCourseBibliography(container,courseId){
 const panel=el('section',null,'course-info-panel course-model-panel'),status=el('p','正在读取模型来源…','small muted');
 panel.append(el('h2','基础模型'),status);container.append(panel);
 fetch('/api/study/course-bibliography?id='+encodeURIComponent(courseId),{cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok)throw Error(d.error||'读取失败');return d}).then(data=>{
  if(!panel.isConnected)return;status.textContent=(data.items?.length||0)+' 篇来源论文 · 年份为 arXiv 首发年份';
  if(data.note){const note=el('details',null,'course-model-notes');note.append(el('summary','来源与阅读顺序说明'),el('p',data.note,'small muted'));panel.append(note)}
  const models=data.items?.filter(p=>p.role==='model')||[],related=data.items?.filter(p=>p.role!=='model')||[];
  const render=(p,box)=>{const card=el('article',null,'course-model-card');card.append(el('h3',p.model),el('p',p.roleLabel+' · '+p.year+' · '+p.originLabel,'course-model-meta'));
   const title=el('a',p.title,'course-model-paper');title.href=p.url;title.target='_blank';title.rel='noopener';card.append(title);
   const guide=el('details',null,'course-model-notes');guide.append(el('summary','阅读重点与来源'),el('p',p.reading,'small muted'));if(p.authors?.length)guide.append(el('p','作者：'+p.authors.join(', '),'small muted'));
   if(p.originNote)guide.append(el('p',p.originNote,'small muted'));
   if(p.sourceNumbers?.length){const posters=el('div',null,'actions');for(const number of p.sourceNumbers){const a=el('a','海报 '+number);a.href='/api/study/course-poster?id='+encodeURIComponent(courseId)+'&source='+number;a.target='_blank';a.rel='noopener';posters.append(a)}guide.append(posters)}card.append(guide);
   const actions=el('div',null,'actions'),read=el('button','阅读 / 笔记','button');read.type='button';read.onclick=()=>openReader(p.paperId);actions.append(read);
   const source=el('a','原论文 ↗','button');source.href=p.url;source.target='_blank';source.rel='noopener';actions.append(source);card.append(actions);box.append(card)};
  if(models.length){const group=el('details',null,'course-model-group');group.open=true;group.append(el('summary','基础模型 / 系统 · '+models.length));for(const p of models)render(p,group);panel.append(group)}
  if(related.length){const group=el('details',null,'course-model-group');group.append(el('summary','相关论文 · 方法 / 数据 / 评测 · '+related.length));for(const p of related)render(p,group);panel.append(group)}
  if(!data.items?.length)panel.append(el('p','待核对模型名称与原论文。','muted'));
  if(data.lineageId){const a=el('a','在论文脉络中查看所属主题 ↗','button');a.href='/lineage.html?map='+encodeURIComponent(data.lineageId);a.target='_blank';a.rel='noopener';panel.append(a)}
 }).catch(e=>{if(panel.isConnected)status.textContent='模型来源暂时读取失败：'+e.message});
}
