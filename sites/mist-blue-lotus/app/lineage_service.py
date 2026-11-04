"""Independent topic/problem paper lineages, using the local study database."""
import json,uuid
import study_service as study

def all_maps():
 import knowledge_service
 definitions=knowledge_service.taxonomy()['nodes']
 with study.connection() as c:
  if not c.execute("SELECT 1 FROM records WHERE kind='lineage-meta' AND id='seed-v1'").fetchone():
   try:topics=json.loads((study.ATLAS/'topics.json').read_text(encoding='utf-8-sig'))
   except (OSError,ValueError):topics=[]
   papers=study.atlas_papers()
   for t in topics:
    ids=[p['id'] for p in papers if p.get('topics',[None])[0]==t['id']]
    paths=[dict(id=str(uuid.uuid4()),name=p['name'],ids=['atlas-'+i for i in p['ids'] if 'atlas-'+i in ids],relation='阅读顺序',evidence='原有 Paper Atlas 的编辑阅读路径；不是已核实的引用关系。') for p in t.get('paths',[])]
    obj=dict(id='topic-'+t['id'],kind='topic',name=t['name'],description=t.get('description',''),paperIds=ids,paths=paths,revision=1,createdAt=study.now(),updatedAt=study.now())
    c.execute('INSERT OR IGNORE INTO records VALUES(?,?,?,0)',('lineage',obj['id'],json.dumps(obj,ensure_ascii=False)))
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage-meta','seed-v1','{}'))
  if not c.execute("SELECT 1 FROM records WHERE kind='lineage-meta' AND id='original-catalog-v2'").fetchone():
   authoritative=study.atlas_papers()
   for obj in study.records(c,'lineage'):
    if obj['id'].startswith('topic-') and obj['revision']==1:
     topic=obj['id'][6:];ids=[p['id'] for p in authoritative if p.get('topics',[None])[0]==topic]
     obj['paperIds']=list(dict.fromkeys(obj['paperIds']+ids))
     c.execute("UPDATE records SET body=? WHERE kind='lineage' AND id=?",(json.dumps(obj,ensure_ascii=False),obj['id']))
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage-meta','original-catalog-v2','{}'))
  repair_initial_membership(c)
  # Every saved classification has its own persistent, independently addressable map.
  for n in definitions:
   ident=n.get('lineageId') or 'taxonomy-'+n['id']
   obj=dict(id=ident,kind=n['kind'],name=n['name']+(' · '+n['en'] if n.get('en') else ''),description=n.get('definition',''),paperIds=[],paths=[],revision=1,createdAt=study.now(),updatedAt=study.now())
   c.execute('INSERT OR IGNORE INTO records VALUES(?,?,?,0)',('lineage',ident,json.dumps(obj,ensure_ascii=False)))
  # Bring existing problem cards into their own maps once; never overwrite edits.
  for old in study.records(c,'problem'):
   obj=dict(id='problem-'+old['id'],kind='problem',name=old['name'],description=old.get('question') or old.get('gap',''),paperIds=old.get('paperIds',[]),paths=[],revision=1,createdAt=study.now(),updatedAt=study.now())
   c.execute('INSERT OR IGNORE INTO records VALUES(?,?,?,0)',('lineage',obj['id'],json.dumps(obj,ensure_ascii=False)))
  items=study.records(c,'lineage')[::-1];archived=study.records(c,'lineage',True)
  for obj in items+archived:obj['paperIds']=list(dict.fromkeys(obj['paperIds']))
  unique={pid for obj in items for pid in obj['paperIds']};known={p['id']:p.get('year',0) for p in study.atlas_papers()}
  import local_app
  with local_app.db() as library:
   for pid in unique:
    found=library.execute('SELECT year FROM papers WHERE id=?',(pid,)).fetchone()
    if found and found[0]:known[pid]=found[0]
  years=[int(known[pid]) for pid in unique if known.get(pid)]
  return dict(items=items,archived=archived,stats=dict(papers=len(unique),topics=sum(p['kind']=='topic' for p in items),problems=sum(p['kind']=='problem' for p in items),years=max(years)-min(years)+1 if years else 0))

def detail(ident):
 all_maps()
 with study.connection() as c:obj=study.row(c,'lineage',ident)
 obj['paperIds']=list(dict.fromkeys(obj['paperIds']))
 atlas={p['id']:p for p in study.atlas_papers()};papers=[]
 import local_app
 with local_app.db() as c:
  for pid in obj['paperIds']:
   r=c.execute('SELECT body FROM papers WHERE id=?',(pid,)).fetchone()
   papers.append({**atlas.get(pid,{}),**json.loads(r[0])} if r else atlas.get(pid,dict(id=pid,title='题录暂不可用：'+pid,year=0)))
 import knowledge_service
 import paper_classification
 return dict(map=obj,papers=paper_classification.decorate(papers),edges=knowledge_service.edges(obj["paperIds"]))

def save(data):
 with study.connection() as c:
  obj=study.row(c,'lineage',data['id']) if data.get('id') else dict(id=str(uuid.uuid4()),createdAt=study.now(),revision=0,paperIds=[],paths=[])
  if data.get('id') and data.get('revision')!=obj['revision']:raise ValueError('图谱已更新，请重新打开后再保存；你的草稿仍保留。')
  obj['kind']=data.get('kind',obj.get('kind'))
  if obj['kind'] not in ('topic','problem','solution'):raise ValueError('请选择主题或问题')
  obj['name']=study.text(data.get('name',obj.get('name','')),160)
  if not obj['name']:raise ValueError('请填写主题或问题名称')
  obj['description']=study.text(data.get('description',obj.get('description','')))
  ids=data.get('paperIds',obj['paperIds'])
  if not isinstance(ids,list) or len(ids)>10000 or any(not isinstance(i,str) or not i or len(i)>200 for i in ids):raise ValueError('每张图谱最多收录 10000 篇论文')
  obj['paperIds']=list(dict.fromkeys(ids));paths=data.get('paths',obj['paths'])
  if not isinstance(paths,list) or len(paths)>60:raise ValueError('每张图谱最多 60 条路径')
  clean=[]
  for p in paths:
   nodes=p.get('ids',[])
   if not isinstance(nodes,list) or not 1<=len(nodes)<=30 or any(i not in obj['paperIds'] for i in nodes):raise ValueError('路径需包含 1–30 篇本图谱中的论文；先调整路径，再移除论文')
   clean.append(dict(id=p.get('id') or str(uuid.uuid4()),name=study.text(p.get('name','阅读路径'),160),ids=nodes,relation=study.text(p.get('relation','阅读顺序'),160),evidence=study.text(p.get('evidence',''),10000)))
  obj.update(paths=clean,revision=obj['revision']+1,updatedAt=study.now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',('lineage',obj['id'],json.dumps(obj,ensure_ascii=False)))
 return obj

def archive(data):
 import taxonomy_lifecycle
 with study.connection() as c:
  matched=next((n for n in study.records(c,'taxonomy')+study.records(c,'taxonomy',True) if (n.get('lineageId') or 'taxonomy-'+n['id'])==data.get('id')),None)
 if matched:return taxonomy_lifecycle.archive(dict(id=matched['id'],restore=data.get('restore') is True))
 with study.connection() as c:
  study.row(c,'lineage',data.get('id'))
  c.execute("UPDATE records SET archived=? WHERE kind='lineage' AND id=?",(0 if data.get('restore') else 1,data['id']))
 return dict(saved=True)

def read_library(data):
 """Resolve explicit browser read marks without marking or importing any papers."""
 ids=data.get('ids',[])
 if not isinstance(ids,list) or len(ids)>10000 or any(not isinstance(i,str) or not i or len(i)>200 for i in ids):raise ValueError('已读论文列表无效')
 import local_app
 atlas={p['id']:p for p in study.atlas_papers()};papers=[];missing=[]
 from reading_journal import complete
 with study.connection() as c:knowledge=study.records(c,'paper-knowledge')
 complete_records=[p for p in knowledge if complete(p) and p.get('readDate')]
 def organized(p):
  if any(p.get(k) for k in ('topicIds','problemIds','solutionIds')):return True
  return any(ref.get('relationTypes') for ref in p.get('tasks',{}).get('related',{}).get('references',[]))
 ids=[p['id'] for p in complete_records if organized(p)]
 with local_app.db() as c:
  for ident in dict.fromkeys(ids):
   found=c.execute('SELECT body FROM papers WHERE id=?',(ident,)).fetchone()
   p={**atlas.get(ident,{}),**json.loads(found[0])} if found else atlas.get(ident)
   if p:papers.append(p)
   else:missing.append(ident)
 return dict(papers=papers,missing=missing)

def repair_initial_membership(c):
 """Recover only papers omitted by the old last-source-wins import, preserving user edits."""
 marker='initial-membership-v3'
 if c.execute("SELECT 1 FROM records WHERE kind='lineage-meta' AND id=?",(marker,)).fetchone():return
 legacy={}
 for filename in ('papers.json','foundations.json','frontier.json'):
  try:items=json.loads((study.ATLAS/filename).read_text(encoding='utf-8-sig'))
  except (OSError,ValueError):continue
  if isinstance(items,list):
   for paper in items:
    if paper.get('id'):legacy['atlas-'+paper['id']]=paper
 try:topics=json.loads((study.ATLAS/'topics.json').read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):topics=[]
 definitions={t['id']:t for t in topics};authoritative=study.atlas_papers();before=[]
 for obj in study.records(c,'lineage'):
  if not obj['id'].startswith('topic-'):continue
  topic=obj['id'][6:]
  # These IDs never belonged to the initial broken seed; do not restore other removed papers.
  missing=[p['id'] for p in authoritative if p.get('topics',[None])[0]==topic and legacy.get(p['id'],{}).get('topic')!=topic and p['id'] not in obj['paperIds']]
  if not missing:continue
  before.append(json.loads(json.dumps(obj)))
  obj['paperIds']=list(dict.fromkeys(obj['paperIds']+missing))
  for path in obj['paths']:
   original=next((p for p in definitions.get(topic,{}).get('paths',[]) if p['name']==path['name']),None)
   if original and path.get('relation')=='阅读顺序' and path.get('evidence')=='原有 Paper Atlas 的编辑阅读路径；不是已核实的引用关系。':
    full=['atlas-'+pid for pid in original['ids']]
    broken=[pid for pid in full if legacy.get(pid,{}).get('topic')==topic]
    if path['ids']==broken and all(pid in obj['paperIds'] for pid in full):path['ids']=full
  obj.update(revision=obj['revision']+1,updatedAt=study.now())
  c.execute("UPDATE records SET body=? WHERE kind='lineage' AND id=?",(json.dumps(obj,ensure_ascii=False),obj['id']))
 c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage-meta',marker,json.dumps(dict(before=before),ensure_ascii=False)))
