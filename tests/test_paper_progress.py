import unittest,tempfile,pathlib,json,gc,contextlib
from unittest.mock import patch
import local_app,study_service as study,paper_progress as progress,reading_journal as journal

class PaperProgressTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=pathlib.Path(self.temp.name)
  self.patches=[patch.object(local_app,'DATA',root),patch.object(study,'DB',root/'study.sqlite'),patch.object(study,'atlas_papers',return_value=[])]
  for p in self.patches:p.start()
  local_app.absorb([dict(id='paper-a',title='Test paper')])
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  gc.collect();self.temp.cleanup()
 def test_manual_read_does_not_complete_checklist(self):
  with study.connection() as c:
   tasks={journal.definitions()[0]['id']:{'done':True}}
   c.execute("INSERT INTO records VALUES('paper-knowledge','paper-a',?,0)",(json.dumps(dict(id='paper-a',tasks=tasks)),))
  read=progress.save(dict(paperId='paper-a',read=True));self.assertTrue(read['read']);self.assertEqual(read['done'],1);self.assertFalse(read['tasksComplete'])
  stats=journal.statistics(True);self.assertEqual(stats['read'],1);self.assertEqual(stats['items'][0]['done'],1)
  unread=progress.save(dict(paperId='paper-a',read=False));self.assertFalse(unread['read']);self.assertEqual(unread['done'],1)
  self.assertEqual(journal.statistics()['read'],0)
 def test_read_date_survives_repeat_save_and_fresh_read(self):
  with patch.object(study,'today',return_value='2026-10-20'):progress.save(dict(paperId='paper-a',read=True))
  with patch.object(study,'today',return_value='2026-10-21'):
   self.assertEqual(progress.save(dict(paperId='paper-a',read=True))['readDate'],'2026-10-20')
   progress.save(dict(paperId='paper-a',read=False));self.assertEqual(progress.save(dict(paperId='paper-a',read=True))['readDate'],'2026-10-21')
 def test_batch_defaults_and_actual_task_completion(self):
  self.assertEqual(progress.listing(['paper-a','paper-a'])['items'][0]['done'],0)
  tasks={t['id']:{'done':True} for t in journal.definitions()}
  with study.connection() as c:c.execute("INSERT INTO records VALUES('paper-knowledge','paper-a',?,0)",(json.dumps(dict(id='paper-a',tasks=tasks,readDate=study.today())),))
  item=progress.listing(['paper-a'])['items'][0];self.assertTrue(item['read']);self.assertTrue(item['tasksComplete']);self.assertFalse(item['manual'])
 def test_invalid_write_and_unknown_paper_are_rejected(self):
  for data in [dict(paperId='paper-a',read='yes'),dict(paperId='bad/id',read=True),dict(paperId='missing',read=True)]:
   with self.assertRaises(ValueError):progress.save(data)
 def test_favorites_persist_separately_from_read_status_and_tasks(self):
  self.assertEqual(progress.featured(),{})
  progress.save_featured(dict(paperId='paper-a',enabled=True));self.assertTrue(progress.featured()['paper-a'])
  item=progress.listing(['paper-a'])['items'][0];self.assertFalse(item['read']);self.assertEqual(item['done'],0)
  progress.save_featured(dict(paperId='paper-a',enabled=False));self.assertFalse(progress.featured()['paper-a'])
  with self.assertRaises(ValueError):progress.save_featured(dict(paperId='paper-a',enabled='true'))
if __name__=='__main__':unittest.main()
