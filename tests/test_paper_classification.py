import unittest,tempfile,pathlib,json
from unittest.mock import patch
import paper_classification as pc,local_app
class ClassificationTests(unittest.TestCase):
 def test_title_is_stronger_than_incidental_abstract_mention(self):
  rules=[{'topicId':'tools','terms':['tool use','tool calling','function calling']}]
  self.assertEqual(pc.match_topics({'title':'Better Tool-Use Agents'},rules)[0]['topicId'],'tools')
  self.assertEqual(pc.match_topics({'title':'Other work','summary':'We discuss tool use.'},rules),[])
  self.assertTrue(pc.match_topics({'summary':'tool use and tool calling with function calling'},rules))
 def test_boundaries_and_unclassified(self):
  rule=[{'topicId':'rl','terms':['rl']}]
  self.assertFalse(pc.match_topics({'title':'World representation'},rule))
  self.assertFalse(pc.match_topics({'title':'Unrelated task'},rule))
 def test_reingest_preserves_saved_titles_but_not_after_source_title_changes(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(local_app,'DATA',pathlib.Path(folder)):
   local_app.absorb([{'id':'p','title':'Original title','titleZh':'已保存中文标题','titleEn':'Original title'}])
   local_app.absorb([{'id':'p','title':'Original title'}])
   with local_app.db() as c:p=json.loads(c.execute('SELECT body FROM papers').fetchone()[0])
   self.assertEqual(p['titleZh'],'已保存中文标题')
   local_app.absorb([{'id':'p','title':'Changed title'}])
   with local_app.db() as c:p=json.loads(c.execute('SELECT body FROM papers').fetchone()[0])
   self.assertNotIn('titleZh',p)
   c.close()
   __import__('gc').collect()
if __name__=='__main__':unittest.main()
