import datetime,pathlib,tempfile,unittest
import learning_service as learning,interview_practice as service
class PracticeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=learning.DB;learning.DB=pathlib.Path(self.temp.name)/'learning.sqlite'
 def tearDown(self):learning.DB=self.old;self.temp.cleanup()
 def answer(self,date,card,text,**extra):return service.submit_answer({'date':date,'id':card['id'],'revision':card['revision'],'studentAnswer':text,**extra})
 def test_code_category_migrates_existing_thirty_and_preserves_evening(self):
  import json
  date='2026-10-20';plan=service.get_day(date)
  with service.connection() as db:
   bank=service.read_bank(db);old=[c for c in plan['cards'] if c['category']!='code'];chosen={c['bankId'] for c in old}
   for category,count in [('basic',2),('theory',2),('math',1),('ml',1)]:
    old.extend(service.make_card(b) for b in [b for b in bank if b['category']==category and b['id'] not in chosen][:count])
   plan.update(cards=old,version=3)
   evening=dict(date=date,mode='evening',version=3,cards=[service.fresh_exam_card(card) for card in old])
   evening['cards'][0].update(studentAnswer='My saved answer',result='correct',revision=2)
   db.execute('UPDATE interview_days SET body=? WHERE date=?',(json.dumps(plan),date))
   db.execute('INSERT INTO interview_evenings VALUES(?,?)',(date,json.dumps(evening)))
   db.execute('INSERT INTO interview_quizzes VALUES(?,?)',(service.week_start(date),json.dumps({**plan,'week':service.week_start(date),'scheduledDate':'2026-10-25'})))
  migrated=service.get_day(date);self.assertEqual(len(migrated['cards']),30);self.assertEqual(sum(c['category']=='code' for c in migrated['cards']),6)
  reopened=service.get_evening(date);saved=next(c for c in reopened['cards'] if c['id']==evening['cards'][0]['id'])
  self.assertEqual(saved['studentAnswer'],'My saved answer');self.assertEqual(saved['revision'],2)
  self.assertEqual([c['bankId'] for c in reopened['cards']],[c['bankId'] for c in migrated['cards']])
  self.assertEqual(len(reopened['previousPlans'][0]['cards']),30)
  quiz=service.get_week(date);self.assertEqual(len(quiz['cards']),30);self.assertEqual(sum(c['category']=='code' for c in quiz['cards']),6)
  code=next(c for c in reopened['cards'] if c['category']=='code')
  result=self.answer(date,code,code['answer'],mode='evening');self.assertEqual(result['result'],'correct');self.assertIn('不执行代码',result['feedback'])
 def test_authored_python_reference_algorithms(self):
  from interview_code import CODE
  cases=[(0,'two_sum',([2,7,11],9),(0,1)),(0,'two_sum',([3],6),None),(1,'stable_unique',([2,1,2,3],),[2,1,3]),(2,'lower_bound',([1,2,2,4],2),1),(2,'lower_bound',([],5),0),(3,'valid_brackets',('([{}])',),True),(3,'valid_brackets',('([)]',),False),(6,'merge_intervals',([[1,3],[2,5],[8,9]],),[[1,5],[8,9]]),(20,'iou',([0,0,2,2],[0,0,2,2]),1.0),(20,'iou',([0,0,0,0],[0,0,0,0]),0.0)]
  for index,name,args,expected in cases:
   namespace={};exec(CODE[index][2].split('\n\n')[0],namespace)
   self.assertEqual(namespace[name](*args),expected)
 def test_weekly_quiz_independent_stable_and_review(self):
  daily=service.get_day('2026-10-20');quiz=service.get_week('2026-10-20')
  self.assertEqual(quiz['week'],'2026-10-19');self.assertEqual(quiz['scheduledDate'],'2026-10-25')
  self.assertEqual(len(quiz['cards']),30)
  self.assertEqual({cat:sum(c['category']==cat for c in quiz['cards']) for cat in ['basic','theory','math','ml','code']},{'basic':6,'theory':6,'math':6,'ml':6,'code':6})
  self.assertTrue(set(c['id'] for c in daily['cards']).isdisjoint(c['id'] for c in quiz['cards']))
  card=quiz['cards'][0];wrong=self.answer('2026-10-20',card,'不知道',mode='quiz')
  reopened=service.get_week('2026-10-21');self.assertEqual(reopened['cards'][0]['id'],card['id']);self.assertEqual(reopened['cards'][0]['result'],'wrong')
  self.assertEqual(service.get_day('2026-10-20')['cards'][0]['result'],'unanswered')
  retry=next(c for c in service.get_day('2026-10-21')['cards'] if c['bankId']==card['bankId']);self.assertEqual(retry['selectionReason'],'retry')
  right=self.answer('2026-10-21',wrong,wrong['answer'],mode='quiz');self.assertEqual(right['result'],'correct')
  self.assertEqual(len(service.get_week('2026-10-21')['history']),2)
  next_week=service.get_week('2026-10-26');self.assertNotEqual(next_week['cards'][0]['id'],card['id'])
 def test_evening_matches_morning_and_remains_stable(self):
  morning=service.get_day('2026-10-20');exam=service.get_evening('2026-10-20')
  self.assertEqual([c['bankId'] for c in morning['cards']],[c['bankId'] for c in exam['cards']])
  self.assertTrue(set(c['id'] for c in morning['cards']).isdisjoint(c['id'] for c in exam['cards']))
  ml=next(c for c in exam['cards'] if c['category']=='ml')
  marked=self.answer(exam['date'],ml,ml['answer'],mode='evening');self.assertEqual(marked['result'],'correct')
  self.assertEqual(service.get_evening(exam['date'])['cards'][exam['cards'].index(ml)]['studentAnswer'],ml['answer'])
  self.assertEqual(next(c for c in service.get_day(exam['date'])['cards'] if c['bankId']==ml['bankId'])['result'],'unanswered')
  previous=service.get_day('2026-10-19');self.answer(previous['date'],previous['cards'][0],'不知道')
  self.assertEqual([c['bankId'] for c in service.get_day(exam['date'])['cards']],[c['bankId'] for c in morning['cards']])
  tomorrow=service.get_day('2026-10-21');self.assertIn(ml['bankId'],[c['bankId'] for c in tomorrow['cards']])
 def test_upgrade_ten_card_plans_keeps_answers(self):
  import json
  plan=service.get_day('2026-10-20');original=plan['cards'][:10];original[0]['edited']=True;original[0]['answer']='Personal reference'
  plan.update(cards=original,version=2)
  with service.connection() as db:db.execute('UPDATE interview_days SET body=? WHERE date=?',(json.dumps(plan),plan['date']))
  upgraded=service.get_day(plan['date']);self.assertEqual(len(upgraded['cards']),30)
  self.assertEqual([c['id'] for c in upgraded['cards'][:10]],[c['id'] for c in original]);self.assertEqual(upgraded['cards'][0]['answer'],'Personal reference')
  quiz=service.get_week(plan['date']);quiz['cards']=quiz['cards'][:10];quiz['cards'][0].update(studentAnswer='saved',result='correct')
  with service.connection() as db:db.execute('UPDATE interview_quizzes SET body=? WHERE date=?',(json.dumps(quiz),quiz['week']))
  upgraded_quiz=service.get_week(plan['date']);self.assertEqual(len(upgraded_quiz['cards']),30);self.assertEqual(upgraded_quiz['cards'][0]['studentAnswer'],'saved')
 def test_ten_questions_categories_and_stable_order(self):
  first=service.get_day('2026-10-20');self.assertEqual(len(first['cards']),30);self.assertEqual(first['bankCount'],134)
  self.assertEqual({cat:sum(c['category']==cat for c in first['cards']) for cat in ['basic','theory','math','ml','code']},{'basic':6,'theory':6,'math':6,'ml':6,'code':6})
  self.assertEqual(service.get_day(first['date'])['cards'],first['cards'])
  with self.assertRaises(ValueError):self.answer(first['date'],first['cards'][3],'')
  with self.assertRaises(ValueError):self.answer(first['date'],first['cards'][3],'',override='correct')
  self.answer(first['date'],first['cards'][3],'不知道')
  self.assertEqual([c['id'] for c in first['cards']],[c['id'] for c in service.get_day(first['date'])['cards']])
 def test_wrong_carries_into_precreated_tomorrow(self):
  plan=service.get_day('2026-10-20');service.get_day('2026-10-21');wrong=self.answer(plan['date'],plan['cards'][0],'不知道')
  self.assertEqual(wrong['result'],'wrong');self.assertEqual(wrong['review']['nextDue'],'2026-10-21')
  future=service.get_day('2026-10-21');retry=next(c for c in future['cards'] if c['bankId']==wrong['bankId'])
  self.assertEqual(retry['selectionReason'],'retry');self.assertEqual(retry['studentAnswer'],'');self.assertEqual(len(future['cards']),30)
 def test_correct_retention_and_spaced_review(self):
  plan=service.get_day('2026-10-20');card=plan['cards'][0];right=self.answer(plan['date'],card,card['answer'])
  self.assertEqual(right['result'],'correct');self.assertEqual(right['review']['nextDue'],'2026-10-21')
  future=service.get_day('2026-10-21');review=next(c for c in future['cards'] if c['bankId']==right['bankId'])
  right2=self.answer(future['date'],review,review['answer']);self.assertEqual(right2['review']['interval'],3);self.assertEqual(right2['review']['nextDue'],'2026-10-24')
  self.assertEqual(service.get_day(plan['date'])['cards'][0]['studentAnswer'],card['answer'])
 def test_marking_and_manual_correction_keep_audit(self):
  plan=service.get_day('2026-10-20');m=next(c for c in plan['cards'] if c['category']=='math')
  right=self.answer(plan['date'],m,m['grading']['aliases'][0]);self.assertEqual(right['result'],'correct')
  wrong=self.answer(plan['date'],right,'999999');self.assertEqual(wrong['result'],'wrong')
  fixed=self.answer(plan['date'],wrong,'',override='correct');self.assertEqual(fixed['result'],'correct');self.assertEqual(fixed['review']['streak'],1)
  with service.connection() as db:
   self.assertEqual(db.execute('SELECT COUNT(*) FROM interview_attempts').fetchone()[0],3);ai=service.bank_row(db,'seed-simple-0')
  self.assertEqual(service.judge(ai,'AI 是人工智能，机器学习是其中一类方法，深度学习又是机器学习的一类。')[0],'correct')
  self.assertEqual(service.judge(ai,'人工智能是机器学习的子集，深度学习也在其中。')[0],'wrong')
  with self.assertRaises(ValueError):self.answer(plan['date'],m,'old revision')
 def test_legacy_records_and_custom_bank_preserved(self):
  import interview_service as legacy
  old=legacy.get_day('2026-10-19');card=old['cards'][0]
  legacy.save_card({'date':old['date'],'id':card['id'],'revision':card['revision'],'answer':'旧版个人记录','done':True})
  new=service.get_day(old['date']);self.assertEqual(len(new['cards']),30);self.assertEqual(new['legacyPlan']['cards'][0]['answer'],'旧版个人记录')
  self.assertTrue(all(c['result']=='unanswered' for c in new['cards']))
  service.add_bank({'category':'math','domain':'cv','topic':'custom','question':'1+1?','answer':'2','grading':{'mode':'exact','aliases':['2']}})
  self.assertEqual(service.get_day(old['date'])['bankCount'],135);self.assertEqual([c['id'] for c in new['cards']],[c['id'] for c in service.get_day(old['date'])['cards']])
  with self.assertRaises(ValueError):service.add_bank({'category':'simple','domain':'cv','question':'Q'})
  self.assertEqual(service.TZ.utcoffset(None),datetime.timedelta(hours=8))
if __name__=='__main__':unittest.main()
