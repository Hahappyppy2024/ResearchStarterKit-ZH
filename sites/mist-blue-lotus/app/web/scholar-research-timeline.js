import {researchTimeline} from './scholar-research-model.mjs';
export function scholarResearchTimeline(person,{compact=false}={}){
 const box=document.createElement(compact?'details':'section');box.className='scholar-research-timeline'+(compact?' compact':'');
 const title=document.createElement(compact?'summary':'h3');title.textContent='研究方向 · Timeline';box.append(title);
 const entries=researchTimeline(person.research),list=document.createElement('ol');
 for(const entry of entries){const row=document.createElement('li'),date=document.createElement('small'),text=document.createElement('p');date.textContent=entry.date||'时间未标注';text.textContent=entry.text;row.append(date,text);list.append(row);}
 if(entries.length)box.append(list);else{const empty=document.createElement('p');empty.textContent='研究方向待补充，可在编辑学者中添加。';box.append(empty);}
 if(!compact&&/^https:\/\//.test(person.source||'')){const link=document.createElement('a');link.textContent='学者资料来源 🔗';link.href=person.source;link.target='_blank';link.rel='noopener';box.append(link);}
 return box;
}
