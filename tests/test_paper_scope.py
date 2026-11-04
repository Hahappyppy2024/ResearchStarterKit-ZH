import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import paper_scope as s
from detection_topics import detection_topics
class ScopeTests(unittest.TestCase):
 def test_explicit_earth_paper(self):self.assertEqual(s.raw_reason({'id':'arxiv-2610.32617','title':'Earth embeddings are decomposable records of the land surface'}),'地理与地球科学')
 def test_subjects(self):
  for title in ['Geospatial reasoning agents','Legal agents for lawyers','Chemical synthesis with language models']:
   self.assertTrue(s.raw_reason({'title':title}))
 def test_preserve_research(self):
  for title in ['个性化学习','自动化学习','方法学研究','强化学习中的算法学习','通过强化学习训练大语言模型搜索','进化学习模型','Liquid Time-constant Networks','Scaling laws for neural networks','Agricultural remote sensing object detection','Military target detection','Law of Large Numbers']:
   self.assertEqual(s.raw_reason({'title':title}),'')
 def test_english_original_precedes_misleading_translation(self):
  self.assertFalse(s.raw_reason({'title':'Personalized learning path planning','titleZh':'个性化学习路径规划'}))
  self.assertFalse(s.raw_reason({'title':'CoWriter: Guiding Methodological Human LLM Co-Authoring','titleZh':'方法学研究'}))
 def test_recoverable_archive(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'PATH',Path(folder)/'trash.json'),patch.object(s,'_CACHE',(None,set())):
   p={'id':'x','title':'Legal reasoning for lawyers'};self.assertEqual(s.archive([p]),1);self.assertEqual(s.archive([p]),0)
   self.assertEqual(s.listing()['count'],1);s.restore({'paperId':'x'});self.assertFalse(s.reason(p));self.assertEqual(s.listing()['count'],0)
   self.assertEqual(json.loads(s.PATH.read_text())['archived']['x']['paper'],p)
 def test_detection_subtopics(self):
  tags=detection_topics({'title':'Infrared small object detection for counter-UAV surveillance','topics':['Object Detection']})
  self.assertIn('红外与低光照目标检测',[t['name'] for t in tags]);self.assertIn('低空无人机与反无人机检测',[t['name'] for t in tags])
  self.assertEqual(detection_topics({'title':'A chemical reaction','topics':[]}),[])
if __name__=='__main__':unittest.main()
