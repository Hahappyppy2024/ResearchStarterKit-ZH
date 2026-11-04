import unittest,tempfile,pathlib,uuid,datetime
from unittest.mock import patch
import learning_service as learning,module_notebook as notes,study_service,local_app,daily_quiz

class ModuleNotebookTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=pathlib.Path(self.tmp.name)
  self.patches=[patch.object(learning,'DB',root/'learning.sqlite'),patch.object(learning,'FILES',root/'files'),patch.object(study_service,'DB',root/'study.sqlite'),patch.object(local_app,'DATA',root)]
  for p in self.patches:p.start()
  self.module=learning.save_module(dict(name='测试模块',en='QA module'));self.id=self.module['id']
 def tearDown(self):
  for p in self.patches:p.stop()
  self.tmp.cleanup()
 def test_notebook_revision_assets_and_module_isolation(self):
  item=str(uuid.uuid4());n=notes.save(dict(id=self.id,revision=0,questions=[dict(id=str(uuid.uuid4()),question='为什么？',answer='因为…')],examples=[dict(id=item,domain='cv',title='输入输出',code='print(1)')],formulas=[dict(id=str(uuid.uuid4()),title='注意力',latex=r'QK^T/\sqrt{d}',explanation='缩放')]))
  with self.assertRaises(ValueError):notes.save(dict(id=self.id,revision=0,questions=[]))
  a=notes.upload(self.id,item,'example.py',b'print(1)');self.assertEqual(notes.file(a['id']).read_bytes(),b'print(1)')
  self.assertEqual(notes.get(self.id)['questions'][0]['answer'],'因为…');self.assertEqual(len(notes.get(self.id)['attachments']),1)
  other=learning.save_module(dict(name='其他模块'));self.assertEqual(notes.get(other['id'])['examples'],[])
  with self.assertRaises(ValueError):notes.upload(other['id'],item,'x.py',b'pass')
  with self.assertRaises(ValueError):notes.upload(self.id,item,'x.png',b'fake')
  with self.assertRaises(ValueError):notes.upload(self.id,item,'x.html',b'<script>')
  with self.assertRaises(ValueError):notes.file('../outside')
 def test_module_quiz_today_selection_and_frozen_attempt(self):
  c=learning.save_flashcard(dict(moduleId=self.id,question='为什么缩放？',answer='控制点积尺度'))
  notes.select(dict(moduleId=self.id,cardIds=[c['id']]));plan=daily_quiz.plan();card=plan['cards'][0];self.assertEqual(card['source'],'module')
  saved=daily_quiz.answer(dict(date=plan['date'],key=card['key'],revision=0,studentAnswer='控制方差',verdict='review'));self.assertEqual(saved['verdict'],'review')
  learning.save_flashcard(dict(id=c['id'],moduleId=self.id,revision=c['revision'],question='新问题',answer='新答案'))
  self.assertEqual(daily_quiz.plan()['cards'][0]['answer'],'控制点积尺度')
  with patch.object(notes,'today',return_value='2099-01-01'):self.assertEqual(notes.get(self.id)['quizCards'],[])
  notes.select(dict(moduleId=self.id,cardIds=[]));self.assertEqual(daily_quiz.plan()['cards'],[])
  blank=learning.save_flashcard(dict(moduleId=self.id,question='空答案',answer=''))
  with self.assertRaises(ValueError):notes.select(dict(moduleId=self.id,cardIds=[blank['id']]))
