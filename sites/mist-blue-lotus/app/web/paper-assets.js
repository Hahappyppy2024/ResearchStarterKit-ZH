import '/research-paste.js';
import {base,knowledgeApi as api} from './paper-knowledge.js';
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
function showFigure(src){
 const viewer=el('dialog'),toolbar=el('div'),image=el('img'),canvas=el('div'),label=el('span'),original=el('a','原尺寸图片 ↗');viewer.className='methodology-viewer';viewer.setAttribute('aria-label','截图大图预览');toolbar.className='methodology-viewer-tools';canvas.className='methodology-viewer-canvas';image.alt='放大的论文截图';original.href=src;original.target='_blank';original.rel='noopener';let scale=1;
 function zoom(value){scale=Math.max(.1,Math.min(8,value));image.style.width=Math.round(image.naturalWidth*scale)+'px';label.textContent=Math.round(scale*100)+'%'}
 function fit(){if(image.naturalWidth)zoom(Math.min(1,window.innerWidth*.9/image.naturalWidth,window.innerHeight*.72/image.naturalHeight))}
 for(const [text,action] of [['缩小 −',()=>zoom(scale/1.25)],['放大 ＋',()=>zoom(scale*1.25)],['适应窗口',fit],['关闭大图',()=>viewer.close()]]){const button=el('button',text);button.type='button';button.className='button';button.onclick=action;toolbar.append(button)}
 toolbar.append(label,original);canvas.append(image);viewer.append(toolbar,canvas);viewer.onclick=e=>{if(e.target===viewer)viewer.close()};viewer.onclose=()=>viewer.remove();image.onload=fit;image.onerror=()=>{label.textContent='图片加载失败，请关闭后重试'};document.body.append(viewer);viewer.showModal();image.src=src;
}
const screenshotPattern=/!\[[^\]]*\]\((http:\/\/127\.0\.0\.1:8866\/api\/study\/paste-image\?id=[a-f0-9-]{36})\)/g;
export function setupPaperPaste(dialog){
 const previews=new WeakMap();
 function draw(field){
  const urls=[...new Set([...field.value.matchAll(screenshotPattern)].map(m=>m[1]))];
  let panel=previews.get(field);
  if(!urls.length){panel?.remove();previews.delete(field);return;}
  if(!panel?.isConnected){panel=el('details');panel.className='paper-saved-screenshots';field.after(panel);previews.set(field,panel);}
  const value=urls.join('|');if(panel.dataset.value===value)return;panel.dataset.value=value;
  panel.replaceChildren(el('summary','已保存的截图 · '+urls.length+' 张（点开查看）'));
  const gallery=el('div');gallery.className='paper-screenshot-gallery';
  for(const url of urls){const a=el('a'),img=el('img');a.href=url;a.title='点击放大截图';a.setAttribute('aria-label','放大阅读任务截图');a.onclick=e=>{e.preventDefault();showFigure(url)};img.src=url;img.alt='已保存的阅读任务截图';img.loading='lazy';a.append(img);gallery.append(a);}panel.append(gallery);
 }
 function refresh(){for(const field of dialog.querySelectorAll('#reader-task-list textarea'))draw(field);}
 dialog.addEventListener('input',e=>{if(e.target.matches('textarea')){const p=previews.get(e.target);if(p)p.hidden=true;}});
 window.addEventListener('paper-knowledge-change',()=>{if(!dialog.open)return;refresh();for(const panel of dialog.querySelectorAll('.paper-saved-screenshots'))panel.hidden=false;});
 return refresh;
}
export function mountMethodology(host,paperId,state,save){
 const wrap=el('section'),list=el('div');wrap.className='paper-methodology-paste';state.figureIds||=[];
 wrap.append(el('p','直接在下方回答框按 Ctrl+V 粘贴方法图，再写图号、页码与自己的解释；截图会随回答自动保存，无需选择本地文件。'));
 host.insertBefore(wrap,host.querySelector('textarea'));
 if(!state.figureIds.length)return;
 const previous=el('details');previous.append(el('summary','以前保存的方法图 · '+state.figureIds.length+' 张'),list);wrap.append(previous);
 function draw(){list.replaceChildren();for(const id of state.figureIds){const card=el('figure'),a=el('a'),img=el('img'),remove=el('button','移除此图');a.href=base+'/api/study/methodology-image?id='+encodeURIComponent(id);a.setAttribute('aria-label','点击放大 Methodology 方法图');a.onclick=e=>{e.preventDefault();showFigure(a.href)};img.src=a.href;img.alt='论文 Methodology 方法总览图';img.loading='lazy';a.append(img);remove.type='button';remove.className='button';remove.onclick=()=>{state.figureIds=state.figureIds.filter(i=>i!==id);save();draw()};card.append(a,remove);list.append(card)}}draw();
}
