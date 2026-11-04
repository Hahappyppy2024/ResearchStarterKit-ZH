import contextlib,json,pathlib,tempfile,unittest,urllib.parse
from unittest.mock import patch
import local_app,topics_service
class TopicTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent,prefix="test-topics-");self.root=pathlib.Path(self.temp.name);assert self.root.parent==pathlib.Path(__file__).resolve().parent
  self.mock=patch.object(topics_service,"DB",self.root/"library.sqlite");self.mock.start()
 def tearDown(self):self.mock.stop();self.temp.cleanup()
 def test_save_persist_grouped_query_and_duplicate(self):
  t=topics_service.add_topic("农业遥感检测","agriculture, crop\nremote sensing, satellite\ndetection")
  self.assertEqual(t["query"],'(all:"agriculture" OR all:"crop") AND (all:"remote sensing" OR all:"satellite") AND (all:"detection")')
  self.assertEqual(len(topics_service.list_topics()),len(topics_service.BUILTINS)+1)
  self.assertEqual(topics_service.list_topics()[-1]["name"],"农业遥感检测")
  with self.assertRaises(ValueError):topics_service.add_topic("农业遥感检测","crop")
  with self.assertRaises(ValueError):topics_service.make_query('unsafe"query')
 def test_saved_custom_query_is_used_and_tags_results(self):
  topics_service.add_topic("农业遥感检测","crop\nsatellite")
  date=local_app.now().date().isoformat()
  atom=f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/2610.12345v1</id><title>Crop mapping from satellite data</title><summary>Mapping crops using imagery.</summary><published>{date}T00:00:00Z</published><updated>{date}T00:00:00Z</updated><author><name>Test Author</name></author></entry></feed>'
  with patch.object(local_app,"DATA",self.root),patch.object(local_app,"fetch",return_value=atom.encode()) as fetch,patch.object(local_app,"absorb") as absorb,patch.object(local_app.time,"sleep"):
   result=local_app.update_arxiv("农业遥感检测")
   self.assertEqual(result["arxiv"],1)
   self.assertIn("农业遥感检测",absorb.call_args.args[0][0]["topics"])
   query=urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)["search_query"][0]
   self.assertIn('all:"crop"',query)
   self.assertEqual(json.loads((self.root/(date+".json")).read_text("utf8"))["coverage"]["农业遥感检测"],"本次匹配 1 篇；关键词分类待复核。")
if __name__=="__main__":unittest.main()
