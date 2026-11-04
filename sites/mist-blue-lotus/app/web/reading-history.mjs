import {chinaTime} from './schedule.mjs';
import {PAPER_TASKS} from './paper-tasks.mjs';
export const READING_STATE_KEY='daily-paper-reading-v1',READING_HISTORY_KEY='paper-read-dates-v1';
export const MANUAL_READING_KEY='paper-manual-reading-v1',SERVER_READING_KEY='paper-server-reading-v1';
export function cacheManualReading(item){const values=readObject(MANUAL_READING_KEY),before=JSON.stringify(values[item.id]);if(item.manual)values[item.id]={read:item.read,readDate:item.readDate};else delete values[item.id];if(before!==JSON.stringify(values[item.id]))localStorage.setItem(MANUAL_READING_KEY,JSON.stringify(values));const server=readObject(SERVER_READING_KEY);if(server[item.id]!==item.read){server[item.id]=item.read;localStorage.setItem(SERVER_READING_KEY,JSON.stringify(server));}const current=readObject(READING_STATE_KEY)[item.id];if((item.manual||item.read||current)&&current!== (item.read?'read':'unread'))markPaperRead(item.id,item.read,true,item.readDate);}
function readObject(key){try{const value=JSON.parse(localStorage.getItem(key)||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{}}catch{return {}}}
export function readingStats(states,history,date){
  const day=new Date(date+'T00:00:00Z'),weekday=(day.getUTCDay()+6)%7;
  day.setUTCDate(day.getUTCDate()-weekday);
  const monday=day.toISOString().slice(0,10),month=date.slice(0,7);
  const result={today:0,week:0,month:0,total:0,undated:0};
  for(const [id,state] of Object.entries(states)){
    if(state!=='read')continue;
    result.total++;
    const when=history[id];
    if(typeof when!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(when)){result.undated++;continue}
    if(when===date)result.today++;
    if(when>=monday&&when<=date)result.week++;
    if(when.startsWith(month)&&when<=date)result.month++;
  }
  return result;
}
export function storedReadingStats(){const states=readObject(READING_STATE_KEY);for(const id of Object.keys(states))if(states[id]==='read'&&!isPaperRead(id))states[id]='unread';return readingStats(states,readObject(READING_HISTORY_KEY),chinaTime().date)}
export function markPaperRead(id,read,verified=false,date=null){
  const manual=readObject(MANUAL_READING_KEY)[id];if(manual)read=manual.read;
  if(read&&!manual&&!verified&&!paperIsComplete(id))return false;
  const server=readObject(SERVER_READING_KEY);if(Object.hasOwn(server,id)&&!manual&&server[id]!==read){server[id]=read;localStorage.setItem(SERVER_READING_KEY,JSON.stringify(server));}
  const states=readObject(READING_STATE_KEY),history=readObject(READING_HISTORY_KEY);
  if(read&&states[id]!=='read')history[id]=date||manual?.readDate||chinaTime().date;
  states[id]=read?'read':'unread';
  localStorage.setItem(READING_HISTORY_KEY,JSON.stringify(history));
  localStorage.setItem(READING_STATE_KEY,JSON.stringify(states));
  window.dispatchEvent(new CustomEvent('paper-reading-status-change'));
  return true;
}
export function paperIsComplete(id){const tasks=readObject('paper-reading-tasks-v1:'+id);return PAPER_TASKS.every(t=>tasks[t.id]?.done===true)}
export function renderReadingStats(){
  if(document.getElementById('read-stat-started'))return;
  const stats=storedReadingStats();
  for(const key of ['today','week','month','total']){const el=document.getElementById('read-stat-'+key);if(el)el.textContent=stats[key]}
  const note=document.getElementById('reading-stats-note');
  if(note)note.textContent='同一论文去重统计 · 本周从周一开始'+(stats.undated?` · ${stats.undated} 篇历史已读无日期，仅计入累计`:'');
}

export function isPaperRead(id){const manual=readObject(MANUAL_READING_KEY)[id];return manual?manual.read===true:readObject(READING_STATE_KEY)[id]==='read'&&(paperIsComplete(id)||readObject(SERVER_READING_KEY)[id]===true)}
