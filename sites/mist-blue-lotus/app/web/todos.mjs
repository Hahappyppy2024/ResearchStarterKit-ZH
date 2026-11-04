export function cleanStudyTask(t){return t&&typeof t.paperId==="string"&&/^[a-zA-Z0-9._-]{1,200}$/.test(t.paperId)&&typeof t.taskId==="string"&&/^[a-z-]{1,60}$/.test(t.taskId)?{paperId:t.paperId,taskId:t.taskId}:null}
export function timeMinutes(value){if(!/^\d{2}:\d{2}$/.test(value||""))return null;const [h,m]=value.split(":").map(Number);return (h<24&&m<60)||(h===24&&m===0)?h*60+m:null}
export function cleanPaper(input){if(!input||typeof input.id!=="string"||!input.id||input.id.length>200||typeof input.title!=="string"||!input.title.trim())return null;return {id:input.id,title:input.title.trim().slice(0,500),url:typeof input.url==="string"&&/^https:\/\//.test(input.url)?input.url:""}}
export function cleanProjectTask(input){if(!input||typeof input.taskId!=="string"||typeof input.projectId!=="string"||!(/^[a-zA-Z0-9-]{1,80}$/).test(input.taskId)||!(/^[a-zA-Z0-9-]{1,80}$/).test(input.projectId)||typeof input.projectName!=="string")return null;return {taskId:input.taskId,projectId:input.projectId,projectName:input.projectName.slice(0,160),...(input.kind==="learning"&&typeof input.deckId==="string"&&/^[a-f0-9-]{36}$/.test(input.deckId)?{kind:"learning",deckId:input.deckId}:{})}}
export function cleanTodos(input){if(!Array.isArray(input))return [];const ids=new Set();return input.filter(t=>t&&typeof t.id==="string"&&/^todo-[a-z0-9-]{1,70}$/i.test(t.id)&&typeof t.title==="string"&&t.title.trim()&&t.title.length<=160&&((t.start===null&&t.end===null)||(Number.isInteger(t.start)&&Number.isInteger(t.end)&&t.start>=0&&t.end<=1440&&t.end>t.start))).filter(t=>{if(ids.has(t.id))return false;ids.add(t.id);return true}).map(t=>({id:t.id,title:t.title.trim(),start:t.start,end:t.end,detail:typeof t.detail==="string"?t.detail.slice(0,20000):"",...(Number.isInteger(t.durationMinutes)&&t.durationMinutes>0&&t.durationMinutes<=1440?{durationMinutes:t.durationMinutes}:{}),...(Number.isInteger(t.spentMinutes)&&t.spentMinutes>0&&t.spentMinutes<=1440?{spentMinutes:t.spentMinutes}:{}),...(typeof t.sourceScheduleId==="string"&&/^[a-z0-9-]{1,80}$/i.test(t.sourceScheduleId)?{sourceScheduleId:t.sourceScheduleId}:{}),...(cleanPaper(t.paper)?{paper:cleanPaper(t.paper)}:{}),...(cleanProjectTask(t.projectTask)?{projectTask:cleanProjectTask(t.projectTask)}:{}),...(cleanStudyTask(t.studyTask)?{studyTask:cleanStudyTask(t.studyTask)}:{})}))}
// Later inserted tasks occupy their chosen interval; surrounding time stays fixed.
export function plannedTasks(base,todos,priority=[]){
  let result=[];
  const inputs=[...base,...cleanTodos(todos).filter(t=>t.start!==null).map(t=>({...t,custom:true,type:"todo",detail:t.detail||"Todo List · 临时安排",alert:true}))];
  if(Array.isArray(priority)&&priority.length){const rank=new Map(priority.map((id,i)=>[id,i+1]));inputs.sort((a,b)=>(rank.get(a.id)||0)-(rank.get(b.id)||0));}
  for(const task of inputs){
    result=result.flatMap(old=>{
      if(old.end<=task.start||old.start>=task.end)return [old];
      const parts=[];
      if(old.start<task.start)parts.push({...old,end:task.start});
      if(old.end>task.end)parts.push({...old,start:task.end});
      return parts;
    });
    result.push({...task,sourceStart:task.start,sourceEnd:task.end});
  }
  return result.sort((a,b)=>a.start-b.start||a.end-b.end);
}
export function currentTask(tasks,minute){return tasks.filter(t=>t.start<=minute&&minute<t.end).sort((a,b)=>Number(!!b.custom)-Number(!!a.custom)||b.start-a.start)[0]||null}

export function cleanSubtasks(base,todos,input){
  if(!input||typeof input!=="object"||Array.isArray(input))return {};
  const result={};
  for(const task of [...base,...cleanTodos(todos)]){
    if(!Array.isArray(input[task.id]))continue;
    const seen=new Set();
    result[task.id]=input[task.id].filter(t=>t&&typeof t.id==="string"&&/^sub-[a-z0-9-]{1,70}$/i.test(t.id)&&typeof t.title==="string"&&t.title.trim()&&t.title.length<=160).filter(t=>{if(seen.has(t.id))return false;seen.add(t.id);return true}).map(t=>({id:t.id,title:t.title.trim(),done:t.done===true,...(Number.isInteger(t.spentMinutes)&&t.spentMinutes>0&&t.spentMinutes<=1440?{spentMinutes:t.spentMinutes}:{}),...(Number.isInteger(t.durationMinutes)&&t.durationMinutes>0&&t.durationMinutes<=1440?{durationMinutes:t.durationMinutes}:{}),...(typeof t.parentSubtaskId==='string'?{parentSubtaskId:t.parentSubtaskId}:{}),...(typeof t.sourceTodoId==='string'&&/^todo-[a-z0-9-]{1,70}$/i.test(t.sourceTodoId)?{sourceTodoId:t.sourceTodoId}:{}),...(typeof t.detail==='string'?{detail:t.detail.slice(0,20000)}:{}),...(cleanProjectTask(t.projectTask)?{projectTask:cleanProjectTask(t.projectTask)}:{}),...(cleanStudyTask(t.studyTask)?{studyTask:cleanStudyTask(t.studyTask)}:{}),...(cleanPaper(t.paper)?{paper:cleanPaper(t.paper)}:{})}));
    const byId=new Map(result[task.id].map(t=>[t.id,t]));
    for(const item of result[task.id]){const path=new Set([item.id]);let parent=item.parentSubtaskId;while(parent){if(path.has(parent)||!byId.has(parent)){delete item.parentSubtaskId;break;}path.add(parent);parent=byId.get(parent).parentSubtaskId;}}
  }
  return result;
}

export function cleanScheduleOverrides(base,input){if(!input||typeof input!=="object"||Array.isArray(input))return {};const out={};for(const task of base){const t=input[task.id];if(!t||typeof t.title!=="string"||!t.title.trim()||t.title.length>160||!Number.isInteger(t.start)||!Number.isInteger(t.end)||t.start<0||t.end>1440||t.end<=t.start)continue;out[task.id]={title:t.title.trim(),start:t.start,end:t.end,detail:typeof t.detail==="string"?t.detail.slice(0,20000):""}}return out}
export function cleanHiddenSchedule(base,input){return Array.isArray(input)?[...new Set(input.filter(id=>base.some(t=>t.id===id)))]:[]}
export function scheduledBase(base,state={}){const overrides=cleanScheduleOverrides(base,state.scheduleOverrides),hidden=cleanHiddenSchedule(base,state.hiddenSchedule);return base.filter(t=>!hidden.includes(t.id)).map(t=>({...t,...overrides[t.id]}))}
