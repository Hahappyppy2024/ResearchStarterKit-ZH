"""Dated questions left unresolved after reading, independent of paper completion."""
import uuid
import study_service as study

def listing(date=None,paper_id='',mode='all'):
 if date:date=study.valid_date(date)
 with study.connection() as c:all_items=study.records(c,'paper-question')
 if mode=='counts':
  counts={}
  for q in all_items:
   count=counts.setdefault(q['paperId'],dict(open=0,resolved=0))
   count['resolved' if q['resolved'] else 'open']+=1
  return dict(byPaper=counts)
 items=[q for q in all_items if not paper_id or q['paperId']==paper_id]
 if date:
  if mode=='daily':items=[q for q in items if q['date']<=date and (not q['resolved'] or q.get('resolvedDate')==date)]
  else:items=[q for q in items if q['date']==date]
 items.sort(key=lambda q:(q['resolved'],-int(q['date'].replace('-','')),q['paperTitle'],q['createdAt']))
 return dict(items=items,date=date,total=len(items),open=sum(not q['resolved'] for q in items),resolved=sum(q['resolved'] for q in items),allTotal=len(all_items),allOpen=sum(not q['resolved'] for q in all_items),allResolved=sum(q['resolved'] for q in all_items))

def save(data):
 ident=data.get('id');paper_id=data.get('paperId');paper=study.resolve('paper',paper_id)
 with study.connection() as c:
  c.execute('BEGIN IMMEDIATE')
  old=study.row(c,'paper-question',ident) if ident else {}
  if old and old['paperId']!=paper_id:raise ValueError('问题不属于这篇论文')
  if old and old['revision']!=data.get('revision'):raise ValueError('问题已在其他窗口更新，请刷新后核对；当前文字仍在页面')
  if old.get('deleted') and data.get('deleted') is not False:raise ValueError('问题已删除，请先撤销删除')
  question=study.text(data.get('question',old.get('question','')),10000)
  if not question:raise ValueError('请填写仍未理解的问题')
  date=old.get('date') or study.valid_date(data.get('date') or study.today())
  if date>study.today():raise ValueError('记录日期不能晚于今天')
  source=study.text(data.get('sourceId',old.get('sourceId','')),100)
  if not ident:
   duplicate=next((q for q in study.records(c,'paper-question') if q['paperId']==paper_id and (source and q.get('sourceId')==source or q['question']==question)),None)
   if duplicate:return duplicate
  obj=dict(id=ident or str(uuid.uuid4()),paperId=paper_id,paperTitle=paper['title'],question=question,answer=study.text(data.get('answer',old.get('answer','')),30000),date=date,sourceId=source,resolved=data.get('resolved',old.get('resolved',False)) is True,revision=old.get('revision',0)+1,createdAt=old.get('createdAt',study.now()),updatedAt=study.now())
  if obj['resolved']:obj['resolvedDate']=old.get('resolvedDate',study.today()) if old.get('resolved') else study.today()
  obj['deleted']=data.get('deleted',False) is True
  c.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=excluded.archived',('paper-question',obj['id'],__import__('json').dumps(obj,ensure_ascii=False),int(obj['deleted'])))
 return obj
