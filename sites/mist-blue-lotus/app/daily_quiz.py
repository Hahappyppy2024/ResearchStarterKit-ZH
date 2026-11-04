"""Paper-owned flash cards and per-day attempts. Foundation quiz keeps its existing store."""
import json
import study_service as study
def selection(paper_id):
 study.resolve('paper',paper_id)
 with study.connection() as c:
  r=c.execute("SELECT body FROM records WHERE kind='paper-quiz-selection' AND id=?",(paper_id,)).fetchone()
 return json.loads(r[0]) if r else dict(id=paper_id,enabled=False,revision=0)
def select(data):
 study.resolve('paper',data.get('paperId'));enabled=data.get('enabled')
 if not isinstance(enabled,bool):raise ValueError('请选择是否加入每日 Quiz')
 with study.connection() as c:
  r=c.execute("SELECT body FROM records WHERE kind='paper-quiz-selection' AND id=?",(data['paperId'],)).fetchone();old=json.loads(r[0]) if r else dict(revision=0)
  if data.get('revision',0)!=old['revision']:raise ValueError('Quiz 选项已在其他窗口更改，请重新打开')
  obj=dict(id=data['paperId'],enabled=enabled,revision=old['revision']+1)
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',('paper-quiz-selection',obj['id'],json.dumps(obj,ensure_ascii=False)))
 return obj
def plan(date=None):
 date=study.valid_date(date or study.today())
 if date>study.today():raise ValueError('未来的 Quiz 尚未开始')
 import flash_review
 inventory=flash_review.inventory(date);previous=flash_review.states(inventory,date,inclusive=False)
 eligible={x['key']:x for x in inventory if x['enrolled'] and x['answer'].strip()}
 with study.connection() as c:
  enabled={s['id'] for s in study.records(c,'paper-quiz-selection') if s['enabled']};knowledge=study.records(c,'paper-knowledge')
  r=c.execute("SELECT body FROM records WHERE kind='daily-paper-quiz' AND id=?",(date,)).fetchone();obj=json.loads(r[0]) if r else dict(id=date,date=date,cards=[])
  known={card['key'] for card in obj['cards']}
  for key,card in eligible.items():
   if key in known or previous.get(key,{}).get('nextDue',date)>date:continue
   obj['cards'].append(dict(**{k:v for k,v in card.items() if k!='enrolled'},studentAnswer='',verdict='unanswered',revision=0));known.add(key)
  c.execute('INSERT INTO records VALUES(?,?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',('daily-paper-quiz',date,json.dumps(obj,ensure_ascii=False)))
  cards=[card for card in obj['cards'] if card['key'] in eligible]
 progress=flash_review.states(inventory,date)
 for card in cards:card['review']=progress.get(card['key'])
 cards.sort(key=lambda card:(previous.get(card['key'],{}).get('verdict')!='review',previous.get(card['key'],{}).get('nextDue','9999'),card['key']))
 return dict(date=date,cards=cards,selectedPapers=len(enabled),answered=sum(card['verdict'] in ('known','review') for card in cards))
def answer(data):
 date=study.valid_date(data.get('date',study.today()));visible=plan(date)
 if data.get('key') not in {card['key'] for card in visible['cards']}:raise ValueError('题目不在当天启用的论文 Quiz 中')
 text=study.text(data.get('studentAnswer',''),30000);verdict=data.get('verdict')
 if not text:raise ValueError('请先填写自己的答案；不会可以填写“不知道”')
 if verdict not in ('submitted','known','review'):raise ValueError('请选择自评结果')
 with study.connection() as c:
  obj=study.row(c,'daily-paper-quiz',date);card=next(card for card in obj['cards'] if card['key']==data['key'])
  if data.get('revision',0)!=card['revision']:raise ValueError('答案已在另一窗口更新，请刷新后核对')
  card.update(studentAnswer=text,verdict=verdict,revision=card['revision']+1,updatedAt=study.now())
  c.execute("UPDATE records SET body=? WHERE kind='daily-paper-quiz' AND id=?",(json.dumps(obj,ensure_ascii=False),date))
 import flash_review
 return dict(card,review=flash_review.states(flash_review.inventory(date),date).get(card['key']))
