import pathlib,tempfile,unittest
import learning_service as s
class FlashcardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=s.DB;s.DB=pathlib.Path(self.tmp.name)/'learning.sqlite'
 def tearDown(self):s.DB=self.old;self.tmp.cleanup()
 def test_migration_once_keeps_legacy_answers(self):
  m=s.list_modules()[0];s.save_module({'id':m['id'],'questions':'问题一\n问题二\n问题一','answers':'原有整段复习笔记'})
  data=s.detail(m['id']);self.assertEqual([c['question'] for c in data['cards']],['问题一','问题二']);self.assertTrue(all(c['answer']=='' for c in data['cards']))
  self.assertEqual(data['module']['answers'],'原有整段复习笔记')
  for c in data['cards']:s.archive_flashcard({'id':c['id'],'moduleId':m['id'],'revision':c['revision']})
  self.assertEqual(s.detail(m['id'])['cards'],[]);self.assertEqual(len(s.detail(m['id'])['archivedCards']),2)
 def test_save_revision_module_isolation_and_restore(self):
  m=s.save_module({'name':'测试模块'});s.detail(m['id'])
  card=s.save_flashcard({'moduleId':m['id'],'question':'Q','answer':'答案一\n答案二'})
  updated=s.save_flashcard({**card,'answer':'修改的答案'})
  with self.assertRaises(ValueError):s.save_flashcard({**card,'answer':'旧窗口覆盖'})
  other=s.save_module({'name':'另一个模块'})
  with self.assertRaises(ValueError):s.save_flashcard({**updated,'moduleId':other['id']})
  archived=s.archive_flashcard({**updated});self.assertEqual(s.detail(m['id'])['cards'],[])
  restored=s.archive_flashcard({**archived,'restore':True});self.assertFalse(restored['archived']);self.assertEqual(s.detail(m['id'])['cards'][0]['answer'],'修改的答案')
  with self.assertRaises(ValueError):s.save_flashcard({'moduleId':m['id'],'question':'  ','answer':'A'})
if __name__=='__main__':unittest.main()
