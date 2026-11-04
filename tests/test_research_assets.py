import unittest,tempfile,pathlib,base64,gc,json
from unittest.mock import patch
import study_service as s,local_app,knowledge_service as k,research_assets as assets,learning_service
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK1sAAAAASUVORK5CYII=')
class AssetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.patches=[patch.object(s,'DB',self.root/'study.sqlite'),patch.object(s,'ATLAS',self.root),patch.object(local_app,'DATA',self.root),patch.object(learning_service,'DB',self.root/'learning.sqlite')]
  for p in self.patches:p.start()
  self.paper=s.save_paper(dict(title='Main paper',authors='A'));self.source=s.save_paper(dict(title='Dataset source paper',authors='B'))
 def tearDown(self):
  for p in self.patches:p.stop()
  gc.collect();self.tmp.cleanup()
 def test_topic_association_preserves_dataset_and_queue(self):
  topic=k.save_node(dict(kind='topic',name='主题 A',en='Test definition'))
  other=k.save_node(dict(kind='topic',name='主题 B',en='Second definition'))
  problem=k.save_node(dict(kind='problem',name='问题',en='Test definition',topicIds=[topic['id']]))
  dataset=assets.save_dataset(dict(name='Benchmark',description='Preserve',sourcePaperIds=[self.source['id']],problemIds=[problem['id']],topicIds=[topic['id']]))
  before=s.state()['queue']
  saved=assets.assign_dataset_topics(dict(id=dataset['id'],revision=dataset['revision'],topicIds=[topic['id'],other['id'],topic['id']]))
  self.assertEqual(saved['topicIds'],[topic['id'],other['id']])
  for key in ['name','description','sourcePaperIds','problemIds']:self.assertEqual(saved[key],dataset[key])
  self.assertEqual(s.state()['queue'],before)
  with self.assertRaises(ValueError):assets.assign_dataset_topics(dict(id=saved['id'],revision=dataset['revision'],topicIds=[]))
  with self.assertRaises(ValueError):assets.assign_dataset_topics(dict(id=saved['id'],revision=saved['revision'],topicIds=[problem['id']]))
  with self.assertRaises(ValueError):k.save_node(dict(kind='solution',name='Invalid',en='Test definition',topicIds=[problem['id']]))
  saved_problem=k.save_node(dict(problem,definition='Preserve Topic'))
  self.assertEqual(saved_problem['topicIds'],[topic['id']])
 def test_dataset_figure_and_old_answers_roundtrip(self):
  nodes={kind:k.save_node(dict(kind=kind,name=kind+'中文',en=kind+' English')) for kind in ('topic','problem','solution')}
  with s.connection() as c:self.assertTrue(k.row_exists(c,'lineage','taxonomy-'+nodes['solution']['id']))
  dataset=assets.save_dataset(dict(name='Test benchmark',en='Test Dataset',sourcePaperIds=[self.source['id']],topicIds=[nodes['topic']['id']],problemIds=[nodes['problem']['id']],solutionIds=[nodes['solution']['id']]))
  fig=assets.upload_figure(self.paper['id'],PNG);path,mime=assets.figure_file(fig['id']);self.assertEqual(path.read_bytes(),PNG);self.assertEqual(mime,'image/png');self.assertTrue(path.is_relative_to(self.root))
  tasks=dict(problem=dict(done=True,answer='Old problem note'),background=dict(done=True,answer='Scene and constraints'),methodology=dict(done=True,answer='Fig 2: input to output',figureIds=[fig['id']]),datasets=dict(done=True,answer='Use official train/test split',datasetIds=[dataset['id']]))
  definitions=json.loads((s.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'));tasks={**tasks,**{t['id']:{**tasks.get(t['id'],{}),'done':True} for t in definitions}}
  saved=k.save_paper(dict(paperId=self.paper['id'],tasks=tasks,solutionIds=[nodes['solution']['id']],read=True));loaded=k.get_paper(self.paper['id']);self.assertEqual(loaded['tasks']['methodology']['figureIds'],[fig['id']]);self.assertEqual(loaded['tasks']['problem']['answer'],'Old problem note');self.assertEqual(loaded['solutionIds'],[nodes['solution']['id']])
  item=assets.datasets()['items'][0];self.assertEqual(item['usedBy'][0]['id'],self.paper['id']);self.assertEqual(item['sourcePapers'][0]['id'],self.source['id']);self.assertEqual(item['classifications']['solutionIds'][0]['id'],nodes['solution']['id']);self.assertEqual(len(k.paper_week()['cards']),4)
  old_client=k.save_paper(dict(paperId=self.paper['id'],revision=saved['revision'],tasks={'problem':dict(done=True,answer='Updated old note')}));self.assertEqual(old_client['tasks']['methodology']['figureIds'],[fig['id']]);self.assertEqual(old_client['tasks']['datasets']['datasetIds'],[dataset['id']])
  with self.assertRaises(ValueError):k.save_paper(dict(paperId=self.source['id'],tasks={'methodology':dict(figureIds=[fig['id']])}))
  with self.assertRaises(ValueError):assets.save_dataset({**dataset,'revision':dataset['revision'],'topicIds':[nodes['problem']['id']]})
 def test_required_queue_and_completion(self):
  dataset=assets.save_dataset(dict(name='Dataset A',sourcePaperIds=[self.source['id']]))
  self.assertEqual([x['paperId'] for x in s.state()['queue']],[self.source['id']])
  definitions=json.loads((s.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
  tasks={t['id']:dict(done=True,answer='') for t in definitions}
  tasks.setdefault('connections',{})['references']=[dict(id='ref-test',paperId=self.source['id'],paper=self.source['title'],relationTypes=['baseline','same-problem'])]
  tasks['datasets']['datasetIds']=[dataset['id']];tasks['datasets']['done']=False
  partial=k.save_paper(dict(paperId=self.paper['id'],tasks=tasks,read=True))
  self.assertFalse(partial['completed']);self.assertNotIn('readDate',partial)
  self.assertEqual(k.get_paper(self.paper['id'])['completedCount'],len(definitions)-1)
  self.assertEqual(len(s.state()['queue']),1) # dataset and related reference share one entry
  tasks['datasets']['done']=True
  complete=k.save_paper(dict(paperId=self.paper['id'],revision=partial['revision'],tasks=tasks))
  self.assertTrue(complete['completed']);self.assertEqual(complete['readDate'],s.today())
  tasks['background']['done']=False
  reopened=k.save_paper(dict(paperId=self.paper['id'],revision=complete['revision'],tasks=tasks))
  self.assertFalse(reopened['completed']);self.assertNotIn('readDate',reopened)
  self.assertEqual(len(s.state()['queue']),1)
 def test_journal_comparison_and_new_problems(self):
  import reading_journal as journal
  definitions=json.loads((s.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
  tasks={t['id']:dict(done=True,answer='') for t in definitions}
  tasks['problem']['answer']='Dataset scarcity'
  with self.assertRaises(ValueError):k.save_paper(dict(paperId=self.paper['id'],tasks={'compare':dict(comparisonPaperIds=[self.source['id']])}))
  k.save_paper(dict(paperId=self.source['id'],tasks=tasks,readDate='2026-10-19'))
  problem=k.save_node(dict(kind='problem',name='缺少标注',en='Missing annotations'))
  tasks['compare']['comparisonPaperIds']=[self.source['id']]
  tasks['next-step']['problems']=[dict(id=problem['id'],keywords=['few-shot','remote sensing','few-shot'])]
  saved=k.save_paper(dict(paperId=self.paper['id'],tasks=tasks))
  self.assertEqual(saved['tasks']['next-step']['problems'][0]['keywords'],['few-shot','remote sensing'])
  self.assertEqual(k.get_paper(self.paper['id'])['tasks']['compare']['comparisonPaperIds'],[self.source['id']])
  items=journal.library()['items'];self.assertEqual(len(items),2)
  self.assertIn('2026-10-19',next(p for p in items if p['id']==self.source['id'])['dates'])
  self.assertEqual(journal.period('week','2026-10-21'),('2026-10-19','2026-10-25'))
  self.assertEqual(journal.period('month','2024-02-12'),('2024-02-01','2024-02-29'))
  review=journal.save_review(dict(kind='week',date='2026-10-21',content='My review'))
  self.assertEqual(journal.review('week','2026-10-25')['content'],'My review')
  with self.assertRaises(ValueError):journal.save_review(dict(kind='week',date='2026-10-21',content='Stale edit'))
  tasks['datasets']['done']=False
  k.save_paper(dict(paperId=self.paper['id'],revision=saved['revision'],tasks=tasks))
  self.assertEqual(len(journal.library()['items']),1)
 def test_question_lists_preserve_answers_and_hidden_annotations(self):
  definitions=json.loads((s.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'))
  self.assertEqual(len(definitions),21)
  tasks={t['id']:dict(done=True,answer='') for t in definitions}
  tasks['reading-questions']['items']=[dict(id='item-q1',question='Why this loss?',answer='My evidence'),dict(id='item-q2',question='Where does it fail?',answer='')]
  tasks['extensions'].update(answer='Old paragraph, preserved',items=[dict(id='item-e1',question='A new domain, with a changed assumption?')])
  tasks['focus']=dict(done=False,answer='Old focus note')
  tasks['connections']=dict(done=False,references=[dict(id='ref-test',paperId=self.source['id'],paper=self.source['title'],relationTypes=['baseline'])])
  saved=k.save_paper(dict(paperId=self.paper['id'],tasks=tasks))
  self.assertTrue(saved['completed']) # hidden annotations are not required checklist items
  updated=k.save_paper(dict(paperId=self.paper['id'],revision=saved['revision'],tasks={'problem':dict(done=True,answer='Updated')}))
  self.assertEqual(updated['tasks']['reading-questions']['items'][0]['answer'],'My evidence')
  self.assertEqual(len(updated['tasks']['reading-questions']['items']),2)
  self.assertEqual(len(updated['tasks']['extensions']['items']),1)
  self.assertEqual(updated['tasks']['extensions']['answer'],'Old paragraph, preserved')
  self.assertEqual(updated['tasks']['focus']['answer'],'Old focus note')
  self.assertEqual(k.edges([self.paper['id']])[0]['types'],['baseline'])
 def test_paper_daily_quiz_selection_snapshots_and_attempts(self):
  import daily_quiz as quiz
  tasks={'flashcards':dict(items=[dict(id='item-card1',question='What is the problem?',answer='Small objects'),dict(id='item-empty',question='Unfinished card',answer='')])}
  saved=k.save_paper(dict(paperId=self.paper['id'],tasks=tasks))
  self.assertEqual(quiz.plan()['cards'],[])
  selected=quiz.select(dict(paperId=self.paper['id'],enabled=True))
  plan=quiz.plan();self.assertEqual(len(plan['cards']),1)
  card=plan['cards'][0]
  with self.assertRaises(ValueError):quiz.answer(dict(key=card['key'],studentAnswer='',verdict='submitted'))
  attempt=quiz.answer(dict(key=card['key'],studentAnswer='My explanation',verdict='submitted'))
  self.assertEqual(quiz.plan()['answered'],0)
  judged=quiz.answer(dict(key=card['key'],revision=attempt['revision'],studentAnswer='My explanation',verdict='review'))
  self.assertEqual(quiz.plan()['answered'],1)
  with self.assertRaises(ValueError):quiz.answer(dict(key=card['key'],revision=0,studentAnswer='Stale',verdict='known'))
  tasks['flashcards']['items'][0]['answer']='Changed reference'
  k.save_paper(dict(paperId=self.paper['id'],revision=saved['revision'],tasks=tasks))
  self.assertEqual(quiz.plan()['cards'][0]['answer'],'Small objects')
  quiz.select(dict(paperId=self.paper['id'],revision=selected['revision'],enabled=False))
  self.assertEqual(quiz.plan()['cards'],[])
 def test_upload_validation(self):
  for payload in [b'<svg><script>alert(1)</script></svg>',b'x'*(8*1024*1024+1),b'']:
   with self.assertRaises(ValueError):assets.upload_figure(self.paper['id'],payload)
  with self.assertRaises(ValueError):assets.figure_file('../../study.sqlite')
if __name__=='__main__':unittest.main()

