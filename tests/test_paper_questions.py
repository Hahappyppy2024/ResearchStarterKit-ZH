import unittest,tempfile,pathlib,gc
from unittest.mock import patch
import study_service as study,local_app,paper_questions as questions

class PaperQuestionTests(unittest.TestCase):
 def test_issue_counts_delete_restore_and_image_answer(self):
  image='![截图](http://127.0.0.1:8766/api/study/paste-image?id=12345678-1234-1234-1234-123456789abc)'
  q=questions.save(dict(paperId=self.paper['id'],question='含截图的问题',answer=image))
  questions.save(dict(paperId=self.paper['id'],question='已解决的问题',resolved=True))
  questions.save(dict(paperId=self.other['id'],question='另一篇'))
  self.assertEqual(questions.listing(mode='counts')['byPaper'][self.paper['id']],dict(open=1,resolved=1))
  deleted=questions.save({**q,'deleted':True})
  self.assertEqual(questions.listing(paper_id=self.paper['id'])['total'],1)
  self.assertEqual(questions.listing(mode='counts')['byPaper'][self.paper['id']],dict(open=0,resolved=1))
  with self.assertRaises(ValueError):questions.save({**q,'answer':'旧版本覆盖'})
  restored=questions.save({**deleted,'deleted':False})
  self.assertEqual(restored['answer'],image);self.assertEqual(restored['paperId'],self.paper['id'])
  self.assertEqual(questions.listing(mode='counts')['byPaper'][self.paper['id']],dict(open=1,resolved=1))
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=pathlib.Path(self.tmp.name);self.patches=[patch.object(study,'DB',root/'study.sqlite'),patch.object(local_app,'DATA',root),patch.object(study,'today',return_value='2026-10-21')]
  for p in self.patches:p.start()
  self.paper=study.save_paper(dict(title='Paper A'));self.other=study.save_paper(dict(title='Paper B'))
 def tearDown(self):
  for p in self.patches:p.stop()
  gc.collect();self.tmp.cleanup()
 def test_dates_resolution_reopen_and_daily_carry(self):
  q=questions.save(dict(paperId=self.paper['id'],question='为什么？',date='2026-10-20'));self.assertEqual(questions.listing('2026-10-21')['total'],0)
  self.assertEqual(questions.listing('2026-10-21',mode='daily')['open'],1)
  q=questions.save({**q,'answer':'因为条件 A','resolved':True});self.assertEqual(q['date'],'2026-10-20');self.assertEqual(q['resolvedDate'],'2026-10-21');self.assertEqual(questions.listing('2026-10-21',mode='daily')['resolved'],1)
  self.assertEqual(questions.listing('2026-10-22',mode='daily')['total'],0)
  q=questions.save({**q,'resolved':False});self.assertNotIn('resolvedDate',q);self.assertEqual(q['answer'],'因为条件 A');self.assertEqual(questions.listing()['open'],1)
  with study.connection() as c:self.assertEqual(study.records(c,'reading-log'),[])
 def test_duplicates_ownership_revision_and_validation(self):
  q=questions.save(dict(paperId=self.paper['id'],question='问题一',sourceId='item-q'));same=questions.save(dict(paperId=self.paper['id'],question='问题一更新',sourceId='item-q'));self.assertEqual(q['id'],same['id']);self.assertEqual(questions.listing()['total'],1)
  with self.assertRaises(ValueError):questions.save({**q,'paperId':self.other['id']})
  changed=questions.save({**q,'answer':'答案'})
  with self.assertRaises(ValueError):questions.save({**q,'resolved':True})
  with self.assertRaises(ValueError):questions.save(dict(paperId=self.paper['id'],question=' '))
  with self.assertRaises(ValueError):questions.save(dict(paperId=self.paper['id'],question='未来问题',date='2026-10-22'))
  questions.save(dict(paperId=self.other['id'],question='另一篇的问题'));data=questions.listing(paper_id=self.paper['id']);self.assertEqual(data['total'],1);self.assertEqual(data['allTotal'],2)
