"""Project-to-paper roles backed by the common catalog and required-reading queue."""
import contextlib,json
import projects_service as projects,study_service as study,local_app

RELATIONS=[
 ('same-problem','研究同一问题','Same research problem','研究问题','与项目研究相同或相近的问题。'),
 ('background','背景与综述','Background / survey','研究问题','了解研究背景、已有工作和研究空白。'),
 ('theory','理论依据','Theoretical foundation','研究问题','为项目的假设、公式或机制提供依据。'),
 ('foundation','项目基础论文','Foundation paper','方法与实现','项目直接基于这篇论文开展。'),
 ('reproduce','复现对象','Reproduction target','方法与实现','项目计划复现这篇论文的代码或实验。'),
 ('improve','改进对象','Method to improve','方法与实现','项目要解决这篇论文方法的局限。'),
 ('module','方法／模型／模块来源','Method / model / component','方法与实现','项目借鉴或使用它的方法、模型或组件。'),
 ('transfer','迁移到项目场景','Transfer to project setting','方法与实现','把它的方法迁移到项目的新任务或场景。'),
 ('baseline','对照基线','Experimental baseline','实验与评估','作为项目实验中的比较基线。'),
 ('dataset','数据集来源','Dataset source','实验与评估','提供项目使用的数据集或数据采集方法。'),
 ('evaluation','评估方法／指标','Evaluation / metrics','实验与评估','提供项目的评价指标、协议或测试方法。'),
 ('scenario','相关应用场景','Related application','证据与启发','帮助理解实际场景、需求或约束。'),
 ('support','支持项目假设','Supporting evidence','证据与启发','提供支持项目想法的证据。'),
 ('challenge','相反证据／失败案例','Counterevidence / failure cases','证据与启发','提供反例、相反结论或失败条件。'),
 ('complement','互补方法／新思路','Complementary ideas','证据与启发','提供可结合的方法或下一步思路。'),
 ('uncertain','关系待判断','To be determined','证据与启发','尚未确定它对项目的具体作用。')]

def relation_options():return [dict(id=i,name=n,en=e,group=g,description=d) for i,n,e,g,d in RELATIONS]
def project(ident):
 with projects.connection() as c:
  p=projects.get_row(c,'projects',ident)
  if c.execute('SELECT archived FROM projects WHERE id=?',(ident,)).fetchone()[0]:raise ValueError('项目已归档，请先恢复项目')
 return p
def clean_relations(values):
 if not isinstance(values,list) or not values or any(v not in {r[0] for r in RELATIONS} for v in values):raise ValueError('请至少选择一种有效的项目关系')
 if 'uncertain' in values and len(set(values))>1:raise ValueError('“关系待判断”请单独选择')
 return list(dict.fromkeys(values))
def listing(project_id):
 # Archived projects remain readable.
 with projects.connection() as c:projects.get_row(c,'projects',project_id)
 with study.connection() as c:items=[x for x in study.records(c,'project-paper') if x['projectId']==project_id]
 for item in items:
  item['paper']=study.resolve('paper',item['paperId'])
 return dict(items=items,relations=relation_options())
def save(data):
 p=project(data.get('projectId'));relations=clean_relations(data.get('relationTypes'))
 reused=False
 if data.get('paperId'):paper=study.resolve('paper',data['paperId']);reused=True
 else:
  fields=data.get('paper')
  if not isinstance(fields,dict):raise ValueError('请新增或选择一篇论文')
  title=study.text(fields.get('title',''),500)
  if not title:raise ValueError('请填写论文标题')
  # Reuse exact-title matches without overwriting their authors, notes or progress.
  with contextlib.closing(local_app.db()) as c:r=c.execute('SELECT body FROM papers WHERE trim(title)=? COLLATE NOCASE ORDER BY rowid LIMIT 1',(title,)).fetchone()
  paper=json.loads(r[0]) if r else study.save_paper({k:fields[k] for k in ('title','authors','source','pdf','summary','year','venue','publicationType') if k in fields});reused=bool(r)
 key=p['id']+':'+paper['id']
 with study.connection() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute("SELECT body FROM records WHERE kind='project-paper' AND id=?",(key,)).fetchone();old=json.loads(r[0]) if r else {}
  if 'revision' in data and data['revision']!=old.get('revision',0):raise ValueError('项目关系已在其他窗口更新，请刷新后再保存')
  if old and 'revision' not in data:
   combined=[v for v in old['relationTypes'] if v!='uncertain']+[v for v in relations if v!='uncertain'];relations=list(dict.fromkeys(combined)) or ['uncertain']
  obj=dict(id=key,projectId=p['id'],projectName=p['name'],paperId=paper['id'],relationTypes=relations,revision=old.get('revision',0)+1,createdAt=old.get('createdAt',study.now()),updatedAt=study.now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',('project-paper',key,json.dumps(obj,ensure_ascii=False)))
  queued=study.queue_paper(c,paper,reason='项目关联论文：'+p['name'])
  queued['projectIds']=list(dict.fromkeys(queued.get('projectIds',[])+[p['id']]))
  labels={r[0]:r[1] for r in RELATIONS}
  queued.setdefault('projectRelations',{})[p['id']]=dict(name=p['name'],labels=[labels[r] for r in relations])
  c.execute('UPDATE queue SET body=? WHERE date=? AND paper_id=?',(json.dumps(queued,ensure_ascii=False),queued['date'],paper['id']))
 return dict(link=obj,paper=paper,reused=reused,queuedDate=queued['date'])
