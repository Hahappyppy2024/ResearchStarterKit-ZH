import {setPaperTitle} from './paper-title.js';
import {notifyRequiredReading} from './required-reading-updates.js';
const base=location.port==='8872'?location.origin:'http://127.0.0.1:8866';
export async function addToCourse(resource){
 const dialog=document.createElement('dialog');dialog.className='course-picker';dialog.style.cssText='max-width:550px;width:90%;border:1px solid #dbe2d0;border-radius:20px;padding:28px;background:#fffef9;color:#28594b';
 dialog.innerHTML='<h2>加入我的课程</h2><p class="resource-name"></p><form><label>课程<select name="course" required></select></label><label>章节<select name="unit" required></select></label><label>在课程中的作用<textarea name="purpose" rows="3" maxlength="5000" placeholder="例如：第二讲的背景知识，或方法对比案例"></textarea></label><p role="status"></p><button type="submit">加入课程</button> <button type="button" data-close>关闭</button></form><p><a href="http://127.0.0.1:8869/#courses" target="_top">新建或设计课程 ↗</a></p>';
 if(resource.resourceKind==='paper')setPaperTitle(dialog.querySelector('.resource-name'),{id:resource.resourceId,title:resource.title});else dialog.querySelector('.resource-name').textContent=resource.title||'当前资料';document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-close]').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();
 const form=dialog.querySelector('form'),message=form.querySelector('[role=status]');
 try{const r=await fetch(base+'/api/study/state');const data=await r.json();if(!r.ok)throw Error(data.error);const courses=data.courses;for(const [type,label] of [['foundation','基础课程'],['research','科研课程'],['self','自研课程']]){const items=courses.filter(c=>(c.courseType||'research')===type);if(!items.length)continue;const group=document.createElement('optgroup');group.label=label;for(const c of items)group.append(new Option(c.name,c.id));form.course.append(group)}if(resource.courseId)form.course.value=resource.courseId;const units=()=>{form.unit.replaceChildren();for(const unit of courses.find(c=>c.id===form.course.value)?.units||[])form.unit.add(new Option(unit,unit));const preferred=resource.resourceKind==='paper'?'论文阅读':'基础知识';if([...form.unit.options].some(o=>o.value===preferred))form.unit.value=preferred};form.course.onchange=units;units();if(resource.unit)form.unit.value=resource.unit;if(!courses.length){message.textContent='先新建一门课程，再回来添加这份资料。';form.querySelector('[type=submit]').disabled=true}
 form.onsubmit=async e=>{e.preventDefault();try{const r=await fetch(base+'/api/study/link',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...resource,courseId:form.course.value,unit:form.unit.value,purpose:form.purpose.value})});const d=await r.json();if(!r.ok)throw Error(d.error);message.textContent=d.alreadyExists?'这份资料已经在该课程中。':'已加入课程。';window.dispatchEvent(new Event('course-resources-change'))}catch(e){message.textContent=e.message}};
 }catch(e){message.textContent='未能读取课程：'+e.message}
}
export function scheduleStudyTask(paperId,taskId){
 const message={type:'research-add-study-task',paperId,taskId};
 if(window.parent!==window)window.parent.postMessage(message,'http://127.0.0.1:8869');
 else window.open(base+'/?studyPaper='+encodeURIComponent(paperId)+'&studyTask='+encodeURIComponent(taskId),'_blank','noopener');
}

export async function addToRequiredReading(paperId,reason=''){
 const {chinaTime}=await import('./schedule.mjs');
 const r=await fetch(base+'/api/study/queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paperId,date:chinaTime().date,reason})});
 const d=await r.json();if(!r.ok)throw Error(d.error||'加入今日必读失败');
 notifyRequiredReading();return d;
}
