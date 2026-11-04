import {subtreeIds} from './timeline-nesting.mjs';

const fields=['paper','projectTask','studyTask','durationMinutes','spentMinutes'];
function metadata(item){return Object.fromEntries(fields.filter(key=>item[key]!==undefined).map(key=>[key,item[key]]));}
function duration(task){return Number.isInteger(task.sourceStart)&&Number.isInteger(task.sourceEnd)?task.sourceEnd-task.sourceStart:Number.isInteger(task.start)&&Number.isInteger(task.end)?task.end-task.start:task.durationMinutes;}

export function returnScheduledTask(state,task,newId){
 const todos=state.todos||[],existing=todos.find(t=>t.id===task.id),timelineOrder=(state.timelineOrder||[]).filter(id=>id!==task.id);
 if(existing)return {...state,todos:todos.map(t=>t.id===task.id?{...t,start:null,end:null,...(duration(t)?{durationMinutes:duration(t)}:{})}:t),timelineOrder};
 if((state.hiddenSchedule||[]).includes(task.id)||todos.some(t=>t.id===newId))return state;
 const todo={id:newId,title:task.title,start:null,end:null,detail:task.detail||'',sourceScheduleId:task.id,...metadata(task),...(duration(task)?{durationMinutes:duration(task)}:{})};
 const subtasks={...state.subtasks,[newId]:state.subtasks?.[task.id]||[]};delete subtasks[task.id];
 return {...state,todos:[...todos,todo],subtasks,timelineOrder,hiddenSchedule:[...new Set([...(state.hiddenSchedule||[]),task.id])],done:(state.done||[]).filter(id=>id!==task.id).concat((state.done||[]).includes(task.id)?[newId]:[])};
}

export function returnSubtask(state,rootId,id,newId){
 const items=state.subtasks?.[rootId]||[],item=items.find(t=>t.id===id);if(!item)return state;
 const saved=state.nestedTodoArchive?.[item.sourceTodoId]?.todo,ident=saved?.id||newId;
 if((state.todos||[]).some(t=>t.id===ident))return state;
 const ids=new Set(subtreeIds(items,id)),todo={...saved,id:ident,title:item.title,start:null,end:null,detail:item.detail??saved?.detail??'',...metadata(item),...(!item.durationMinutes&&saved&&duration(saved)?{durationMinutes:duration(saved)}:{})};
 const children=items.filter(t=>t.id!==id&&ids.has(t.id)).map(t=>{const child={...t};if(child.parentSubtaskId===id)delete child.parentSubtaskId;return child;});
 const archive={...state.nestedTodoArchive};if(item.sourceTodoId)delete archive[item.sourceTodoId];
 return {...state,todos:[...(state.todos||[]),todo],done:[...new Set([...(state.done||[]),...(item.done?[ident]:[])])],subtasks:{...state.subtasks,[rootId]:items.filter(t=>!ids.has(t.id)),[ident]:children},nestedTodoArchive:archive};
}
