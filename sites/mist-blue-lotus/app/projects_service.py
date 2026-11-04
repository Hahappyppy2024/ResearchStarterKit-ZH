"""Local project notebook with durable SQLite records and recoverable archives."""
import contextlib, csv, datetime as dt, io, json, pathlib, sqlite3, uuid
ROOT=pathlib.Path(__file__).resolve().parent
DB_PATH=ROOT/'local-data/projects.sqlite'
PROJECT_FIELDS=['name','problem','goal','papers','codePath','status','projectNotes']
LOG_FIELDS=['date','name','hypothesis','baseline','changes','codeVersion','command','environment','dataSplit','seed','artifacts','results','conclusion','limitations','next','notes','parentId','outcome']
DEFAULT_TASKS=['明确研究问题与目标','准备数据与检查数据划分','复现并确认 baseline','设计对照与消融实验','运行实验并分析结果','整理图表与论文写作']
def now():return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec='seconds')
@contextlib.contextmanager
def connection():
 DB_PATH.parent.mkdir(exist_ok=True)
 with contextlib.closing(sqlite3.connect(DB_PATH,timeout=30)) as c:
  c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
  c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,body TEXT NOT NULL,archived INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS project_notes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,body TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id),body TEXT NOT NULL,archived INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS logs(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id),body TEXT NOT NULL,archived INTEGER DEFAULT 0);''')
  with c:
   c.execute('BEGIN IMMEDIATE')
   yield c
def text(value,limit=30000):
 if not isinstance(value,str) or len(value)>limit:raise ValueError('字段内容无效或过长')
 return value
def get_row(c,table,id):
 row=c.execute(f'SELECT body FROM {table} WHERE id=?',(id,)).fetchone()
 if row is None:raise ValueError('记录不存在')
 return json.loads(row[0])
def touch_project(c,id):
 p=get_row(c,'projects',id);p['updatedAt']=now();c.execute('UPDATE projects SET body=? WHERE id=?',(json.dumps(p,ensure_ascii=False),id))
def list_projects(archived=False):
 with connection() as c:
  projects=[json.loads(r[0]) for r in c.execute('SELECT body FROM projects WHERE archived=?',(int(archived),))]
  for p in projects:
   tasks=[json.loads(r[0]) for r in c.execute('SELECT body FROM tasks WHERE project_id=? AND archived=0',(p['id'],))]
   logs=[json.loads(r[0]) for r in c.execute('SELECT body FROM logs WHERE project_id=? AND archived=0',(p['id'],))]
   logs.sort(key=lambda l:(l['date'],l['createdAt'],l.get('number',0)),reverse=True)
   p.update(taskTotal=len(tasks),taskDone=sum(t['done'] for t in tasks),logTotal=len(logs),latest=logs[0] if logs else None,nextTask=next((t['title'] for t in tasks if not t['done']),''))
 return sorted(projects,key=lambda p:p['updatedAt'],reverse=True)
def project_detail(id):
 with connection() as c:
  p=get_row(c,'projects',id)
  p['archived']=bool(c.execute('SELECT archived FROM projects WHERE id=?',(id,)).fetchone()[0])
  tasks=[json.loads(r[0]) for r in c.execute('SELECT body FROM tasks WHERE project_id=? AND archived=0 ORDER BY rowid',(id,))]
  logs=[json.loads(r[0]) for r in c.execute('SELECT body FROM logs WHERE project_id=? AND archived=0 ORDER BY rowid',(id,))]
 return {'project':p,'tasks':tasks,'logs':logs}
def save_project(data):
 with connection() as c:
  fresh=not data.get('id');p={'id':str(uuid.uuid4()),'createdAt':now()} if fresh else get_row(c,'projects',data['id'])
  for key in PROJECT_FIELDS:
   if key in data:p[key]=text(data[key],160 if key=='name' else 30000)
  if not p.get('name','').strip():raise ValueError('请填写项目名称')
  p.setdefault('status','active');p['updatedAt']=now()
  c.execute('INSERT INTO projects(id,body) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(p['id'],json.dumps(p,ensure_ascii=False)))
  if fresh:
   for title in DEFAULT_TASKS:
    task={'id':str(uuid.uuid4()),'projectId':p['id'],'title':title,'detail':'','done':False,'createdAt':now()}
    c.execute('INSERT INTO tasks(id,project_id,body) VALUES(?,?,?)',(task['id'],p['id'],json.dumps(task,ensure_ascii=False)))
 return p
def save_task(data):
 with connection() as c:
  get_row(c,'projects',data.get('projectId',''))
  task=get_row(c,'tasks',data['id']) if data.get('id') else {'id':str(uuid.uuid4()),'projectId':data['projectId'],'createdAt':now(),'done':False,'detail':''}
  if task['projectId']!=data['projectId']:raise ValueError('任务不属于该项目')
  for key in ['title','detail']:
   if key in data:task[key]=text(data[key],160 if key=='title' else 10000).strip()
  if not task.get('title'):raise ValueError('请填写任务名称')
  if 'done' in data:task['done']=data['done'] is True
  task['updatedAt']=now();c.execute('INSERT INTO tasks(id,project_id,body) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(task['id'],task['projectId'],json.dumps(task,ensure_ascii=False)))
  touch_project(c,task['projectId'])
 return task
def task_detail(id):
 with connection() as c:
  task=get_row(c,'tasks',id);project=get_row(c,'projects',task['projectId'])
 return {'task':task,'project':{'id':project['id'],'name':project['name']}}
def save_log(data):
 with connection() as c:
  get_row(c,'projects',data.get('projectId',''))
  log=get_row(c,'logs',data['id']) if data.get('id') else {'id':str(uuid.uuid4()),'projectId':data['projectId'],'createdAt':now(),'revision':0}
  if not data.get('id'):log['number']=c.execute('SELECT count(*) FROM logs WHERE project_id=?',(data['projectId'],)).fetchone()[0]+1
  if log['projectId']!=data['projectId']:raise ValueError('实验不属于该项目')
  if data.get('id') and data.get('revision')!=log.get('revision',0):raise ValueError('记录已在其他窗口更新，请保留草稿后刷新')
  for key in LOG_FIELDS:
   if key in data:log[key]=text(data[key])
  try:dt.date.fromisoformat(log.get('date',''))
  except ValueError:raise ValueError('请选择有效日期')
  log.setdefault('name','实验记录');log.setdefault('outcome','pending')
  parent=log.get('parentId','')
  if parent:
   previous=get_row(c,'logs',parent)
   if previous['projectId']!=log['projectId'] or parent==log['id']:raise ValueError('前序实验无效')
   seen={log['id']}
   while previous:
    if previous['id'] in seen:raise ValueError('实验关系不能形成循环')
    seen.add(previous['id']);previous=get_row(c,'logs',previous['parentId']) if previous.get('parentId') else None
  metrics=data.get('metrics',log.get('metrics',[]))
  if not isinstance(metrics,list) or len(metrics)>100:raise ValueError('指标表无效')
  log['metrics']=[{key:text(m.get(key,''),300) for key in ['name','value','unit']} for m in metrics if isinstance(m,dict)]
  log['updatedAt']=now();log['revision']=log.get('revision',0)+1
  c.execute('INSERT INTO logs(id,project_id,body) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(log['id'],log['projectId'],json.dumps(log,ensure_ascii=False)))
  touch_project(c,log['projectId'])
 return log
def archive(data):
 table={'project':'projects','task':'tasks','log':'logs'}.get(data.get('kind'))
 if not table:raise ValueError('记录类型无效')
 with connection() as c:
  get_row(c,table,data.get('id',''));c.execute(f'UPDATE {table} SET archived=? WHERE id=?',(0 if data.get('restore') else 1,data['id']))
 return {'saved':True}
def export_project(id,format):
 data=project_detail(id);p=data['project'];logs=data['logs']
 if format=='csv':
  stream=io.StringIO(newline='');writer=csv.writer(stream)
  writer.writerow(['实验ID','日期','名称','假设','baseline','改动','代码版本','命令','环境','数据划分','随机种子','指标JSON','结果','结论','局限','下一步','笔记','文件路径','前序实验','假设验证状态'])
  for l in logs:writer.writerow([l['id'],l['date'],l['name']]+[l.get(k,'') for k in ['hypothesis','baseline','changes','codeVersion','command','environment','dataSplit','seed']]+[json.dumps(l['metrics'],ensure_ascii=False)]+[l.get(k,'') for k in ['results','conclusion','limitations','next','notes','artifacts','parentId','outcome']])
  return '\ufeff'+stream.getvalue()
 lines=['# '+p['name'],'']
 for key,label in [('projectNotes','项目笔记'),('problem','研究问题'),('goal','目标'),('papers','关联论文'),('codePath','代码路径')]:lines.extend(['## '+label,p.get(key,''),''])
 for item in records_for_export(id):
  lines+=['## 项目笔记 / '+item['path'],item['content'],'']
 lines+=['## 基础任务']+['- ['+('x' if t['done'] else ' ')+'] '+t['title']+('：'+t['detail'] if t.get('detail') else '') for t in data['tasks']]
 for i,l in enumerate(logs,1):
  lines+=['',f"## E{l.get('number',i):03} · {l['date']} · {l['name']}",'实验 ID：'+l['id']]
  for key in LOG_FIELDS[2:]:
   if l.get(key):lines+=['','### '+{'hypothesis':'实验问题／假设','baseline':'对照 baseline','changes':'具体改动','codeVersion':'代码版本','command':'运行命令','environment':'环境','dataSplit':'数据划分','seed':'随机种子','artifacts':'文件与路径','results':'结果观察','conclusion':'结论','limitations':'局限','next':'下一步','notes':'随手笔记','parentId':'前序实验 ID','outcome':'验证状态'}.get(key,key),l[key]]
  lines+=['','### 指标']+['- '+m['name']+'：'+m['value']+' '+m['unit'] for m in l['metrics']]
 return '\n'.join(lines)

def records_for_export(project):
 with connection() as c:
  items=[json.loads(r[0]) for r in c.execute('SELECT body FROM project_notes WHERE project_id=?',(project,))]
 byid={i['id']:i for i in items};result=[]
 for item in items:
  if item['kind']!='note' or item.get('deleted'):continue
  names=[item['title']];parent=item.get('parentId');seen=set()
  while parent in byid and parent not in seen:
   seen.add(parent);names.insert(0,byid[parent]['title']);parent=byid[parent].get('parentId')
  result.append(dict(path='/'.join(names),content=item.get('content','')))
 return result
