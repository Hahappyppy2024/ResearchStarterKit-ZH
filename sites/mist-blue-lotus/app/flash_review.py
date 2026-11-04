"""Content-aware review state derived from dated, self-assessed quiz snapshots."""
import datetime,json
import study_service as study
import learning_service as learning
INTERVALS=[1,3,7,14,30]

def inventory(date):
 cards=[]
 with study.connection() as c:
  enabled={x['id'] for x in study.records(c,'paper-quiz-selection') if x['enabled']}
  for p in study.records(c,'paper-knowledge'):
   for item in p.get('tasks',{}).get('flashcards',{}).get('items',[]):
    if not item.get('question','').strip():continue
    cards.append(dict(key=p['id']+':'+item['id'],paperId=p['id'],source='paper',title=p.get('title',''),question=item['question'],answer=item.get('answer',''),enrolled=p['id'] in enabled))
 with learning.connection() as c:
  modules={r[0]:json.loads(r[1]) for r in c.execute('SELECT id,body FROM modules')}
  for row in c.execute('SELECT body FROM flashcards'):
   item=json.loads(row[0]);m=modules.get(item['moduleId'])
   if not m or item.get('archived'):continue
   choices=m.get('quizCards',{});enrolled=item['id'] in choices[date] if date in choices else any(item['id'] in ids for day,ids in choices.items() if day<date)
   cards.append(dict(key='module:'+item['id'],paperId='module:'+m['id'],source='module',title=m['name']+' / '+m.get('en',''),question=item['question'],answer=item.get('answer',''),enrolled=enrolled))
 return cards

def states(cards,date,inclusive=True):
 by_key={x['key']:x for x in cards};result={}
 with study.connection() as c:days=sorted(study.records(c,'daily-paper-quiz'),key=lambda p:p['date'])
 for day in days:
  if day['date']>date or not inclusive and day['date']==date:continue
  for item in day['cards']:
   current=by_key.get(item['key'])
   if not current or (current['question'],current['answer'])!=(item['question'],item['answer']) or item['verdict'] not in ('known','review'):continue
   old=result.get(item['key'],{});streak=old.get('streak',0)+1 if item['verdict']=='known' else 0
   interval=INTERVALS[min(streak-1,len(INTERVALS)-1)] if streak else 1
   result[item['key']]=dict(verdict=item['verdict'],streak=streak,interval=interval,lastDate=day['date'],nextDue=(datetime.date.fromisoformat(day['date'])+datetime.timedelta(days=interval)).isoformat())
 return result

def statistics():
 date=study.today();cards=inventory(date);progress=states(cards,date);known=review=untested=due=0
 for card in cards:
  state=progress.get(card['key'])
  if state:known+=state['verdict']=='known';review+=state['verdict']=='review'
  else:untested+=1
  due+=bool(card['enrolled'] and card['answer'].strip() and (not state or state['nextDue']<=date))
 legacy=0
 with learning.connection() as c:
  tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if {'interview_bank','interview_attempts'}<=tables:
   import interview_practice
   bank=interview_practice.read_bank(c);latest=interview_practice.review_states(c,(datetime.date.fromisoformat(date)+datetime.timedelta(days=1)).isoformat())
   assigned=set()
   for table in ('interview_days','interview_evenings'):
    if table not in tables:continue
    row=c.execute(f'SELECT body FROM {table} WHERE date=?',(date,)).fetchone()
    if row:assigned.update(card.get('bankId') for card in json.loads(row[0]).get('cards',[]))
   for card in bank:
    legacy+=1;state=latest.get(card['id'])
    if state:known+=state['result']=='correct';review+=state['result']=='wrong';due+=state['nextDue']<=date
    else:untested+=1;due+=card['id'] in assigned
 return dict(date=date,total=len(cards)+legacy,known=known,review=review,untested=untested,due=due,paper=sum(c['source']=='paper' for c in cards),module=sum(c['source']=='module' for c in cards),legacy=legacy)
