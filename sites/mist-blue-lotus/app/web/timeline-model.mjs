export const TIMELINE_START=360,TIMELINE_END=1380,TIMELINE_STEP=5,TIMELINE_SCALE=2;
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
export const snapMinute=n=>Math.round(n/TIMELINE_STEP)*TIMELINE_STEP;
export function adjustInterval(start,end,mode,delta){
 const change=snapMinute(delta);
 if(mode==='start')return {start:clamp(snapMinute(start+change),TIMELINE_START,end-TIMELINE_STEP),end};
 if(mode==='end')return {start,end:clamp(snapMinute(end+change),start+TIMELINE_STEP,TIMELINE_END)};
 const duration=Math.min(TIMELINE_END-TIMELINE_START,Math.max(TIMELINE_STEP,end-start)),next=clamp(snapMinute(start+change),TIMELINE_START,TIMELINE_END-duration);return {start:next,end:next+duration};
}
export function intervalAt(minute,duration=60){return adjustInterval(snapMinute(minute),snapMinute(minute)+duration,'move',0);}
export function prioritizeTask(order,id){return [...(Array.isArray(order)?order:[]).filter(i=>typeof i==='string'&&i!==id),id];}

export function todoDuration(todo){return Number.isInteger(todo.start)&&Number.isInteger(todo.end)&&todo.end>todo.start?todo.end-todo.start:todo.durationMinutes|| (todo.paper?10:60);}

// Automatic planned slots, never actual time spent. Nested children fit inside their branch.
export function subtaskSlots(task,items){
 const slots=new Map();
 function duration(item){const children=items.filter(t=>t.parentSubtaskId===item.id);return Math.max(item.durationMinutes||10,children.reduce((sum,c)=>sum+duration(c),0));}
 function place(parentId,start,limit){let cursor=start;for(const item of items.filter(t=>(t.parentSubtaskId||null)===parentId)){const end=cursor+duration(item);slots.set(item.id,{start:cursor,end,duration:end-cursor,overflow:end>limit});place(item.id,cursor,Math.min(end,limit));cursor=end;}}
 if(Number.isInteger(task.start))place(null,task.start,task.end);return slots;
}

// Expanded content changes only its parent's visual span; following clock positions stay ordered.
export function contentTimeMap(tasks,heights={},scale=2){
 const intervals=tasks.filter(t=>t.end>TIMELINE_START&&t.start<TIMELINE_END).map(t=>({start:Math.max(TIMELINE_START,t.start),end:Math.min(TIMELINE_END,t.end),height:Math.max((Math.min(TIMELINE_END,t.end)-Math.max(TIMELINE_START,t.start))*scale,heights[t.id]||0)})).sort((a,b)=>a.start-b.start);
 const segments=[];let minute=TIMELINE_START,pixel=0;
 for(const t of intervals){if(t.start>minute){segments.push({start:minute,end:t.start,top:pixel,height:(t.start-minute)*scale});pixel+=(t.start-minute)*scale;}segments.push({...t,top:pixel});pixel+=t.height;minute=t.end;}
 if(minute<TIMELINE_END){segments.push({start:minute,end:TIMELINE_END,top:pixel,height:(TIMELINE_END-minute)*scale});pixel+=(TIMELINE_END-minute)*scale;}
 return {height:pixel,position(value){const m=clamp(value,TIMELINE_START,TIMELINE_END),s=segments.find(t=>m>=t.start&&m<=t.end);return s?s.top+(m-s.start)/(s.end-s.start)*s.height:0;},minute(value){const y=clamp(value,0,pixel),s=segments.find(t=>y>=t.top&&y<=t.top+t.height);return s?s.start+(y-s.top)/s.height*(s.end-s.start):TIMELINE_START;}};
}
