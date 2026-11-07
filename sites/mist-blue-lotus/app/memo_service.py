"""Private quick memos with optimistic edits and reversible deletion."""
import uuid,json,datetime
import study_service as study

def listing():
 with study.connection() as c:return {'items':study.records(c,'memo'),'trash':study.records(c,'memo',True)}

def save(data):
 with study.connection() as c:
  old=study.row(c,'memo',data['id']) if data.get('id') else dict(id=str(uuid.uuid4()),createdAt=study.now(),revision=0)
  if data.get('revision',0)!=old['revision']:raise ValueError('此随手记已在其他窗口更新，请刷新后再编辑；草稿仍保留')
  content=study.text(data.get('content',old.get('content','')),30000)
  if not content:raise ValueError('先写下一点内容吧')
  obj={**old,'content':content,'pinned':data.get('pinned',old.get('pinned',False)) is True,'updatedAt':study.now(),'revision':old['revision']+1}
  archived=1 if data.get('deleted',False) else 0
  c.execute("INSERT INTO records VALUES('memo',?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=excluded.archived",(obj['id'],json.dumps(obj,ensure_ascii=False),archived))
  sync_blog(c,memo_day(obj))
  return obj

def memo_day(item):
 return datetime.datetime.fromisoformat(item['createdAt']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()

def sync_blog(c,date):
 items=sorted((m for m in study.records(c,'memo') if memo_day(m)==date),key=lambda m:m['createdAt'])
 ident='memo-day-'+date;existing=c.execute("SELECT body FROM records WHERE kind='blog-post' AND id=?",(ident,)).fetchone()
 if not items:
  if existing:c.execute("UPDATE records SET archived=1 WHERE kind='blog-post' AND id=?",(ident,))
  return
 folder='memo-daily-folder';stamp=study.now()
 if not c.execute("SELECT 1 FROM records WHERE kind='blog-folder' AND id=?",(folder,)).fetchone():
  body=dict(id=folder,name='每日随手记',parentId='',revision=1,createdAt=stamp,updatedAt=stamp)
  c.execute("INSERT INTO records VALUES('blog-folder',?,?,0)",(folder,json.dumps(body,ensure_ascii=False)))
 content='\n\n---\n\n'.join('### '+datetime.datetime.fromisoformat(m['createdAt']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%H:%M')+'\n\n'+m['content'] for m in items)
 old=json.loads(existing[0]) if existing else {}
 body={**old,'id':ident,'title':date,'folderId':folder,'noteDate':date,'content':content,'tags':'Memo 随手记','paperIds':[],'deleted':False,'source':'daily-memo','createdAt':old.get('createdAt',items[0]['createdAt']),'updatedAt':stamp,'revision':old.get('revision',0)+1}
 if old.get('content')==content and old.get('title')==date:
  c.execute("UPDATE records SET archived=0 WHERE kind='blog-post' AND id=?",(ident,));return
 c.execute("INSERT INTO records VALUES('blog-post',?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=0",(ident,json.dumps(body,ensure_ascii=False)))

def backfill():
 with study.connection() as c:
  days={memo_day(m) for m in study.records(c,'memo')}
  for date in days:sync_blog(c,date)
 return len(days)
