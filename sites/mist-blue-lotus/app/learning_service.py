"""Local AI learning modules, source decks, preview jobs and study notes."""
import re
import contextlib, datetime, json, pathlib, sqlite3, subprocess, threading, uuid, zipfile, io, xml.etree.ElementTree as ET
from learning_editor import slide_names
from learning_taxonomy import entries as taxonomy_entries
ROOT=pathlib.Path(__file__).resolve().parent
DB=ROOT/'local-data'/'learning.sqlite'
FILES=ROOT/'local-data'/'learning-files'
CONVERT_LOCK=threading.Lock()
SEEDS=[]  # No bundled course content in public copy.
@contextlib.contextmanager
def connection():
 DB.parent.mkdir(exist_ok=True,parents=True)
 with contextlib.closing(sqlite3.connect(DB,timeout=20)) as c:
  c.execute('CREATE TABLE IF NOT EXISTS modules(id TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS decks(id TEXT PRIMARY KEY, module_id TEXT NOT NULL, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS flashcards(id TEXT PRIMARY KEY, module_id TEXT NOT NULL, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS learning_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
  if not c.execute('SELECT 1 FROM modules LIMIT 1').fetchone():
   for name,en,summary,questions in SEEDS:
    ident=str(uuid.uuid4());body=dict(id=ident,name=name,en=en,summary=summary,notes='',questions='\n'.join(questions),answers='',updatedAt=now())
    c.execute('INSERT INTO modules VALUES(?,?)',(ident,json.dumps(body,ensure_ascii=False)))
  c.commit()
  c.execute('BEGIN IMMEDIATE')
  if not c.execute("SELECT 1 FROM learning_meta WHERE key='knowledge-taxonomy-1'").fetchone():
   existing={json.loads(r[0]).get('en','').casefold():json.loads(r[0]) for r in c.execute('SELECT body FROM modules')}
   for item in taxonomy_entries():
    key=item['en'].casefold();old=existing.get(key)
    if old:
     for field in ['domain','section','source']:old.setdefault(field,item[field])
     c.execute('UPDATE modules SET body=? WHERE id=?',(json.dumps(old,ensure_ascii=False),old['id']))
    else:
     body=dict(id=str(uuid.uuid4()),**item,notes='',answers='',questions='\n'.join([item['en']+' 主要解决什么问题？',item['en']+' 的输入、输出与工作流程是什么？',item['en']+' 有什么局限，适合什么场景？']),updatedAt=now())
     c.execute('INSERT INTO modules VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
   c.execute("INSERT INTO learning_meta VALUES('knowledge-taxonomy-1','installed')")
  c.commit()
  with c:yield c
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def row(c,table,ident):
 result=c.execute(f'SELECT body FROM {table} WHERE id=?',(ident,)).fetchone()
 if not result:raise ValueError('记录不存在')
 return json.loads(result[0])
def write(c,table,data):c.execute(f'UPDATE {table} SET body=? WHERE id=?',(json.dumps(data,ensure_ascii=False),data['id']))
def clean(value,limit=50000):
 if not isinstance(value,str) or len(value)>limit:raise ValueError('内容无效或过长')
 return value
LEARNING_STAGES={'model':'模型／模块理解','training':'模型训练','inference':'模型推理','deployment':'模型部署'}
def learning_stage(module):
 explicit=module.get('learningStage')
 if explicit in LEARNING_STAGES:return explicit
 text=(module.get('name','')+' '+module.get('en','')).lower()
 if re.search(r'部署|服务化|量化|剪枝|蒸馏|模型压缩|onnx|tensorrt|serving|deployment|quantiz|pruning|distillation|compression',text):return 'deployment'
 if re.search(r'推理|解码|缓存|nms|kv.?cache|inference|decoding|beam.search|\bsampling\b|speculative',text):return 'inference'
 if re.search(r'训练|优化|损失|反向传播|正则化|微调|学习率|梯度|初始化|归一化|training|optimization|optimizer|loss|交叉熵|均方误差|\badam\b|\bsgd\b|\blora\b|\bpeft\b|\bdpo\b|\brlhf\b|\bgrpo\b|\bppo\b|backprop|regulariz|fine.tun|learning.rate|gradient|initializ|normalization|dropout',text):return 'training'
 return 'model'

def list_modules():
 with connection() as c:
  modules=[json.loads(r[0]) for r in c.execute('SELECT body FROM modules ORDER BY rowid')]
  for m in modules:m['learningStage']=learning_stage(m);m['deckCount']=sum(not json.loads(r[0]).get('archived',False) for r in c.execute('SELECT body FROM decks WHERE module_id=?',(m['id'],)))
  return modules
def detail(ident):
 with connection() as c:
  c.execute('BEGIN IMMEDIATE')
  module=row(c,'modules',ident);decks=[json.loads(r[0]) for r in c.execute('SELECT body FROM decks WHERE module_id=? ORDER BY rowid DESC',(ident,))]
  if not module.get('flashcardsMigrated'):
   for question in dict.fromkeys(q.strip() for q in module.get('questions','').splitlines() if q.strip()):
    card=dict(id=str(uuid.uuid4()),moduleId=ident,question=question,answer='',revision=1,createdAt=now(),updatedAt=now(),archived=False)
    c.execute('INSERT INTO flashcards VALUES(?,?,?)',(card['id'],ident,json.dumps(card,ensure_ascii=False)))
   module['flashcardsMigrated']=True;write(c,'modules',module)
  cards=[json.loads(r[0]) for r in c.execute('SELECT body FROM flashcards WHERE module_id=? ORDER BY rowid',(ident,))]
  module={**module,'learningStage':learning_stage(module)}
  return dict(module=module,decks=[d for d in decks if not d.get('archived')],archivedDecks=[d for d in decks if d.get('archived') and not d.get('systemSample')],cards=[v for v in cards if not v.get('archived')],archivedCards=[v for v in cards if v.get('archived')])

def save_flashcard(data):
 with connection() as c:
  c.execute('BEGIN IMMEDIATE')
  module_id=data.get('moduleId');row(c,'modules',module_id)
  fresh=not data.get('id')
  card=dict(id=str(uuid.uuid4()),moduleId=module_id,createdAt=now(),revision=0,archived=False) if fresh else row(c,'flashcards',data['id'])
  if card['moduleId']!=module_id:raise ValueError('卡片不属于当前模块')
  if not fresh and data.get('revision')!=card['revision']:raise ValueError('卡片已在其他窗口修改，请关闭编辑框并重新打开后再保存')
  question=clean(data.get('question',''),10000).strip();answer=clean(data.get('answer',''),50000)
  if not question:raise ValueError('请填写正面的问题')
  card.update(question=question,answer=answer,revision=card['revision']+1,updatedAt=now())
  if fresh:c.execute('INSERT INTO flashcards VALUES(?,?,?)',(card['id'],module_id,json.dumps(card,ensure_ascii=False)))
  else:write(c,'flashcards',card)
  return card

def archive_flashcard(data):
 with connection() as c:
  c.execute('BEGIN IMMEDIATE')
  card=row(c,'flashcards',data.get('id'))
  if card['moduleId']!=data.get('moduleId'):raise ValueError('卡片不属于当前模块')
  if card['revision']!=data.get('revision'):raise ValueError('卡片已更新，请刷新卡片后重试')
  card.update(archived=not data.get('restore',False),revision=card['revision']+1,updatedAt=now());write(c,'flashcards',card);return card
def save_module(data):
 with connection() as c:
  ident=data.get('id');m=row(c,'modules',ident) if ident else dict(id=str(uuid.uuid4()),notes='',questions='',answers='',summary='',en='')
  for k in ['name','en','summary','notes','questions','answers','domain','section','learningStage']:
   if k in data:m[k]=clean(data[k],160 if k in ['name','en'] else 50000)
  if not m.get('name','').strip():raise ValueError('请填写模块名称')
  if m.get('domain','general') not in ('general','cv','nlp','agent'):raise ValueError('知识分类无效')
  if m.get('learningStage',learning_stage(m)) not in LEARNING_STAGES:raise ValueError('请选择有效的学习部分')
  m['updatedAt']=now()
  if ident:write(c,'modules',m)
  else:c.execute('INSERT INTO modules VALUES(?,?)',(m['id'],json.dumps(m,ensure_ascii=False)))
  return m
def save_deck(data):
 with connection() as c:
  d=row(c,'decks',data.get('id'))
  for k in ['title','notes']:
   if k in data:d[k]=clean(data[k],200 if k=='title' else 50000)
  if not d['title'].strip():raise ValueError('请填写 PPT 名称')
  if 'done' in data:d['done']=data['done'] is True
  if 'page' in data:d['page']=max(0,min(int(data['page']),max(d.get('slideCount',1)-1,0)))
  d['updatedAt']=now();write(c,'decks',d);return d
def get_deck(ident):
 with connection() as c:return row(c,'decks',ident)
def archive_deck(data):
 with connection() as c:
  d=row(c,'decks',data.get('id'));d['archived']=not data.get('restore',False);d['updatedAt']=now();write(c,'decks',d);return d
def open_deck(data):
 import os
 d=get_deck(data.get('id'))
 if d.get('archived'):raise ValueError('PPT 已删除，请先恢复')
 try:os.startfile(str(file_path(d['id'],'source.pptx')))
 except OSError:raise ValueError('无法打开 PowerPoint，请确认已安装并关联 .pptx 文件')
 return {'ok':True}
def refresh_deck(data):
 ident=data.get('id');d=get_deck(ident)
 if d.get('archived'):raise ValueError('PPT 已删除，请先恢复')
 if d['preview'] in ('pending','converting'):return {'ok':True}
 with zipfile.ZipFile(file_path(ident,'source.pptx')) as z:
  import re
  names=slide_names(z)
  texts=['\n'.join(e.text or '' for e in ET.fromstring(z.read(n)).iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')) for n in names]
 with connection() as c:
  d=row(c,'decks',ident);d.update(texts=texts,slideCount=len(texts),preview='pending',previewError='',updatedAt=now());d['page']=min(d.get('page',0),max(len(texts)-1,0));write(c,'decks',d)
 threading.Thread(target=convert,args=(ident,),daemon=True).start();return {'ok':True}
def import_deck(module_id,filename,content):
 filename=pathlib.PureWindowsPath(filename).name
 if pathlib.Path(filename).suffix.lower()!='.pptx':raise ValueError('请上传 .pptx 文件；旧版 .ppt 请先在 PowerPoint 中另存为 .pptx')
 if not content or len(content)>50*1024*1024:raise ValueError('文件需在 50 MB 以内')
 try:
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   if '[Content_Types].xml' not in z.namelist() or 'ppt/presentation.xml' not in z.namelist():raise ValueError('不是有效的 PPTX 文件')
   if len(z.infolist())>20000 or sum(i.file_size for i in z.infolist())>200*1024*1024:raise ValueError('PPTX 解压内容过大')
   if any('vbaproject' in n.lower() for n in z.namelist()):raise ValueError('请使用不含宏的 PPTX 文件')
   import re
   names=slide_names(z)
   if len(names)>500:raise ValueError('单份 PPT 最多支持 500 页')
   texts=['\n'.join(e.text or '' for e in ET.fromstring(z.read(n)).iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')) for n in names]
 except (zipfile.BadZipFile,ET.ParseError):raise ValueError('无法读取此 PPTX 文件')
 with connection() as c:
  row(c,'modules',module_id);ident=str(uuid.uuid4());folder=FILES/ident;folder.mkdir(parents=True);(folder/'source.pptx').write_bytes(content)
  d=dict(id=ident,moduleId=module_id,title=filename[:-5],filename=filename,size=len(content),notes='',done=False,page=0,texts=texts,slideCount=len(texts),preview='pending',previewError='',createdAt=now(),updatedAt=now())
  c.execute('INSERT INTO decks VALUES(?,?,?)',(ident,module_id,json.dumps(d,ensure_ascii=False)))
 threading.Thread(target=convert,args=(ident,),daemon=True).start();return d
def convert(ident):
 with CONVERT_LOCK:
  folder=FILES/ident
  with connection() as c:
   d=row(c,'decks',ident);d['preview']='converting';write(c,'decks',d)
  try:
   for old in (folder/'slides').glob('slide-*.png'):old.unlink()
   run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'render_learning.ps1'),'-Source',str(folder/'source.pptx'),'-Output',str(folder/'slides')],capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   images=sorted((folder/'slides').glob('*.png'))
   if run.returncode or not images:raise ValueError('PowerPoint 预览转换未成功。可下载原文件，或点击重试。')
   with connection() as c:
    d=row(c,'decks',ident);d.update(preview='ready',slideCount=len(images),previewError='',updatedAt=now());d['page']=min(d.get('page',0),max(len(images)-1,0));write(c,'decks',d)
  except Exception as err:
   with connection() as c:
    d=row(c,'decks',ident);d.update(preview='failed',previewError=str(err)[:500]);write(c,'decks',d)
def task_detail(ident):
 d=get_deck(ident.removeprefix('learning-'))
 if d.get('archived'):raise ValueError('PPT 已删除，请先在学习本恢复')
 with connection() as c:m=row(c,'modules',d['moduleId'])
 return dict(project=dict(id=m['id'],name='AI 学习 · '+m['name'],kind='learning',deckId=d['id']),task=dict(id='learning-'+d['id'],title=d['title'],detail='PPT 学习任务 · '+str(d['slideCount'])+' 页'))
def editable_slide(ident,index):
 import learning_editor as editor
 d=get_deck(ident)
 if d.get('archived'):raise ValueError('请先恢复 PPT')
 return editor.get_slide(file_path(ident,'source.pptx'),int(index))
def save_slide(data):
 import learning_editor as editor
 ident=data.get('id');d=get_deck(ident)
 if d.get('archived'):raise ValueError('请先恢复 PPT')
 if d['preview'] in ('pending','converting'):raise ValueError('请等待预览生成完毕后再编辑')
 source=file_path(ident,'source.pptx')
 if data.get('undo'):editor.undo(source,data.get('revision'))
 else:editor.save_slide(source,int(data.get('index',0)),data.get('revision'),data.get('fields'))
 refresh_deck({'id':ident});return {'ok':True}
def file_path(ident,name):
 uuid.UUID(ident)
 import re
 if name!='source.pptx' and not re.fullmatch(r'slides/slide-\d{4}\.png',name):raise ValueError('文件路径无效')
 p=FILES/ident/name
 if not p.is_file():raise ValueError('文件不存在')
 return p
