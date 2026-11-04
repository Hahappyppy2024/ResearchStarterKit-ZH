import {cleanTodos,cleanScheduleOverrides,cleanHiddenSchedule,cleanSubtasks} from './todos.mjs';

// Keep a persistent undo snapshot while changing only this day's checkmarks.
export function resetDailyCompletion(state){
 const children=Object.fromEntries(Object.entries(state.subtasks||{}).map(([root,items])=>[root,items.map(item=>({...item,done:false}))]));
 const checked=Object.values(state.subtasks||{}).flat().filter(item=>item.done).map(item=>item.id);
 if(!(state.done||[]).length&&!checked.length)return state;
 return {...state,done:[],subtasks:children,completionResetUndo:{done:[...(state.done||[])],children:checked}};
}
export function undoDailyCompletionReset(state){
 const snapshot=state.completionResetUndo;if(!snapshot)return state;
 const checked=new Set(snapshot.children||[]),next={...state,done:[...new Set([...(state.done||[]),...(snapshot.done||[])])],subtasks:Object.fromEntries(Object.entries(state.subtasks||{}).map(([root,items])=>[root,items.map(item=>({...item,done:item.done||checked.has(item.id)}))]))};
 delete next.completionResetUndo;return next;
}

// A day's completion belongs to that date; global paper reading state is separate.
export function dailyState(base,days,date){
  const saved=days?.[date],value=saved&&typeof saved==='object'&&!Array.isArray(saved)?saved:{};
  const todos=cleanTodos(value.todos);
  return {
    ...value,
    notes:typeof value.notes==='string'?value.notes:'',
    todos,
    done:[...new Set(Array.isArray(value.done)?value.done:[])],
    scheduleOverrides:cleanScheduleOverrides(base,value.scheduleOverrides),
    hiddenSchedule:cleanHiddenSchedule(base,value.hiddenSchedule),
    subtasks:cleanSubtasks(base,todos,value.subtasks)
  };
}

export function restoreDailyTemplate(state){return {...state,templateResetUndo:{scheduleOverrides:state.scheduleOverrides||{},hiddenSchedule:state.hiddenSchedule||[],timelineOrder:state.timelineOrder||[]},scheduleOverrides:{},hiddenSchedule:[],timelineOrder:[]};}
export function undoDailyTemplateRestore(state){if(!state.templateResetUndo)return state;const next={...state,...state.templateResetUndo};delete next.templateResetUndo;return next;}
