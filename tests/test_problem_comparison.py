import contextlib,json,pathlib,tempfile,unittest
from unittest.mock import patch
import problem_comparison as pc
import study_service as study

class CandidateTests(unittest.TestCase):
 def test_title_only_bilingual_suggestions_and_multiple_membership(self):
  papers=[dict(id='a',title='Faster R-CNN: Towards Real-Time Object Detection'),dict(id='b',title='Small Object Detection in Crowded Images'),dict(id='c',title='Other Work',summary='object detection')]
  groups=pc.candidate_groups(papers)
  self.assertTrue(all(g['suggested'] and g['name'] and g['en'] for g in groups))
  detection=next(g for g in groups if g['id']=='suggested:detection')
  self.assertEqual(detection['paperIds'],['a','b'])
  self.assertNotIn('c',{i for g in groups for i in g['paperIds']})
  self.assertTrue(any(g['id']=='suggested:small-detection' and 'b' in g['paperIds'] for g in groups))
 def test_no_fabricated_findings(self):
  group=pc.candidate_groups([dict(id='a',title='Prompt Injection in Agents')])[0]
  self.assertNotIn('method',group);self.assertNotIn('evidence',group)
 def test_bilingual_problem_required(self):
  with self.assertRaises(ValueError):pc.confirm(dict(name='具体问题',en='',paperIds=[]))
 def test_structured_reading_tasks_are_available_without_inventing_answers(self):
  result=pc.task_values({'reading-questions':{'items':[{'question':'为何使用该损失？','answer':'仍需核实'}]},'datasets':{'datasetIds':['d1']},'background':{'answer':'真实场景'},'code-trace':{}},{'d1':{'name':'Example Dataset','en':'Example'}},{})
  self.assertIn('为何使用该损失',result['reading-questions'])
  self.assertIn('Example Dataset',result['datasets'])
  self.assertEqual(result['background'],'真实场景')
  self.assertEqual(result['code-trace'],'')

class SynthesisTests(unittest.TestCase):
 def test_revision_and_confirmed_problem_required(self):
  with tempfile.TemporaryDirectory(dir=study.ROOT/'local-data') as temp,patch.object(study,'DB',pathlib.Path(temp)/'study.sqlite'):
   with self.assertRaises(ValueError):pc.save_synthesis(dict(id='candidate',revision=0,gap='draft'))
   with study.connection() as c:
    c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage','confirmed',json.dumps(dict(kind='problem'))))
   saved=pc.save_synthesis(dict(id='confirmed',revision=0,gap='Needs evidence'))
   self.assertEqual(saved['revision'],1)
   self.assertEqual(saved['gap'],'Needs evidence')
   with self.assertRaises(ValueError):pc.save_synthesis(dict(id='confirmed',revision=0,gap='stale'))
   with study.connection() as c:
    value=study.row(c,'problem-synthesis','confirmed')
   self.assertEqual(value['gap'],'Needs evidence')

if __name__=='__main__':unittest.main()
