"""Explicit read marks and checklist progress, stored separately on this computer."""
import json,re
import study_service as study

def identifiers(values):
 if not isinstance(values,list) or len(values)>200:raise ValueError('一次最多读取 200 篇论文')
 if any(not isinstance(i,str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,200}',i) for i in values):raise ValueError('论文编号无效')
 return list(dict.fromkeys(values))

def listing(ids):
 ids=identifiers(ids)
 definitions=json.loads((study.ROOT/'web/paper-task-definitions.json').read_text(encoding='utf-8'))
 with study.connection() as c:
  rows=c.execute("SELECT kind,id,body FROM records WHERE archived=0 AND kind IN ('paper-knowledge','paper-reading-status') AND id IN ("+','.join('?' for _ in ids)+')',ids).fetchall() if ids else []
 records={(r[0],r[1]):json.loads(r[2]) for r in rows};items=[]
 for ident in ids:
  knowledge=records.get(('paper-knowledge',ident),{});manual=records.get(('paper-reading-status',ident))
  done=sum(knowledge.get('tasks',{}).get(t['id'],{}).get('done') is True for t in definitions)
  complete=done==len(definitions);read=manual['read'] if manual else bool(complete and knowledge.get('readDate'))
  items.append(dict(id=ident,read=read,readDate=(manual or knowledge).get('readDate') if read else None,manual=manual is not None,done=done,total=len(definitions),tasksComplete=complete))
 return dict(items=items)

def save(data):
 ident=identifiers([data.get('paperId')])[0]
 if type(data.get('read')) is not bool:raise ValueError('请选择已读或未读')
 study.resolve('paper',ident)
 with study.connection() as c:
  row=c.execute("SELECT body FROM records WHERE kind='paper-reading-status' AND id=?",(ident,)).fetchone();old=json.loads(row[0]) if row else {}
  obj=dict(id=ident,read=data['read'],readDate=(old.get('readDate') if old.get('read') else None) or study.today() if data['read'] else None,updatedAt=study.now())
  c.execute("INSERT INTO records VALUES('paper-reading-status',?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=0",(ident,json.dumps(obj,ensure_ascii=False)))
 return listing([ident])['items'][0]

def featured():
 with study.connection() as c:return {p['id']:p['enabled'] for p in study.records(c,'paper-featured')}

def save_featured(data):
 ident=identifiers([data.get('paperId')])[0]
 if type(data.get('enabled')) is not bool:raise ValueError('精选状态无效')
 study.resolve('paper',ident)
 obj=dict(id=ident,enabled=data['enabled'],updatedAt=study.now())
 with study.connection() as c:
  c.execute("INSERT INTO records VALUES('paper-featured',?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body,archived=0",(ident,json.dumps(obj,ensure_ascii=False)))
 return obj
