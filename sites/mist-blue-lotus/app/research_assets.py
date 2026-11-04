"""Local methodology images and reusable datasets. All private files follow study.DB."""
import hashlib,json,re,uuid
import study_service as study

def datasets():
 import knowledge_service as k
 taxonomy=k.taxonomy()['nodes'];index={n['id']:n for n in taxonomy}
 with study.connection() as c:
  items=study.records(c,'dataset');knowledge=study.records(c,'paper-knowledge')
 for obj in items:
  obj['usedBy']=[dict(id=p['id'],title=p.get('title',p['id'])) for p in knowledge if obj['id'] in p.get('tasks',{}).get('datasets',{}).get('datasetIds',[])]
  obj['classifications']={key:[index[i] for i in obj.get(key,[]) if i in index] for key in ('topicIds','problemIds','solutionIds')}
  obj['sourcePapers']=[]
  for pid in obj.get('sourcePaperIds',[]):
   try:p=study.resolve('paper',pid);obj['sourcePapers'].append(dict(id=pid,title=p['title'],source=p.get('source','')))
   except ValueError:obj['sourcePapers'].append(dict(id=pid,title=pid,source=''))
 return dict(items=items)

def save_dataset(data):
 import knowledge_service as k
 index={n['id']:n for n in k.taxonomy()['nodes']}
 sources=data.get('sourcePaperIds',[])
 if not isinstance(sources,list) or len(sources)>30:raise ValueError('来源论文最多 30 篇')
 for pid in sources:study.resolve('paper',pid)
 with study.connection() as c:
  old=study.row(c,'dataset',data['id']) if data.get('id') else dict(id='dataset-'+str(uuid.uuid4()),revision=0,createdAt=study.now())
  if old['revision']!=data.get('revision',0):raise ValueError('数据集已更新，请重新打开编辑；当前表单仍保留')
  obj={**old}
  for key,limit in [('name',300),('en',300),('description',20000),('sourceCitation',5000),('usage',10000)]:obj[key]=study.text(data.get(key,old.get(key,'')),limit)
  if not obj['name']:raise ValueError('请填写数据集名称')
  obj['url']=study.url(data.get('url',old.get('url','')))
  for key,kind in [('topicIds','topic'),('problemIds','problem'),('solutionIds','solution')]:
   ids=data.get(key,old.get(key,[]))
   if not isinstance(ids,list) or len(ids)>100 or any(i not in index or index[i]['kind']!=kind for i in ids):raise ValueError('数据集分类无效')
   obj[key]=list(dict.fromkeys(ids))
   for ident in obj[key]:
    for n in k.ancestors(ident,list(index.values())):
     mapid=n.get('lineageId','taxonomy-'+n['id'])
     if not k.row_exists(c,'lineage',mapid):k.put(c,'lineage',dict(id=mapid,kind=n['kind'],name=n['name']+(' · '+n['en'] if n.get('en') else ''),description=n.get('definition',''),paperIds=[],paths=[],revision=1,createdAt=study.now()))
  obj.update(sourcePaperIds=list(dict.fromkeys(sources)),revision=old['revision']+1,updatedAt=study.now())
  k.put(c,'dataset',obj)
  for pid in obj['sourcePaperIds']:study.queue_paper(c,study.resolve('paper',pid),reason='数据集来源论文：'+obj['name'])
  return obj

def assign_dataset_topics(data):
 """Change classification only, without rescheduling source papers."""
 import knowledge_service as k
 index={n['id']:n for n in k.taxonomy()['nodes']}
 ids=data.get('topicIds')
 if not isinstance(ids,list) or len(ids)>100 or any(not isinstance(i,str) or i not in index or index[i]['kind']!='topic' for i in ids):raise ValueError('数据集主题分类无效')
 with study.connection() as c:
  old=study.row(c,'dataset',data.get('id',''))
  if old['revision']!=data.get('revision'):raise ValueError('数据集已更新，请刷新后重试')
  obj={**old,'topicIds':list(dict.fromkeys(ids)),'revision':old['revision']+1,'updatedAt':study.now()}
  k.put(c,'dataset',obj)
  return obj

def upload_figure(paper_id,raw):
 import knowledge_service as k
 study.resolve('paper',paper_id)
 if not raw or len(raw)>8*1024*1024:raise ValueError('请上传不超过 8 MB 的 PNG、JPEG 或 WebP 图片')
 if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw)>=24:ext,mime='png','image/png'
 elif raw.startswith(b'\xff\xd8\xff') and len(raw)>=20:ext,mime='jpg','image/jpeg'
 elif raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' and len(raw)>=20:ext,mime='webp','image/webp'
 else:raise ValueError('图片内容需为 PNG、JPEG 或 WebP；不接受 SVG 或其他文件')
 ident=str(uuid.uuid4());folder=study.DB.parent/'paper-methodology'/hashlib.sha256(paper_id.encode()).hexdigest()[:24];folder.mkdir(parents=True,exist_ok=True);path=folder/(ident+'.'+ext)
 with path.open('xb') as f:f.write(raw)
 obj=dict(id=ident,paperId=paper_id,mime=mime,extension=ext,createdAt=study.now(),size=len(raw))
 try:
  with study.connection() as c:k.put(c,'paper-figure',obj)
 except Exception:
  path.unlink();raise
 return obj

def figure_file(ident):
 if not re.fullmatch(r'[a-f0-9-]{36}',ident):raise ValueError('图片编号无效')
 with study.connection() as c:obj=study.row(c,'paper-figure',ident)
 path=study.DB.parent/'paper-methodology'/hashlib.sha256(obj['paperId'].encode()).hexdigest()[:24]/(ident+'.'+obj['extension'])
 if not path.is_file():raise ValueError('图片文件不存在，请重新上传')
 return path,obj['mime']
