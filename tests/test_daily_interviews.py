import datetime,pathlib,tempfile,unittest
import learning_service as learning,interview_service as service
class DailyInterviews(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=learning.DB;learning.DB=pathlib.Path(self.temp.name)/'learning.sqlite'
 def tearDown(self):learning.DB=self.old;self.temp.cleanup()
 def test_five_categories_rotation_history_and_edits(self):
  first=service.get_day('2026-10-20');self.assertEqual(len(first['cards']),5);self.assertEqual(len({c['category'] for c in first['cards']}),5)
  self.assertEqual(first['bankCount'],70);self.assertTrue(all(c['question'] and c['answer'] for c in first['cards']))
  card=first['cards'][0];edited=service.save_card({'date':first['date'],'id':card['id'],'revision':card['revision'],'question':'我的问题','answer':'我的回答','done':True})
  with self.assertRaises(ValueError):service.save_card({'date':first['date'],'id':card['id'],'revision':card['revision'],'answer':'旧窗口'})
  tomorrow=service.get_day('2026-10-21');self.assertNotEqual([c['bankId'] for c in first['cards']],[c['bankId'] for c in tomorrow['cards']])
  again=service.get_day('2026-10-20');self.assertEqual(again['cards'][0]['answer'],'我的回答');self.assertTrue(again['cards'][0]['done']);self.assertEqual(again['cards'][0]['id'],edited['id'])
 def test_custom_bank_does_not_rewrite_frozen_day(self):
  first=service.get_day('2026-10-20')
  service.add_bank({'category':'simple','domain':'cv','topic':'My module','question':'自定义问题','answer':'自定义答案'})
  later=service.get_day('2026-10-20');self.assertEqual(later['bankCount'],71);self.assertEqual(first['cards'],later['cards'])
  with self.assertRaises(ValueError):service.add_bank({'category':'invalid','domain':'cv','question':'Q'})
  with self.assertRaises(ValueError):service.get_day('2026-02-30')
  self.assertEqual(service.TZ.utcoffset(None),datetime.timedelta(hours=8))
if __name__=='__main__':unittest.main()
