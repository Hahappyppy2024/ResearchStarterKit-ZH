import {subtreeIds} from './timeline-nesting.mjs';
import {cleanPaper} from './todos.mjs';
export function paperPdfUrl(p){
 const safe=v=>typeof v==='string'&&/^https?:\/\//i.test(v)?v:'';
 if(safe(p.pdf))return p.pdf;
 for(const url of [p.arxivUrl,p.source,p.url]){if(!safe(url))continue;if(/arxiv\.org\/(abs|pdf)\//i.test(url))return url.replace('/abs/','/pdf/');if(/\.pdf(?:[?#]|$)/i.test(url))return url;if(/openaccess\.thecvf\.com\/.*\/html\/.*\.html/i.test(url))return url.replace('/html/','/papers/').replace(/\.html(?=[?#]|$)/,'.pdf');}
 return '';
}
export function appendPaperTodo(database,paper,date,id){
 if(!database||typeof database!=='object'||Array.isArray(database)||!database.days||typeof database.days!=='object'||Array.isArray(database.days))throw Error('待办记录无法读取，请先检查每日努力中的现有记录');
 const p=cleanPaper({...paper,url:paperPdfUrl(paper)||paper.source});if(!p)throw Error('论文题录不完整');
 const day=database.days[date]||{},todos=day.todos||[];if(!Array.isArray(todos))throw Error('当天待办记录格式异常');
 if(paperTodoInDay(day,p.id))return {database,added:false};
 const todo={id,title:p.title.slice(0,160),start:null,end:null,detail:'',paper:p};
 return {database:{...database,days:{...database.days,[date]:{...day,todos:[...todos,todo]}}},added:true};
}
export function togglePaperTodo(database,paper,date,id){
 const prepared=appendPaperTodo(database,paper,date,id),day=database.days[date]||{},matching=(day.todos||[]).filter(t=>t.paper?.id===paper.id);
 if(matching.length){
  const ids=new Set(matching.map(t=>t.id)),subtasks={...day.subtasks},savedSubtasks={};for(const ident of ids){if(subtasks[ident])savedSubtasks[ident]=subtasks[ident];delete subtasks[ident];}
  const archive={...(day.catalogTodoArchive||{}),[paper.id]:{todos:matching,done:(day.done||[]).filter(i=>ids.has(i)),subtasks:savedSubtasks}};
  return {added:false,database:{...database,days:{...database.days,[date]:{...day,todos:day.todos.filter(t=>!ids.has(t.id)),done:(day.done||[]).filter(i=>!ids.has(i)),subtasks,catalogTodoArchive:archive}}}};
 }
 const nested=[];for(const [rootId,items] of Object.entries(day.subtasks||{})){const ids=new Set(items.filter(t=>t.paper?.id===paper.id).flatMap(t=>subtreeIds(items,t.id)));if(ids.size)nested.push({rootId,items:items.filter(t=>ids.has(t.id))});}
 if(nested.length){const subtasks={...day.subtasks};for(const group of nested){const ids=new Set(group.items.map(t=>t.id));subtasks[group.rootId]=subtasks[group.rootId].filter(t=>!ids.has(t.id));}return {added:false,database:{...database,days:{...database.days,[date]:{...day,subtasks,catalogTodoArchive:{...day.catalogTodoArchive,[paper.id]:{todos:[],done:[],subtasks:{},nested}}}}}};}
 const saved=day.catalogTodoArchive?.[paper.id];if(!saved)return prepared;
 const archive={...day.catalogTodoArchive};delete archive[paper.id];const subtasks={...day.subtasks,...saved.subtasks};for(const group of saved.nested||[])subtasks[group.rootId]=[...(subtasks[group.rootId]||[]),...group.items];
 return {added:true,database:{...database,days:{...database.days,[date]:{...day,todos:[...(day.todos||[]),...saved.todos],done:[...new Set([...(day.done||[]),...saved.done])],subtasks,catalogTodoArchive:archive}}}};
}

export function paperTodoInDay(day,id){return (day?.todos||[]).some(t=>t.paper?.id===id)||Object.values(day?.subtasks||{}).some(items=>items.some(t=>t.paper?.id===id));}
