let sequence=0;
export async function refreshDailyPaperStatistics(date){
 const stamp=++sequence;
 try{
  const r=await fetch('/api/study/daily-paper-statistics?'+new URLSearchParams({date}),{cache:'no-store'}),data=await r.json();
  if(!r.ok)throw Error(data.error||'统计暂未连接');if(stamp!==sequence)return;
  for(const key of ['started','inProgress','today','week','month','total']){const el=document.getElementById('read-stat-'+key);if(el)el.textContent=data[key];}
  const note=document.getElementById('reading-stats-note');if(note)note.textContent=date+' · 第一个阅读任务完成即开始阅读；全部任务完成才计为已读。每篇去重，历史开始日期不明的记录不补算到今天。';
 }catch(e){const note=document.getElementById('reading-stats-note');if(note)note.textContent='阅读统计暂未连接，保留上次显示。';}
}
