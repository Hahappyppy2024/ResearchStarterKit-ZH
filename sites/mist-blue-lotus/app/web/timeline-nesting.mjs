export function nestTodo(state,parentId,todoId,childId,parentSubtaskId=null){
 const todo=state.todos.find(t=>t.id===todoId);if(!todo||parentId===todoId)return state;
 if(parentSubtaskId&&!(state.subtasks?.[parentId]||[]).some(t=>t.id===parentSubtaskId))return state;
 const children=state.subtasks?.[todoId]||[],child={id:childId,title:todo.title,done:(state.done||[]).includes(todoId),sourceTodoId:todoId,...(todo.paper?{paper:todo.paper}:{}),...(todo.projectTask?{projectTask:todo.projectTask}:{}),...(todo.studyTask?{studyTask:todo.studyTask}:{}),...(todo.detail?{detail:todo.detail}:{}),...(Number.isInteger(todo.start)&&Number.isInteger(todo.end)?{durationMinutes:todo.end-todo.start}:todo.durationMinutes?{durationMinutes:todo.durationMinutes}:{}),...(todo.spentMinutes?{spentMinutes:todo.spentMinutes}:{})};
 if(parentSubtaskId)child.parentSubtaskId=parentSubtaskId;
 const subtasks={...state.subtasks,[parentId]:[...(state.subtasks?.[parentId]||[]),child,...children.map(t=>({...t,parentSubtaskId:t.parentSubtaskId||child.id}))]};delete subtasks[todoId];
 return {...state,todos:state.todos.filter(t=>t.id!==todoId),done:(state.done||[]).filter(i=>i!==todoId),subtasks,nestedTodoArchive:{...state.nestedTodoArchive,[todoId]:{todo,parentId,childIds:[child.id,...children.map(c=>c.id)],children,wasDone:child.done}}};
}
export function restoreNestedTodo(state,todoId){
 const saved=state.nestedTodoArchive?.[todoId];if(!saved||state.todos.some(t=>t.id===todoId))return state;
 const entry=Object.entries(state.subtasks||{}).find(([,items])=>items.some(t=>t.sourceTodoId===todoId));if(!entry)return state;
 const [rootId,current]=entry,child=current.find(t=>t.sourceTodoId===todoId),remove=new Set(subtreeIds(current,child.id)),subtasks={...state.subtasks,[rootId]:current.filter(i=>!remove.has(i.id)),[todoId]:current.filter(t=>t.id!==child.id&&remove.has(t.id)).map(t=>{const next={...t};if(next.parentSubtaskId===child.id)delete next.parentSubtaskId;return next;})},archive={...state.nestedTodoArchive};delete archive[todoId];
 return {...state,todos:[...state.todos,{...saved.todo,...(child?{title:child.title,...(typeof child.detail==='string'?{detail:child.detail}:{})}:{})}],done:[...new Set([...(state.done||[]),...((child?child.done:saved.wasDone)?[todoId]:[])])],subtasks,nestedTodoArchive:archive};
}
export function subtreeIds(items,id){const ids=new Set([id]);let changed=true;while(changed){changed=false;for(const t of items)if(ids.has(t.parentSubtaskId)&&!ids.has(t.id)){ids.add(t.id);changed=true;}}return [...ids];}
// Each root owns a flat list; parentSubtaskId supplies the visible tree.
export function moveSubtask(state,fromRoot,id,toRoot,parentSubtaskId=null){
 const source=state.subtasks?.[fromRoot]||[],item=source.find(t=>t.id===id),target=state.subtasks?.[toRoot]||[];if(!item)return state;
 const ids=new Set(subtreeIds(source,id));if((fromRoot===toRoot&&ids.has(parentSubtaskId))||(parentSubtaskId&&!target.some(t=>t.id===parentSubtaskId)))return state;
 const moved=source.filter(t=>ids.has(t.id)).map(t=>{if(t.id!==id)return t;const next={...t};if(parentSubtaskId)next.parentSubtaskId=parentSubtaskId;else delete next.parentSubtaskId;return next;});
 const subtasks={...state.subtasks,[fromRoot]:source.filter(t=>!ids.has(t.id))};subtasks[toRoot]=[...(fromRoot===toRoot?subtasks[toRoot]:target),...moved];return {...state,subtasks};
}
