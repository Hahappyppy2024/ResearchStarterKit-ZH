"""Local research-cat ledger: one lifetime reading reward per paper, explicit user spending."""
import contextlib,hashlib,json,pathlib,re,sqlite3,uuid
import study_service as study
DB=pathlib.Path(__file__).resolve().parent/'local-data'/'research-pet.sqlite'

@contextlib.contextmanager
def connection():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with contextlib.closing(sqlite3.connect(DB,timeout=30)) as c:
  c.executescript('CREATE TABLE IF NOT EXISTS rewards(id TEXT PRIMARY KEY,paper_id TEXT,title TEXT,at TEXT);CREATE TABLE IF NOT EXISTS reward_aliases(alias TEXT PRIMARY KEY,reward_id TEXT);CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,action TEXT,amount INTEGER,at TEXT);CREATE TABLE IF NOT EXISTS profile(id INTEGER PRIMARY KEY,body TEXT);CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY,paper_key TEXT UNIQUE,body TEXT,deleted INTEGER DEFAULT 0);')
  c.execute('BEGIN IMMEDIATE')
  try:yield c;c.commit()
  except BaseException:c.rollback();raise

def completed_items():
 import reading_journal
 with study.connection() as c:
  knowledge=study.records(c,'paper-knowledge');manual={p['id']:p for p in study.records(c,'paper-reading-status')};logs=study.records(c,'reading-log')
 ids={p['paperId'] for p in logs if p.get('paperId')}
 ids.update(p['id'] for p in knowledge if p.get('readDate') and reading_journal.complete(p))
 for ident,obj in manual.items():
  if obj.get('read'):ids.add(ident)
  elif ident not in {p.get('paperId') for p in logs}:ids.discard(ident)
 items=[]
 for ident in sorted(ids):
  try:items.append(study.resolve('paper',ident))
  except ValueError:continue
 return items

def aliases(paper):
 values={'id:'+paper['id']};title=re.sub(r'[^\w\u4e00-\u9fff]+','',paper.get('title','').casefold())
 if title:values.add('title:'+hashlib.sha256(title.encode()).hexdigest())
 for value in [paper['id'],paper.get('source',''),paper.get('pdf','')]:
  match=re.search(r'(?:arxiv-|/abs/|/pdf/)(\d{4}\.\d{4,5})',value)
  if match:values.add('arxiv:'+match[1])
 doi=str(paper.get('doi','')).casefold().strip().removeprefix('https://doi.org/')
 if doi:values.add('doi:'+doi)
 return values

def sync(c,items):
 for paper in items:
  keys=aliases(paper);found=c.execute('SELECT reward_id FROM reward_aliases WHERE alias IN ('+','.join('?' for _ in keys)+') LIMIT 1',list(keys)).fetchone()
  ident=found[0] if found else uuid.uuid4().hex
  if not found:c.execute('INSERT INTO rewards VALUES(?,?,?,?)',(ident,paper['id'],paper.get('title',''),study.now()))
  c.executemany('INSERT OR IGNORE INTO reward_aliases VALUES(?,?)',[(key,ident) for key in keys])

def progress(readings,published):
 stages=[('奶猫',0,0,0),('少年猫',5,0,1),('成年猫',20,0,2),('舞蹈伙伴',60,1,2),('音乐伙伴',150,3,2)]
 index=max(i for i,s in enumerate(stages) if readings>=s[1] and published>=s[2]);stage=stages[index]
 next_stage=stages[index+1] if index+1<len(stages) else None
 return dict(level=index,name=stage[0],sprite=stage[3],dance=readings>=5,hum=readings>=20 or published>=1,next=dict(name=next_stage[0],readings=next_stage[1],publications=next_stage[2],remainingReadings=max(0,next_stage[1]-readings),remainingPublications=max(0,next_stage[2]-published)) if next_stage else None)

def snapshot(c):
 readings=c.execute('SELECT count(*) FROM rewards').fetchone()[0]
 spent=c.execute("SELECT coalesce(sum(amount),0) FROM events WHERE action='exchange'").fetchone()[0];fed=c.execute("SELECT coalesce(sum(amount),0) FROM events WHERE action='feed'").fetchone()[0]
 publications=[json.loads(r[0]) for r in c.execute("SELECT body FROM publications WHERE deleted=0 ORDER BY json_extract(body,'$.date') DESC")]
 row=c.execute('SELECT body FROM profile WHERE id=1').fetchone();profile=json.loads(row[0]) if row else {'name':'小金'}
 return dict(name=profile['name'],readings=readings,shells=readings-spent,food=spent-fed,fed=fed,publications=publications,growth=progress(readings,len(publications)),rules='每篇首次完成阅读获得 1 枚贝壳；1 枚贝壳兑换 1 份猫粮。同一论文重复标记不重复奖励，已获得奖励保留。发表记录由本人登记，仅统计一作／共同一作。')

def state():
 items=completed_items()
 with connection() as c:sync(c,items);return snapshot(c)

def act(data):
 items=completed_items();action=data.get('action')
 with connection() as c:
  sync(c,items);current=snapshot(c)
  if action in ('exchange','feed'):
   ident=data.get('requestId','');amount=data.get('amount',1)
   if not isinstance(ident,str) or not re.fullmatch(r'[a-zA-Z0-9-]{8,80}',ident):raise ValueError('操作编号无效，请重试')
   if type(amount) is not int or not 1<=amount<=10000:raise ValueError('数量无效')
   previous=c.execute('SELECT action,amount FROM events WHERE id=?',(ident,)).fetchone()
   if previous:
    if previous!=(action,amount):raise ValueError('操作编号重复，请刷新重试')
    return snapshot(c)
   if amount>current['shells' if action=='exchange' else 'food']:raise ValueError('贝壳不足' if action=='exchange' else '猫粮不足，请先兑换')
   c.execute('INSERT INTO events VALUES(?,?,?,?)',(ident,action,amount,study.now()))
  elif action=='rename':
   name=study.text(data.get('name',''),30).strip()
   if not name:raise ValueError('请给小猫取个名字')
   c.execute('INSERT OR REPLACE INTO profile VALUES(1,?)',(json.dumps({'name':name},ensure_ascii=False),))
  elif action=='publication-add':
   title=study.text(data.get('title',''),500).strip();venue=study.text(data.get('venue',''),200).strip();date=study.valid_date(data.get('date',''));author=data.get('author','first');doi=study.text(data.get('doi',''),200).strip()
   if not title or not venue:raise ValueError('请填写发表论文标题和期刊／会议')
   if date>study.today():raise ValueError('这里只登记已经发表的论文，日期不能晚于今天')
   if author not in ('first','co-first'):raise ValueError('请选择一作或共同一作')
   key=''.join(title.casefold().split());found=c.execute('SELECT id,deleted FROM publications WHERE paper_key=?',(key,)).fetchone()
   if found and not found[1]:raise ValueError('这篇论文已经登记')
   ident=found[0] if found else uuid.uuid4().hex;obj=dict(id=ident,title=title,venue=venue,date=date,author=author,doi=doi,createdAt=study.now())
   c.execute('INSERT OR REPLACE INTO publications VALUES(?,?,?,0)',(ident,key,json.dumps(obj,ensure_ascii=False)))
  elif action in ('publication-remove','publication-restore'):
   ident=study.text(data.get('id',''),80)
   if not c.execute('SELECT 1 FROM publications WHERE id=?',(ident,)).fetchone():raise ValueError('发表记录不存在')
   c.execute('UPDATE publications SET deleted=? WHERE id=?',(int(action=='publication-remove'),ident))
  else:raise ValueError('操作无效')
  return snapshot(c)
