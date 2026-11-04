"""Local courses, problem-led reading, comparison sheets and intentional reading queue."""
import contextlib,datetime as dt,json,pathlib,re,sqlite3,uuid
ROOT=pathlib.Path(__file__).resolve().parent;DB=ROOT/'local-data'/'study-workspace.sqlite'
ATLAS=ROOT/'local-data'/'atlas'
COURSE_TYPES=('foundation','research','self')
INNOVATION_TASK_IDS=('foundations','problem','related','data','method','baseline','ablation','analysis','writing')

def innovation_projects(value):
 if not isinstance(value,list) or len(value)>30:raise ValueError('创新点列表格式无效')
 result=[];seen=set()
 for project in value:
  if not isinstance(project,dict):raise ValueError('创新点格式无效')
  ident=text(project.get('id',''),100)
  if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',ident) or ident in seen:raise ValueError('创新点编号无效或重复')
  seen.add(ident)
  if project.get('tier') not in ('q1','q2'):raise ValueError('请选择一区或二区目标')
  title=text(project.get('title',''),3000)
  if not title:raise ValueError('请填写创新点')
  tasks=project.get('tasks',{})
  if not isinstance(tasks,dict) or set(tasks)-set(INNOVATION_TASK_IDS):raise ValueError('创新任务类型无效')
  cleaned={}
  for key in INNOVATION_TASK_IDS:
   task=tasks.get(key,{})
   if not isinstance(task,dict) or task.get('status','todo') not in ('todo','doing','done'):raise ValueError('任务进度无效')
   cleaned[key]={'status':task.get('status','todo'),'notes':text(task.get('notes',''),15000)}
   if 'guide' in task:cleaned[key]['guide']=text(task['guide'],30000)
  result.append(dict(id=ident,tier=project['tier'],title=title,tasks=cleaned))
 return result
def today():return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def text(value,limit=30000):
 if not isinstance(value,str) or len(value)>limit:raise ValueError('字段内容无效或过长')
 return value.strip()
def valid_date(value):
 try:d=dt.date.fromisoformat(value)
 except (ValueError,TypeError):raise ValueError('日期无效')
 if d.isoformat()!=value:raise ValueError('日期格式无效')
 return value
def url(value):
 value=text(value,3000)
 if value and not re.match(r'^https?://[^\s]+$',value):raise ValueError('链接需以 http:// 或 https:// 开头')
 return value
@contextlib.contextmanager
def connection():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with contextlib.closing(sqlite3.connect(DB,timeout=30)) as c,c:
  c.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,body TEXT,archived INTEGER DEFAULT 0,PRIMARY KEY(kind,id))')
  c.execute('CREATE TABLE IF NOT EXISTS links(id TEXT PRIMARY KEY,course_id TEXT,resource_key TEXT,body TEXT,archived INTEGER DEFAULT 0)')
  c.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_course_resource ON links(course_id,resource_key) WHERE archived=0')
  c.execute('CREATE TABLE IF NOT EXISTS queue(date TEXT,paper_id TEXT,body TEXT,archived INTEGER DEFAULT 0,PRIMARY KEY(date,paper_id))')
  yield c
def record_body(kind,body):
 obj=json.loads(body)
 if kind=='course':obj.setdefault('courseType','research')
 return obj

def row(c,kind,ident):
 r=c.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,ident)).fetchone()
 if not r:raise ValueError('记录不存在')
 return record_body(kind,r[0])
def records(c,kind,archived=False):return [record_body(kind,r[0]) for r in c.execute('SELECT body FROM records WHERE kind=? AND archived=? ORDER BY rowid DESC',(kind,int(archived)))]

def course_materials(ident):
 with connection() as c:row(c,'course',ident)
 manifest=ROOT/'local-data'/'course-materials'/'source-manifest.json'
 if not manifest.is_file():return {'items':[]}
 items=json.loads(manifest.read_text(encoding='utf-8'))
 return {'items':[{'sourceNumber':m['sourceNumber'],'duplicateOf':m.get('exactDuplicateOf')} for m in items if m.get('courseId')==ident]}

def course_bibliography(ident):
 with connection() as c:row(c,'course',ident)
 path=ROOT/'local-data'/'course-materials'/'model-paper-catalog.json'
 if not path.is_file():return {'items':[],'note':'模型来源论文待整理'}
 catalog=json.loads(path.read_text(encoding='utf-8'))
 return catalog.get('courses',{}).get(ident,{'items':[],'note':'模型来源论文待整理'})

def course_poster(ident,number):
 allowed={m['sourceNumber'] for m in course_materials(ident)['items']}
 try:number=int(number)
 except (ValueError,TypeError):raise ValueError('材料编号无效')
 if number not in allowed:raise ValueError('课程材料不存在')
 base=(ROOT/'local-data'/'course-materials').resolve()
 manifest=json.loads((base/'source-manifest.json').read_text(encoding='utf-8'))
 item=next(m for m in manifest if m['sourceNumber']==number)
 target=(base/item['storedPath']).resolve()
 if not target.is_relative_to(base) or target.suffix.lower()!='.jpg' or not target.is_file():raise ValueError('课程材料路径无效')
 return target.read_bytes()
def state(date=None):
 date=valid_date(date or today())
 with connection() as c:
  return dict(courseCategories=records(c,'course-category'),courses=records(c,'course'),archivedCourses=records(c,'course',True),problems=records(c,'problem'),comparisons=records(c,'comparison'),archivedProblems=records(c,'problem',True),archivedComparisons=records(c,'comparison',True),links=[json.loads(r[0]) for r in c.execute('SELECT body FROM links WHERE archived=0 ORDER BY rowid')],queue=reading_queue(c,date),date=date)

def save_course_category(data):
 course_type=data.get('courseType')
 if course_type not in COURSE_TYPES:raise ValueError('请选择基础课程、科研课程或自研课程')
 name=text(data.get('name',''),100);parent=text(data.get('parent',''),100)
 if not name:raise ValueError('请填写分类名称')
 with connection() as c:
  categories=records(c,'course-category')
  if parent:
   roots={v['name'] for v in categories if v['courseType']==course_type and not v.get('parent')}
   roots.update(v.get('category') or '未分类' for v in records(c,'course') if v.get('courseType','research')==course_type)
   if course_type=='foundation':roots.update(('AI 模块','Agent','LLM'))
   if parent not in roots:raise ValueError('请先创建所属分类')
  for value in categories:
   if value['courseType']==course_type and value.get('parent','')==parent and value['name'].casefold()==name.casefold():return value
  obj=dict(id=str(uuid.uuid4()),courseType=course_type,name=name,parent=parent,createdAt=now())
  c.execute('INSERT INTO records VALUES(?,?,?,0)',('course-category',obj['id'],json.dumps(obj,ensure_ascii=False)))
  return obj

def save_record(kind,data):
 if kind not in ('course','problem','comparison'):raise ValueError('记录类型无效')
 fields={'course':['name','audience','goal','prerequisites','assessment','design','category','innovationQ1','innovationQ2','innovationNotes','materialFolder','outlineStatus','subcategory','sourceVariant'],'problem':['name','broad','narrow','question','known','gap','hypothesis','evidence','next'],'comparison':['name','question','conditions','conclusion','next']}
 with connection() as c:
  obj=row(c,kind,data['id']) if data.get('id') else dict(id=str(uuid.uuid4()),createdAt=now(),revision=0)
  if data.get('id') and data.get('revision')!=obj.get('revision',0):raise ValueError('记录已更新，请刷新后再编辑，保留你的草稿')
  for field in fields[kind]:
   if field in data:obj[field]=text(data[field],160 if field=='name' else 30000)
  if not obj.get('name'):raise ValueError('请填写名称')
  if kind=='course':
   course_type=data.get('courseType',obj.get('courseType','research'))
   if course_type not in COURSE_TYPES:raise ValueError('请选择基础课程、科研课程或自研课程')
   obj['courseType']=course_type
   if 'sourceTitles' in data:
    titles=data['sourceTitles']
    if not isinstance(titles,list) or len(titles)>20:raise ValueError('原图标题格式无效')
    obj['sourceTitles']=list(dict.fromkeys(text(title,2000) for title in titles))
   if 'innovationProjects' in data:obj['innovationProjects']=innovation_projects(data['innovationProjects'])
   units=data.get('units',obj.get('units',['基础知识','论文阅读','课程设计']))
   if not isinstance(units,list) or not units or len(units)>30:raise ValueError('请设置 1–30 个课程章节')
   obj['units']=list(dict.fromkeys(text(v,100) for v in units if isinstance(v,str) and v.strip()))
   if not obj['units']:raise ValueError('章节不能为空')
   used={json.loads(r[0])['unit'] for r in c.execute('SELECT body FROM links WHERE course_id=? AND archived=0',(obj['id'],))}
   if used-set(obj['units']):raise ValueError('不能移除仍有资料的章节；请先将其中资料移出课程再修改章节')
   if 'lessonPlans' in data:
    plans=data['lessonPlans']
    if not isinstance(plans,dict) or len(plans)>30:raise ValueError('课次备课内容格式无效')
    if any(unit not in obj['units'] for unit in plans):raise ValueError('备课内容需要对应现有课次')
    obj['lessonPlans']={unit:text(content,30000) for unit,content in plans.items()}
  else:
   ids=data.get('paperIds',obj.get('paperIds',[]))
   if not isinstance(ids,list) or len(ids)>30 or any(not isinstance(v,str) or len(v)>200 for v in ids):raise ValueError('论文列表格式无效')
   obj['paperIds']=list(dict.fromkeys(ids))
   if kind=='comparison':
    if not 2<=len(obj['paperIds'])<=5:raise ValueError('每张对比表选择 2–5 篇论文')
    rows=data.get('rows',obj.get('rows',{}))
    if not isinstance(rows,dict):raise ValueError('对比内容格式无效')
    obj['rows']={pid:{k:text(rows.get(pid,{}).get(k,''),10000) for k in ('problem','assumptions','method','data','metrics','evidence','limitations','cost')} for pid in ids}
  obj.update(revision=obj.get('revision',0)+1,updatedAt=now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',(kind,obj['id'],json.dumps(obj,ensure_ascii=False)))
  return obj
def archive(data):
 kind=data.get('kind');ident=data.get('id');archived=0 if data.get('restore') else 1
 with connection() as c:
  if kind=='link':c.execute('UPDATE links SET archived=? WHERE id=?',(archived,ident))
  elif kind in ('course','problem','comparison','paper'):row(c,kind,ident);c.execute('UPDATE records SET archived=? WHERE kind=? AND id=?',(archived,kind,ident))
  else:raise ValueError('类型无效')
 return {'saved':True}
def atlas_papers():
 result=[]
 for name in ('papers.json','foundations.json','frontier.json'):
  try:items=json.loads((ATLAS/name).read_text(encoding='utf-8-sig'))
  except (OSError,ValueError):continue
  if isinstance(items,dict):items=items.get('papers',[])
  if not isinstance(items,list):continue
  for p in items:
   if not p.get('id') or not p.get('title'):continue
   result.append(dict(id='atlas-'+p['id'],title=p['title'],authors=p.get('authors',''),venue='Paper Atlas',year=p.get('year',2026),source=p.get('url',''),pdf=p.get('pdf') or p.get('url',''),summary=p.get('summary',''),topics=[p.get('topic',''),p.get('subtopic','')],kind='paper',short=p.get('short',''),level=p.get('level',''),subtopic=p.get('subtopic',''),notable=p.get('notable',[]),keywords=p.get('keywords',[])))
 unique={}
 for p in result:unique.setdefault(p['id'],p)
 return list(unique.values())
def catalog(query='',kind='',page=0,venue=''):
 import local_app,learning_service
 query=text(query,300).lower();page=max(0,int(page));items=[];offset=page*40;total=0
 if kind in ('','paper'):
  with local_app.db() as c:
   args=[];where=' WHERE paper_visible(body)=1'
   if query:where+=' AND (lower(title) LIKE ? OR lower(body) LIKE ?)';args=['%'+query+'%']*2
   if venue:where+=(' AND ' if where else ' WHERE ')+'venue=?';args.append(text(venue,100))
   total=c.execute('SELECT count(*) FROM papers'+where,args).fetchone()[0]
   rows=c.execute('SELECT body FROM papers'+where+' ORDER BY year DESC,title LIMIT ? OFFSET ?',args+[40,offset]).fetchall()
   items.extend(dict(json.loads(r[0]),kind='paper') for r in rows)
   atlas=[p for p in atlas_papers() if (not venue or venue=='Paper Atlas') and (not query or query in json.dumps(p,ensure_ascii=False).lower()) and not c.execute('SELECT 1 FROM papers WHERE id=?',(p['id'],)).fetchone()]
  if len(items)<40:items.extend(atlas[max(0,offset-total):max(0,offset-total)+40-len(items)])
  total+=len(atlas)
 if kind in ('','module'):
  modules=[dict(id=m['id'],kind='module',title=m['name']+' · '+m.get('en',''),summary=m.get('summary',''),url='http://127.0.0.1:8870/learning?module='+m['id']) for m in learning_service.list_modules() if not query or query in json.dumps(m,ensure_ascii=False).lower()]
  if len(items)<40:items.extend(modules[max(0,offset-total):max(0,offset-total)+40-len(items)])
  total+=len(modules)
 return dict(items=items,count=total,page=page,note='检索全部现有本地题录、论文脉络资料与基础知识模块；题录匹配，不自动判定相关性。')

def resolve(kind,ident):
 import local_app,learning_service
 if kind=='paper':
  with local_app.db() as c:r=c.execute('SELECT body FROM papers WHERE id=?',(ident,)).fetchone()
  if r:return dict(json.loads(r[0]),kind='paper')
  import scholar_papers
  p=scholar_papers.resolve(ident)
  if p:local_app.absorb([p]);return p
  p=next((p for p in atlas_papers() if p['id']==ident),None)
  if p:local_app.absorb([p]);return p
 elif kind=='module':
  with learning_service.connection() as c:m=learning_service.row(c,'modules',ident)
  return dict(id=m['id'],kind='module',title=m['name']+' · '+m.get('en',''),url='http://127.0.0.1:8870/learning?module='+m['id'])
 elif kind=='deck':
  with learning_service.connection() as c:
   r=c.execute('SELECT body FROM decks WHERE id=?',(ident,)).fetchone()
  if r:
   d=json.loads(r[0]);return dict(id=ident,kind='deck',title=d['title'],url='http://127.0.0.1:8870/learning?module='+d['moduleId']+'&deck='+ident)
 raise ValueError('资料不存在')
def add_link(data):
 kind=data.get('resourceKind');ident=data.get('resourceId');resource=resolve(kind,ident);key=kind+':'+ident
 with connection() as c:
  course=row(c,'course',data.get('courseId'))
  if not c.execute('SELECT 1 FROM records WHERE kind="course" AND id=? AND archived=0',(course['id'],)).fetchone():raise ValueError('课程已移除，请选择其他课程')
  unit=text(data.get('unit',''),100)
  if unit not in course['units']:raise ValueError('请选择课程中的章节')
  old=c.execute('SELECT body FROM links WHERE course_id=? AND resource_key=? AND archived=0',(course['id'],key)).fetchone()
  if old:return {**json.loads(old[0]),'alreadyExists':True}
  obj=dict(id=str(uuid.uuid4()),courseId=course['id'],unit=unit,resourceKind=kind,resourceId=ident,title=resource['title'],url=resource.get('url') or resource.get('pdf') or resource.get('source',''),createdAt=now(),purpose=text(data.get('purpose',''),5000))
  c.execute('INSERT INTO links VALUES(?,?,?,?,0)',(obj['id'],course['id'],key,json.dumps(obj,ensure_ascii=False)));return obj
def save_paper(data):
 import local_app
 with connection() as c:
  p=row(c,'paper',data['id']) if data.get('id') else dict(id='manual-'+str(uuid.uuid4()),venue='自选论文',year=dt.date.today().year,createdAt=now(),revision=0,topics=[])
  if data.get('id') and data.get('revision')!=p['revision']:raise ValueError('论文已更新，请刷新后再编辑')
  for key in ('title','authors','summary'):
   if key in data:p[key]=text(data[key],500 if key=='title' else 30000)
  for key in ('source','pdf'):
   if key in data:p[key]=url(data[key])
  if 'year' in data:
   try:year=int(data['year'])
   except (ValueError,TypeError):raise ValueError('年份无效')
   if not 1900<=year<=2100:raise ValueError('年份需在 1900–2100 之间')
   p['year']=year
  if 'venue' in data:
   venue=text(data['venue'],200)
   if not venue:raise ValueError('请填写期刊／会议名称')
   p['venue']=venue
  if 'publicationType' in data:
   if data['publicationType'] not in ('conference','journal','preprint','other'):raise ValueError('请选择有效的发表类型')
   p['publicationType']=data['publicationType']
  if not p.get('title'):raise ValueError('请输入论文标题')
  p.update(revision=p['revision']+1,updatedAt=now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',('paper',p['id'],json.dumps(p,ensure_ascii=False)))
 local_app.absorb([p]);return p
def add_queue(data):
 date=valid_date(data.get('date',today()));p=resolve('paper',data.get('paperId'))
 with connection() as c:
  obj=queue_paper(c,p,date,data.get('reason'))
 return obj

def queue_paper(c,p,date=None,reason=None):
 date=valid_date(date or today())
 old=c.execute('SELECT body FROM queue WHERE date=? AND paper_id=?',(date,p['id'])).fetchone()
 obj=json.loads(old[0]) if old else dict(paperId=p['id'],date=date,title=p['title'],reason='',createdAt=now())
 if reason is not None and not obj.get('reason'):obj['reason']=text(reason,3000)
 c.execute('INSERT INTO queue VALUES(?,?,?,0) ON CONFLICT(date,paper_id) DO UPDATE SET body=excluded.body,archived=0',(date,p['id'],json.dumps(obj,ensure_ascii=False)))
 return obj
def remove_queue(data):
 date=valid_date(data.get('date',today()))
 with connection() as c:
  paper=resolve('paper',data.get('paperId'));queue_paper(c,paper,date)
  c.execute('UPDATE queue SET archived=? WHERE date=? AND paper_id=?',(0 if data.get('restore') else 1,date,data.get('paperId')))

 return {'saved':True}
def task_detail(pid,taskid):
 definitions=json.loads((ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
 task=next((t for t in definitions if t['id']==taskid),None)
 if not task:raise ValueError('阅读任务不存在')
 paper=resolve('paper',pid)
 return dict(id='study-'+pid+'-'+taskid,title=(paper['title'][:75]+' · '+task['title'])[:160],detail='论文：'+paper['title']+'\n具体动作与交付标准：'+task['hint'],paperId=pid,taskId=taskid)

def reading_queue(c,date):
 from reading_journal import complete
 latest={}
 for day,ident,body,archived in c.execute('SELECT date,paper_id,body,archived FROM queue WHERE date<=? ORDER BY date,rowid',(date,)):latest[ident]=(day,json.loads(body),archived)
 result=[]
 knowledge={p['id']:p for p in records(c,'paper-knowledge')}
 manual={p['id']:p for p in records(c,'paper-reading-status')}
 for ident,(day,obj,archived) in latest.items():
  if archived:continue
  if day<date and (manual[ident]['read'] if ident in manual else complete(knowledge.get(ident,{}))):continue
  if day<date:obj={**obj,'carriedFrom':day,'date':date}
  result.append(obj)
 return result

def select_reading_paper(data):
 paper=resolve('paper',data.get('paperId'))
 with connection() as c:
  obj=dict(id=paper['id'],createdAt=now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET archived=0',('reading-library',paper['id'],json.dumps(obj)))
 return {'saved':True}
