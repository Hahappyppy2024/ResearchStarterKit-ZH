import csv,io,pathlib,tempfile,unittest
from unittest.mock import patch
import projects_service as s

class ProjectNotebookTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=patch.object(s,'DB_PATH',pathlib.Path(self.tmp.name)/'projects.sqlite');self.path.start()
  self.project=s.save_project({'name':'农业遥感实验','problem':'小目标漏检','goal':'验证改进'})
 def tearDown(self):self.path.stop();self.tmp.cleanup()
 def test_default_tasks_edit_archive_restore(self):
  tasks=s.project_detail(self.project['id'])['tasks'];self.assertEqual(len(tasks),6)
  task=s.save_task({**tasks[0],'done':True,'detail':'对照论文问题'})
  self.assertTrue(s.task_detail(task['id'])['task']['done'])
  s.archive({'kind':'task','id':task['id']});self.assertEqual(len(s.project_detail(self.project['id'])['tasks']),5)
  s.archive({'kind':'task','id':task['id'],'restore':True});self.assertEqual(len(s.project_detail(self.project['id'])['tasks']),6)
 def test_experiment_evidence_revision_and_chain(self):
  first=s.save_log({'projectId':self.project['id'],'date':'2026-10-20','name':'baseline','outcome':'not_supported','metrics':[{'name':'mAP','value':'0.32','unit':''}],'conclusion':'原始结果未支持假设'})
  second=s.save_log({'projectId':self.project['id'],'date':'2026-10-20','name':'增加分辨率','parentId':first['id'],'metrics':[{'name':'mAP','value':'0.36','unit':''}]})
  self.assertEqual((first['number'],second['number']),(1,2))
  with self.assertRaises(ValueError):s.save_log({**first,'parentId':second['id']})
  saved=s.save_log({**first,'notes':'保留失败证据'})
  with self.assertRaises(ValueError):s.save_log({**first,'notes':'过期窗口'})
  self.assertEqual(saved['outcome'],'not_supported')
  s.archive({'kind':'log','id':first['id']})
  third=s.save_log({'projectId':self.project['id'],'date':'2026-10-21','name':'后续'})
  self.assertEqual(third['number'],3)
 def test_exports_and_project_recovery(self):
  s.save_log({'projectId':self.project['id'],'date':'2026-10-20','name':'失败实验','command':'python train.py --seed 42','outcome':'blocked','notes':'报错\n排查过程','metrics':[{'name':'速度','value':'12','unit':'FPS'}]})
  md=s.export_project(self.project['id'],'md');self.assertIn('失败实验',md);self.assertIn('python train.py --seed 42',md)
  rows=list(csv.reader(io.StringIO(s.export_project(self.project['id'],'csv').lstrip('\ufeff'))));self.assertEqual(len(rows),2);self.assertIn('报错\n排查过程',rows[1]);self.assertEqual(rows[1][-1],'blocked')
  s.archive({'kind':'project','id':self.project['id']});self.assertEqual(s.list_projects(),[]);self.assertEqual(len(s.list_projects(True)),1)
  s.archive({'kind':'project','id':self.project['id'],'restore':True});self.assertEqual(len(s.list_projects()),1)
 def test_cross_project_links_and_invalid_dates(self):
  other=s.save_project({'name':'另一个项目'})
  task=s.project_detail(self.project['id'])['tasks'][0]
  with self.assertRaises(ValueError):s.save_task({**task,'projectId':other['id']})
  with self.assertRaises(ValueError):s.save_log({'projectId':self.project['id'],'date':'not-a-date'})

if __name__=='__main__':unittest.main()
