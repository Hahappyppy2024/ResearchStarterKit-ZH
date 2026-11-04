// A historical date is a view for this session; the next Beijing day starts on today.
// Keep lastToday unchanged while editing, so the next check retries after saving.
export function advanceDailyDate(state,today,busy=false){
 if(today===state.lastToday)return {...state,changed:false,pending:false};
 if(busy)return {...state,changed:false,pending:true};
 return {...state,selected:today,lastToday:today,followToday:true,changed:true,pending:false};
}

export function unscheduledPeriod(tasks,minute){
 if(minute<360)return {title:'夜间休息',detail:'今天的日程从 06:00 开始。',start:1380,end:360,timePrefix:'昨晚 ',timeMiddle:' — 今天 '};
 if(minute>=1380)return {title:'休息，明天再出发',detail:'收好今天的收获，准备明天的新安排。',start:1380,end:360,timePrefix:'',timeMiddle:' — 次日 '};
 const previous=tasks.filter(t=>t.end<=minute).sort((a,b)=>b.end-a.end)[0],next=tasks.filter(t=>t.start>minute).sort((a,b)=>a.start-b.start)[0];
 return {title:'当前时段未安排任务',detail:next?'下一项：'+next.title+'。可以从 Todo List 拖入任务安排这个空档。':'可以从 Todo List 拖入任务，安排今天剩余的时间。',start:Math.max(360,previous?.end||360),end:Math.min(1380,next?.start||1380),timePrefix:'',timeMiddle:' — '};
}
