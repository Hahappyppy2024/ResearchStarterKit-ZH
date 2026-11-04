import {paperTitle} from './paper-title.js';
import {knowledgeApi as api} from './paper-knowledge.js';
import {questionCard} from './paper-questions-ui.js';
import {openReader} from './paper-reader.js';
const $=id=>document.getElementById(id),node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
let paperId=new URLSearchParams(location.search).get('paperId')||'',questionId=new URLSearchParams(location.search).get('questionId')||'',data=null,token=0;
const expanded=new Set();if(paperId)expanded.add(paperId);
function filtered(){const word=$('question-search').value.trim().toLowerCase(),state=$('question-state').value,date=$('question-date').value;return (data?.items||[]).filter(q=>(!date||q.date===date)&&(state==='all'||q.resolved===(state==='resolved'))&&(!word||[q.paperTitle,q.question,q.answer].join(' ').toLowerCase().includes(word)));}
function choose(id,qid=''){paperId=id;questionId=qid;expanded.add(id);render();const u=new URL(location.href);u.searchParams.set('paperId',paperId);if(questionId)u.searchParams.set('questionId',questionId);else u.searchParams.delete('questionId');history.replaceState(null,'',u);}
function nav(label,count,active,action){const b=node('button',undefined,'desk-nav');b.type='button';b.setAttribute('aria-current',String(active));b.append(node('span',label),node('small',String(count)));b.onclick=action;return b;}
function drawTree(items){const tree=$('question-tree');tree.replaceChildren();$('question-tree-count').textContent=(data?.total||0)+' 个';
 for(const [label,value] of [['全部问题','all'],['未解决','open'],['已解决','resolved']]){const count=data.items.filter(q=>value==='all'||q.resolved===(value==='resolved')).length;tree.append(nav(label,count,$('question-state').value===value,()=>{$('question-state').value=value;render();}));}
 tree.append(node('h3','论文笔记','question-tree-heading'));
 for(const id of [...new Set(items.map(q=>q.paperId))]){const list=items.filter(q=>q.paperId===id),branch=node('details',undefined,'desk-folder'),summary=node('summary'),title=node('button',undefined,'desk-nav');branch.open=expanded.has(id);branch.ontoggle=()=>{if(branch.open)expanded.add(id);else expanded.delete(id);};title.type='button';title.setAttribute('aria-current',String(id===paperId));title.append(paperTitle({id,title:list[0].paperTitle},'span'),node('small',list.length+' 个'));title.onclick=()=>choose(id);summary.append(title);branch.append(summary);for(const q of list){const b=nav(q.question,q.resolved?'已解决':'未解决',questionId===q.id,()=>choose(id,q.id));b.classList.add('question-tree-item');branch.append(b);}tree.append(branch);}
 if(!items.length)tree.append(node('p','暂无匹配的问题。','desk-status'));
}
function drawTimeline(items){const host=$('question-timeline');host.replaceChildren();const dates=[...new Set(items.map(q=>q.date))].sort().reverse();$('question-paper-count').textContent=new Set(items.map(q=>q.paperId)).size+' 篇';
 for(const date of dates){host.append(node('h3',date,'timeline-date'));const daily=items.filter(q=>q.date===date);for(const id of [...new Set(daily.map(q=>q.paperId))]){const list=daily.filter(q=>q.paperId===id),row=node('article',undefined,'timeline-record'),b=node('button',undefined,'timeline-note'+(id===paperId?' active':''));b.type='button';b.append(paperTitle({id,title:list[0].paperTitle},'strong'),node('p',list[0].question),node('small',list.length+' 个问题 · '+list.filter(q=>!q.resolved).length+' 个未解决'));b.onclick=()=>choose(id,list[0].id);row.append(b);host.append(row);}}
 if(!items.length)host.append(node('p','这个范围还没有论文问题记录。','desk-status'));
}
function drawContent(items){const host=$('question-content');host.replaceChildren();const q=items.find(q=>q.paperId===paperId&&q.id===questionId);
 if(!q){host.append(node('p','这里还没有问题。可在论文阅读清单的最后添加，每个问题会保存为一篇独立的问题笔记。','question-empty'));if(paperId){const add=node('button','打开关联论文 · 添加问题','button');add.type='button';add.onclick=()=>openReader(paperId,'tasks');host.append(add);}return;}
 const head=node('div',undefined,'question-paper-heading'),open=node('button','打开关联论文','button');open.type='button';open.onclick=()=>openReader(q.paperId,'tasks');head.append(node('small','关联论文'),paperTitle({id:q.paperId,title:q.paperTitle},'h3'),open);host.append(head);
 const card=questionCard(q,load);card.id='question-record-'+q.id;const subject=card.querySelector('.question-title'),body=card.querySelector('textarea:not(.question-title)'),subjectLabel=node('label','问题标题 · Subject'),bodyLabel=node('label','正文 · 答案、推导与证据');subject.id='question-subject';body.id='question-note-body';subjectLabel.htmlFor=subject.id;bodyLabel.htmlFor=body.id;body.placeholder='写下你的理解、推导、证据、论文页码或代码／日志路径。';card.insertBefore(subjectLabel,subject);card.insertBefore(bodyLabel,body);host.append(card);
}
function render(){if(!data)return;const items=filtered();if(items.length&&!paperId){paperId=items[0].paperId;questionId='';}const list=items.filter(q=>q.paperId===paperId);if(!list.some(q=>q.id===questionId))questionId=list[0]?.id||'';if(questionId)expanded.add(paperId);drawTree(items);drawTimeline(items);drawContent(items);$('question-statistics').textContent='累计 '+data.allTotal+' 个 · 未解决 '+data.allOpen+' · 已解决 '+data.allResolved;$('question-scope').textContent=($('question-date').value||'全部记录日期')+' · '+items.length+' 个问题';}

async function load(){const current=++token;try{const latest=await api('paper-questions');if(current!==token)return;data=latest;render();}catch(e){$('question-statistics').textContent='问题记录暂未读取：'+e.message;}}
$('question-date').onchange=render;$('all-question-dates').onclick=()=>{$('question-date').value='';render();};$('question-state').onchange=render;$('question-search').oninput=render;$('question-refresh').onclick=load;window.addEventListener('focus',load);window.addEventListener('paper-questions-change',load);load();

const initialState=new URLSearchParams(location.search).get('state');if(['open','resolved'].includes(initialState))$('question-state').value=initialState;
window.addEventListener('storage',e=>{if(e.key==='paper-questions-updated')load();});
