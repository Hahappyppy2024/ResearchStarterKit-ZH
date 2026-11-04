"""Bilingual topic/problem definitions, paper annotations and paper revision quizzes."""
import datetime,json,re,uuid
import study_service as study
RELATIONS={'same-problem','builds-on','improves','extends','uses-component','baseline','compares','complements','applies','supports','challenges','background','surveys','uncertain'}
TRANSLATIONS={'软件工程':'Software Engineering','AIGC':'AI Generated Content','自动驾驶':'Autonomous Driving','多模态':'Multimodal Learning','Agent / LLM':'Agents / Large Language Models','持续维护与评测':'Continuous Maintenance and Evaluation','仓库级 Agent':'Repository-level Agents','代码生成':'Code Generation','程序修复与代码建模':'Program Repair and Code Modeling','统一与音视频生成':'Unified Audio and Video Generation','Transformer 与流':'Transformers and Flows','扩散与潜空间':'Diffusion and Latent Spaces','生成模型基础':'Generative Model Foundations','实时推理':'Real-time Inference','检索与未来表征':'Retrieval and Future Representations','VLA 与世界模型':'Vision-Language-Action and World Models','BEV 与规划':'Bird’s-eye View and Planning','端到端驾驶基础':'End-to-end Driving Foundations','交错推理与决策':'Interleaved Reasoning and Decision Making','全模态模型':'Omni-modal Models','视觉指令学习':'Visual Instruction Learning','视觉语言对齐':'Vision-Language Alignment','Agentic RL 系统':'Agentic Reinforcement Learning Systems','强化学习与对齐':'Reinforcement Learning and Alignment','记忆与自演化':'Memory and Self-evolution','推理与工具':'Reasoning and Tools','语言模型基础':'Language Model Foundations'}
STATUSES={'unverified','author-claim','checked','inference'}
def row(c,kind,ident):return study.row(c,kind,ident)
def put(c,kind,obj):c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',(kind,obj['id'],json.dumps(obj,ensure_ascii=False)))
def row_exists(c,kind,ident):return c.execute('SELECT 1 FROM records WHERE kind=? AND id=?',(kind,ident)).fetchone()

def nodes(c):return study.records(c,'taxonomy')
def taxonomy():
 with study.connection() as c:
  if not c.execute("SELECT 1 FROM records WHERE kind='knowledge-meta' AND id='taxonomy-v1'").fetchone():
   import lineage_service
   # Read seed files directly so the initialization does not nest a database transaction.
   try:topics=json.loads((study.ATLAS/'topics.json').read_text(encoding='utf-8-sig'))
   except (OSError,ValueError):topics=[]
   for t in topics:
    root=dict(id='tax-'+t['id'],kind='topic',name=t['name'],en=t.get('en',''),definition=t.get('description',''),parentId=None,revision=1,lineageId='topic-'+t['id'])
    put(c,'taxonomy',root)
    branches=list(dict.fromkeys(t.get('branches',[])))
    for i,name in enumerate(branches):put(c,'taxonomy',dict(id='tax-'+t['id']+'-'+str(i),kind='topic',name=name,en='',definition='',parentId=root['id'],revision=1))
   put(c,'knowledge-meta',dict(id='taxonomy-v1'))
  if not row_exists(c,'knowledge-meta','taxonomy-bilingual-v2'):
   for n in nodes(c):
    if n['revision']==1 and n['name'] in TRANSLATIONS:n['en']=TRANSLATIONS[n['name']];put(c,'taxonomy',n)
   put(c,'knowledge-meta',dict(id='taxonomy-bilingual-v2'))
  return dict(nodes=nodes(c))
def ancestors(ident,items):
 index={n['id']:n for n in items};result=[];seen=set()
 while ident:
  if ident in seen or ident not in index:raise ValueError('分类层级无效')
  seen.add(ident);n=index[ident];result.insert(0,n);ident=n.get('parentId')
 return result
def save_node(data):
 taxonomy()
 with study.connection() as c:
  items=nodes(c);obj=row(c,'taxonomy',data['id']) if data.get('id') else dict(id=str(uuid.uuid4()),revision=0)
  if data.get('id') and obj['revision']!=data.get('revision'):raise ValueError('定义已更新，请重新打开后编辑')
  kind=data.get('kind',obj.get('kind'))
  if obj.get('kind') and kind!=obj['kind'] and any(n.get('parentId')==obj['id'] for n in items):raise ValueError('有子分类时不能更改 Topic / Problem 类型')
  parent=data.get('parentId') or None
  if kind not in ('topic','problem','solution'):raise ValueError('请选择 Topic、Problem 或 Solution')
  name=study.text(data.get('name',''),160);en=study.text(data.get('en',''),200)
  if not name or not en:raise ValueError('请填写中文名称和英文名称')
  chain=ancestors(parent,items) if parent else []
  if any(n['id']==obj['id'] for n in chain):raise ValueError('分类不能形成循环')
  if any(n['kind']!=kind for n in chain):raise ValueError('Topic、Problem 与 Solution 分别维护层级')
  if len(chain)>=3:raise ValueError('当前支持大类、子类、子子类三级')
  # A move must preserve the depth of every existing descendant as well.
  for n in items:
   path=ancestors(n['id'],items)
   if obj['id'] in [p['id'] for p in path] and len(chain)+len(path)-[p['id'] for p in path].index(obj['id'])>3:raise ValueError('移动后子分类将超过三级')
  if any(n['id']!=obj['id'] and n['kind']==kind and n.get('parentId')==parent and (n['name'].casefold()==name.casefold() or n.get('en','').casefold()==en.casefold()) for n in items):raise ValueError('同一层级已有同名分类，请直接选择或编辑已有定义')
  topic_ids=data.get('topicIds',obj.get('topicIds',[]))
  if not isinstance(topic_ids,list) or len(topic_ids)>50:raise ValueError('最多关联 50 个 Topic')
  index={n['id']:n for n in items}
  if any(not isinstance(i,str) or i not in index or index[i]['kind']!='topic' for i in topic_ids):raise ValueError('关联的 Topic 不存在')
  if kind=='topic' and topic_ids:raise ValueError('Topic 自身的层级请通过父分类设置')
  obj['topicIds']=list(dict.fromkeys(topic_ids))
  obj.update(kind=kind,name=name,en=en,parentId=parent,definition=study.text(data.get('definition','')),revision=obj['revision']+1,updatedAt=study.now())
  put(c,'taxonomy',obj)
  mapid=obj.get('lineageId','taxonomy-'+obj['id']);existing=c.execute("SELECT body FROM records WHERE kind='lineage' AND id=?",(mapid,)).fetchone()
  if existing:
   m=json.loads(existing[0]);m.update(name=name+' · '+en,description=obj['definition'],revision=m['revision']+1);put(c,'lineage',m)
  else:put(c,'lineage',dict(id=mapid,kind=kind,name=name+' · '+en,description=obj['definition'],paperIds=[],paths=[],revision=1,createdAt=study.now()))
  return obj

def get_paper(ident):
 taxonomy()
 with study.connection() as c:
  r=c.execute("SELECT body FROM records WHERE kind='paper-knowledge' AND id=?",(ident,)).fetchone()
  obj=json.loads(r[0]) if r else dict(id=ident,revision=0,topicIds=[],problemIds=[],solutionIds=[],tasks={},ownedMaps=[])
  definitions=json.loads((study.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
  obj['completedCount']=sum(obj.get('tasks',{}).get(t['id'],{}).get('done') is True for t in definitions)
  obj['taskCount']=len(definitions);obj['completed']=obj['completedCount']==len(definitions)
  if not obj['completed']:obj.pop('readDate',None)
  return obj
def save_paper(data):
 pid=study.text(data.get('paperId',''),200);paper=study.resolve('paper',pid);taxonomy()
 with study.connection() as c:
  r=c.execute("SELECT body FROM records WHERE kind='paper-knowledge' AND id=?",(pid,)).fetchone()
  old=json.loads(r[0]) if r else dict(id=pid,revision=0,ownedMaps=[])
  if data.get('revision',0)!=old['revision']:raise ValueError('这篇论文已在另一窗口更新。草稿仍在当前浏览器，请刷新后核对。')
  allnodes=nodes(c);index={n['id']:n for n in allnodes};obj={**old};selected=[]
  for key,kind in [('topicIds','topic'),('problemIds','problem'),('solutionIds','solution')]:
   ids=data.get(key,old.get(key,[]))
   if not isinstance(ids,list) or len(ids)>50:raise ValueError('每篇最多选择 50 个分类')
   obj[key]=list(dict.fromkeys(ids))
   for ident in obj[key]:
    if ident not in index or index[ident]['kind']!=kind:raise ValueError('选择的分类不存在')
    selected.extend(ancestors(ident,allnodes))
  tasks=data.get('tasks',old.get('tasks',{}))
  if not isinstance(tasks,dict):raise ValueError('阅读任务格式无效')
  definitions=json.loads((study.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
  clean={}
  # Removed checklist items remain stored as annotations, especially paper relations.
  for task in definitions+[dict(id=ident) for ident in ('connections','focus','taxonomy') if not any(t['id']==ident for t in definitions)]:
   value=tasks.get(task['id'],old.get('tasks',{}).get(task['id'],{}));entry=dict(done=value.get('done') is True,answer=study.text(value.get('answer',''),20000))
   if entry['done']:
    previous=old.get('tasks',{}).get(task['id'],{})
    entry['completedDate']=previous.get('completedDate',study.today()) if previous.get('done') else study.today()
   if task['id'] in ('methodology','datasets'):
    key='figureIds' if task['id']=='methodology' else 'datasetIds';ids=value.get(key,[])
    if not isinstance(ids,list) or len(ids)>(12 if key=='figureIds' else 100):raise ValueError('关联图片或数据集数量无效')
    for ident in ids:
     linked=row(c,'paper-figure' if key=='figureIds' else 'dataset',ident)
     if key=='figureIds' and linked['paperId']!=pid:raise ValueError('不能使用其他论文的上传图片')
     if key=='datasetIds':
      for source in linked.get('sourcePaperIds',[]):study.queue_paper(c,study.resolve('paper',source),reason='数据集来源论文：'+linked['name'])
    entry[key]=list(dict.fromkeys(ids))
   if task['id']=='categories':entry['tags']=[study.text(t,80) for t in value.get('tags',[]) if isinstance(t,str)][:100]
   if task['id'] in ('extensions','reading-questions','flashcards'):
    items=value.get('items',[])
    if not isinstance(items,list) or len(items)>100:raise ValueError('每个清单最多 100 条问题')
    entry['items']=[];seen=set()
    for item in items:
     ident=study.text(item.get('id',''),80)
     if not re.fullmatch(r'item-[a-zA-Z0-9-]{1,70}',ident):raise ValueError('问题编号无效')
     if ident in seen:continue
     seen.add(ident);part=dict(id=ident,question=study.text(item.get('question',''),10000))
     if task['id'] in ('reading-questions','flashcards'):part['answer']=study.text(item.get('answer',''),20000)
     entry['items'].append(part)
   if task['id']=='compare':
    ids=value.get('comparisonPaperIds',[])
    if not isinstance(ids,list) or len(ids)>10 or any(not isinstance(i,str) for i in ids):raise ValueError('对比论文最多 10 篇')
    previous=old.get('tasks',{}).get('compare',{}).get('comparisonPaperIds',[])
    for ident in ids:
     if ident==pid:raise ValueError('请选择另一篇已读论文进行对比')
     study.resolve('paper',ident)
     if ident not in previous:
      target=row(c,'paper-knowledge',ident)
      if not target.get('readDate') or not all(target.get('tasks',{}).get(t['id'],{}).get('done') is True for t in definitions):raise ValueError('对比论文必须来自已完成阅读任务的论文')
    entry['comparisonPaperIds']=list(dict.fromkeys(ids))
   if task['id']=='next-step':
    problems=value.get('problems',[])
    if not isinstance(problems,list) or len(problems)>50:raise ValueError('每篇最多添加 50 个新问题')
    entry['problems']=[];seen=set()
    for problem in problems:
     ident=problem.get('id');n=index.get(ident)
     if not n or n['kind']!='problem':raise ValueError('新问题需关联已有或新建的 Problem 定义')
     words=problem.get('keywords',[])
     if not isinstance(words,list) or len(words)>50:raise ValueError('每个问题最多 50 个关键词')
     if ident not in seen:entry['problems'].append(dict(id=ident,name=n['name'],en=n.get('en',''),keywords=list(dict.fromkeys(study.text(w,160) for w in words if study.text(w,160)))));seen.add(ident)
   if task['id']=='connections':
    refs=value.get('references',[])
    if not isinstance(refs,list) or len(refs)>200:raise ValueError('关联论文最多 200 条')
    entry['references']=[]
    for ref in refs:
     target=study.text(ref.get('paperId',''),200)
     if target==pid:raise ValueError('不能把论文关联到自身')
     if target:study.queue_paper(c,study.resolve('paper',target),reason='相关论文：'+paper['title'][:500])
     types=ref.get('relationTypes',[])
     if not isinstance(types,list) or any(t not in RELATIONS for t in types):raise ValueError('论文关系类型无效')
     entry['references'].append(dict(id=study.text(ref.get('id',''),100),paperId=target,paper=study.text(ref.get('paper',''),1000),relation=study.text(ref.get('relation',''),10000),relationTypes=list(dict.fromkeys(types)),evidenceStatus=ref.get('evidenceStatus') if ref.get('evidenceStatus') in STATUSES else 'unverified',evidence=study.text(ref.get('evidence',''),10000)))
   clean[task['id']]=entry
  import paper_flashcards
  extra=[]
  for key,prompt in [('topicIds','论文属于哪些 Topic？'),('problemIds','研究问题属于哪些 Problem？'),('solutionIds','方法属于哪些 Solution？')]:
   names=[index[i]['name']+(' / '+index[i].get('en','') if index[i].get('en') else '') for i in obj[key]]
   if names:extra.append(dict(source='classification:'+key,question=prompt,answer='；'.join(names)))
  for ref in clean.get('connections',{}).get('references',[]):
   if not ref.get('paper') or not ref.get('relationTypes'):continue
   labels='；'.join({'same-problem':'研究同一问题','builds-on':'继承其方法','improves':'改进其方法或局限','extends':'扩展其能力或场景','uses-component':'使用其模型或组件','baseline':'作为对照基线','compares':'进行实验对比','complements':'方法互补','applies':'迁移到新任务','supports':'支持其结论','challenges':'质疑或提出反例','background':'背景或概念来源','surveys':'综述其工作','uncertain':'关系待判断'}[t] for t in ref['relationTypes'])
   status={'unverified':'待核实','author-claim':'作者陈述','checked':'已核对','inference':'我的推断'}[ref['evidenceStatus']]
   extra.append(dict(source='relation:'+ref['id'],question='本文与《'+ref['paper']+'》有什么关系？',answer=labels+'（'+status+'）'+('。依据：'+ref['evidence'] if ref.get('evidence') else '；未填写关系依据')))
  for dataset_id in clean.get('datasets',{}).get('datasetIds',[]):
   dataset=row(c,'dataset',dataset_id)
   extra.append(dict(source='dataset-name:'+dataset_id,question='论文使用了什么数据集？',answer=dataset['name']+(' / '+dataset.get('en','') if dataset.get('en') else '')))
   names=[study.resolve('paper',i)['title'] for i in dataset.get('sourcePaperIds',[])]
   if names:extra.append(dict(source='dataset:'+dataset_id,question='数据集“'+dataset['name']+'”来自哪篇论文？',answer='；'.join(names)))
  obj.update(paper_flashcards.sync(pid,clean,old,definitions,extra));obj['autoFlashcardVersion']=1
  obj.update(tasks=clean,title=paper['title'],revision=old['revision']+1,updatedAt=study.now())
  if clean.get('methodology',{}).get('done') and not old.get('tasks',{}).get('methodology',{}).get('done') and not obj.get('startedDate'):
   obj['startedDate']=study.today()
  complete=all(clean[t['id']]['done'] for t in definitions)
  if complete and not obj.get('readDate'):
   read_date=study.valid_date(data.get('readDate') or study.today())
   if read_date>study.today():raise ValueError('已读日期不能晚于今天')
   obj['readDate']=read_date
  if not complete:obj.pop('readDate',None)
  obj['completed']=complete
  if complete and not old.get('readDate'):
   put(c,'reading-log',dict(id=pid+':'+obj['readDate'],paperId=pid,date=obj['readDate'],createdAt=study.now()))
  wanted={n.get('lineageId','taxonomy-'+n['id']):n for n in selected};owned=set(old.get('ownedMaps',[]))
  for mapid in owned-set(wanted):
   m=row(c,'lineage',mapid);m['paperIds']=[i for i in m['paperIds'] if i!=pid];m['paths']=[{**p,'ids':[i for i in p['ids'] if i!=pid]} for p in m['paths'] if any(i!=pid for i in p['ids'])];m['revision']+=1;put(c,'lineage',m)
  newowned=owned&set(wanted)
  for mapid,n in wanted.items():
   r=c.execute("SELECT body FROM records WHERE kind='lineage' AND id=?",(mapid,)).fetchone()
   m=json.loads(r[0]) if r else dict(id=mapid,kind=n['kind'],name=n['name']+(' · '+n['en'] if n.get('en') else ''),description=n.get('definition',''),paperIds=[],paths=[],revision=0,createdAt=study.now())
   if pid not in m['paperIds']:m['paperIds'].append(pid);newowned.add(mapid);m['revision']+=1;put(c,'lineage',m)
  obj['ownedMaps']=sorted(newowned);put(c,'paper-knowledge',obj);return obj
def edges(paperids):
 with study.connection() as c:
  result=[]
  for obj in study.records(c,'paper-knowledge'):
   for ref in obj.get('tasks',{}).get('connections',{}).get('references',[]):
    if ref.get('paperId') and (not paperids or obj['id'] in paperids or ref['paperId'] in paperids):result.append(dict(source=obj['id'],sourceTitle=obj['title'],target=ref['paperId'],targetTitle=ref['paper'],types=ref['relationTypes'],evidence=ref['evidence'],status=ref['evidenceStatus']))
  return result
def week(date):
 d=datetime.date.fromisoformat(study.valid_date(date));return (d-datetime.timedelta(days=d.weekday())).isoformat()
def paper_week(date=None):
 date=date or study.today();monday=week(date);end=(datetime.date.fromisoformat(monday)+datetime.timedelta(days=6)).isoformat()
 definitions=json.loads((study.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
 with study.connection() as c:
  for obj in study.records(c,'paper-knowledge'):
   if not obj.get('readDate'):continue
   for task in definitions:
    answer=obj.get('tasks',{}).get(task['id'],{})
    eligible=max(obj['readDate'],answer.get('completedDate',obj['readDate']))
    if not answer.get('done') or not answer.get('answer') or not monday<=eligible<=min(date,end):continue
    ident=obj['id']+':'+task['id'];key=monday+':'+ident
    r=c.execute("SELECT body FROM records WHERE kind='paper-quiz-snapshot' AND id=?",(key,)).fetchone()
    old=json.loads(r[0]) if r else {}
    if not old.get('paperId'):put(c,'paper-quiz-snapshot',dict(id=key,cardId=ident,paperId=obj['id'],title=obj['title'],week=monday,eligibleDate=eligible,question=old.get('question',task['title']),reference=old.get('reference',answer['answer'])))
  cards=[]
  for ref in study.records(c,'paper-quiz-snapshot'):
   if ref.get('week')!=monday or ref.get('eligibleDate','9999')>date:continue
   r=c.execute("SELECT body FROM records WHERE kind='paper-quiz' AND id=?",(ref['id'],)).fetchone();attempt=json.loads(r[0]) if r else {}
   cards.append(dict(id=ref['cardId'],paperId=ref['paperId'],title=ref['title'],question=ref['question'],reference=ref['reference'],revision=attempt.get('revision',0),studentAnswer=attempt.get('studentAnswer',''),verdict=attempt.get('verdict','unanswered')))
  return dict(week=monday,end=end,cards=cards,papers=len({c['paperId'] for c in cards}))

def paper_attempt(data):
 monday=week(data.get('date',study.today()));ident=study.text(data.get('id',''),300);answer=study.text(data.get('studentAnswer',''),30000)
 if not answer:raise ValueError('请先填写自己的答案')
 if data.get('verdict') not in ('submitted','known','review'):raise ValueError('请选择对照笔记或自评结果')
 if not any(c['id']==ident for c in paper_week(data.get('date',study.today()))['cards']):raise ValueError('题目不在本周阅读复习范围')
 with study.connection() as c:
  key=monday+':'+ident;r=c.execute("SELECT body FROM records WHERE kind='paper-quiz' AND id=?",(key,)).fetchone();old=json.loads(r[0]) if r else dict(revision=0)
  if old['revision']!=data.get('revision',0):raise ValueError('作答记录已更新，请刷新')
  obj=dict(id=key,studentAnswer=answer,verdict=data['verdict'],revision=old['revision']+1,updatedAt=study.now());put(c,'paper-quiz',obj);return obj
