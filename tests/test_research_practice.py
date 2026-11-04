import pathlib,tempfile,unittest
from unittest.mock import patch
import research_practice as service
class ResearchPracticeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.patches=[patch.object(service,'DB',pathlib.Path(self.temp.name)/'practice.sqlite'),patch.object(service,'today',return_value='2026-10-19'),patch.object(service,'context',return_value={'project':{'name':'Test project'},'papers':[],'week':'2026-10-12','selectionNote':'Test context'})]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_seven_days_rotate_and_remain_stable(self):
  methods=set()
  for date in ['2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25']:
   plan=service.get_day(date);self.assertEqual(len(plan['tasks']),3);self.assertEqual(service.get_day(date),plan)
   for task in plan['tasks']:
    self.assertEqual(len(task['steps']),3);self.assertTrue(task['output']);methods.add(task['method'])
  self.assertIn('最小复现',methods);self.assertIn('每周复盘',methods);self.assertIn('对比阅读',methods)
 def test_no_fake_history_and_invalid_date(self):
  self.assertEqual(service.get_day('2026-10-18')['tasks'],[])
  for date in ['2026-99-01','../../data','2026-1-1']:
   with self.assertRaises(ValueError):service.get_day(date)
 def test_outputs_status_and_conflicts(self):
  plan=service.get_day('2026-10-21');task=plan['tasks'][0];base=dict(date=plan['date'],id=task['id'],revision=task['revision'])
  with self.assertRaises(ValueError):service.save_task({**base,'content':'','status':'done'})
  saved=service.save_task({**base,'content':'Hypothesis not supported; log/path.txt','status':'done'})
  self.assertEqual(saved['revision'],2);self.assertEqual(saved['status'],'done')
  with self.assertRaises(ValueError):service.save_task({**base,'content':'overwrite','status':'done'})
  self.assertEqual(service.get_day(plan['date'])['tasks'][0]['content'],'Hypothesis not supported; log/path.txt')
  self.assertEqual(service.get_day('2026-10-22')['tasks'][0]['content'],'')
 def test_existing_assignment_keeps_original_project_and_papers(self):
  old=service.get_day('2026-10-21')
  with patch.object(service,'context',side_effect=RuntimeError('project changed')):self.assertEqual(service.get_day('2026-10-21'),old)
if __name__=='__main__':unittest.main()
