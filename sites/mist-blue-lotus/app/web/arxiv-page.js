import {chinaTime} from './schedule.mjs';
import {renderReadingStats,READING_STATE_KEY,READING_HISTORY_KEY} from './reading-history.mjs';
const $=id=>document.getElementById(id);
window.addEventListener('paper-add-to-task',e=>{
 const id=e.detail?.id;if(typeof id!=='string'||!(/^[a-zA-Z0-9._-]{1,200}$/).test(id))return;
 if(window.parent!==window){window.parent.postMessage({type:'research-add-arxiv-task',paperId:id},'http://127.0.0.1:8869');$('arxiv-task-status').textContent='正在打开今日安排，请选择放入哪个任务。'}
 else window.open('/?addPaper='+encodeURIComponent(id)+'&paperToday=1','_blank','noopener');
});
renderReadingStats();
window.addEventListener('paper-reading-status-change',renderReadingStats);
window.addEventListener('storage',e=>{if(e.key===READING_STATE_KEY||e.key===READING_HISTORY_KEY)renderReadingStats()});
window.addEventListener('focus',renderReadingStats);
setInterval(renderReadingStats,60000);
