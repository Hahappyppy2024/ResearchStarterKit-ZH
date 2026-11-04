"""Editable module notebooks, safe local attachments and today's card selection."""
import datetime,json,pathlib,uuid
import learning_service as learning

def today():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()

def get(ident):
 with learning.connection() as c:
  m=learning.row(c,'modules',ident)
 return dict(id=ident,revision=m.get('notebookRevision',0),questions=m.get('questionList',[]),examples=m.get('examples',[]),formulas=m.get('formulas',[]),attachments=m.get('attachments',[]),quizDate=today(),quizCards=m.get('quizCards',{}).get(today(),[]))

def save(data):
 with learning.connection() as c:
  c.execute('BEGIN IMMEDIATE');m=learning.row(c,'modules',data.get('id'))
  if data.get('revision')!=m.get('notebookRevision',0):raise ValueError('模块内容已在其他窗口更新，请刷新后再保存；当前输入仍在页面')
  for source,target,fields in [('questions','questionList',['question','answer']),('examples','examples',['domain','title','description','code']),('formulas','formulas',['title','latex','explanation'])]:
   if source not in data:continue
   values=data[source]
   if not isinstance(values,list) or len(values)>200:raise ValueError('每类最多 200 条')
   clean=[];ids=set()
   for item in values:
    ident=str(uuid.UUID(item['id']))
    if ident in ids:raise ValueError('条目重复')
    ids.add(ident);obj=dict(id=ident)
    for k in fields:obj[k]=learning.clean(item.get(k,''),50000)
    if source=='examples' and obj['domain'] not in ('nlp','cv'):raise ValueError('请选择 NLP 或 CV')
    clean.append(obj)
   m[target]=clean
  m['notebookRevision']=m.get('notebookRevision',0)+1;m['updatedAt']=learning.now();learning.write(c,'modules',m)
 return get(m['id'])

def select(data):
 with learning.connection() as c:
  c.execute('BEGIN IMMEDIATE');m=learning.row(c,'modules',data.get('moduleId'))
  cards=[json.loads(r[0]) for r in c.execute('SELECT body FROM flashcards WHERE module_id=?',(m['id'],))]
  ids=data.get('cardIds',[])
  if not isinstance(ids,list) or any(i not in {x['id'] for x in cards if not x.get('archived') and x.get('answer','').strip()} for i in ids):raise ValueError('请先填写卡片答案，再加入今日 Quiz')
  m.setdefault('quizCards',{})[today()]=list(dict.fromkeys(ids));learning.write(c,'modules',m)
 return dict(date=today(),cardIds=ids)

def quiz_cards(date):
 result=[]
 with learning.connection() as c:
  for r in c.execute('SELECT body FROM modules'):
   m=json.loads(r[0]);selected=m.get('quizCards',{}).get(date,[])
   if not selected:continue
   for r in c.execute('SELECT body FROM flashcards WHERE module_id=?',(m['id'],)):
    card=json.loads(r[0])
    if card['id'] in selected and not card.get('archived') and card.get('answer','').strip():result.append(dict(key='module:'+card['id'],paperId='module:'+m['id'],title=m['name']+' / '+m.get('en',''),question=card['question'],answer=card['answer'],source='module'))
 return result

def folder():return learning.FILES/'module-assets'

def file(ident):
 try:ident=str(uuid.UUID(ident))
 except (ValueError,TypeError):raise ValueError('附件不存在')
 matches=list(folder().glob(ident+'.*'))
 if len(matches)!=1:raise ValueError('附件不存在')
 return matches[0]

def upload(module_id,item_id,name,content):
 ext=pathlib.PureWindowsPath(name).suffix.lower();images={'.png':b'\x89PNG\r\n\x1a\n','.jpg':b'\xff\xd8\xff','.jpeg':b'\xff\xd8\xff','.webp':b'RIFF'}
 if ext not in images and ext not in ('.py','.txt','.ipynb','.js','.ts','.cpp','.c','.h','.cu','.json','.md'):raise ValueError('支持 PNG/JPEG/WebP 或文本代码文件')
 if not content or len(content)>8*1024*1024:raise ValueError('附件需在 8 MB 以内')
 if ext in images:
  if not content.startswith(images[ext]) or ext=='.webp' and content[8:12]!=b'WEBP':raise ValueError('图片格式不匹配')
 else:
  try:content.decode('utf-8-sig')
  except UnicodeError:raise ValueError('代码文件请保存为 UTF-8 文本')
 ident=str(uuid.uuid4());meta=dict(id=ident,itemId=item_id,name=pathlib.PureWindowsPath(name).name,kind='image' if ext in images else 'code')
 with learning.connection() as c:
  c.execute('BEGIN IMMEDIATE');m=learning.row(c,'modules',module_id)
  if item_id not in {e['id'] for e in m.get('examples',[])}:raise ValueError('请先保存实例，再上传附件')
  if len(m.get('attachments',[]))>=200:raise ValueError('单模块最多 200 个附件')
  folder().mkdir(parents=True,exist_ok=True);(folder()/(ident+ext)).write_bytes(content)
  m.setdefault('attachments',[]).append(meta);m['notebookRevision']=m.get('notebookRevision',0)+1;learning.write(c,'modules',m)
 return meta
