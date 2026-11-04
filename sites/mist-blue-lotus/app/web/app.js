import {refreshDailyPaperStatistics} from './daily-paper-statistics.js';
import {openScheduleCalendar} from './schedule-calendar.js';
import {TEMPLATE_KEY,cleanTemplateTasks,defaultTemplates,validateTemplates,baseForDate,freezeExistingDays,applyTemplateToDay,undoTemplateApplication} from './schedule-templates.mjs';
import {openTemplateSettings} from './schedule-template-settings.js';
import {advanceDailyDate,unscheduledPeriod} from './daily-date.mjs';
import {dailyState,resetDailyCompletion,undoDailyCompletionReset,restoreDailyTemplate,undoDailyTemplateRestore} from './daily-state.mjs';
import {knowledgeApi} from './paper-knowledge.js';
import {returnScheduledTask,returnSubtask} from './timeline-return.mjs';
import {nestTodo,restoreNestedTodo,moveSubtask,subtreeIds} from './timeline-nesting.mjs';
import {makeTodoDraggable,mountDailyTimeline,makeSubtaskDraggable,makeSubtaskDropTarget,makeSubtaskResizable,mountTodoReturnTarget} from './daily-timeline.js';
import {prioritizeTask,subtaskSlots} from './timeline-model.mjs';
import {dailyCompletion} from './daily-completion.mjs';
import {mountPaperProgress} from './paper-progress.js';
import {renderWeeklyCats} from './weekly-cats.js';
import {paperTitle,setPaperTitle,paperOption} from './paper-title.js';
import {mountQuizToggle} from './paper-quiz-ui.js';
import {cacheManualReading,markPaperRead,isPaperRead,renderReadingStats,READING_STATE_KEY,READING_HISTORY_KEY} from "./reading-history.mjs";
import {openReader,paperTaskProgress,paperTaskTotal,markPaperTaskDone} from "./paper-reader.js";
import {cleanTodos,plannedTasks,currentTask,timeMinutes,scheduledBase,cleanScheduleOverrides,cleanHiddenSchedule,cleanSubtasks,cleanPaper} from "./todos.mjs";
import {schedule as builtinSchedule,reminders,timeLabel,chinaTime,currentAt,nextAt,shiftDate,calendarText} from "./schedule.mjs";
let schedule=builtinSchedule;
let templateConfig=defaultTemplates(builtinSchedule);try{const raw=localStorage.getItem(TEMPLATE_KEY);if(raw)templateConfig=validateTemplates(JSON.parse(raw));}catch{}
const $=id=>document.getElementById(id);
const key="daily-practice-v1";
let db={days:{},notifications:false},storageOkay=true;
try{const saved=JSON.parse(localStorage.getItem(key)||"null");if(saved?.days&&typeof saved.days==="object")db={days:saved.days,notifications:saved.notifications===true}}catch{storageOkay=false}
let selected=chinaTime().date,lastToday=selected,followToday=true,lastMinute=null;
let pendingTimelineTodo=null;
let editingTodo=null,removedTodo=null,editingSchedule=null,scheduleUndo=null,removedSubtask=null;
function scheduleFor(date){return baseForDate(builtinSchedule,db.days,templateConfig,date,chinaTime().date)}
function day(){return dailyState(scheduleFor(selected),db.days,selected)}
function tasksFor(date){return plannedTasks(scheduledBase(scheduleFor(date),db.days[date]||{}),db.days[date]?.todos,db.days[date]?.timelineOrder)}
function totalTasks(){return [...new Map([...tasksFor(selected),...day().todos].map(t=>[t.id,t])).values()]}
function refreshTodos(){lastMinute=null;renderDay(false);tick()}
function fillTimeChoices(id,value=""){
  const control=$(id),isEnd=id.endsWith("end");control.replaceChildren();
  const empty=document.createElement("option");empty.value="";empty.textContent="选择时间";control.append(empty);
  for(let minute=isEnd?30:0;minute<=(isEnd?1440:1410);minute+=30){const option=document.createElement("option");option.value=timeLabel(minute);option.textContent=option.value;control.append(option)}
  // Keep previously saved minute-level times until the user explicitly changes them.
  if(value&&![...control.options].some(o=>o.value===value)){const legacy=document.createElement("option");legacy.value=value;legacy.textContent=value+"（原记录）";legacy.disabled=true;control.append(legacy)}
  control.value=value;
}
function setTimePair(prefix,start,end){fillTimeChoices(prefix+"-start",start===null?"":timeLabel(start));fillTimeChoices(prefix+"-end",end===null?"":timeLabel(end))}
for(const prefix of ["todo","schedule-edit"]){setTimePair(prefix,null,null);$(prefix+"-start").onchange=()=>{const start=timeMinutes($(prefix+"-start").value),end=timeMinutes($(prefix+"-end").value);if(start!==null&&(end===null||end<=start))fillTimeChoices(prefix+"-end",timeLabel(start+30))}}
function resetTodoForm(){editingTodo=null;$("todo-form").reset();setTimePair("todo",null,null);$("todo-submit").textContent="添加待办";$("todo-cancel").hidden=true}
// Daily reading sessions have their own check; the paper's cumulative record is retained.
function mountDailyPaperCheck(host,paper,checked,onChange){
 const date=selected,wrap=document.createElement('div'),label=document.createElement('label'),check=document.createElement('input'),text=document.createElement('span');
 wrap.className='paper-progress-controls';check.type='checkbox';check.checked=checked;
 check.setAttribute('aria-label',date+' 阅读完成：'+paper.title);label.title=date+' 的阅读任务';text.textContent=checked?'已读':'未读';label.append(check,text);wrap.append(label);host.append(wrap);
 check.onchange=()=>{if(selected!==date)return;const read=check.checked;onChange(read);
  // Undoing today's session must not erase a paper read on an earlier day.
  if(read&&date===chinaTime().date&&!isPaperRead(paper.id))knowledgeApi('paper-read-status',{paperId:paper.id,read:true}).then(value=>{cacheManualReading(value);localStorage.setItem('paper-progress-updated',Date.now()+':'+crypto.randomUUID());window.dispatchEvent(new CustomEvent('paper-progress-change',{detail:value}));}).catch(()=>toast('当天完成状态已保留；论文已读状态同步失败，请稍后重试。'));
 };
 return wrap;
}
function setTaskDone(id,completed){const done=new Set(day().done);if(completed)done.add(id);else done.delete(id);updateDay({done:[...done]});refreshTodos();}
function openTodoPlan(todo){pendingTimelineTodo=todo.id;refreshTodos();$('schedule').scrollIntoView({behavior:'smooth',block:'start'});}
function changeTimeline(task,value){
 const state=day(),timelineOrder=prioritizeTask(state.timelineOrder,task.id);
 if(task.custom)updateDay({todos:state.todos.map(t=>t.id===task.id?{...t,...value}:t),timelineOrder});
 else updateDay({scheduleOverrides:{...state.scheduleOverrides,[task.id]:{title:task.title,detail:task.detail||'',...value}},timelineOrder});
 pendingTimelineTodo=null;refreshTodos();
}
function placeTimelineTodo(id,value){const state=day();if(!state.todos.some(t=>t.id===id))return;updateDay({todos:state.todos.map(t=>t.id===id?{...t,...value}:t),timelineOrder:prioritizeTask(state.timelineOrder,id)});pendingTimelineTodo=null;refreshTodos();}
function returnTimelineTask(task){const state=day(),next=returnScheduledTask(state,task,'todo-'+crypto.randomUUID());if(next===state)return;updateDay(next);pendingTimelineTodo=null;refreshTodos();}
function returnTimelineChild(rootId,id){const state=day(),next=returnSubtask(state,rootId,id,'todo-'+crypto.randomUUID());if(next===state)return;updateDay(next);pendingTimelineTodo=null;refreshTodos();}
function projectActions(task){const a=document.createElement("a");a.className="task-project-actions";a.href=task.kind==="learning"?"http://127.0.0.1:8870/learning?module="+encodeURIComponent(task.projectId)+"&deck="+encodeURIComponent(task.deckId):"http://127.0.0.1:8870/?project="+encodeURIComponent(task.projectId);a.target="_blank";a.rel="noopener";a.textContent=(task.kind==="learning"?"打开学习 PPT · ":"打开项目 · ")+task.projectName+" ↗";return a}
function nestTimelineTodo(rootId,todoId,parentSubtaskId=null){const state=day();if(![...schedule,...state.todos].some(t=>t.id===rootId))return;updateDay(nestTodo(state,rootId,todoId,'sub-'+crypto.randomUUID(),parentSubtaskId));pendingTimelineTodo=null;refreshTodos();}
function moveTimelineSubtask(fromRoot,id,toRoot,parentSubtaskId=null){const state=day(),next=moveSubtask(state,fromRoot,id,toRoot,parentSubtaskId);if(next===state)return;updateDay(next);refreshTodos();}
function renderSubtasks(task,{compact=false}={}){
 const area=document.createElement(compact?'div':'details');area.className='subtasks'+(compact?' subtask-tree-compact':'');
 const items=day().subtasks[task.id]||[],summary=document.createElement(compact?'div':'summary');
 summary.textContent=`子任务 ${items.filter(t=>t.done).length} / ${items.length}`;area.append(summary);if(!compact)area.open=items.length>0;
 const setItems=next=>{updateDay({subtasks:{...day().subtasks,[task.id]:next}});refreshTodos();};
 const dropOptions={onMove:moveTimelineSubtask,onTodo:nestTimelineTodo},slots=subtaskSlots({...task,start:task.sourceStart??task.start,end:task.sourceEnd??task.end},items);
 function appendItems(parentId,container){for(const item of items.filter(t=>(t.parentSubtaskId||null)===parentId)){
  const branch=document.createElement('div');branch.className='subtask-branch';
  const row=document.createElement('div');row.className='subtask-row';makeSubtaskDraggable(row,task.id,item,moveTimelineSubtask,returnTimelineChild);makeSubtaskDropTarget(row,task.id,item.id,dropOptions);
  const name=document.createElement(item.paper?'button':'span');name.className='subtask-name';if(item.paper){name.type='button';setPaperTitle(name,item.paper);name.onclick=()=>openReader(item.paper.id);}else name.textContent=item.title;name.classList.toggle('subtask-done',item.done);
  const grip=document.createElement('span');grip.className='subtask-grip';grip.textContent='⠿';grip.title='拖入其他子任务';
  const slotCell=document.createElement('div');slotCell.className='subtask-slot';
  if(compact){if(item.paper){mountDailyPaperCheck(slotCell,item.paper,item.done,done=>setItems(items.map(t=>t.id===item.id?{...t,done}:t)));}else{const check=document.createElement('input');check.type='checkbox';check.checked=item.done;check.setAttribute('aria-label','子任务完成：'+item.title);check.onchange=()=>{if(item.studyTask)markPaperTaskDone(item.studyTask.paperId,item.studyTask.taskId,check.checked);setItems(items.map(t=>t.id===item.id?{...t,done:check.checked}:t));};slotCell.append(check);}}
  const slot=slots.get(item.id);if(slot){row.dataset.subtaskStart=slot.start;row.dataset.subtaskEnd=slot.end;}const time=document.createElement('small');time.className='subtask-time';time.textContent=slot?`${timeLabel(slot.start)}–${timeLabel(slot.end)}`:'待安排';time.title='计划 '+(slot?.duration||item.durationMinutes||10)+' 分钟';time.classList.toggle('subtask-time-overflow',!!slot?.overflow);slotCell.append(time);if(slot?.overflow){const warning=document.createElement('small');warning.textContent='超出父任务';warning.className='subtask-time-overflow';slotCell.append(warning);}
  const content=document.createElement('div');content.className='subtask-content';const heading=document.createElement('div');heading.className='subtask-heading';heading.append(grip,name);if(item.paper){const count=document.createElement('span');count.className='paper-title-progress';mountPaperProgress(count,item.paper,{showRead:false,countLabel:'阅读清单'});heading.append(count);}content.append(heading);if(item.detail){const detail=document.createElement('p');detail.className='subtask-detail small muted';detail.textContent=item.detail;content.append(detail);}row.append(slotCell,content);if(compact){branch.style.minHeight=(70+Math.max(0,(slot?.duration||item.durationMinutes||10)-10)*2)+'px';makeSubtaskResizable(branch,slot?.duration||item.durationMinutes||10,minutes=>setItems(items.map(t=>t.id===item.id?{...t,durationMinutes:minutes,spentMinutes:minutes}:t)));}if(item.spentMinutes){const spent=document.createElement('small');spent.className='subtask-spent';spent.textContent='已记录用时 '+item.spentMinutes+' 分钟';slotCell.append(spent);}branch.append(row);
  if(!compact){
   const actions=document.createElement('div');actions.className='subtask-tools';
   if(item.paper)mountDailyPaperCheck(actions,item.paper,item.done,done=>setItems(items.map(t=>t.id===item.id?{...t,done}:t)));else{const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=item.done;check.setAttribute('aria-label','子任务完成：'+item.title);label.append(check);check.onchange=()=>{if(item.studyTask)markPaperTaskDone(item.studyTask.paperId,item.studyTask.taskId,check.checked);setItems(items.map(t=>t.id===item.id?{...t,done:check.checked}:t));};actions.append(label);}
   const edit=document.createElement('button'),remove=document.createElement('button');edit.type=remove.type='button';edit.textContent='编辑';remove.textContent='删除';edit.setAttribute('aria-label','编辑子任务：'+item.title);remove.setAttribute('aria-label','删除子任务：'+item.title);
   const form=document.createElement('form'),input=document.createElement('input'),save=document.createElement('button'),cancel=document.createElement('button');form.className='subtask-add';form.hidden=true;input.value=item.title;input.maxLength=160;input.required=true;input.setAttribute('aria-label','修改子任务：'+item.title);save.type='submit';save.textContent='保存';cancel.type='button';cancel.textContent='取消';form.append(input,save,cancel);edit.onclick=()=>{form.hidden=false;input.focus();};cancel.onclick=()=>form.hidden=true;form.onsubmit=e=>{e.preventDefault();if(input.value.trim())setItems(items.map(t=>t.id===item.id?{...t,title:input.value.trim()}:t));};
   remove.onclick=()=>{const ids=new Set(subtreeIds(items,item.id));removedSubtask={date:selected,taskId:task.id,items:items.filter(t=>ids.has(t.id))};setItems(items.filter(t=>!ids.has(t.id)));};actions.append(edit,remove);
   if(item.paper)mountQuizToggle(actions,item.paper.id,{quiet:true});
   {const restore=document.createElement('button');restore.type='button';restore.textContent='移回 Todo List';restore.onclick=()=>{returnTimelineChild(task.id,item.id);};actions.append(restore);}
   branch.append(actions,form);if(item.projectTask)branch.append(projectActions(item.projectTask));
  }
  const children=document.createElement('div');children.className='subtask-children';appendItems(item.id,children);if(children.children.length)branch.append(children);container.append(branch);
 }}
 const tree=document.createElement('div');tree.className='subtask-tree';appendItems(null,tree);area.append(tree);
 if(!compact){
  const form=document.createElement('form'),input=document.createElement('input'),add=document.createElement('button');form.className='subtask-add';input.type='text';input.maxLength=160;input.required=true;input.placeholder='添加子任务，默认 10 分钟';input.setAttribute('aria-label','新子任务：'+task.title);add.type='submit';add.textContent='添加';add.setAttribute('aria-label','添加子任务：'+task.title);form.append(input,add);form.onsubmit=e=>{e.preventDefault();if(input.value.trim())setItems([...items,{id:'sub-'+crypto.randomUUID(),title:input.value.trim(),done:false}]);};area.append(form);
  if(removedSubtask?.date===selected&&removedSubtask.taskId===task.id){area.open=true;const undo=document.createElement('button');undo.type='button';undo.textContent='撤销删除子任务';undo.onclick=()=>{const restored=removedSubtask.items;removedSubtask=null;setItems([...items,...restored]);};area.append(undo);}
 }
 return area;
}
function renderTodos(){
 $("todo-date-label").textContent=selected;$("todo-list").replaceChildren();
 for(const todo of day().todos){const row=document.createElement("div");row.className="todo-item"+(day().done.includes(todo.id)?" done":"");const label=document.createElement("label"),check=document.createElement("input"),body=document.createElement("span"),title=document.createElement("span"),time=document.createElement("small");check.type="checkbox";check.checked=day().done.includes(todo.id);check.setAttribute("aria-label","待办完成："+todo.title);if(todo.paper)setPaperTitle(title,todo.paper);else title.textContent=todo.title;time.hidden=todo.start===null;time.textContent=todo.start===null?"":`${timeLabel(todo.start)}–${timeLabel(todo.end)} · 已加入今日安排`;body.append(title);if(todo.paper){const count=document.createElement('span');count.className='paper-title-progress';mountPaperProgress(count,todo.paper,{showRead:false,countLabel:'阅读清单'});body.append(count);}body.append(time);label.append(...(todo.paper?[]:[check]),body);check.onchange=()=>{const done=new Set(day().done);if(check.checked)done.add(todo.id);else done.delete(todo.id);if(todo.studyTask)markPaperTaskDone(todo.studyTask.paperId,todo.studyTask.taskId,check.checked);updateDay({done:[...done]});refreshTodos()};const actions=document.createElement("div");actions.className="todo-item-actions";const edit=document.createElement("button"),remove=document.createElement("button");edit.type=remove.type="button";edit.textContent="编辑";remove.textContent="删除";edit.setAttribute("aria-label","编辑待办："+todo.title);remove.setAttribute("aria-label","删除待办："+todo.title);edit.onclick=()=>{editingTodo=todo.id;$("todo-title").value=todo.title;$("todo-detail").value=todo.detail||"";setTimePair("todo",todo.start,todo.end);$("todo-submit").textContent="保存修改";$("todo-cancel").hidden=false;$("todo-title").focus()};remove.onclick=()=>{removedTodo={date:selected,todo,subtasks:day().subtasks[todo.id]||[],done:day().done.includes(todo.id)};updateDay({todos:day().todos.filter(t=>t.id!==todo.id),done:day().done.filter(id=>id!==todo.id)});if(editingTodo===todo.id)resetTodoForm();refreshTodos();$("todo-status").textContent="已删除待办，可撤销。"};const move=document.createElement('button');move.type='button';move.textContent=todo.start===null?'拖入时间轴':'移除今日安排';move.onclick=()=>{if(todo.start===null){openTodoPlan(todo);}else{updateDay({todos:day().todos.map(t=>t.id===todo.id?{...t,start:null,end:null}:t)});refreshTodos();}};if(todo.paper)mountDailyPaperCheck(actions,todo.paper,day().done.includes(todo.id),done=>setTaskDone(todo.id,done));actions.append(edit,...(todo.start===null?[]:[move]),remove);if(todo.paper)mountQuizToggle(actions,todo.paper.id,{quiet:true});row.append(label,actions);if(todo.detail&&!todo.studyTask){const detail=document.createElement("p");detail.className="small muted";detail.textContent=todo.detail;row.append(detail);}if(todo.studyTask){const b=document.createElement("button");b.className="button";b.textContent="打开论文任务与回答";b.onclick=()=>openReader(todo.studyTask.paperId,"tasks");row.append(b);const detail=document.createElement("p");detail.className="small muted";detail.textContent=todo.detail;row.append(detail)}if(todo.projectTask)row.append(projectActions(todo.projectTask));row.append(renderSubtasks(todo));makeTodoDraggable(row,todo,{onNest:nestTimelineTodo,onDrop:placeTimelineTodo});$("todo-list").append(row)}
 if(!day().todos.length){const empty=document.createElement("p");empty.className="small muted";empty.textContent="这一天还没有额外待办。";$("todo-list").append(empty)}
 $("todo-undo").hidden=!removedTodo||removedTodo.date!==selected;
}
function toast(message){$("toast").textContent=message;$("toast").hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$("toast").hidden=true,4500)}
function save(){
  try{localStorage.setItem(key,JSON.stringify(db));storageOkay=true;$("save-status").textContent="已保存到当前浏览器"}catch{storageOkay=false;$("save-status").textContent="保存失败，请导出备份，避免丢失记录";toast("浏览器无法保存，请导出备份")}
}
function updateDay(updates){db.days[selected]={...day(),baseSchedule:structuredClone(scheduleFor(selected)),...updates};save()}
function renderProgress(){
  const {done:n,total}=dailyCompletion(schedule,day());
  renderWeeklyCats($("weekly-task-cats"),schedule,{...db.days,...(selected===chinaTime().date||db.days[selected]?{[selected]:day()}:{})},selected,chinaTime().date,value=>{selectDate(value);$("schedule-heading").scrollIntoView({behavior:"smooth",block:"start"});});
  $("progress-count").textContent=`${n} / ${total}`;
  $("progress-fill").style.width=`${total?n/total*100:0}%`;
  document.querySelector(".progress-track").setAttribute("aria-valuenow",n);document.querySelector(".progress-track").setAttribute("aria-valuemax",total);
}
function durationLabel(minutes){return [Math.floor(minutes/60)?`${Math.floor(minutes/60)} 小时`:"",minutes%60?`${minutes%60} 分钟`:""].filter(Boolean).join(" ")}
function renderDay(announceDate=true){
  refreshDailyPaperStatistics(selected);
  schedule=scheduleFor(selected);
  if(selected===chinaTime().date&&!Array.isArray(db.days[selected]?.baseSchedule)){db.days[selected]={...db.days[selected],baseSchedule:structuredClone(schedule)};save();}
  $("date").value=selected;
  $("schedule-heading").textContent=selected===chinaTime().date?"今日安排":"每日安排";
  $("day-label").textContent=new Intl.DateTimeFormat("zh-CN",{year:"numeric",month:"long",day:"numeric",weekday:"long",timeZone:"Asia/Shanghai"}).format(new Date(`${selected}T12:00:00+08:00`));
  $("schedule").replaceChildren();
  const state=day();
  $('completion-reset').disabled=!state.done.length&&!Object.values(state.subtasks).flat().some(item=>item.done);
  $('completion-reset').title='重置 '+selected+' 的父任务和子任务勾选';
  $('completion-reset-notice').hidden=!state.completionResetUndo;
  $('template-reset-notice').hidden=!state.templateResetUndo;
  $('template-apply-notice').hidden=!state.templateApplyUndo;
  $('schedule-settings-date').textContent=selected+' · 仅作用于当天';
  const planned=tasksFor(selected);$("schedule-window").textContent="06:00 — 23:00";
  for(const task of planned){
    const row=document.createElement("div");row.className="task";row.dataset.id=task.id;row.dataset.start=task.start;row.dataset.end=task.end;
    row.innerHTML=`<div class="task-time">${timeLabel(task.start)}–${timeLabel(task.end)}<div class="task-duration">${durationLabel(task.end-task.start)}</div></div><div><div class="task-title"><i class="task-marker ${task.type}"></i><span class="task-name"></span><span class="task-badge" hidden>进行中</span></div><p class="task-details"></p></div><input type="checkbox">`;
    if(task.paper)setPaperTitle(row.querySelector('.task-name'),task.paper);else row.querySelector('.task-name').textContent=task.title;
    row.querySelector(".task-details").textContent=task.detail;
    const check=row.querySelector("input");check.checked=state.done.includes(task.id);check.setAttribute("aria-label",`完成：${task.title}`);
    row.classList.toggle("done",check.checked);
    check.addEventListener("change",()=>{const done=new Set(day().done);if(check.checked)done.add(task.id);else done.delete(task.id);if(task.studyTask)markPaperTaskDone(task.studyTask.paperId,task.studyTask.taskId,check.checked);updateDay({done:[...done]});refreshTodos()});
    const actions=document.createElement("div");actions.className="schedule-item-actions";const edit=document.createElement("button"),remove=document.createElement("button");edit.type=remove.type="button";edit.textContent="编辑";remove.textContent="删除";edit.setAttribute("aria-label","编辑安排："+task.title);remove.textContent=task.custom?"移除今日安排":"删除";remove.setAttribute("aria-label",(task.custom?"移除今日安排：":"删除安排：")+task.title);edit.onclick=()=>openScheduleEditor(task);remove.onclick=()=>deleteScheduleTask(task);if(task.paper)mountDailyPaperCheck(actions,task.paper,state.done.includes(task.id),done=>setTaskDone(task.id,done));actions.append(edit,remove);if(task.custom){const del=document.createElement('button');del.type='button';del.textContent='删除';del.onclick=()=>{updateDay({todos:day().todos.filter(t=>t.id!==task.id),done:day().done.filter(id=>id!==task.id)});refreshTodos();};actions.append(del);}if(task.paper)mountQuizToggle(actions,task.paper.id,{quiet:true});row.children[1].append(actions);if(task.paper){const count=document.createElement('div');count.className='timeline-paper-count';mountPaperProgress(count,task.paper,{showRead:false,countLabel:'阅读清单'});row.querySelector('.task-title').append(count);}if(task.studyTask){const b=document.createElement("button");b.className="button";b.textContent="打开论文任务与回答";b.onclick=()=>openReader(task.studyTask.paperId,"tasks");row.children[1].append(b)}if(task.projectTask)row.children[1].append(projectActions(task.projectTask));row.children[1].append(renderSubtasks(task));
    if(task.paper){check.remove();const corner=document.createElement('div');corner.className='timeline-parent-paper-check';mountDailyPaperCheck(corner,task.paper,state.done.includes(task.id),done=>setTaskDone(task.id,done));row.append(corner);}$("schedule").append(row);
  }
  if(!planned.length){const empty=document.createElement("p");empty.className="small muted";empty.textContent="这一天暂无定时安排，可从 Todo List 添加。";$("schedule").append(empty)}
  mountDailyTimeline($('schedule'),planned,{onChange:changeTimeline,onDrop:placeTimelineTodo,onNest:nestTimelineTodo,onMoveSubtask:moveTimelineSubtask,onReturn:returnTimelineTask,renderChildren:task=>(day().subtasks[task.id]||[]).length?renderSubtasks(task,{compact:true}):null,pendingTodo:state.todos.find(t=>t.id===pendingTimelineTodo),onCancel:()=>{pendingTimelineTodo=null;refreshTodos();}});
  $("schedule-undo").hidden=!scheduleUndo||scheduleUndo.date!==selected;$("schedule-reset").disabled=!state.hiddenSchedule.length&&!Object.keys(state.scheduleOverrides).length&&!(state.timelineOrder||[]).length;
  $("notes").value=state.notes??"";
  $("save-status").textContent=storageOkay?"记录保存在当前浏览器":"浏览器存储不可用，请导出备份";
  renderTodos();renderProgress();highlightCurrent();
  if(announceDate)window.dispatchEvent(new CustomEvent("schedule-date-change",{detail:selected}));
}
function selectDate(value){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||Number.isNaN(Date.parse(value)))return;
  pendingTimelineTodo=null;selected=value;followToday=selected===chinaTime().date;resetTodoForm();renderDay();
}
function highlightCurrent(){
  const ct=chinaTime(),current=currentTask(tasksFor(ct.date),ct.minute);
  for(const row of document.querySelectorAll(".task")){
    const active=selected===ct.date&&current?.id===row.dataset.id&&ct.minute>=Number(row.dataset.start)&&ct.minute<Number(row.dataset.end);
    row.classList.toggle("active",active);row.querySelector(".task-badge").hidden=!active;
  }
}
function dailyEditingInProgress(){
 if(document.querySelector('dialog[open],.timeline-dragging,.timeline-todo-dragging,.subtask-drag-preview,.subtask-resizing'))return true;
 if(editingTodo||$('todo-title').value.trim()||$('todo-detail').value.trim())return true;
 if(document.activeElement===$('notes'))return true;
 return [...document.querySelectorAll('.subtasks form:not([hidden])')].some(form=>form.querySelector('input[aria-label^="修改子任务"]')||[...form.querySelectorAll('input')].some(input=>input.value.trim()));
}
function syncDailyDate(today){
 const next=advanceDailyDate({selected,lastToday,followToday},today,dailyEditingInProgress());
 const hint=$('daily-date-state');if(hint){hint.hidden=selected===today&&!next.pending;const text=next.pending?'新的一天已开始，完成当前编辑后自动切换到 '+today:selected!==today?'正在查看 '+selected+'；北京时间今天是 '+today:'';if(hint.textContent!==text)hint.textContent=text;}
 $('today').title=selected===today?'查看今天的日程':'回到今天 '+today;
 if(!next.changed)return;selected=next.selected;lastToday=next.lastToday;followToday=next.followToday;pendingTimelineTodo=null;lastMinute=null;resetTodoForm();renderDay();if(hint)hint.hidden=true;
}
function tick(){
  const ct=chinaTime();$("clock").textContent=ct.clock;
  syncDailyDate(ct.date);
  if(lastMinute!==`${ct.date}:${ct.minute}`){
    lastMinute=`${ct.date}:${ct.minute}`;
    const todayTasks=tasksFor(ct.date),task=currentTask(todayTasks,ct.minute),next=[...todayTasks,...reminders.filter(t=>t.id==="sleep")].sort((a,b)=>a.start-b.start).find(t=>t.start>ct.minute)||schedule[0];
    const gap=task?null:unscheduledPeriod(todayTasks,ct.minute);$("current-title").textContent=task?.title??gap.title;
    $("current-detail").textContent=task?.detail??gap.detail;
    $("current-time").textContent=task?`${timeLabel(task.start)} — ${timeLabel(task.end)}`:`${gap.timePrefix}${timeLabel(gap.start)}${gap.timeMiddle}${timeLabel(gap.end)}`;
    $("remaining").textContent=task?`本时段还剩 ${task.end-ct.minute} 分钟`:"";
    $("next-title").textContent=next.title;
    $("next-time").textContent=`${next.start<=ct.minute?"明天 ":""}${timeLabel(next.start)} — ${timeLabel(next.end)}`;
    highlightCurrent();
    if(db.notifications&&"Notification" in window&&Notification.permission==="granted"){
      for(const reminder of [...reminders.filter(t=>t.id==="sleep"),...tasksFor(ct.date).filter(t=>t.alert&&(!t.custom||!db.days[ct.date]?.done?.includes(t.id)))].filter(s=>s.start===ct.minute)){
        const sentKey=`daily-notified:${ct.date}:${reminder.id}:${reminder.start}`;
        let sent=false;try{sent=localStorage.getItem(sentKey)==="1"}catch{}
        if(!sent){try{new Notification(reminder.title,{body:reminder.detail,tag:sentKey});localStorage.setItem(sentKey,"1")}catch{toast(`现在：${reminder.title}`)}}
      }
    }
  }
}
function openScheduleEditor(task){editingSchedule={id:task.id,date:selected,custom:!!task.custom};$("schedule-edit-title").value=task.title;setTimePair("schedule-edit",task.sourceStart??task.start,task.sourceEnd??task.end);$("schedule-edit-detail").value=task.custom?(day().todos.find(t=>t.id===task.id)?.detail||""):task.detail||"";$("schedule-edit-status").textContent="修改仅保存到 "+selected+"。分段任务编辑的是整项原始安排；新增任务占用的时间会自动分离。";$("schedule-edit-dialog").showModal()}
function deleteScheduleTask(task){const done=day().done.includes(task.id);if(task.custom){const todo=day().todos.find(t=>t.id===task.id);scheduleUndo={date:selected,kind:"custom",todo,subtasks:day().subtasks[todo.id]||[],done};removedTodo={date:selected,todo,subtasks:day().subtasks[todo.id]||[],done};updateDay({todos:day().todos.map(t=>t.id===task.id?{...t,start:null,end:null}:t)});if(editingTodo===task.id)resetTodoForm()}else{scheduleUndo={date:selected,kind:"base",id:task.id,done};updateDay({hiddenSchedule:[...day().hiddenSchedule,task.id],done:day().done.filter(id=>id!==task.id)})}refreshTodos();$("schedule-status").textContent="已从当天安排移除“"+task.title+"”，可撤销。"}
$("schedule-undo").onclick=()=>{if(!scheduleUndo||scheduleUndo.date!==selected)return;const u=scheduleUndo,done=new Set(day().done);if(u.done)done.add(u.kind==="base"?u.id:u.todo.id);if(u.kind==="base")updateDay({hiddenSchedule:day().hiddenSchedule.filter(id=>id!==u.id),done:[...done]});else{updateDay({todos:[...day().todos.filter(t=>t.id!==u.todo.id),u.todo],subtasks:{...day().subtasks,[u.todo.id]:u.subtasks||[]},done:[...done]});if(removedTodo?.todo.id===u.todo.id)removedTodo=null}scheduleUndo=null;refreshTodos();$("schedule-status").textContent="已恢复安排。"};
$('manage-default-schedule').onclick=()=>{ $('schedule-settings').open=false;openTemplateSettings(templateConfig,config=>{const frozen=freezeExistingDays(builtinSchedule,db.days,templateConfig,chinaTime().date);localStorage.setItem(TEMPLATE_KEY,JSON.stringify(config));db.days=frozen;save();templateConfig=config;refreshTodos();toast('默认日程已保存；已有日期保持原样，新日期自动选用对应模板。');},(config,id)=>{const today=chinaTime().date,previous=scheduleFor(today),state=dailyState(previous,db.days,today),template=config.templates.find(t=>t.id===id);const frozen=freezeExistingDays(builtinSchedule,db.days,templateConfig,today);localStorage.setItem(TEMPLATE_KEY,JSON.stringify(config));db.days=frozen;db.days[today]=applyTemplateToDay(state,previous,template);templateConfig=config;selected=today;followToday=true;save();refreshTodos();toast('已将“'+template.name+'”应用到今天，可在日程设置中撤销。');});};
$('template-apply-undo').onclick=()=>{db.days[selected]=undoTemplateApplication(day());save();refreshTodos();toast('已撤销模板应用。');};
window.addEventListener('storage',e=>{if(e.key===TEMPLATE_KEY&&e.newValue){try{templateConfig=validateTemplates(JSON.parse(e.newValue));refreshTodos();}catch{}}});
$("schedule-reset").onclick=()=>{db.days[selected]=restoreDailyTemplate(day());save();scheduleUndo=null;$('schedule-settings').open=false;refreshTodos();};
$('template-reset-undo').onclick=()=>{db.days[selected]=undoDailyTemplateRestore(day());save();refreshTodos();};
document.addEventListener('click',e=>{if(!e.target.closest('#schedule-settings'))$('schedule-settings').open=false;});
document.addEventListener('keydown',e=>{if(e.key==='Escape')$('schedule-settings').open=false;});
$('completion-reset').onclick=()=>{db.days[selected]=resetDailyCompletion(day());save();$('schedule-settings').open=false;refreshTodos();$('schedule-status').textContent='已重置 '+selected+' 的任务勾选，可撤销。';};
$('completion-reset-undo').onclick=()=>{db.days[selected]=undoDailyCompletionReset(day());save();refreshTodos();$('schedule-status').textContent='已恢复 '+selected+' 重置前的勾选。';};
$("schedule-edit-cancel").onclick=()=>$("schedule-edit-dialog").close();
$("schedule-edit-form").onsubmit=e=>{e.preventDefault();if(!editingSchedule||editingSchedule.date!==selected)return;const title=$("schedule-edit-title").value.trim(),start=timeMinutes($("schedule-edit-start").value),end=timeMinutes($("schedule-edit-end").value),detail=$("schedule-edit-detail").value;if(!title||start===null||end===null||end<=start){$("schedule-edit-status").textContent="请填写名称和有效起止时间，结束时间须晚于开始时间。";return}const values={title,start,end,detail};if(editingSchedule.custom){updateDay({todos:[...day().todos.filter(t=>t.id!==editingSchedule.id),{...day().todos.find(t=>t.id===editingSchedule.id),...values}]})}else updateDay({scheduleOverrides:{...day().scheduleOverrides,[editingSchedule.id]:values}});$("schedule-edit-dialog").close();editingSchedule=null;refreshTodos();$("schedule-status").textContent="已保存当天修改，重叠时间已自动分离。"};
$("todo-form").onsubmit=e=>{e.preventDefault();const title=$("todo-title").value.trim(),startValue=$("todo-start").value,endValue=$("todo-end").value,start=timeMinutes(startValue),end=timeMinutes(endValue);if(!title)return;if((startValue||endValue)&&(start===null||end===null||end<=start)){$("todo-status").textContent="请填写有效的起止时间，结束时间须晚于开始时间。";return}const todo={...day().todos.find(t=>t.id===editingTodo),id:editingTodo||"todo-"+crypto.randomUUID(),title,start,end,detail:$("todo-detail").value};const todos=day().todos.filter(t=>t.id!==todo.id);todos.push(todo);updateDay({todos});resetTodoForm();refreshTodos();$("todo-status").textContent=start===null?"已加入待办清单，之后可编辑时间。":"已插入今日安排，原任务在开始处暂停，结束后继续；其他时段保持不变。"};
$("todo-cancel").onclick=resetTodoForm;
$("todo-undo").onclick=()=>{if(!removedTodo||removedTodo.date!==selected)return;const done=new Set(day().done);if(removedTodo.done)done.add(removedTodo.todo.id);updateDay({todos:[...day().todos.filter(t=>t.id!==removedTodo.todo.id),removedTodo.todo],subtasks:{...day().subtasks,[removedTodo.todo.id]:removedTodo.subtasks||[]},done:[...done]});if(scheduleUndo?.kind==="custom"&&scheduleUndo.todo.id===removedTodo.todo.id)scheduleUndo=null;removedTodo=null;refreshTodos();$("todo-status").textContent="已恢复待办。"};
$("date").addEventListener("change",e=>selectDate(e.target.value));
$('schedule-calendar-open').onclick=()=>openScheduleCalendar({selected,today:chinaTime().date,days:db.days,base:builtinSchedule,onSelect:value=>{selectDate(value);$('schedule-heading').scrollIntoView({behavior:'smooth',block:'start'});}});
$("prev-day").onclick=()=>selectDate(shiftDate(selected,-1));
$("next-day").onclick=()=>selectDate(shiftDate(selected,1));
$("today").onclick=()=>selectDate(chinaTime().date);
$("notes").addEventListener("input",()=>updateDay({notes:$("notes").value}));
$("reminder-open").onclick=()=>{$("reminder-dialog").showModal();notificationStatus()};
$("reminder-close").onclick=()=>$("reminder-dialog").close();
function notificationStatus(){
  const supported="Notification" in window;
  const permitted=supported&&Notification.permission==="granted";
  $("enable-notifications").textContent=db.notifications&&permitted?"关闭浏览器提醒":"开启浏览器提醒";
  $("notification-status").textContent=!supported?"此浏览器不支持系统通知，可使用日历提醒。":Notification.permission==="denied"?"通知权限已被阻止。可在浏览器的网站设置中调整。":db.notifications&&permitted?"已开启：保持页面运行，到点显示通知。":"尚未开启浏览器提醒。";
}
$("enable-notifications").onclick=async()=>{
  if(!("Notification" in window)){notificationStatus();return}
  if(db.notifications&&Notification.permission==="granted"){db.notifications=false;save();notificationStatus();return}
  try{const permission=await Notification.requestPermission();db.notifications=permission==="granted";save();notificationStatus();if(db.notifications)toast("浏览器提醒已开启")}catch{toast("无法启用通知，请使用日历提醒")}
};
function download(content,name,type){
  const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$("calendar").onclick=()=>download(calendarText(chinaTime().date),"每日努力.ics","text/calendar;charset=utf-8");
$("export").onclick=()=>download(JSON.stringify({version:1,exportedAt:new Date().toISOString(),days:db.days},null,2),`每日记录-${chinaTime().date}.json`,"application/json");
$("import").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
    if(file.size>5_000_000)throw Error("文件过大");
    const data=JSON.parse(await file.text());
    if(data.version!==1||!data.days||Array.isArray(data.days)||typeof data.days!=="object")throw Error("格式不正确");
    const cleaned={};
    for(const [date,value] of Object.entries(data.days)){
      if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||Number.isNaN(Date.parse(date))||!value||!Array.isArray(value.done)||typeof value.notes!=="string")throw Error("记录格式不正确");
      const importBase=Array.isArray(value.baseSchedule)?cleanTemplateTasks(value.baseSchedule):builtinSchedule;const todos=cleanTodos(value.todos);cleaned[date]={baseSchedule:importBase,...(value.nestedTodoArchive&&typeof value.nestedTodoArchive==='object'?{nestedTodoArchive:value.nestedTodoArchive}:{}),...(value.catalogTodoArchive&&typeof value.catalogTodoArchive==='object'?{catalogTodoArchive:value.catalogTodoArchive}:{}),timelineOrder:Array.isArray(value.timelineOrder)?value.timelineOrder.filter(i=>typeof i==='string'):[],scheduleOverrides:cleanScheduleOverrides(importBase,value.scheduleOverrides),hiddenSchedule:cleanHiddenSchedule(importBase,value.hiddenSchedule),done:[...new Set(value.done.filter(id=>importBase.some(t=>t.id===id)||todos.some(t=>t.id===id)))],notes:value.notes,todos,subtasks:cleanSubtasks(importBase,todos,value.subtasks)};
    }
    const overlap=Object.keys(cleaned).some(d=>db.days[d]);
    if(overlap&&!confirm("备份中有与当前记录相同的日期。导入会替换这些日期的打卡和笔记，是否继续？"))return;
    db.days={...db.days,...cleaned};save();renderDay();toast(`已导入 ${Object.keys(cleaned).length} 天记录`);
  }catch{toast("导入失败，请选择本网页导出的 JSON 备份文件")}finally{e.target.value=""}
});
window.addEventListener("storage",e=>{if(e.key===key){try{const updated=JSON.parse(e.newValue);if(updated?.days){db=updated;renderDay();notificationStatus()}}catch{}}});
document.addEventListener("visibilitychange",()=>{if(!document.hidden)tick()});
window.addEventListener('focus',tick);window.addEventListener('pageshow',tick);
window.addEventListener('message',e=>{if(e.origin==='http://127.0.0.1:8869'&&e.source===window.parent&&e.data?.type==='research-daily-activate')tick();});
renderDay();tick();setInterval(tick,1000);

let paperTaskDialog=null,pendingPaperTask=null;
window.addEventListener("paper-add-to-task",e=>{
  const paper=cleanPaper(e.detail);if(!paper)return;
  pendingPaperTask={paper,date:selected};
  if(!paperTaskDialog){
    paperTaskDialog=document.createElement("dialog");paperTaskDialog.id="paper-task-dialog";
    paperTaskDialog.innerHTML=`<div class="dialog-heading"><h2>把论文加入任务</h2><button type="button" class="icon-button" aria-label="关闭加入任务">×</button></div><p id="paper-task-title" class="small"></p><p id="paper-task-date" class="small muted"></p><form id="paper-task-form"><label class="field-label" for="paper-task-target">放到哪里？</label><select id="paper-task-target"></select><p class="small muted">加入已有任务会成为不计时的子任务。单独建为待办后，可在待办清单中编辑整点／半点时间。</p><p id="paper-task-status" class="small muted" role="status"></p><button class="button primary" type="submit">确认加入</button></form>`;
    document.body.append(paperTaskDialog);paperTaskDialog.querySelector('[aria-label="关闭加入任务"]').onclick=()=>paperTaskDialog.close();
    $("paper-task-form").onsubmit=event=>{
      event.preventDefault();if(!pendingPaperTask||pendingPaperTask.date!==selected)return;
      const {paper}=pendingPaperTask,target=$("paper-task-target").value,state=day();let destination;
      if(target==="new"){
        const existing=state.todos.find(t=>t.paper?.id===paper.id);
        if(existing){$("paper-task-status").textContent="这篇论文已经是当天的待办，无需重复添加。";return}
        updateDay({todos:[...state.todos,{id:"todo-"+crypto.randomUUID(),title:paper.title.slice(0,160),start:null,end:null,detail:"论文阅读",paper}]});destination="Todo List · 待办清单";
      }else{
        const parent=[...scheduledBase(schedule,state),...state.todos].find(t=>t.id===target);if(!parent){$("paper-task-status").textContent="所属任务已发生变化，请重新选择。";return}
        const children=state.subtasks[target]||[];
        if(children.some(t=>t.paper?.id===paper.id)){$("paper-task-status").textContent="这篇论文已在该任务下面，无需重复添加。";return}
        updateDay({subtasks:{...state.subtasks,[target]:[...children,{id:"sub-"+crypto.randomUUID(),title:paper.title.slice(0,160),done:false,paper}]}});destination=parent.title;
      }
      refreshTodos();paperTaskDialog.close();toast("已加入「"+destination+"」，可在上方任务中查看。");
    };
  }
  setPaperTitle($('paper-task-title'),paper);$("paper-task-date").textContent="保存日期："+selected;$("paper-task-status").textContent="";
  const select=$("paper-task-target");select.replaceChildren();
  const state=day(),parents=[...scheduledBase(schedule,state),...state.todos];
  for(const task of parents){const option=document.createElement("option");option.value=task.id;option.textContent=task.title+(task.start===null?"":` · ${timeLabel(task.start)}–${timeLabel(task.end)}`);select.append(option)}
  const standalone=document.createElement("option");standalone.value="new";standalone.textContent="＋ 单独建为待办（之后可安排时间）";select.append(standalone);
  select.value=parents.some(t=>t.id==="papers")?"papers":"new";paperTaskDialog.showModal();
});

async function openLibraryPaperTask(id){
  if(typeof id!=="string"||!(/^[a-zA-Z0-9._-]{1,200}$/).test(id))return;
  try{const response=await fetch("/api/reader?id="+encodeURIComponent(id),{cache:"no-store"});if(!response.ok)throw Error();const paper=await response.json();window.dispatchEvent(new CustomEvent("paper-add-to-task",{detail:{id:paper.id,title:paper.title,url:paper.pdf}}))}catch{toast("论文暂时无法读取，请返回论文页面重试。")}
}
window.addEventListener("message",e=>{if(e.origin==="http://127.0.0.1:8869"&&e.source===window.parent&&e.data?.type==="library-paper-task")openLibraryPaperTask(e.data.paperId)});
window.addEventListener("message",e=>{if(e.origin==="http://127.0.0.1:8869"&&e.source===window.parent&&e.data?.type==="arxiv-paper-task"){selected=chinaTime().date;followToday=true;renderDay();openLibraryPaperTask(e.data.paperId)}});
const incomingParams=new URLSearchParams(location.search);if(incomingParams.get("paperToday")==="1"){selected=chinaTime().date;followToday=true;renderDay()}
const incomingPaper=incomingParams.get("addPaper");if(incomingPaper){const cleanedUrl=new URL(location.href);cleanedUrl.searchParams.delete("addPaper");cleanedUrl.searchParams.delete("paperToday");history.replaceState(null,"",cleanedUrl);openLibraryPaperTask(incomingPaper)}

window.addEventListener("paper-reading-status-change",renderReadingStats);
window.addEventListener("storage",e=>{if(e.key===READING_STATE_KEY||e.key===READING_HISTORY_KEY)renderReadingStats()});
renderReadingStats();refreshDailyPaperStatistics(selected);setInterval(()=>refreshDailyPaperStatistics(selected),15000);
window.addEventListener("paper-knowledge-change",()=>refreshDailyPaperStatistics(selected));
window.addEventListener("storage",e=>{if(e.key==="paper-knowledge-updated")refreshDailyPaperStatistics(selected)});

let projectTaskDialog=null,pendingProjectTask=null;
async function openProjectTask(taskId){
 if(typeof taskId!=="string"||!(/^[a-zA-Z0-9-]{1,80}$/).test(taskId))return;
 try{const response=await fetch("http://127.0.0.1:8870/api/project-task?id="+encodeURIComponent(taskId),{cache:"no-store"});if(!response.ok)throw Error();pendingProjectTask=await response.json();
 if(!projectTaskDialog){projectTaskDialog=document.createElement("dialog");projectTaskDialog.id="project-task-dialog";projectTaskDialog.innerHTML=`<div class="dialog-heading"><h2>项目任务加入今日任务</h2><button id="project-task-close" type="button" class="icon-button" aria-label="关闭项目任务安排">×</button></div><p id="project-task-name" class="small"></p><form id="project-task-form"><label class="field-label" for="project-task-date">安排日期</label><input id="project-task-date" type="date" required><div class="todo-time-fields"><div><label class="field-label" for="project-task-start">开始时间（选填）</label><select id="project-task-start"></select></div><div><label class="field-label" for="project-task-end">结束时间（选填）</label><select id="project-task-end"></select></div></div><p class="small muted">设置时间后插入当天安排；留空则加入待办清单。</p><p id="project-task-status" class="small muted" role="status"></p><button class="button primary" type="submit">确认安排项目任务</button></form>`;document.body.append(projectTaskDialog);$("project-task-close").onclick=()=>projectTaskDialog.close();$("project-task-start").onchange=()=>{const start=timeMinutes($("project-task-start").value),end=timeMinutes($("project-task-end").value);if(start!==null&&(end===null||end<=start))fillTimeChoices("project-task-end",timeLabel(start+30))};
 $("project-task-form").onsubmit=e=>{e.preventDefault();if(!pendingProjectTask)return;const date=$("project-task-date").value,sv=$("project-task-start").value,ev=$("project-task-end").value,start=timeMinutes(sv),end=timeMinutes(ev);if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||Number.isNaN(Date.parse(date))||((sv||ev)&&(start===null||end===null||end<=start))){$("project-task-status").textContent="请选择有效的日期与起止时间。";return}selectDate(date);const {project,task}=pendingProjectTask;if(day().todos.some(t=>t.projectTask?.taskId===task.id)){$("project-task-status").textContent="这个任务已经加入当天，可在待办清单编辑时间。";return}updateDay({todos:[...day().todos,{id:"todo-"+crypto.randomUUID(),title:(project.name+" · "+task.title).slice(0,160),detail:task.detail||"项目基础任务",start,end,projectTask:{projectId:project.id,projectName:project.name,taskId:task.id,...(project.kind==="learning"?{kind:"learning",deckId:project.deckId}:{})}}]});refreshTodos();projectTaskDialog.close();toast("已加入 "+date+" 的"+(start===null?"待办清单":"安排"))};
 }
 projectTaskDialog.querySelector("h2").textContent=pendingProjectTask.project.kind==="learning"?"PPT 学习任务加入今日任务":"项目任务加入今日任务";$("project-task-form").querySelector("[type=submit]").textContent=pendingProjectTask.project.kind==="learning"?"确认安排学习任务":"确认安排项目任务";$("project-task-name").textContent=pendingProjectTask.project.name+" · "+pendingProjectTask.task.title;$("project-task-date").value=selected;setTimePair("project-task",null,null);$("project-task-status").textContent="";projectTaskDialog.showModal();
 }catch{toast("项目实验本暂时无法连接，请先启动本地项目网站。")}
}
window.addEventListener("message",e=>{if(e.origin==="http://127.0.0.1:8869"&&e.source===window.parent&&e.data?.type==="project-task-request")openProjectTask(e.data.taskId)});
const incomingProjectTask=new URLSearchParams(location.search).get("projectTask");if(incomingProjectTask){const cleanedUrl=new URL(location.href);cleanedUrl.searchParams.delete("projectTask");history.replaceState(null,"",cleanedUrl);openProjectTask(incomingProjectTask)}

window.addEventListener('research-practice-add',e=>{
 const task=e.detail?.task,date=e.detail?.date;if(!task||typeof task.id!=='string'||!/^research-\d{4}-\d{2}-\d{2}-[1-3]$/.test(task.id)||typeof task.title!=='string'||date!==selected)return;
 const id='todo-'+task.id;if(day().todos.some(t=>t.id===id)){if(!e.detail.quiet)toast('该科研练习已经在当天待办中。');return}
 const detail=['科研练习 · '+task.method,...(Array.isArray(task.steps)?task.steps:[]),'成果：'+(task.output||'')].join('\n');
 updateDay({todos:[...day().todos,{id,title:('科研练习 · '+task.title).slice(0,160),start:null,end:null,detail:detail.slice(0,2000)}]});refreshTodos();if(!e.detail.quiet)toast('已加入待办。点击编辑选择整点／半点，即可放入今日安排；成果在科研练习卡中记录。');
});

async function addStudyTask(paperId,taskId){
 if(typeof paperId!=='string'||!/^[a-zA-Z0-9._-]{1,200}$/.test(paperId)||typeof taskId!=='string'||!/^[a-z-]{1,60}$/.test(taskId))return;
 try{const response=await fetch('/api/study/task?paperId='+encodeURIComponent(paperId)+'&taskId='+encodeURIComponent(taskId)),task=await response.json();if(!response.ok)throw Error(task.error);selected=chinaTime().date;followToday=true;renderDay();
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(paperId+':'+taskId)),id='todo-study-'+Array.from(new Uint8Array(digest)).slice(0,16).map(n=>n.toString(16).padStart(2,'0')).join('');
 if(day().todos.some(t=>t.id===id)){toast('这项论文任务已经在今日待办中。');return}
 updateDay({todos:[...day().todos,{id,title:task.title,start:null,end:null,detail:task.detail.slice(0,2000),studyTask:{paperId,taskId}}]});refreshTodos();toast('已加入今日待办。编辑时间即可插入今日安排；全部阅读任务完成后才自动计为整篇已读。');
 }catch(e){toast('添加任务失败：'+e.message)}
}
async function addPracticeTask(taskId,date){
 try{const r=await fetch('/api/research-practice?date='+encodeURIComponent(date)),plan=await r.json();if(!r.ok)throw Error(plan.error);const task=plan.tasks.find(t=>t.id===taskId);if(!task)throw Error('练习不存在');selected=date;followToday=date===chinaTime().date;renderDay();window.dispatchEvent(new CustomEvent('research-practice-add',{detail:{date,task}}))}catch(e){toast(e.message)}
}
window.addEventListener('message',e=>{if(e.origin!=='http://127.0.0.1:8869'||e.source!==parent)return;if(e.data?.type==='study-task-request')addStudyTask(e.data.paperId,e.data.taskId);if(e.data?.type==='practice-task-request')addPracticeTask(e.data.taskId,e.data.date)});
const studyParams=new URLSearchParams(location.search);if(studyParams.has('studyPaper'))addStudyTask(studyParams.get('studyPaper'),studyParams.get('studyTask'));if(studyParams.has('practiceTask'))addPracticeTask(studyParams.get('practiceTask'),studyParams.get('practiceDate'));

async function receiveReadPaper(id){if(typeof id!=='string'||!/^[a-zA-Z0-9._-]{1,200}$/.test(id))return;try{const r=await fetch('/api/reader?id='+encodeURIComponent(id));if(!r.ok)return;markPaperRead(id,true)}catch{}}
window.addEventListener('message',e=>{if(e.origin==='http://127.0.0.1:8869'&&e.source===parent&&e.data?.type==='paper-read-status')receiveReadPaper(e.data.paperId)});
const markReadParam=new URLSearchParams(location.search).get('markRead');if(markReadParam){receiveReadPaper(markReadParam);const u=new URL(location.href);u.searchParams.delete('markRead');history.replaceState(null,'',u)}

// Share completion with the reading queue across pages and browser origins.
let completionRefresh=false;
async function refreshPaperCompletions(){if(completionRefresh||dailyEditingInProgress())return;completionRefresh=true;try{const ids=[...new Set([...day().todos.map(t=>t.paper?.id||t.studyTask?.paperId),...Object.values(day().subtasks).flat().map(t=>t.paper?.id)].filter(Boolean))];for(const id of ids){if(localStorage.getItem('paper-knowledge-draft:'+id))continue;const response=await fetch('/api/study/paper-knowledge?id='+encodeURIComponent(id),{cache:'no-store'});if(!response.ok)continue;const record=await response.json();if(localStorage.getItem('paper-knowledge-draft:'+id))continue;localStorage.setItem('paper-reading-tasks-v1:'+id,JSON.stringify(record.tasks));markPaperRead(id,record.completed)}refreshTodos()}catch{}finally{completionRefresh=false}}
window.addEventListener('paper-completion-change',()=>refreshTodos());
window.addEventListener('storage',e=>{if(e.key==='paper-knowledge-updated')refreshPaperCompletions()});
window.addEventListener('focus',refreshPaperCompletions);
window.addEventListener('schedule-date-change',refreshPaperCompletions);
setInterval(refreshPaperCompletions,20000);refreshPaperCompletions();

window.addEventListener('paper-progress-change',()=>refreshTodos());
window.addEventListener('paper-reading-status-change',()=>refreshTodos());

window.addEventListener('daily-todo-change',()=>{try{const stored=JSON.parse(localStorage.getItem(key));if(stored?.days){db=stored;refreshTodos();}}catch{}});

mountTodoReturnTarget($('todo-panel'),{onTask:id=>{const task=tasksFor(selected).find(t=>t.id===id);if(task)returnTimelineTask(task);},onSubtask:returnTimelineChild});
