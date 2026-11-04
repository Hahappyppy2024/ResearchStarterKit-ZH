"""One pearl fish per completed paper; release is explicit and idempotent."""
import contextlib,json,pathlib,sqlite3,uuid
import study_service as study
from research_pet import aliases

DB=pathlib.Path(__file__).resolve().parent/'local-data'/'research-pond.sqlite'

@contextlib.contextmanager
def connection():
 with contextlib.closing(sqlite3.connect(DB,timeout=30)) as c:
  c.executescript('CREATE TABLE IF NOT EXISTS fish(id TEXT PRIMARY KEY,paper_id TEXT,title TEXT,completed_date TEXT,released_at TEXT);CREATE TABLE IF NOT EXISTS aliases(alias TEXT PRIMARY KEY,fish_id TEXT);')
  c.execute('BEGIN IMMEDIATE')
  try:yield c;c.commit()
  except BaseException:c.rollback();raise

def completed_items():
 import reading_journal
 with study.connection() as c:records=study.records(c,'paper-knowledge')
 result=[]
 for r in records:
  if not r.get('readDate') or not reading_journal.complete(r):continue
  try:p=study.resolve('paper',r['id'])
  except ValueError:continue
  result.append({**p,'completedDate':r['readDate']})
 return result

def sync(c,items):
 active=set()
 for p in items:
  keys=aliases(p);found=c.execute('SELECT fish_id FROM aliases WHERE alias IN ('+','.join('?' for _ in keys)+') LIMIT 1',list(keys)).fetchone()
  ident=found[0] if found else uuid.uuid4().hex
  if not found:c.execute('INSERT INTO fish VALUES(?,?,?,?,NULL)',(ident,p['id'],p.get('titleZh') or p['title'],p['completedDate']))
  c.executemany('INSERT OR IGNORE INTO aliases VALUES(?,?)',[(k,ident) for k in keys]);active.add(ident)
 return active

def snapshot(c,active):
 rows=[dict(id=r[0],paperId=r[1],title=r[2],completedDate=r[3],releasedAt=r[4]) for r in c.execute('SELECT id,paper_id,title,completed_date,released_at FROM fish ORDER BY completed_date,id')]
 ready=[r for r in rows if not r['releasedAt'] and r['id'] in active];released=[r for r in rows if r['releasedAt']]
 return dict(ready=ready,released=released,readyCount=len(ready),releasedCount=len(released))

def state():
 with connection() as c:return snapshot(c,sync(c,completed_items()))

def release(data):
 ident=study.text(data.get('fishId',''),80)
 with connection() as c:
  active=sync(c,completed_items());row=c.execute('SELECT released_at FROM fish WHERE id=?',(ident,)).fetchone()
  if not row:raise ValueError('这条小鱼不存在，请刷新荷塘')
  if row[0]:return {**snapshot(c,active),'alreadyReleased':True}
  if ident not in active:raise ValueError('请先完成这篇论文的全部阅读任务')
  c.execute('UPDATE fish SET released_at=? WHERE id=? AND released_at IS NULL',(study.now(),ident))
  return {**snapshot(c,active),'alreadyReleased':False}
