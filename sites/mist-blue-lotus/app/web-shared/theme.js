(()=>{
 const KEY='research-theme-v1',HUB='http://127.0.0.1:8869',allowed=new Set([8866,8867,8868,8869,8870,8891,8873,8872].map(p=>'http://127.0.0.1:'+p));allowed.add('http://localhost:8869');const isLocal=allowed.has(location.origin);let current=isLocal&&getComputedStyle(document.documentElement).getPropertyValue('--research-local-theme').trim()==='blue-mint'?'blue-mint':'blue',changed=false;
 function apply(theme){theme=isLocal&&theme==='blue-mint'?'blue-mint':'blue';current=theme;document.documentElement.dataset.researchTheme=theme;try{localStorage.setItem(KEY,theme)}catch{}const label=document.querySelector('.research-theme-label');const localLabel=getComputedStyle(document.documentElement).getPropertyValue('--research-local-label').trim().replace(/^['"]|['"]$/g,'')||'蓝绿 · 柔彩';if(label)label.textContent=theme==='blue-mint'?localLabel:'蓝色';document.querySelector('.research-theme-switch')?.setAttribute('aria-label',theme==='blue-mint'?localLabel+'主题':'蓝色主题')}
 function broadcast(){for(const frame of document.querySelectorAll('iframe')){try{const origin=new URL(frame.src).origin;if(allowed.has(origin))frame.contentWindow.postMessage({type:'research-theme',theme:current},origin)}catch{}}}

 apply(current);
 // Map existing palette declarations onto shared tokens; preserve warm warning/error colors.
 function mapped(hex,property){let raw=hex.slice(1);if(raw.length===3||raw.length===4)raw=raw.split('').map(c=>c+c).join('');if(raw.length!==6&&raw.length!==8)return hex;const values=[0,2,4].map(i=>parseInt(raw.slice(i,i+2),16)/255),max=Math.max(...values),min=Math.min(...values),light=(max+min)/2,delta=max-min;let hue=0;if(delta){const [r,g,b]=values;hue=60*(max===r?((g-b)/delta)%6:max===g?(b-r)/delta+2:(r-g)/delta+4);if(hue<0)hue+=360}const saturation=delta/(1-Math.abs(2*light-1)||1);if(saturation>.3&&(hue<75||hue>300)&&light<.85)return hex;if(raw.length===8&&raw.slice(6)!=='ff')return hex;const bg=property.includes('background'),border=/border|outline/.test(property);if(light>.975)return bg?'var(--theme-paper)':hex;if(light>.94)return bg?(delta>.04?'var(--theme-soft)':'var(--theme-bg)'):'var(--theme-line)';if(light>.86)return bg?'var(--theme-soft)':'var(--theme-line)';if(light>.73)return bg?'var(--theme-soft)':'var(--theme-line)';if(light<.25)return bg?'var(--theme-strong)':'var(--theme-ink)';return saturation>.18?'var(--theme-accent)':bg?'var(--theme-soft)':'var(--theme-muted)'}
 function rules(list){let out='';for(const r of list){if(r.selectorText&&r.style){let declarations='';for(const property of r.style){if(!/(color|background|border|outline|fill|stroke|shadow)/.test(property)||property.startsWith('--'))continue;const original=r.style.getPropertyValue(property),value=original.replace(/#[0-9a-f]{3,8}\b/gi,h=>mapped(h,property)).replace(/rgba?\([^)]+\)/gi,color=>{const numbers=color.match(/[\d.]+/g)?.map(Number);if(!numbers||numbers.length<3||numbers.length>3&&numbers[3]<1)return color;const hex='#'+numbers.slice(0,3).map(n=>Math.round(n).toString(16).padStart(2,'0')).join('');return mapped(hex,property)});if(value!==original)declarations+=property+':'+value+(r.style.getPropertyPriority(property)?' !important':'')+';'}if(declarations)out+=r.selectorText+'{'+declarations+'}'}else if(r.cssRules&&r.conditionText)out+=(r.constructor.name==='CSSSupportsRule'?'@supports ':'@media ')+r.conditionText+'{'+rules(r.cssRules)+'}'}return out}
 const mappedStyle=document.createElement('style');mappedStyle.id='research-theme-mapped';let css='';for(const sheet of document.styleSheets){if(sheet.href?.includes('research-theme.css'))continue;try{css+=rules(sheet.cssRules)}catch{}}mappedStyle.textContent=css;if(location.port!=='8869')document.head.append(mappedStyle);
 if(parent===window){const switcher=document.createElement('div');switcher.className='research-theme-switch research-theme-unified';switcher.setAttribute('aria-label','蓝绿柔彩主题');const swatch=document.createElement('span');swatch.className='theme-unified-swatch';swatch.setAttribute('aria-hidden','true');const label=document.createElement('span');label.className='research-theme-label';switcher.append(swatch,label);const header=document.querySelector('.hub-header');if(header)header.append(switcher);else{switcher.classList.add('research-theme-floating');document.body.append(switcher)}}
 apply(current);document.querySelectorAll('iframe').forEach(f=>f.addEventListener('load',broadcast));window.addEventListener('storage',e=>{if(e.key===KEY){apply(e.newValue);broadcast()}});
 window.addEventListener('message',e=>{if(!allowed.has(e.origin))return;if(e.data?.type==='research-theme-ready'&&parent===window&&[...document.querySelectorAll('iframe')].some(f=>f.contentWindow===e.source))e.source.postMessage({type:'research-theme',theme:current},e.origin);if(e.data?.type==='research-theme'&&e.source===parent&&allowed.has(e.origin)){changed=true;apply(e.data.theme)}});
 if(isLocal&&parent!==window){let parentOrigin=HUB;try{const referrerOrigin=new URL(document.referrer).origin;if(allowed.has(referrerOrigin))parentOrigin=referrerOrigin}catch{}parent.postMessage({type:'research-theme-ready'},parentOrigin)}
 if(isLocal)fetch(HUB+'/api/theme',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{if(d&&!changed){apply(d.theme);broadcast()}}).catch(()=>{});
})();

// One navigation design for the hub and every standalone local page.
(()=>{
 const hub='http://127.0.0.1:8869/';
 const entries=[["daily", "每日努力", "Daily Effort"], ["courses", "我的课程", "My Courses"], ["learning", "基础知识", "AI Foundations"], ["reading", "今日必读", "Must Read"], ["arxiv", "arXiv 每周论文", "Weekly Papers"], ["library", "论文库", "Paper Library"], ["atlas", "论文脉络", "Paper Atlas"], ["scholars", "实验室与学者", "Labs & Scholars"], ["methods", "科研方法", "Research Methods"], ["projects", "项目实验本", "Projects Notebook"], ["blog", "Blog", "Research Blog"]];
 const existing=document.querySelector('.hub-header');
 if(existing){existing.classList.add('research-nav-host');return}
 const embedded=window.parent!==window;document.body.classList.add(embedded?'research-embedded':'research-has-topbar');
 for(const old of document.querySelectorAll('header.topbar')){
  for(const brand of old.querySelectorAll('.brand'))brand.hidden=true;
  if(!old.querySelector('button,input,select,label'))old.hidden=true;
  else old.classList.add('research-page-tools');
 }
 if(embedded)return;
 let active='daily';const p=location.pathname,port=location.port;
 if(port==='8867')active='library';else if(port==='8868')active='poetry';else if(port==='8891')active='scholars';else if(port==='8870'||port==='8771')active=p.startsWith('/learning')?'learning':'projects';else if(port==='8873')active='atlas';else if(/arxiv/.test(p))active='arxiv';else if(/courses|innovation/.test(p))active='courses';else if(/reading|paper-questions|paper-week/.test(p))active='reading';else if(/lineage|taxonomy|datasets/.test(p))active='atlas';else if(/library/.test(p))active='library';else if(/labs/.test(p))active='scholars';else if(/blog/.test(p))active='blog';else if(/methods/.test(p))active='methods';
 const header=document.createElement('header');header.className='hub-header research-nav-host research-shared-header';
 const brand=document.createElement('a');brand.className='hub-brand';brand.href=hub+'#daily';
 const mark=document.createElement('span');mark.className='brand-mark';mark.setAttribute('role','img');mark.setAttribute('aria-label','七朵莲花，从含苞到盛开');mark.innerHTML="<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 196 106\" fill=\"none\">\n<defs>\n <linearGradient id=\"petal\" x1=\"0\" y1=\"0\" x2=\".5\" y2=\"1\"><stop stop-color=\"#fafcff\"/><stop offset=\".52\" stop-color=\"#e2ddec\"/><stop offset=\"1\" stop-color=\"#8db8d1\"/></linearGradient>\n <linearGradient id=\"pink\" x1=\"0\" y1=\"0\" x2=\".5\" y2=\"1\"><stop stop-color=\"#fffaff\"/><stop offset=\".5\" stop-color=\"#ecdce9\"/><stop offset=\"1\" stop-color=\"#b8b9d8\"/></linearGradient>\n <linearGradient id=\"leaf\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#d8ebe3\"/><stop offset=\"1\" stop-color=\"#98bbbd\"/></linearGradient>\n <path id=\"p\" d=\"M0 0C-10-6-10-18 0-29C10-18 10-6 0 0Z\"/>\n <g id=\"bloom\" stroke=\"#94b5c9\" stroke-width=\".65\" stroke-linejoin=\"round\">\n  <use href=\"#p\" transform=\"rotate(-74) scale(.8)\" fill=\"url(#petal)\"/><use href=\"#p\" transform=\"rotate(74) scale(.8)\" fill=\"url(#petal)\"/>\n  <use href=\"#p\" transform=\"rotate(-49) scale(.92)\" fill=\"url(#petal)\"/><use href=\"#p\" transform=\"rotate(49) scale(.92)\" fill=\"url(#petal)\"/>\n  <use href=\"#p\" transform=\"rotate(-25)\" fill=\"url(#pink)\"/><use href=\"#p\" transform=\"rotate(25)\" fill=\"url(#pink)\"/>\n  <use href=\"#p\" fill=\"url(#petal)\"/><path d=\"M-15-3Q0 10 15-3Q0 2-15-3Z\" fill=\"url(#pink)\"/><path d=\"M-5 1Q0 3 5 1\" stroke=\"#c9b97f\"/>\n </g>\n <g id=\"half\" stroke=\"#95b4c6\" stroke-width=\".7\"><use href=\"#p\" transform=\"rotate(-23) scale(.7)\" fill=\"url(#pink)\"/><use href=\"#p\" transform=\"rotate(23) scale(.7)\" fill=\"url(#pink)\"/><use href=\"#p\" transform=\"scale(.7 .9)\" fill=\"url(#petal)\"/></g>\n <g id=\"bud\" stroke=\"#98b9ca\" stroke-width=\".7\"><path d=\"M0 0C-10-7-5-20 0-27C6-19 11-7 0 0Z\" fill=\"url(#pink)\"/><path d=\"M0 0Q-4-10 0-24M0 0Q5-10 0-24\"/><path d=\"M-6-5L0 1 6-5\" stroke=\"#8dafac\"/></g>\n</defs>\n<!-- Seven individual lotus blossoms, each at a different height and stage. -->\n<g stroke=\"#99b9b8\" stroke-width=\"1.1\" stroke-linecap=\"round\"><path d=\"M15 86Q12 70 15 56M40 84Q36 56 38 35M65 88Q62 76 64 65M93 86Q91 54 91 42M121 88Q125 77 123 66M151 87Q146 56 151 36M177 88Q181 77 177 69\"/></g>\n<g opacity=\".85\" fill=\"url(#leaf)\" stroke=\"#a9c8c9\" stroke-width=\".65\"><path d=\"M4 88Q23 66 43 85Q26 99 4 88Z\"/><path d=\"M58 91Q80 74 102 88Q84 102 58 91Z\"/><path d=\"M118 91Q140 74 163 88Q146 102 118 91Z\"/><path d=\"M157 91Q179 76 193 90Q175 101 157 91Z\"/></g>\n<use href=\"#bud\" transform=\"translate(15 56) scale(.57)\"/>\n<use href=\"#bud\" transform=\"translate(38 35) scale(.72)\"/>\n<use href=\"#half\" transform=\"translate(64 65) scale(.8)\"/>\n<use href=\"#half\" transform=\"translate(91 42) scale(1)\"/>\n<use href=\"#bloom\" transform=\"translate(123 66) scale(.7)\"/>\n<use href=\"#bloom\" transform=\"translate(151 36) scale(.83)\"/>\n<use href=\"#bloom\" transform=\"translate(177 69) scale(.94)\"/>\n<path d=\"M14 100Q92 105 184 99\" stroke=\"#b8d7e6\" stroke-width=\".8\" opacity=\".7\"/>\n</svg>";
 const title=document.createElement('span');title.textContent='我的研究桌面';brand.append(mark,title);header.append(brand);const motto=document.createElement('div');motto.className='research-motto';motto.textContent='世上无难事，只要肯登攀。';motto.title='毛泽东《水调歌头·重上井冈山》；当前书法字体：华文行楷';header.append(motto);
 const nav=document.createElement('nav');nav.className='hub-tabs';nav.setAttribute('aria-label','研究网站切换');
 for(const [id,zh,en] of entries){const a=document.createElement('a');a.href=hub+'#'+id;a.dataset.site=id;a.textContent=zh;const small=document.createElement('small');small.textContent=en;a.append(small);if(id===active)a.setAttribute('aria-current','page');nav.append(a)}
 header.append(nav);document.body.prepend(header);
 const switcher=document.querySelector('.research-theme-switch');if(switcher){switcher.classList.remove('research-theme-floating');header.append(switcher)}
 const measure=()=>document.documentElement.style.setProperty('--research-topbar-height',header.getBoundingClientRect().height+'px');measure();new ResizeObserver(measure).observe(header);
})();

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

/* A shared sticky close control for every dialog, including dynamically created ones. */
(()=>{
 const install=()=>{
  for(const dialog of document.querySelectorAll('dialog,[role="dialog"]')){
   if(dialog.querySelector(':scope > .reader-frozen-tools')||dialog.querySelector(':scope > .research-dialog-closebar'))continue;
   const controls=[...dialog.querySelectorAll('button,[role="button"]')].filter(b=>b.matches('[data-close],.modal-close,.dialog-close,.close-button')||/^关闭/.test(b.getAttribute('aria-label')||'')||/^(关闭|关闭窗口|关闭弹窗)$/.test(b.textContent.trim()));
   if(!controls.length&&dialog.tagName!=='DIALOG')continue;
   const bar=document.createElement('div');bar.className='research-dialog-closebar';const close=document.createElement('button');close.type='button';close.textContent='关闭';close.setAttribute('aria-label','关闭当前窗口');
   close.onclick=()=>{if(controls[0])controls[0].click();else dialog.close()};bar.append(close);for(const control of controls)control.classList.add('research-original-close');dialog.prepend(bar);
  }
 };
 let scheduled=false;new MutationObserver(()=>{if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;install()})}}).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open','aria-hidden']});install();
})();

// Local navigation remembers list positions, including independently scrolling panels.
(()=>{
 const origins=new Set([8866,8867,8868,8869,8870,8891,8873,8872].map(p=>'http://127.0.0.1:'+p));origins.add('http://localhost:8869');
 if(!origins.has(location.origin))return;
 const prefix='research-return-v1:',query=new URLSearchParams(location.search),safe=value=>{if(!value)return null;try{const u=new URL(value,location.href);return origins.has(u.origin)?u:null;}catch{return null;}};
 const read=(store,key)=>{try{return JSON.parse(store.getItem(key)||'null');}catch{return null;}};
 const write=(store,key,value)=>{try{store.setItem(key,JSON.stringify(value));}catch{}};
 const pageKey=()=>prefix+'page:'+location.href;
 function selector(e){if(e.id)return '#'+CSS.escape(e.id);const parts=[];while(e&&e!==document.body&&parts.length<9){const tag=e.tagName.toLowerCase(),siblings=e.parentElement?Array.from(e.parentElement.children).filter(n=>n.tagName===e.tagName):[];parts.unshift(tag+':nth-of-type('+(siblings.indexOf(e)+1)+')');e=e.parentElement;if(e?.id){parts.unshift('#'+CSS.escape(e.id));break;}}return parts.join('>');}
 function snapshot(){const panels=[];for(const e of document.querySelectorAll('aside,nav,section,div,main,ul,dialog')){if(!e.getClientRects().length||(!e.scrollTop&&!e.scrollLeft))continue;const style=getComputedStyle(e);if(!/(auto|scroll)/.test(style.overflow+style.overflowX+style.overflowY))continue;panels.push({selector:selector(e),x:e.scrollLeft,y:e.scrollTop});if(panels.length===40)break;}return {url:location.href,x:scrollX,y:scrollY,panels,at:Date.now()};}
 let restoring=false,timer,restoreTimer;
 function save(){if(!restoring)write(sessionStorage,pageKey(),snapshot());}
 function stop(){restoring=false;clearInterval(restoreTimer);}
 function restore(saved){if(!saved||Date.now()-saved.at>86400000)return;stop();restoring=true;const start=Date.now();let settled=0;const apply=()=>{if(Date.now()-start>30000){stop();return;}window.scrollTo({left:saved.x||0,top:saved.y||0,behavior:'instant'});let ready=Math.abs(scrollY-(saved.y||0))<3&&Math.abs(scrollX-(saved.x||0))<3;for(const p of saved.panels||[]){let e;try{e=document.querySelector(p.selector);}catch{}if(e){e.scrollTo({left:p.x||0,top:p.y||0,behavior:'instant'});ready=ready&&Math.abs(e.scrollTop-p.y)<3&&Math.abs(e.scrollLeft-p.x)<3;}else ready=false;}settled=ready?settled+1:0;if(settled>=4&&Date.now()-start>=700)stop();};apply();restoreTimer=setInterval(apply,180);}

 for(const type of ['wheel','touchstart','pointerdown','keydown'])window.addEventListener(type,stop,{capture:true,passive:true});
 document.addEventListener('scroll',()=>{if(restoring)return;clearTimeout(timer);timer=setTimeout(save,160);},{capture:true,passive:true});
 window.addEventListener('pagehide',save);
 // Record the source before opening a standalone reader. No content or form values are copied.
 function rememberLink(e){const a=e.target.closest?.('a[href]');if(!a||a.hasAttribute('data-research-back'))return;save();const u=safe(a.href);if(!u||!/(^|\/)(paper|article)\.html$/.test(u.pathname))return;const token=crypto.randomUUID(),saved=snapshot();write(localStorage,prefix+token,saved);try{const keys=Object.keys(localStorage).filter(k=>k.startsWith(prefix)&&!k.startsWith(prefix+'page:')).sort((a,b)=>(read(localStorage,b)?.at||0)-(read(localStorage,a)?.at||0));for(const key of keys.slice(80))localStorage.removeItem(key);}catch{}u.searchParams.set('returnTo',location.href);u.searchParams.set('returnToken',token);u.searchParams.set('returnMode',a.target==='_blank'||e.ctrlKey||e.metaKey||e.button===1?'tab':'history');a.href=u.href;}
 document.addEventListener('click',rememberLink,true);document.addEventListener('auxclick',rememberLink,true);
 function setupBack(){for(const a of document.querySelectorAll('[data-research-back]')){a.classList.add('research-return-button');const source=safe(query.get('returnTo'));if(source){const names={'arxiv.html':'论文观测台','library.html':'论文库','reading.html':'今日必读','methods.html':'科研方法','blog.html':'Blog','courses.html':'我的课程','lineage.html':'论文脉络'};a.textContent='返回'+(names[source.pathname.split('/').pop()]||'原位置');a.title='返回打开文章的位置';const token=query.get('returnToken');if(token&&/^[a-f0-9-]{36}$/.test(token))source.searchParams.set('restoreToken',token);a.href=source.href;}a.onclick=e=>{e.preventDefault();const from=safe(query.get('returnTo'))||safe(document.referrer),fallback=safe(a.href);let target=from||fallback;if(!target)return;const token=query.get('returnToken');if(token&&/^[a-f0-9-]{36}$/.test(token))target.searchParams.set('restoreToken',token);if(query.get('returnMode')==='tab'){window.close();setTimeout(()=>location.assign(target.href),180);return;}if(!token&&from&&history.length>1&&safe(document.referrer)?.href===from.href){history.back();return;}location.assign(target.href);};}}
 setupBack();
 let initial=null;const token=query.get('restoreToken');if(token&&/^[a-f0-9-]{36}$/.test(token)){initial=read(localStorage,prefix+token);const clean=new URL(location.href);clean.searchParams.delete('restoreToken');history.replaceState(history.state,'',clean);}
 const navigation=performance.getEntriesByType('navigation')[0];if(!initial&&['back_forward','reload'].includes(navigation?.type))initial=read(sessionStorage,pageKey());
 if(initial)restore(initial);
 window.addEventListener('pageshow',e=>{setupBack();if(e.persisted)restore(read(sessionStorage,pageKey()));});
 window.addEventListener('popstate',()=>{const saved=read(sessionStorage,pageKey());if(saved)restore(saved);});
})();

// Keep text legible on every filled control, including dynamically created reader tabs.
(()=>{
 let pending=false;
 const luminance=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
 function update(){pending=false;const enabled=document.documentElement.dataset.researchTheme==='blue-mint';
  for(const n of document.querySelectorAll('button,a.button,.now-card,.nightly-quiz-entry,.task.active,.tree-topic.active,.module-nav.active,.course-selection-card.active')){
   const rgb=getComputedStyle(n).backgroundColor.match(/[\d.]+/g)?.map(Number);const filled=enabled&&rgb&&rgb.length>=3&&(rgb.length<4||rgb[3]>.9)&&luminance(rgb.slice(0,3))<.36;
   if(filled)n.setAttribute('data-research-contrast','light');else n.removeAttribute('data-research-contrast');
  }
 }
 function schedule(){if(!pending){pending=true;requestAnimationFrame(update);}}
 new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style','aria-current','aria-pressed','aria-selected','data-research-theme']});
 window.addEventListener('load',schedule);schedule();
})();

// Style every return link consistently without replacing its navigation behavior.
(()=>{const mark=root=>{const links=[];if(root.nodeType===1&&root.matches('a[href]'))links.push(root);if(root.querySelectorAll)links.push(...root.querySelectorAll('a[href]'));for(const a of links)if(/^(?:[←‹↩]\s*)?返回/.test(a.textContent.trim()))a.classList.add('research-return-button');};mark(document);new MutationObserver(records=>{for(const r of records){if(r.type==='characterData'){const a=r.target.parentElement?.closest('a[href]');if(a)mark(a);}else for(const n of r.addedNodes)mark(n);}}).observe(document.body,{childList:true,subtree:true,characterData:true});})();

// CUTE_NAV_TRIAL_BEGIN
// Decorative replacements only: existing links, handlers and disclosure semantics stay intact.
(()=>{
 const strip=(control,pattern)=>{const walker=document.createTreeWalker(control,NodeFilter.SHOW_TEXT);let n;while((n=walker.nextNode())){if(n.parentElement?.closest('svg,script,style'))continue;const value=n.nodeValue.replace(pattern,'');if(value!==n.nodeValue)n.nodeValue=value;}};
 const decorate=control=>{
  if(!(control instanceof Element))return;
  const text=control.textContent.trim(),label=control.getAttribute('aria-label')||control.title||text;
  if(control.matches('summary')){
   control.classList.add('cute-disclosure');strip(control,/^[\s]*[▸▹▶►▾▼⌄›‹]\s*/g);return;
  }
  if(control.matches('button[aria-expanded]')){control.classList.add('cute-disclosure');strip(control,/^[\s]*[▸▹▶►▾▼⌄›‹]\s*/g);}
  if(control.matches('a')&&(/^(?:[←‹↩]\s*)?返回/.test(text)||control.classList.contains('research-return-button'))){
   control.classList.add('research-return-button','cute-return');strip(control,/^[\s]*[←‹↩]\s*/g);
  }else if(control.matches('a')&&text.includes('↗')){
   control.classList.add('cute-external');strip(control,/↗[\uFE0E\uFE0F]?/g);
   if(!control.textContent.trim()&&!control.getAttribute('aria-label'))control.setAttribute('aria-label',label||'打开链接');
  }
  if(!control.matches('button,a'))return;
  const normalized=text.replace(/[←→‹›«»❮❯〈〉<>]/g,'').trim();
  const previous=/^(?:上一篇(?:论文)?|上一页|上一组|上一周|前一天)$/.test(normalized)||/^(?:上一篇(?:论文)?|前一天)$/.test(label)||/^(?:obs-prev|prev-day)$/.test(control.id);
  const next=/^(?:下一篇(?:论文)?|下一页|下一组|下一周|后一天)$/.test(normalized)||/^(?:下一篇(?:论文)?|后一天)$/.test(label)||/^(?:obs-next|next-day)$/.test(control.id);
  if(previous||next){
   control.classList.add('cute-step');control.dataset.cuteDirection=previous?'previous':'next';
   if(!control.getAttribute('aria-label'))control.setAttribute('aria-label',normalized|| (previous?'上一篇':'下一篇'));
   strip(control,/[←→‹›«»❮❯〈〉<>]/g);control.classList.toggle('cute-icon-only',!control.textContent.trim());
  }
 };
 const scan=root=>{if(root.nodeType===1&&root.matches('a,button,summary'))decorate(root);if(root.querySelectorAll)for(const c of root.querySelectorAll('a,button,summary'))decorate(c);};
 scan(document);
 const pending=new Set();let frame=false;
 new MutationObserver(records=>{for(const r of records){if(r.type==='characterData'){const c=r.target.parentElement?.closest('a,button,summary');if(c)pending.add(c);}else for(const n of r.addedNodes){if(n.nodeType===1)pending.add(n);else{const c=n.parentElement?.closest('a,button,summary');if(c)pending.add(c);}}}if(pending.size&&!frame){frame=true;requestAnimationFrame(()=>{frame=false;for(const root of pending)if(root.isConnected)scan(root);pending.clear();});}}).observe(document.body,{childList:true,subtree:true,characterData:true});
})();
// CUTE_NAV_TRIAL_END
