import unittest,tempfile,pathlib,json
import study_service as study,knowledge_service as k,learning_service as learning,learning_workflow as flow,interview_practice as ip
class KnowledgeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=study.DB;study.DB=pathlib.Path(self.tmp.name)/'study.sqlite'
 def tearDown(self):study.DB=self.old;self.tmp.cleanup()
 def test_hierarchy_and_paper(self):
  root=k.save_node(dict(kind='problem',name='小目标漏检',en='Small object misses'));child=k.save_node(dict(kind='problem',name='遥感',en='Remote sensing',parentId=root['id']));leaf=k.save_node(dict(kind='problem',name='农田',en='Farmland',parentId=child['id']))
  with self.assertRaises(ValueError):k.save_node(dict(kind='problem',name='第四层',en='Fourth',parentId=leaf['id']))
  with self.assertRaises(ValueError):k.save_node({**root,'parentId':leaf['id']})
  papers=study.atlas_papers();p,q=papers[:2];tasks={'problem':{'done':True,'answer':'my evidence'},'connections':{'references':[dict(id='ref-test',paperId=q['id'],paper=q['title'],relationTypes=['improves'])]}}
  definitions=json.loads((study.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'));tasks={**tasks,**{t['id']:{**tasks.get(t['id'],{}),'done':True} for t in definitions}}
  saved=k.save_paper(dict(paperId=p['id'],revision=0,problemIds=[leaf['id']],tasks=tasks,read=True));self.assertEqual(len(saved['ownedMaps']),3);self.assertEqual(k.edges([p['id']])[0]['types'],['improves']);quiz=k.paper_week();self.assertEqual(len(quiz['cards']),1)
  k.paper_attempt(dict(id=quiz['cards'][0]['id'],studentAnswer='test',verdict='review'));self.assertEqual(k.paper_week()['cards'][0]['verdict'],'review')
  updated=k.save_paper(dict(paperId=p['id'],revision=saved['revision'],problemIds=[],tasks=tasks));self.assertEqual(updated['ownedMaps'],[])
  changed={'problem':dict(done=False,answer='changed')}
  k.save_paper(dict(paperId=p['id'],revision=updated['revision'],tasks=changed));self.assertEqual(k.paper_week()['cards'][0]['reference'],'my evidence')
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=learning.DB;learning.DB=pathlib.Path(self.tmp.name)/'learning.sqlite'
 def tearDown(self):learning.DB=self.old;self.tmp.cleanup()
 def test_carry_and_week(self):
  a=flow.session('2026-10-20','evening');card=a['cards'][0];flow.submit(dict(date=a['date'],sessionDate='2026-10-20',mode='evening',id=card['id'],revision=card['revision'],studentAnswer='不知道'))
  b=flow.session('2026-10-21','evening');self.assertEqual(b['date'],a['date']);self.assertEqual(b['cards'][0]['result'],'wrong');self.assertEqual(b['session']['answered'],1);self.assertEqual(flow.weekly('2026-10-21')['cards'],[])
  flow.session('2026-10-22') # Viewing tomorrow early must not pin a completed old batch there.
  for card in b['cards'][1:]:flow.submit(dict(date=b['date'],sessionDate='2026-10-21',mode='evening',id=card['id'],revision=card['revision'],studentAnswer='不知道'))
  self.assertEqual(flow.session('2026-10-21','evening')['session']['status'],'completed');q=flow.weekly('2026-10-21');self.assertEqual(len(q['cards']),30)
  c=q['cards'][0];flow.submit(dict(date=q['date'],mode='completed-quiz',id=c['id'],revision=c['revision'],studentAnswer='不知道'));self.assertEqual(flow.weekly('2026-10-22')['cards'][0]['result'],'wrong');self.assertEqual(flow.session('2026-10-22')['date'],'2026-10-22')
if __name__=='__main__':unittest.main()
