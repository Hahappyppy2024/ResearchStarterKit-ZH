const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const plain=value=>(value||'').replace(/!\[[^\]]*\]\([^)]*\)/g,'（含截图，请打开阅读笔记查看）');
const action=(text,fn)=>{const b=node('button',text,'pc-button');b.type='button';b.onclick=fn;return b;};
export async function mountProblemComparison(host,{mapId,api,onChanged,choosePaper}){
 const status=node('p','正在整理当前分类的问题与已有阅读记录……','pc-status');host.replaceChildren(status);
 let data,selected='',search='',onlyNotes=false;
 try{data=await api('problem-comparison?'+new URLSearchParams({mapId}));if(!host.isConnected)return;}catch(e){status.textContent=e.message;return;}
 const defaults=['problem','method','evidence','limitations'];
 const columns=[
  {id:'problem',label:'具体问题 / Problem',hint:'这篇具体要解决什么？'},
  {id:'method',label:'怎么做 / Method',hint:'核心方法与关键设计是什么？'},
  {id:'evidence',label:'依据与条件 / Evidence',hint:'证据在哪一页？实验设置是否一致？'},
  {id:'limitations',label:'还缺什么 / Limitation',hint:'作者承认或你发现了哪些不足？'},
  ...(data.taskDefinitions||[]).filter(t=>!['problem','solution','why','limitations'].includes(t.id)).map(t=>({id:'task:'+t.id,label:t.title,hint:'这项阅读任务尚未填写'}))
 ];
 const valid=new Set(columns.map(c=>c.id)),columnKey='problem-comparison-columns-v1';let selectedColumns=defaults.slice();
 try{const saved=JSON.parse(localStorage.getItem(columnKey)||'null');if(Array.isArray(saved)){const chosen=[...new Set(saved.filter(id=>valid.has(id)))];if(chosen.length)selectedColumns=chosen;}}catch{}
 const cellValue=(p,id)=>id.startsWith('task:')?p.taskValues?.[id.slice(5)]||'':id==='evidence'?(p.evidence||(p.settings?'已保存实验／复现记录，可展开查看。':'')):p[id]||'';
 selected=data.groups[0]?.id||'';
 function form(group=null){
  const d=node('dialog',undefined,'pc-dialog'),f=node('form'),message=node('p',undefined,'pc-status');
  const title=node('h2',group?'确认同一个研究问题':'新建研究问题');
  const cn=node('input'),en=node('input'),description=node('textarea');cn.required=en.required=true;cn.maxLength=160;en.maxLength=200;cn.value=group?.name||'';en.value=group?.en||'';description.value=group?.definition||'';
  const field=(label,input)=>{const l=node('label',label);l.append(input);f.append(l);};field('研究问题（中文）',cn);field('Research question (English)',en);field('这个问题的边界／如何判断属于同一问题',description);
  let picked=new Set(group?.paperIds||[]);const q=node('input'),list=node('div',undefined,'pc-pick-list'),count=node('p');q.placeholder='搜索本分类中的论文';q.setAttribute('aria-label','选择要归入问题的论文');
  function choices(){list.replaceChildren();const matches=data.papers.filter(p=>(p.title+' '+p.titleZh).toLowerCase().includes(q.value.toLowerCase()));for(const p of matches.slice(0,50)){const label=node('label'),check=node('input');check.type='checkbox';check.checked=picked.has(p.id);check.onchange=()=>{check.checked?picked.add(p.id):picked.delete(p.id);count.textContent='已选 '+picked.size+' 篇';};label.append(check,node('span',(p.titleZh||p.title)+' · '+(p.year||'年份待补充')));list.append(label);}count.textContent='已选 '+picked.size+' 篇 · 搜索结果显示前 50 篇';}q.oninput=choices;choices();if(!group||group.suggested)f.append(q,count,list);else f.append(node('p','这次编辑保留已有论文归类。'));
  const save=node('button','保存问题分组','pc-button primary');save.type='submit';f.append(save,action('取消',()=>d.close()),message);d.append(title,f);document.body.append(d);d.onclose=()=>d.remove();d.showModal();
  f.onsubmit=async e=>{e.preventDefault();if(!picked.size){message.textContent='请至少选择一篇论文，再保存问题分组';return;}save.disabled=true;try{const saved=await api('problem-comparison-confirm',{mapId,problemId:group&&!group.suggested?group.id:undefined,name:cn.value,en:en.value,definition:description.value,paperIds:[...picked]});d.close();data=await api('problem-comparison?'+new URLSearchParams({mapId}));selected=saved.id;draw();onChanged?.();}catch(error){message.textContent=error.message;}finally{save.disabled=false;}};
 }
 function draw(){
  host.replaceChildren();
  const intro=node('section',undefined,'pc-intro');intro.append(node('h2','围绕一个问题，读懂一组论文'),node('p','① 看清问题 → ② 从早到晚比较方法 → ③ 找到还没解决的地方'),node('small','包含未读论文；对比不会改变已读状态。内容来自你已有的阅读回答，空白处留待整理。'));host.append(intro);
  const tools=node('div',undefined,'pc-tools'),select=node('select');select.setAttribute('aria-label','选择中英文研究问题');select.add(new Option('选择一个研究问题',''));for(const g of data.groups)select.add(new Option((g.unassigned?'待整理 · ':g.suggested?'待确认 · ':'已归类 · ')+g.name+' / '+(g.en||'英文待补充')+'（'+g.paperIds.length+' 篇）',g.id));select.value=selected;select.onchange=()=>{selected=select.value;draw();};tools.append(select,action('＋ 新建中英文问题',()=>form()));host.append(tools);
  const group=data.groups.find(g=>g.id===selected);
  if(!group){host.append(node('p','先新建一个具体的研究问题，再选择要一起比较的论文。问题比“目标检测”“智能体”更具体，例如：如何减少小目标漏检？','pc-empty'));return;}
  const head=node('section',undefined,'pc-question');head.append(node('span',group.unassigned?'尚未归类':group.suggested?'候选问题 · 题名关键词匹配，尚未确认':'已保存的问题分组','pc-badge'),node('h2',group.name),node('p',group.en||'English research question not yet provided','pc-question-en'),node('p',group.definition||'先核对研究对象、任务和假设，避免把相似题目当作同一个问题。'));
  if(group.unassigned)head.append(action('为相关论文新建问题',()=>form()));else if(group.suggested)head.append(action('核对并确认这个分组',()=>form(group)));
  else head.append(action('加入一篇论文',()=>choosePaper(async p=>{await api('problem-comparison-confirm',{name:group.name,en:group.en,definition:group.definition,paperIds:[p.id]});data=await api('problem-comparison?'+new URLSearchParams({mapId}));draw();onChanged?.();})),action('编辑／补充中英文问题',()=>form(group)));
  host.append(head);
  const filter=node('div',undefined,'pc-tools'),q=node('input');q.placeholder='在这组论文中搜索';q.setAttribute('aria-label','搜索对比论文');q.value=search;const l=node('label'),check=node('input');check.type='checkbox';check.checked=onlyNotes;l.append(check,document.createTextNode('只看已有阅读回答'));
  const caption=node('p',undefined,'pc-caption'),wrap=node('div',undefined,'pc-table-wrap');
  function table(){
   wrap.replaceChildren();const rows=data.papers.filter(p=>group.paperIds.includes(p.id)&&(!onlyNotes||selectedColumns.some(id=>cellValue(p,id)))&&(p.title+' '+p.titleZh).toLowerCase().includes(search.toLowerCase()));caption.textContent='由早到新 · '+rows.length+' 篇 · 方法与证据来自你的记录；实验条件不同，不能直接比较数值。';
   const selected=selectedColumns.map(id=>columns.find(c=>c.id===id)),t=node('table',undefined,'pc-table'),thead=node('thead'),tr=node('tr');wrap.classList.toggle('pc-wide',selected.length>4);t.style.minWidth=(selected.length<=4?760:(selected.length+1)*180)+'px';for(const name of ['论文 / Paper',...selected.map(c=>c.label)])tr.append(node('th',name));thead.append(tr);t.append(thead);const body=node('tbody');
   for(const p of rows){const row=node('tr'),paper=node('td');paper.append(node('span',p.year||'年份待补充','pc-year'),node('strong',p.titleZh||p.title),...(p.titleZh?[node('small',p.title)]:[]),node('small',p.venue||'来源待补充'));
    const link=node('a','打开论文与阅读任务 ↗','pc-read');link.href='paper.html?id='+encodeURIComponent(p.id);link.target='_blank';link.rel='noopener';paper.append(link);row.append(paper);
    for(const {id:key,hint} of selected){const cell=node('td'),value=cellValue(p,key);cell.append(node('div',value?plain(value):'待整理：'+hint,value?'pc-answer':'pc-missing'));if(key==='evidence'&&p.settings){const d=node('details'),summary=node('summary','我的实验／复现记录');d.append(summary,node('p',plain(p.settings)));cell.append(d);}row.append(cell);}body.append(row);
   }t.append(body);wrap.append(t);if(!rows.length)wrap.append(node('p','当前条件下没有论文。可以取消筛选，或把相关论文加入这个问题。','pc-empty'));
  }
  const picker=node('details',undefined,'pc-column-picker'),pickerTitle=node('summary'),choices=node('div',undefined,'pc-column-choices'),pickerStatus=node('p',undefined,'pc-status');
  function rememberColumns(){localStorage.setItem(columnKey,JSON.stringify(selectedColumns));pickerTitle.textContent='选择对比内容 · '+selectedColumns.length+' 项';table();}
  pickerTitle.textContent='选择对比内容 · '+selectedColumns.length+' 项';picker.append(pickerTitle,node('p','论文列固定保留；其余内容可以自由选择。'));for(const c of columns){const label=node('label'),input=node('input');input.type='checkbox';input.value=c.id;input.checked=selectedColumns.includes(c.id);input.onchange=()=>{if(!input.checked&&selectedColumns.length===1){input.checked=true;pickerStatus.textContent='至少保留一项对比内容。';return;}selectedColumns=input.checked?[...selectedColumns,c.id]:selectedColumns.filter(id=>id!==c.id);pickerStatus.textContent='已记住选择';rememberColumns();};label.append(input,node('span',c.label+(defaults.includes(c.id)?'（默认）':'')));choices.append(label);}picker.append(choices,action('恢复默认四项',()=>{selectedColumns=defaults.slice();for(const input of choices.querySelectorAll('input'))input.checked=defaults.includes(input.value);pickerStatus.textContent='已恢复问题、方法、依据与条件、局限';rememberColumns();}),pickerStatus);host.append(picker);
  q.oninput=()=>{search=q.value;table();};check.onchange=()=>{onlyNotes=check.checked;table();};filter.append(q,l);const reminder=node('div',undefined,'pc-current-problem');reminder.append(node('strong',group.name),node('small',group.en||'英文问题待补充'));host.append(filter,reminder,caption,wrap);table();
  const summary=node('section',undefined,'pc-synthesis');summary.append(node('h3','读完这一组后，写下自己的判断'),node('p','相同结论、方法分歧和研究空白，需要结合原文证据判断。这里不会自动生成论文结论。'));
  if(group.suggested||group.unassigned){summary.append(node('p','先确认这个问题分组，就可以保存自己的对比结论。'));host.append(summary);return;}
  let record=data.syntheses.find(r=>r.id===group.id)||{id:group.id,revision:0};const draftKey='problem-synthesis-draft:'+group.id;let draft;try{draft=JSON.parse(localStorage.getItem(draftKey)||'null');}catch{}const fields={};
  for(const [key,label,hint] of [['consensus','共同发现 / Common findings','哪些结论有多篇论文的证据支持？'],['disagreement','分歧与条件 / Differences and conditions','结论冲突，还是数据、任务、指标不同？'],['gap','研究空白 / Research gap','哪些问题被反复提及，但证据仍不充分？'],['nextStep','我的下一步 / My next step','重要吗？我能验证吗？最小实验是什么？']]){const l=node('label',label),input=node('textarea');input.rows=3;input.maxLength=20000;input.placeholder=hint;input.value=draft?.[key]??record[key]??'';fields[key]=input;l.append(input);summary.append(l);}
  const saveStatus=node('p',draft?'已恢复未保存草稿':'按研究问题独立保存','pc-status'),values=()=>Object.fromEntries(Object.entries(fields).map(([k,input])=>[k,input.value]));for(const input of Object.values(fields))input.oninput=()=>{localStorage.setItem(draftKey,JSON.stringify(values()));saveStatus.textContent='草稿已保存在当前浏览器，点击下方按钮保存到本机';};
  const save=action('保存我的对比结论',async()=>{save.disabled=true;try{record=await api('problem-comparison-synthesis',{...record,...values()});data.syntheses=data.syntheses.filter(r=>r.id!==record.id).concat(record);localStorage.removeItem(draftKey);saveStatus.textContent='已保存到本机';}catch(e){saveStatus.textContent=e.message;}finally{save.disabled=false;}});summary.append(save,saveStatus);host.append(summary);
 }
 draw();
}
