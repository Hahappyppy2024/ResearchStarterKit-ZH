"""Local blog, lab catalogue and clipboard images. No external publishing."""
import base64,datetime,io,json,pathlib,uuid
import study_service as study
ROOT=pathlib.Path(__file__).resolve().parent/'local-data'/'pasted-images'
def listing(kind):
 if kind not in ('blog-post','blog-folder','research-lab','method-post','method-resource'):raise ValueError('类型无效')
 with study.connection() as c:
  active=study.records(c,kind);archived=study.records(c,kind,True)
  if kind=='blog-post':return dict(items=active,archived=[p for p in archived if not p.get('deleted')],trash=[p for p in archived if p.get('deleted')])
  return dict(items=active,archived=archived)
def save(kind,data):
 if kind not in ('blog-post','blog-folder','research-lab','method-post','method-resource'):raise ValueError('类型无效')
 with study.connection() as c:
  old=study.row(c,kind,data['id']) if data.get('id') else {'id':str(uuid.uuid4()),'revision':0,'createdAt':study.now()}
  if data.get('revision',0)!=old['revision']:raise ValueError('已在其他窗口更新，请刷新核对；草稿仍保留')
  obj=dict(old)
  fields=['title','content','tags','paperIds','folderId','noteDate'] if kind=='blog-post' else ['name','parentId'] if kind=='blog-folder' else ['name','university','institution','leaders','scholars','description','source','paperIds','topicIds']
  if kind=='method-post':fields=['title','content','category','stepId','noteDate']
  if kind=='method-resource':fields=['title','url','category','resourceType','publishedDate','note','favorite','seedId']
  for key in fields:
   if key in data:
    if key=='favorite':obj[key]=data[key] is True
    elif key in ('paperIds','topicIds'):
     if not isinstance(data[key],list) or len(data[key])>1000:raise ValueError('论文列表无效')
     obj[key]=list(dict.fromkeys(study.text(i,200) for i in data[key]))
    else:obj[key]=study.text(data[key],1000000 if key=='content' else 30000)
  if kind in ('method-post','method-resource'):
   workflow=json.loads((pathlib.Path(__file__).resolve().parent/'web'/'method-workflow.json').read_text(encoding='utf-8'))
   category=next((item for item in workflow if item['id']==obj.get('category')),None)
   if not category:raise ValueError('请选择科研流程分类')
   if kind=='method-post' and obj.get('stepId') and obj['stepId'] not in {step['id'] for step in category['steps']}:raise ValueError('请选择当前大分类下的具体步骤')
   for key in ('noteDate','publishedDate'):
    if obj.get(key):obj[key]=study.valid_date(obj[key])
   if kind=='method-resource':
    obj['url']=study.url(obj.get('url',''))
    if not obj['url']:raise ValueError('请填写资源链接')
    if obj.get('resourceType') not in ('article','video','website'):raise ValueError('请选择文章、视频或网站')
  if not obj.get('title' if kind in ('blog-post','method-post','method-resource') else 'name','').strip():raise ValueError('请填写标题或名称')
  if kind=='blog-folder':
   parent=obj.get('parentId','');seen={obj['id']}
   while parent:
    if parent in seen:raise ValueError('分类不能形成循环')
    seen.add(parent)
    if len(seen)>10:raise ValueError('分类层级最多 10 层')
    parent=study.row(c,'blog-folder',parent).get('parentId','')
  if kind=='blog-post':
   obj['deleted']=data.get('deleted',obj.get('deleted',False)) is True
   if obj.get('folderId'):
    folder=study.row(c,'blog-folder',obj['folderId'])
   if obj.get('noteDate'):obj['noteDate']=study.valid_date(obj['noteDate'])
  obj.update(revision=old['revision']+1,updatedAt=study.now())
  if kind=='research-lab':
   index={n['id']:n for n in study.records(c,'taxonomy')}
   if any(i not in index or index[i]['kind']!='topic' for i in obj.get('topicIds',[])):raise ValueError('请选择已定义的 Topic')
  archived=bool(data.get('archived',False)) or (kind=='blog-post' and obj.get('deleted',False))
  c.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=excluded.archived',(kind,obj['id'],json.dumps(obj,ensure_ascii=False),int(archived)))
 return obj
def paste_image(data):
 from PIL import Image
 raw=data.get('image','')
 if not isinstance(raw,str) or len(raw)>12000000:raise ValueError('截图最大 8 MB')
 try:
  header,encoded=raw.split(',',1)
  if header not in ('data:image/png;base64','data:image/jpeg;base64','data:image/webp;base64'):raise ValueError()
  content=base64.b64decode(encoded,validate=True)
  if len(content)>8*1024*1024:raise ValueError()
  im=Image.open(io.BytesIO(content));im.verify()
  if im.format not in ('PNG','JPEG','WEBP'):raise ValueError()
 except Exception:raise ValueError('请粘贴有效 PNG、JPG 或 WebP 截图，最大 8 MB')
 ident=str(uuid.uuid4());ext={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[im.format]
 ROOT.mkdir(parents=True,exist_ok=True);(ROOT/(ident+ext)).write_bytes(content)
 return {'url':'http://127.0.0.1:8866/api/study/paste-image?id='+ident,'id':ident}
def image_file(ident):
 try:ident=str(uuid.UUID(ident))
 except (ValueError,TypeError):raise ValueError('图片不存在')
 for ext,kind in [('.png','image/png'),('.jpg','image/jpeg'),('.webp','image/webp')]:
  p=ROOT/(ident+ext)
  if p.is_file():return p.read_bytes(),kind
 raise ValueError('图片不存在')

def scholar_photo(ident):
 profiles=scholar_directory()['people']
 if ident not in {p['id'] for p in profiles}:raise ValueError('学者不存在')
 person=next(p for p in profiles if p['id']==ident)
 if str(person.get('photoUrl','')).startswith('https://'):return dict(image=person['photoUrl'],source=person.get('source') or person['photoUrl'])
 path=study.ROOT/'local-data'/'scholar-photos'/(ident+'.json')
 try:obj=json.loads(path.read_text(encoding='utf-8'))
 except (OSError,ValueError):return dict(image='',source='')
 # Only verified web portraits, never report screenshots or user-uploaded photos.
 if obj.get('report') or not str(obj.get('source','')).startswith('https://'):return dict(image='',source='')
 return dict(image=obj.get('image',''),source=obj['source'])

def scholar_directory():
 people=json.loads((study.ROOT/'web'/'scholar-profiles.json').read_text(encoding='utf-8'))
 path=study.ROOT/'local-data'/'scholar-tracking.json'
 try:tracked=json.loads(path.read_text(encoding='utf-8')).get('scholars',[])
 except (OSError,ValueError):tracked=[]
 for s in tracked:
  old=next((p for p in people if p['id']==s.get('personId') or p.get('en','').casefold()==s.get('author','').casefold()),None)
  if old:old.update(research=s.get('research',''),tracked=True)
  else:people.append(dict(id=s['id'],name=s.get('name',''),en=s.get('author',''),institution=s.get('org',''),source=s.get('source',''),research=s.get('research',''),tracked=True))
 with study.connection() as c:custom=study.records(c,'scholar')
 byid={p['id']:dict(p,revision=0,labIds=[]) for p in people}
 for p in custom:byid[p['id']]={**byid.get(p['id'],{}),**p}
 return dict(people=list(byid.values()))

def save_scholar(data):
 """Local directory entries; does not change external author-tracking settings."""
 people=scholar_directory()['people'];ident=data.get('id')
 base=next((p for p in people if p['id']==ident),None)
 if ident and not base:raise ValueError('学者不存在，请刷新后重试')
 old=base or dict(id='scholar-'+str(uuid.uuid4()),revision=0,createdAt=study.now())
 obj=dict(old)
 for key in ('name','en','institution','research'):
  obj[key]=study.text(data.get(key,old.get(key,'')),10000 if key=='research' else 300)
 if not obj['name']:raise ValueError('请填写学者姓名')
 for key in ('source','photoUrl'):
  obj[key]=study.url(data.get(key,old.get(key,'')))
  if obj[key] and not obj[key].startswith('https://'):raise ValueError('主页与头像链接请使用 HTTPS')
 ids=data.get('labIds',old.get('labIds',[]))
 if not isinstance(ids,list) or len(ids)>50 or any(not isinstance(i,str) for i in ids):raise ValueError('实验室选择无效')
 if any(p['id']!=obj['id'] and ((obj['en'] and p.get('en','').casefold()==obj['en'].casefold()) or (not obj['en'] and p.get('name')==obj['name'] and p.get('institution','')==obj['institution'])) for p in people):raise ValueError('这位学者已在列表中，可直接编辑现有档案')
 with study.connection() as c:
  row=c.execute("SELECT body FROM records WHERE kind='scholar' AND id=?",(obj['id'],)).fetchone()
  actual=json.loads(row[0]) if row else old
  if data.get('revision',0)!=actual.get('revision',0):raise ValueError('学者档案已在其他窗口更新，请刷新后重试')
  labs={l['id'] for l in study.records(c,'research-lab')}
  if any(i not in labs for i in ids):raise ValueError('所选实验室不存在，请刷新后重试')
  obj.update(labIds=list(dict.fromkeys(ids)),revision=actual.get('revision',0)+1,updatedAt=study.now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=0',('scholar',obj['id'],json.dumps(obj,ensure_ascii=False)))
 return obj
