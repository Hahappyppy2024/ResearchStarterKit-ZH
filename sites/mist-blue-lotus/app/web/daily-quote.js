import {chinaTime} from "./schedule.mjs";
import data from "./ganying-quotes-data.js";
let selected=document.getElementById("date").value||chinaTime().date;
const DAY=86400000;
export function quoteIndex(date,start,count){const days=Math.floor((Date.parse(date+"T00:00:00+08:00")-Date.parse(start+"T00:00:00+08:00"))/DAY);return ((days%count)+count)%count}
function render(){if(!data?.quotes?.length)return;const i=quoteIndex(selected,data.startDate,data.quotes.length);document.getElementById("daily-quote").textContent=data.quotes[i];document.getElementById("daily-quote-meta").textContent=`《${data.title}》· 每日一句 · ${selected} · 第 ${i+1} 句`;const source=document.getElementById("daily-quote-source");if(data.source?.startsWith("https://")){source.href=data.source;source.hidden=false}}
window.addEventListener("schedule-date-change",e=>{selected=e.detail;render()});
render();
