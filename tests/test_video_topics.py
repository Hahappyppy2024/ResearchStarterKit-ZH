import unittest
from video_topics import video_topics,RULES
from topics_service import BUILTINS,bilingual
class VideoTests(unittest.TestCase):
 def test_four_directions_are_tracked_with_chinese_labels(self):
  for name,label,pattern,query in RULES:
   self.assertIn((name,query),BUILTINS);self.assertEqual(bilingual(name)['nameZh'],label)
 def test_specific_task_matches_and_title_precedes_abstract(self):
  self.assertEqual(video_topics({'title':'Text-to-video retrieval with temporal grounding','summary':'We compare against video generation.'})[0]['name'],'Video Retrieval')
  self.assertEqual(video_topics({'title':'Instruction guided video editing'})[0]['name'],'Video Editing')
  self.assertEqual(video_topics({'title':'Image-to-video diffusion'})[0]['name'],'Video Generation')
  self.assertEqual(video_topics({'title':'Long-video question answering'})[0]['name'],'Video Understanding')
 def test_multi_label_preserves_cross_topic_work_and_ignores_unrelated(self):
  self.assertEqual({t['name'] for t in video_topics({'title':'Video editing and video understanding'})},{'Video Editing','Video Understanding'})
  self.assertEqual(video_topics({'title':'Image generation and text retrieval'}),[])
if __name__=='__main__':unittest.main()
