"""Daily local practice plans. Frozen snapshots preserve edits and review history."""
import contextlib,datetime,json,uuid
import learning_service as learning
from interview_bank import BANK,CATEGORIES
from interview_extra import EXTRA
from learning_taxonomy import DOMAINS,SOURCES
TZ=datetime.timezone(datetime.timedelta(hours=8))
def today():return datetime.datetime.now(TZ).date().isoformat()
def valid_date(value):
 try:d=datetime.date.fromisoformat(value)
 except (ValueError,TypeError):raise ValueError('请选择有效日期')
 if d.isoformat()!=value:raise ValueError('日期格式应为 YYYY-MM-DD')
 return d
@contextlib.contextmanager
def connection():
 with learning.connection() as c:
  c.execute('CREATE TABLE IF NOT EXISTS interview_bank(id TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS interview_days(date TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('BEGIN IMMEDIATE')
  for category,_ in CATEGORIES:
   for i,(question,answer) in enumerate(BANK[category]):
    body=dict(id=f'seed-{category}-{i}',category=category,domain='general',topic='通用基础',question=question,answer=answer,source=SOURCES['general'])
    c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
   for i,(domain,topic,question,answer) in enumerate(EXTRA[category]):
    body=dict(id=f'extra-{category}-{i}',category=category,domain=domain,topic=topic,question=question,answer=answer,source=SOURCES[domain])
    if topic=='FPN':body['source']='https://arxiv.org/abs/1612.03144'
    c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
  yield c
def get_day(date=None):
 date=date or today();day=valid_date(date)
 with connection() as c:
  bank=[json.loads(r[0]) for r in c.execute('SELECT body FROM interview_bank ORDER BY rowid')]
  existing=c.execute('SELECT body FROM interview_days WHERE date=?',(date,)).fetchone()
  if existing:plan=json.loads(existing[0])
  else:
   last_seen={}
   for r in c.execute('SELECT body FROM interview_days WHERE date<? ORDER BY date',(date,)):
    previous=json.loads(r[0])
    for card in previous['cards']:last_seen[card['bankId']]=previous['date']
   offset=(day-datetime.date(2026,10,20)).days;domains=[d for d,_ in DOMAINS];cards=[]
   for i,(category,_) in enumerate(CATEGORIES):
    group=[b for b in bank if b['category']==category];domain=domains[(offset+i)%len(domains)];pool=[b for b in group if b['domain']==domain] or group
    chosen=min(pool,key=lambda b:(last_seen.get(b['id'],''),b['id']))
    cards.append(dict(**{k:v for k,v in chosen.items() if k!='id'},id=str(uuid.uuid4()),bankId=chosen['id'],done=False,revision=1))
   plan=dict(date=date,cards=cards,createdAt=learning.now());c.execute('INSERT INTO interview_days VALUES(?,?)',(date,json.dumps(plan,ensure_ascii=False)))
  return {**plan,'today':today(),'categories':[dict(id=k,name=v) for k,v in CATEGORIES],'domains':[dict(id=k,name=v) for k,v in DOMAINS],'bankCount':len(bank),'bankCounts':{cat:sum(b['category']==cat for b in bank) for cat,_ in CATEGORIES}}
def save_card(data):
 date=data.get('date');valid_date(date)
 with connection() as c:
  row=c.execute('SELECT body FROM interview_days WHERE date=?',(date,)).fetchone()
  if not row:raise ValueError('当天题单不存在，请先打开该日期')
  plan=json.loads(row[0]);card=next((v for v in plan['cards'] if v['id']==data.get('id')),None)
  if not card:raise ValueError('题目不存在')
  if card['revision']!=data.get('revision'):raise ValueError('题目已在其他窗口修改，请重新读取题单')
  for field in ['question','answer']:
   if field in data:card[field]=learning.clean(data[field],10000 if field=='question' else 50000)
  if not card['question'].strip():raise ValueError('请填写问题')
  if 'done' in data:card['done']=data['done'] is True
  card['revision']+=1;card['updatedAt']=learning.now();c.execute('UPDATE interview_days SET body=? WHERE date=?',(json.dumps(plan,ensure_ascii=False),date));return card
def add_bank(data):
 category=data.get('category');domain=data.get('domain')
 if category not in dict(CATEGORIES) or domain not in dict(DOMAINS):raise ValueError('请选择有效的题型和方向')
 question=learning.clean(data.get('question',''),10000).strip();answer=learning.clean(data.get('answer',''),50000)
 if not question:raise ValueError('请填写问题')
 body=dict(id='custom-'+str(uuid.uuid4()),category=category,domain=domain,topic=learning.clean(data.get('topic','自定义'),160),question=question,answer=answer,source='',createdAt=learning.now())
 with connection() as c:c.execute('INSERT INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
 return body
