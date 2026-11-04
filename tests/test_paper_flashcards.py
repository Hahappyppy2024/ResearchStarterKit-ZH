import copy,json,unittest
import paper_flashcards as cards
from test_research_assets import AssetTests
import knowledge_service as knowledge,study_service as study

class AutoCardUnitTests(unittest.TestCase):
 def test_simple_split_manual_edit_delete_and_source_update(self):
  tasks={'problem':{'answer':'小目标容易漏检。背景干扰较强。'},'flashcards':{'items':[]}}
  definitions=[{'id':'problem','title':'Problem'}]
  meta=cards.sync('paper',tasks,{},definitions);self.assertEqual(len(tasks['flashcards']['items']),2);first=copy.deepcopy(tasks['flashcards']['items'][0]);self.assertEqual(first['answer'],'小目标容易漏检。');self.assertIn('解决什么问题',first['question'])
  old={**meta,'tasks':copy.deepcopy(tasks)};tasks['problem']['answer']='低分辨率小目标容易漏检。背景干扰较强。';meta=cards.sync('paper',tasks,old,definitions);self.assertEqual(tasks['flashcards']['items'][0]['id'],first['id']);self.assertEqual(tasks['flashcards']['items'][0]['answer'],'低分辨率小目标容易漏检。')
  old={**meta,'tasks':copy.deepcopy(tasks)};tasks['flashcards']['items'][0]['answer']='我的精简答案';tasks['problem']['answer']='再次更新原笔记。背景干扰较强。';meta=cards.sync('paper',tasks,old,definitions);self.assertEqual(tasks['flashcards']['items'][0]['answer'],'我的精简答案')
  old={**meta,'tasks':copy.deepcopy(tasks)};tasks['flashcards']['items']=tasks['flashcards']['items'][:1];meta=cards.sync('paper',tasks,old,definitions);old={**meta};meta=cards.sync('paper',tasks,old,definitions);self.assertEqual(len(tasks['flashcards']['items']),1)
 def test_no_invention_incomplete_qa_and_capacity(self):
  tasks={'reading-questions':{'items':[dict(id='item-q',question='为什么？',answer=''),dict(id='item-q2',question='条件是什么？',answer='x > 0；y < 2。')]},'flashcards':{'items':[]}}
  cards.sync('p',tasks,{},[{'id':'reading-questions','title':'问题'}]);self.assertEqual(len(tasks['flashcards']['items']),1);self.assertEqual(tasks['flashcards']['items'][0]['answer'],'x > 0；y < 2。')
  tasks={'problem':{'answer':'\n'.join('要点 '+str(i) for i in range(105))},'flashcards':{'items':[]}}
  meta=cards.sync('p',tasks,{},[dict(id='problem',title='问题')]);self.assertEqual(len(tasks['flashcards']['items']),100);self.assertEqual(meta['autoFlashcardOverflow'],5)

class AutoCardIntegrationTests(AssetTests):
 def test_answer_save_autogenerates_and_roundtrips_without_duplicates(self):
  saved=knowledge.save_paper(dict(paperId=self.paper['id'],tasks={'problem':dict(answer='小目标容易漏检。')}))
  items=saved['tasks']['flashcards']['items'];self.assertEqual(len(items),1);self.assertEqual(saved['autoFlashcardVersion'],1)
  updated=knowledge.save_paper(dict(paperId=self.paper['id'],revision=saved['revision'],tasks=saved['tasks']));self.assertEqual(updated['tasks']['flashcards']['items'],items)
