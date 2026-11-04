"""Thirty-card practice, local rubric marking and durable spaced review."""
import contextlib,datetime,json,math,re,unicodedata,uuid,hashlib
from fractions import Fraction
import learning_service as learning
from interview_bank import BANK,CATEGORIES as OLD_CATEGORIES
from interview_extra import EXTRA
from interview_math import MATH,RUBRICS
from interview_ml import ML,SOURCE as ML_SOURCE
from interview_code import CODE
from learning_taxonomy import DOMAINS,SOURCES
TZ=datetime.timezone(datetime.timedelta(hours=8))
CATEGORIES=[('basic','基础面试题'),('theory','理论面试题'),('math','数学面试题'),('ml','机器学习面试题'),('code','代码面试题')]
QUOTAS={'basic':6,'theory':6,'math':6,'ml':6,'code':6}
PLAN_VERSION=4
DAILY_COUNT=30
INTERVALS=[1,3,7,14,30]
def today():return datetime.datetime.now(TZ).date().isoformat()
def valid_date(value):
 try:d=datetime.date.fromisoformat(value)
 except (ValueError,TypeError):raise ValueError('请选择有效日期')
 if d.isoformat()!=value:raise ValueError('日期格式应为 YYYY-MM-DD')
 return d
def normalized(value):
 value=unicodedata.normalize('NFKC',value).lower().replace('−','-').replace('×','x')
 return re.sub(r'[\s。；;：:，]','',value)
def validate_grading(value,answer):
 if value is None:return {'mode':'concepts','groups':[]}
 if not isinstance(value,dict) or value.get('mode') not in ('exact','concepts'):raise ValueError('判题方式无效')
 if value['mode']=='exact':
  aliases=value.get('aliases',[])
  if not isinstance(aliases,list) or len(aliases)>30 or any(not isinstance(v,str) or not v.strip() or len(v)>1000 for v in aliases):raise ValueError('可接受答案格式无效')
  return {'mode':'exact','aliases':aliases or [answer]}
 groups=value.get('groups',[])
 if not isinstance(groups,list) or len(groups)>30 or any(not isinstance(g,list) or not g or len(g)>20 or any(not isinstance(v,str) or not v.strip() or len(v)>300 for v in g) for g in groups):raise ValueError('每个判题要点需包含至少一个有效关键词')
 return {'mode':'concepts','groups':groups}
@contextlib.contextmanager
def connection():
 with learning.connection() as c:
  c.execute('CREATE TABLE IF NOT EXISTS interview_bank(id TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS interview_days(date TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS interview_attempts(id TEXT PRIMARY KEY, bank_id TEXT NOT NULL, practice_date TEXT NOT NULL, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS interview_quizzes(date TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS interview_evenings(date TEXT PRIMARY KEY, body TEXT NOT NULL)')
  c.execute('BEGIN IMMEDIATE')
  for category,_ in OLD_CATEGORIES:
   for i,(question,answer) in enumerate(BANK[category]):
    body=dict(id=f'seed-{category}-{i}',category=category,domain='general',topic='通用基础',question=question,answer=answer,source=SOURCES['general'])
    c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
   for i,(domain,topic,question,answer) in enumerate(EXTRA[category]):
    body=dict(id=f'extra-{category}-{i}',category=category,domain=domain,topic=topic,question=question,answer=answer,source=SOURCES[domain])
    c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
  for r in c.execute('SELECT id,body FROM interview_bank').fetchall():
   b=json.loads(r[1]);changed=False
   if b.get('category') not in dict(CATEGORIES):
    old=b['category'];b.setdefault('originalCategory',old);b['category']='basic' if old=='simple' else 'theory';b['active']=old!='project';changed=True
   if 'grading' not in b:b['grading']={'mode':'concepts','groups':RUBRICS.get(b['id'],[])};changed=True
   if changed:c.execute('UPDATE interview_bank SET body=? WHERE id=?',(json.dumps(b,ensure_ascii=False),b['id']))
  for i,(topic,question,answer,aliases) in enumerate(MATH):
   b=dict(id=f'math-{i:02}',category='math',domain='general',topic=topic,question=question,answer=answer,source='',grading={'mode':'exact','aliases':aliases})
   c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(b['id'],json.dumps(b,ensure_ascii=False)))
  for i,(topic,question,answer,groups) in enumerate(ML):
   b=dict(id=f'ml-{i:02}',category='ml',domain='general',topic=topic,question=question,answer=answer,source=ML_SOURCE,grading={'mode':'concepts','groups':groups})
   c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(b['id'],json.dumps(b,ensure_ascii=False)))
  for i,(topic,question,answer,groups,source) in enumerate(CODE):
   b=dict(id=f'code-{i:02}',category='code',domain='general',topic=topic,question=question,answer=answer,source=source,grading={'mode':'concepts','groups':groups})
   c.execute('INSERT OR IGNORE INTO interview_bank VALUES(?,?)',(b['id'],json.dumps(b,ensure_ascii=False)))
  yield c
def read_bank(c):return [json.loads(r[0]) for r in c.execute('SELECT body FROM interview_bank ORDER BY rowid') if json.loads(r[0]).get('active',True)]
def bank_row(c,ident):
 r=c.execute('SELECT body FROM interview_bank WHERE id=?',(ident,)).fetchone()
 if not r:raise ValueError('题库题目不存在')
 return json.loads(r[0])
def review_states(c,before=None):
 states={}
 query='SELECT body FROM interview_attempts'+(' WHERE practice_date<?' if before else '')+' ORDER BY practice_date,rowid'
 for row in c.execute(query,(before,) if before else ()):
  a=json.loads(row[0]);old=states.get(a['bankId'],{});correct=a['verdict']=='correct'
  streak=(old.get('streak',0) if old.get('lastDate')==a['date'] and old.get('result')=='correct' else old.get('streak',0)+1) if correct and old.get('result')=='correct' else 1 if correct else 0
  interval=INTERVALS[min(streak-1,len(INTERVALS)-1)] if correct else 1
  states[a['bankId']]={'result':a['verdict'],'lastDate':a['date'],'nextDue':(valid_date(a['date'])+datetime.timedelta(days=interval)).isoformat(),'streak':streak,'interval':interval,'content':a.get('content',{})}
 return states
def make_card(b,old=None,reason='new',state=None):
 card={**{k:v for k,v in b.items() if k not in ('id','active')},'id':str(uuid.uuid4()),'bankId':b['id'],'done':False,'revision':1,'studentAnswer':'','result':'unanswered','selectionReason':reason}
 if state and reason!='new':card.update(state.get('content',{}))
 if old:
  card.update(old);card['category']=b['category'];card['grading']=old.get('grading',b['grading'])
  if 'result' not in old:card.update(done=False,result='unanswered',studentAnswer='',legacyReadFlag=old.get('done',False))
  if state and reason!='new' and not old.get('edited') and old.get('result','unanswered')=='unanswered':
   content=state.get('content',{})
   if any(card.get(k)!=v for k,v in content.items()):card['revision']+=1
   card.update(content)
 card['selectionReason']=reason
 return card
def protected(card):
 return card.get('result') in ('correct','wrong') or card.get('edited') or bool(card.get('studentAnswer'))

def snapshot_plan(plan):
 if plan.get('cards'):
  plan.setdefault('previousPlans',[]).append(dict(version=plan.get('version'),cards=plan['cards'],savedAt=learning.now()))

def ensure_plan(c,date,bank):
 record=c.execute('SELECT body FROM interview_days WHERE date=?',(date,)).fetchone();plan=json.loads(record[0]) if record else {'date':date,'cards':[],'createdAt':learning.now()}
 old_cards=plan['cards'];by_id={b['id']:b for b in bank};old_by_bank={v['bankId']:v for v in old_cards}
 upgrading=plan.get('version')!=PLAN_VERSION
 if upgrading:
  snapshot_plan(plan)
  if old_cards and 'legacyPlan' not in plan:plan['legacyPlan']={'cards':old_cards,'createdAt':plan.get('createdAt')}
  plan['version']=PLAN_VERSION
 states=review_states(c,date)
 signature=hashlib.sha256(json.dumps(states,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 if not upgrading and len(old_cards)==DAILY_COUNT and (plan.get('selectionSignature')==signature or c.execute('SELECT 1 FROM interview_evenings WHERE date=?',(date,)).fetchone()):return plan
 cards=[];chosen=set();last_seen={}
 for row in c.execute('SELECT body FROM interview_days WHERE date<? ORDER BY date',(date,)):
  previous=json.loads(row[0])
  for item in previous['cards']:last_seen[item['bankId']]=previous['date']
 def add(b,reason='new',state=None):
  if b['id'] in chosen or len(cards)>=DAILY_COUNT:return
  chosen.add(b['id']);cards.append(make_card(b,old_by_bank.get(b['id']),reason,state))
 # Keep completed/edited evening questions during a category migration as well.
 evening=c.execute('SELECT body FROM interview_evenings WHERE date=?',(date,)).fetchone()
 evening_protected={v['bankId'] for v in json.loads(evening[0])['cards'] if protected(v)} if evening else set()
 for old in old_cards:
  if old['bankId'] in by_id and (protected(old) or old['bankId'] in evening_protected):add(by_id[old['bankId']],old.get('selectionReason','new'),states.get(old['bankId']))
 due=[(ident,state) for ident,state in states.items() if ident in by_id and state['nextDue']<=date]
 due.sort(key=lambda item:(item[1]['result']!='wrong',item[1]['nextDue'],item[1]['lastDate'],item[0]))
 for ident,state in due:add(by_id[ident],'retry' if state['result']=='wrong' else 'review',state)
 if upgrading:
  for old in old_cards:
   if old['bankId'] in by_id and sum(v['category']==by_id[old['bankId']]['category'] for v in cards)<QUOTAS[by_id[old['bankId']]['category']]:add(by_id[old['bankId']],old.get('selectionReason','new'),states.get(old['bankId']))
 offset=(valid_date(date)-datetime.date(2026,10,20)).days;domains=[d for d,_ in DOMAINS]
 def pick(category):
  available=[b for b in bank if b['category']==category and b['id'] not in chosen]
  if not available:return None
  # A new day's fresh questions come from different knowledge directions.
  target=domains[(offset+len(cards))%len(domains)]
  available.sort(key=lambda b:(b['id'] in states,last_seen.get(b['id'],''),b['domain']!=target,b['id']))
  return available[0]
 for category,_ in CATEGORIES:
  while len(cards)<DAILY_COUNT and sum(v['category']==category for v in cards)<QUOTAS[category]:
   b=pick(category)
   if not b:break
   add(b,'review' if b['id'] in states else 'new',states.get(b['id']))
 while len(cards)<DAILY_COUNT:
  b=next((pick(category) for category,_ in CATEGORIES if pick(category)),None)
  if not b:break
  add(b,'review' if b['id'] in states else 'new',states.get(b['id']))
 order={v['bankId']:i for i,v in enumerate(old_cards)};new_order={v['bankId']:i for i,v in enumerate(cards)}
 cards.sort(key=lambda v:order.get(v['bankId'],100+new_order[v['bankId']]))
 plan['selectionSignature']=signature;plan['cards']=cards;plan['deferredDue']=max(0,len([ident for ident,_ in due if ident not in chosen]));plan['updatedAt']=learning.now()
 c.execute('INSERT INTO interview_days VALUES(?,?) ON CONFLICT(date) DO UPDATE SET body=excluded.body',(date,json.dumps(plan,ensure_ascii=False)))
 return plan
def get_day(date=None):
 date=date or today();valid_date(date)
 with connection() as c:
  bank=read_bank(c);plan=ensure_plan(c,date,bank);states=review_states(c,(valid_date(date)+datetime.timedelta(days=1)).isoformat())
  cards=[{**card,'review':states.get(card['bankId'])} for card in plan['cards']]
  wanted={v['bankId'] for v in cards};history=[]
  for row in c.execute('SELECT body FROM interview_attempts WHERE practice_date<=? ORDER BY practice_date,rowid',(date,)):
   attempt=json.loads(row[0])
   if attempt['bankId'] in wanted:history.append({k:v for k,v in attempt.items() if k!='content'})
  return {**plan,'cards':cards,'history':history,'today':today(),'categories':[dict(id=k,name=v) for k,v in CATEGORIES],'domains':[dict(id=k,name=v) for k,v in DOMAINS],'bankCount':len(bank),'bankCounts':{cat:sum(b['category']==cat for b in bank) for cat,_ in CATEGORIES},'intervals':INTERVALS}
def get_card(c,data):
 date=data.get('date');valid_date(date);table,key=plan_location(data.get('mode'),date);row=c.execute(f'SELECT body FROM {table} WHERE date=?',(key,)).fetchone()
 if not row:raise ValueError('请先打开当天题单')
 plan=json.loads(row[0]);plan['date']=date;card=next((v for v in plan['cards'] if v['id']==data.get('id')),None)
 if not card:raise ValueError('题目不存在，请刷新题单')
 if card['revision']!=data.get('revision'):raise ValueError('题目已在其他窗口更新，请重新打开题单')
 return plan,card
def contains(text,word):
 word=word.casefold()
 if word.isascii() and len(word)<=2:return bool(re.search(r'(?<![a-z0-9])'+re.escape(word)+r'(?![a-z0-9])',unicodedata.normalize('NFKC',text).lower()))
 return normalized(word) in normalized(text)
def numeric(text):
 text=normalized(text)
 for prefix in ['最终结果=','最终结果','结果=','结果','答案=','答案']:text=text.removeprefix(prefix)
 if len(text)>120:return None
 try:
  value=float(Fraction(text[:-1]))/100 if text.endswith('%') else float(Fraction(text))
  return value if math.isfinite(value) else None
 except (ValueError,ZeroDivisionError,OverflowError):return None
def judge(card,answer):
 if normalized(answer)==normalized(card['answer']):return 'correct','与参考答案一致。'
 if any(word in answer for word in ['不知道','不清楚','忘记了','完全不会']):return 'wrong','已记为不会，下一天优先重做。'
 rubric=card.get('grading',{});mode=rubric.get('mode','concepts')
 if mode=='exact':
  aliases=rubric.get('aliases') or [card['answer']];value=numeric(answer)
  if any(normalized(answer)==normalized(v) or value is not None and numeric(v) is not None and math.isclose(value,numeric(v),rel_tol=1e-4,abs_tol=1e-6) for v in aliases):return 'correct','最终结果匹配（允许合理数值误差）。'
  return 'wrong','最终结果未匹配。请查看解答；计算题可只填写最终数值、分数或规定格式。'
 groups=rubric.get('groups',[])
 forbidden=['人工智能是机器学习的子集','人工智能是机器学习的一部分','推理时需要更新参数','推理时必须更新参数']
 if any(phrase in normalized(answer) for phrase in forbidden):return 'wrong','检测到与核心概念冲突的表述，暂记为不会。'
 if not groups:return 'wrong','本题未配置判题要点，且未与参考答案匹配，暂记不会。可补充判题要点或手动更正。'
 missing=[g for g in groups if not any(contains(answer,word) for word in g)]
 if missing:return 'wrong','覆盖 '+str(len(groups)-len(missing))+'/'+str(len(groups))+' 个要点；未识别：'+'、'.join(g[0] for g in missing)+'。本机要点匹配可能误判，可手动更正。'
 return 'correct','已覆盖配置的全部关键要点（本机辅助判定；不代表完整语义核验）。'
def submit_answer(data):
 with connection() as c:
  plan,card=get_card(c,data);manual=data.get('override')
  if manual:
   if manual not in ('correct','wrong') or card.get('result') not in ('correct','wrong'):raise ValueError('请先输入答案并提交，再更正判定')
   answer=card.get('studentAnswer','');verdict=manual;reason='手动更正为'+('答对' if manual=='correct' else '不会')+'。'
  else:
   answer=learning.clean(data.get('studentAnswer',''),30000).strip()
   if not answer:raise ValueError('请先输入你的答案；不会时可以填写“不知道”')
   verdict,reason=judge(card,answer)
  if card['category']=='code':reason+=' 代码题仅核对文本要点，不执行代码，也不验证运行结果；可手动更正。'
  ident=str(uuid.uuid4());content={k:card[k] for k in ('question','answer','grading','category','domain','topic') if k in card}
  actual_date=data.get('sessionDate') or data['date'] if data.get('mode') in ('evening','completed-quiz') else plan['date']
  valid_date(actual_date)
  attempt=dict(mode=data.get('mode','flash'),id=ident,bankId=card['bankId'],cardId=card['id'],date=actual_date,studentAnswer=answer,verdict=verdict,reason=reason,manual=bool(manual),content=content,createdAt=learning.now())
  c.execute('INSERT INTO interview_attempts VALUES(?,?,?,?)',(ident,card['bankId'],actual_date,json.dumps(attempt,ensure_ascii=False)))
  card.update(studentAnswer=answer,result=verdict,feedback=reason,attemptId=ident,done=True,revision=card['revision']+1,submittedAt=learning.now())
  store_plan(c,plan,data)
  state=review_states(c,(valid_date(actual_date)+datetime.timedelta(days=1)).isoformat()).get(card['bankId'])
  return {**card,'review':state,'historyEntry':{k:v for k,v in attempt.items() if k!='content'}}
def save_card(data):
 with connection() as c:
  plan,card=get_card(c,data)
  for field in ['question','answer']:
   if field in data:card[field]=learning.clean(data[field],10000 if field=='question' else 50000)
  if not card['question'].strip():raise ValueError('请填写问题')
  if 'grading' in data:card['grading']=validate_grading(data['grading'],card['answer'])
  card['edited']=True;card['revision']+=1
  store_plan(c,plan,data);return card
def add_bank(data):
 category=data.get('category');domain=data.get('domain')
 if category not in dict(CATEGORIES) or domain not in dict(DOMAINS):raise ValueError('请选择有效的题型和方向')
 question=learning.clean(data.get('question',''),10000).strip();answer=learning.clean(data.get('answer',''),50000)
 if not question:raise ValueError('请填写问题')
 body=dict(id='custom-'+str(uuid.uuid4()),category=category,domain=domain,topic=learning.clean(data.get('topic','自定义'),160),question=question,answer=answer,source='',grading=validate_grading(data.get('grading'),answer),createdAt=learning.now())
 with connection() as c:c.execute('INSERT INTO interview_bank VALUES(?,?)',(body['id'],json.dumps(body,ensure_ascii=False)))
 return body


def week_start(date):
 d=valid_date(date)
 return (d-datetime.timedelta(days=d.weekday())).isoformat()

def plan_location(mode,date):
 if mode not in (None,'flash','evening','quiz','completed-quiz'):raise ValueError('学习模式无效')
 if mode=='completed-quiz':return ('learning_completed_quizzes',week_start(date))
 return ('interview_quizzes',week_start(date)) if mode=='quiz' else ('interview_evenings',date) if mode=='evening' else ('interview_days',date)

def store_plan(c,plan,data):
 table,key=plan_location(data.get('mode'),plan['date'])
 c.execute(f'UPDATE {table} SET body=? WHERE date=?',(json.dumps(plan,ensure_ascii=False),key))

def exam_response(c,daily,plan,date):
 states=review_states(c,(valid_date(date)+datetime.timedelta(days=1)).isoformat())
 wanted={card['bankId'] for card in plan['cards']};history=[]
 for row in c.execute('SELECT body FROM interview_attempts WHERE practice_date<=? ORDER BY practice_date,rowid',(date,)):
  attempt=json.loads(row[0])
  if attempt['bankId'] in wanted:history.append({k:v for k,v in attempt.items() if k!='content'})
 return {**daily,**plan,'date':date,'history':history,'cards':[{**card,'review':states.get(card['bankId'])} for card in plan['cards']],'deferredDue':0,'legacyPlan':None}

def fresh_exam_card(source):
 card=make_card({'id':source['bankId'],**{k:v for k,v in source.items() if k in ('question','answer','grading','category','domain','topic','source')}},reason=source.get('selectionReason','new'))
 return card

def get_evening(date=None):
 date=date or today();valid_date(date);daily=get_day(date)
 with connection() as c:
  row=c.execute('SELECT body FROM interview_evenings WHERE date=?',(date,)).fetchone()
  if row:
   plan=json.loads(row[0])
   if plan.get('version')!=PLAN_VERSION:
    snapshot_plan(plan);old={card['bankId']:card for card in plan['cards']}
    plan['cards']=[old.get(card['bankId']) or fresh_exam_card(card) for card in daily['cards']];plan['version']=PLAN_VERSION
    c.execute('UPDATE interview_evenings SET body=? WHERE date=?',(json.dumps(plan,ensure_ascii=False),date))
  else:
   plan=dict(date=date,mode='evening',version=PLAN_VERSION,cards=[fresh_exam_card(card) for card in daily['cards']],createdAt=learning.now())
   c.execute('INSERT INTO interview_evenings VALUES(?,?)',(date,json.dumps(plan,ensure_ascii=False)))
  return exam_response(c,daily,plan,date)

def get_week(date=None):
 date=date or today();week=week_start(date);daily=get_day(date)
 with connection() as c:
  row=c.execute('SELECT body FROM interview_quizzes WHERE date=?',(week,)).fetchone()
  plan=json.loads(row[0]) if row else dict(date=date,week=week,scheduledDate=(valid_date(week)+datetime.timedelta(days=6)).isoformat(),cards=[],createdAt=learning.now(),mode='quiz')
  if len(plan['cards'])<DAILY_COUNT or plan.get('version')!=PLAN_VERSION:
   if plan.get('version')!=PLAN_VERSION:
    snapshot_plan(plan);retained=[card for card in plan['cards'] if protected(card)]
    for card in plan['cards']:
     if not protected(card) and sum(v['category']==card['category'] for v in retained)<QUOTAS[card['category']] and len(retained)<DAILY_COUNT:retained.append(card)
    order={card['id']:i for i,card in enumerate(plan['cards'])};retained.sort(key=lambda card:order[card['id']]);plan['cards']=retained
   bank=read_bank(c);by_id={b['id']:b for b in bank};states=review_states(c,(valid_date(date)+datetime.timedelta(days=1)).isoformat());pool=[]
   for row_day in c.execute('SELECT body FROM interview_days WHERE date>=? AND date<=? ORDER BY date DESC',(week,date)):
    for card in json.loads(row_day[0])['cards']:
     if card['bankId'] in by_id and card['bankId'] not in pool:pool.append(card['bankId'])
   # Re-test wrong material before learned material; fill only when the week has too few questions.
   pool.extend(b['id'] for b in bank if b['id'] not in pool)
   pool.sort(key=lambda ident:not (ident in states and states[ident]['result']=='wrong'))
   cards=plan['cards'];chosen={card['bankId'] for card in cards}
   for category,_ in CATEGORIES:
    needed=max(0,QUOTAS[category]-sum(card['category']==category for card in cards))
    for ident in [v for v in pool if v not in chosen and by_id[v]['category']==category][:needed]:
     state=states.get(ident);cards.append(make_card(by_id[ident],reason='retry' if state and state['result']=='wrong' else 'review' if state else 'new',state=state));chosen.add(ident)
   for ident in pool:
    if len(cards)>=DAILY_COUNT:break
    if ident not in chosen:cards.append(make_card(by_id[ident]));chosen.add(ident)
   plan['version']=PLAN_VERSION
   c.execute('INSERT INTO interview_quizzes VALUES(?,?) ON CONFLICT(date) DO UPDATE SET body=excluded.body',(week,json.dumps(plan,ensure_ascii=False)))
  return exam_response(c,daily,plan,date)
