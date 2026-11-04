import datetime,unittest
from unittest.mock import patch
from test_module_notebook import ModuleNotebookTests
import learning_service as learning,module_notebook as notes,daily_quiz,flash_review,study_service as study

class FlashReviewTests(ModuleNotebookTests):
 def test_spaced_review_statistics_and_unfinished_carry(self):
  card=learning.save_flashcard(dict(moduleId=self.id,question='问题',answer='答案'))
  start=datetime.date(2026,10,1)
  def day(n):return (start+datetime.timedelta(days=n)).isoformat()
  with patch.object(notes,'today',return_value=day(0)),patch.object(study,'today',return_value=day(0)):
   notes.select(dict(moduleId=self.id,cardIds=[card['id']]));p=daily_quiz.plan();key=p['cards'][0]['key'];self.assertEqual(flash_review.statistics()['untested'],1)
  # Unanswered selected module cards automatically carry to tomorrow.
  with patch.object(study,'today',return_value=day(1)):
   p=daily_quiz.plan();self.assertEqual(len(p['cards']),1)
   daily_quiz.answer(dict(key=key,studentAnswer='回答',verdict='known'));s=flash_review.statistics();self.assertEqual((s['known'],s['review'],s['untested']),(1,0,0))
  with patch.object(study,'today',return_value=day(2)):
   self.assertEqual(len(daily_quiz.plan()['cards']),1)
   a=daily_quiz.answer(dict(key=key,studentAnswer='回答',verdict='known'));self.assertEqual(a['review']['interval'],3)
   # Same-day resubmission does not advance another interval.
   a=daily_quiz.answer(dict(key=key,revision=a['revision'],studentAnswer='修改回答',verdict='known'));self.assertEqual(a['review']['interval'],3)
  with patch.object(study,'today',return_value=day(3)):self.assertEqual(daily_quiz.plan()['cards'],[])
  with patch.object(study,'today',return_value=day(6)):
   self.assertEqual(len(daily_quiz.plan()['cards']),1)
   a=daily_quiz.answer(dict(key=key,studentAnswer='忘了',verdict='review'));self.assertEqual(a['review']['interval'],1);self.assertEqual(flash_review.statistics()['review'],1)
  with patch.object(study,'today',return_value=day(7)):
   self.assertEqual(len(daily_quiz.plan()['cards']),1)
   a=daily_quiz.answer(dict(key=key,studentAnswer='回答',verdict='known'));self.assertEqual(a['review']['interval'],1)
  learning.archive_flashcard(dict(id=card['id'],moduleId=self.id,revision=card['revision']))
  self.assertEqual(flash_review.statistics()['total'],0)
