"""Daily batches survive midnight; completed batches feed an independent weekly quiz."""
import json,datetime
import interview_practice as ip

def setup(c):
 c.execute('CREATE TABLE IF NOT EXISTS learning_sessions(date TEXT PRIMARY KEY,body TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS learning_session_days(date TEXT PRIMARY KEY,origin TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS learning_completed_quizzes(date TEXT PRIMARY KEY,body TEXT NOT NULL)')

def status(origin,view):
 with ip.connection() as c:
  setup(c);r=c.execute('SELECT body FROM interview_evenings WHERE date=?',(origin,)).fetchone();cards=json.loads(r[0])['cards'] if r else []
  answered=sum(x.get('result') in ('correct','wrong') for x in cards);complete=bool(cards) and answered==len(cards)
  r=c.execute('SELECT body FROM learning_sessions WHERE date=?',(origin,)).fetchone();s=json.loads(r[0]) if r else dict(originDate=origin)
  if complete and not s.get('completedDate'):s.update(completedDate=view,snapshot=cards)
  s.update(status='completed' if complete else 'unfinished',answered=answered,total=len(cards))
  c.execute('INSERT OR REPLACE INTO learning_sessions VALUES(?,?)',(origin,json.dumps(s,ensure_ascii=False)))
  return {**s,'viewDate':view,'carried':origin!=view}

def session(date=None,mode='flash'):
 date=date or ip.today();ip.valid_date(date)
 with ip.connection() as c:
  setup(c);r=c.execute('SELECT origin FROM learning_session_days WHERE date=?',(date,)).fetchone()
  if r:
   origin=r[0];saved=c.execute('SELECT body FROM learning_sessions WHERE date=?',(origin,)).fetchone();previous=json.loads(saved[0]) if saved else {}
   if origin<date and previous.get('completedDate') and previous['completedDate']<date:
    origin=date;c.execute('UPDATE learning_session_days SET origin=? WHERE date=?',(origin,date))
  else:
   rows=[json.loads(x[0]) for x in c.execute('SELECT body FROM learning_sessions WHERE date<? ORDER BY date DESC',(date,))]
   previous=rows[0] if rows else None
   origin=previous['originDate'] if previous and previous.get('status')!='completed' else date
   c.execute('INSERT INTO learning_session_days VALUES(?,?)',(date,origin))
 evening=ip.get_evening(origin);daily=ip.get_day(origin)
 return {**(evening if mode=='evening' else daily),'viewDate':date,'session':status(origin,date)}

def submit(data):
 result=ip.submit_answer(data)
 if data.get('mode')=='evening':result['sessionStatus']=status(data['date'],data.get('sessionDate') or ip.today())
 return result

def weekly(date=None):
 date=date or ip.today();ip.valid_date(date);week=ip.week_start(date);end=(ip.valid_date(week)+datetime.timedelta(days=6)).isoformat()
 with ip.connection() as c:
  setup(c);completed=[json.loads(r[0]) for r in c.execute('SELECT body FROM learning_sessions')]
  completed=[s for s in completed if week<=s.get('completedDate','')<=min(date,end)]
  r=c.execute('SELECT body FROM learning_completed_quizzes WHERE date=?',(week,)).fetchone()
  plan=json.loads(r[0]) if r else dict(date=week,week=week,scheduledDate=end,cards=[],mode='completed-quiz')
  known={x['bankId'] for x in plan['cards']}
  for batch in completed:
   for card in batch.get('snapshot',[]):
    if card['bankId'] not in known:plan['cards'].append(ip.fresh_exam_card(card));known.add(card['bankId'])
  c.execute('INSERT OR REPLACE INTO learning_completed_quizzes VALUES(?,?)',(week,json.dumps(plan,ensure_ascii=False)))
  bank_count=len(ip.read_bank(c))
 # Read metadata without creating another daily batch.
 daily=ip.get_day(completed[0]['originDate']) if completed else dict(categories=[dict(id=k,name=v) for k,v in ip.CATEGORIES],domains=[dict(id=k,name=v) for k,v in ip.DOMAINS],bankCount=bank_count)
 with ip.connection() as c:return {**ip.exam_response(c,daily,plan,date),'date':date,'viewDate':date,'completedBatches':len(completed)}
