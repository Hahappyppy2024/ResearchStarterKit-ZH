"""Explicit paper-author-lab associations, independent of reading completion."""
import json
import study_service as study
import workspace_content as content

def listing(paper_id=''):
 with study.connection() as c:
  items=study.records(c,'paper-affiliations');labs=study.records(c,'research-lab')
 if not paper_id:return dict(items=items)
 p=study.resolve('paper',paper_id)
 record=next((r for r in items if r['id']==paper_id),dict(id=paper_id,paperId=paper_id,revision=0,labIds=[],scholarIds=[],source='',affiliationText='',publicationStatus='auto',publishedVenue=''))
 record=dict(record,labIds=list(dict.fromkeys(record.get('labIds',[])+[l['id'] for l in labs if paper_id in l.get('paperIds',[])])))
 return dict(record=record,paper=p,labs=labs,people=content.scholar_directory()['people'])

def save(data):
 pid=study.text(data.get('paperId',''),200);study.resolve('paper',pid)
 people={p['id'] for p in content.scholar_directory()['people']}
 with study.connection() as c:
  rows=study.records(c,'paper-affiliations');old=next((r for r in rows if r['id']==pid),dict(id=pid,paperId=pid,revision=0,createdAt=study.now()))
  if data.get('revision',0)!=old['revision']:raise ValueError('论文关联已在其他窗口更新，请刷新后重试')
  obj=dict(old);labs=study.records(c,'research-lab');lab_ids={l['id'] for l in labs}
  for key,valid in [('labIds',lab_ids),('scholarIds',people)]:
   values=data.get(key,old.get(key,[]))
   if not isinstance(values,list) or len(values)>100 or any(not isinstance(v,str) or v not in valid for v in values):raise ValueError('请选择已有的实验室和学者，或先新增档案')
   obj[key]=list(dict.fromkeys(values))
  for key in ('affiliationText','publishedVenue'):obj[key]=study.text(data.get(key,old.get(key,'')),10000 if key=='affiliationText' else 300)
  obj['source']=study.url(data.get('source',old.get('source','')))
  obj['publicationStatus']=data.get('publicationStatus',old.get('publicationStatus','auto'))
  if obj['publicationStatus'] not in ('auto','published','preprint','unknown'):raise ValueError('论文发表状态无效')
  if obj['publicationStatus']=='published' and not obj['publishedVenue']:raise ValueError('请填写正式发表的会议或期刊名称')
  obj.update(revision=old['revision']+1,updatedAt=study.now())
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=0',('paper-affiliations',pid,json.dumps(obj,ensure_ascii=False)))
  # Maintain the existing lab editor links, in the same transaction.
  for lab in labs:
   ids=lab.get('paperIds',[]);selected=lab['id'] in obj['labIds']
   if selected==(pid in ids):continue
   lab['paperIds']=list(dict.fromkeys(ids+[pid])) if selected else [i for i in ids if i!=pid]
   lab.update(revision=lab.get('revision',0)+1,updatedAt=study.now())
   c.execute("UPDATE records SET body=? WHERE kind='research-lab' AND id=?",(json.dumps(lab,ensure_ascii=False),lab['id']))
 return obj
