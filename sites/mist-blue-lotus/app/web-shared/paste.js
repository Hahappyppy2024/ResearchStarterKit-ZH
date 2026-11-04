// Screenshot paste is stored as a local Markdown image link, never as base64 in notes.
(()=>{
 if(window.__researchPasteInstalled)return;
 window.__researchPasteInstalled=true;
 const endpoint='http://127.0.0.1:8866/api/study/paste-image';
 const pattern=/!\[[^\]]*\]\((http:\/\/127\.0\.0\.1:8866\/api\/study\/paste-image\?id=[a-f0-9-]{36})\)/g;
 const fields=new WeakMap();
 const style=document.createElement('style');
 style.textContent='.research-paste-preview{display:block;margin:6px 0;font-size:12px;color:var(--theme-muted,#666)}.research-inline-shot{display:inline-block;vertical-align:middle;max-width:120px!important;max-height:90px!important;width:auto;height:auto;object-fit:contain;border:1px solid var(--theme-line,#ccc);border-radius:8px;margin:4px}.research-saved-shot{display:inline-block;max-width:100%;vertical-align:middle}.research-paste-status{font-size:12px;color:var(--theme-muted,#666)}';
 document.head.append(style);
 function state(field){let item=fields.get(field);if(!item){item={};fields.set(field,item);}return item;}
 function preview(field){
  const item=state(field),count=new Set([...field.value.matchAll(pattern)].map(m=>m[1])).size;
  if(!count){item.box?.remove();item.box=null;return;}
  if(!item.box?.isConnected){item.box=document.createElement('div');item.box.className='research-paste-preview';field.after(item.box);}
  const text='已附 '+count+' 张截图 · 保存内容后显示，点击缩略图可放大';
  if(item.box.textContent!==text)item.box.textContent=text;
 }
 document.addEventListener('paste',async event=>{
  const field=event.target;
  if(!(field instanceof HTMLTextAreaElement||field instanceof HTMLInputElement&&['text','search'].includes(field.type)))return;
  const files=[...(event.clipboardData?.items||[])].filter(i=>i.type.startsWith('image/')).map(i=>i.getAsFile()).filter(Boolean);
  if(!files.length)return;
  event.preventDefault();
  const item=state(field);item.status?.remove();
  const status=document.createElement('p');item.status=status;status.className='research-paste-status';status.setAttribute('role','status');status.textContent='正在保存截图到本机……';field.after(status);
  let cursor=field.selectionStart??field.value.length;
  try{
   for(const file of files){
    if(file.size>8*1024*1024)throw Error('单张截图最大 8 MB');
    const image=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});
    const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image})}),data=await response.json();
    if(!response.ok)throw Error(data.error||'截图保存失败');
    const markdown='\n![截图]('+data.url+')\n';
    if(field.maxLength>0&&field.value.length+markdown.length>field.maxLength)throw Error('这个字段字数上限不足，请放到笔记或任务说明中');
    field.setRangeText(markdown,cursor,cursor,'end');cursor+=markdown.length;
    field.dispatchEvent(new Event('input',{bubbles:true}));
   }
   status.textContent='截图已存到本机；请按当前表单的保存方式保存内容。';preview(field);
  }catch(e){status.textContent=e.message;}
  setTimeout(()=>status.remove(),6000);
 });
 document.addEventListener('input',e=>{if(e.target.matches('textarea,input'))preview(e.target);});
 let pending=false;
 function scan(){
  pending=false;
  for(const f of document.querySelectorAll('textarea,input[type=text],input:not([type])'))if(fields.has(f)||f.value.includes('/api/study/paste-image?id='))preview(f);
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),nodes=[];
  while(walker.nextNode()){
   const n=walker.currentNode;
   if(n.textContent.includes('/api/study/paste-image?id=')&&!n.parentElement.closest('textarea,input,script,style,pre,code,.research-paste-preview,.research-paste-status,[contenteditable="true"]'))nodes.push(n);
  }
  for(const n of nodes){
   const text=n.textContent,matches=[...text.matchAll(pattern)];if(!matches.length)continue;
   const fragment=document.createDocumentFragment(),seen=new Set();let at=0;
   for(const m of matches){
    fragment.append(document.createTextNode(text.slice(at,m.index)));
    if(!seen.has(m[1])){
     seen.add(m[1]);const a=document.createElement('a'),img=document.createElement('img');
     a.href=m[1];a.target='_blank';a.rel='noopener';a.className='research-saved-shot';a.title='点击查看原图';
     img.src=m[1];img.alt='截图（点击放大）';img.className='research-inline-shot';img.loading='lazy';a.append(img);fragment.append(a);
    }
    at=m.index+m[0].length;
   }
   fragment.append(document.createTextNode(text.slice(at)));n.replaceWith(fragment);
  }
 }
 new MutationObserver(()=>{if(!pending){pending=true;requestAnimationFrame(scan);}}).observe(document.body,{childList:true,subtree:true});
 scan();
})();
