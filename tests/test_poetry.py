import json,pathlib,tempfile,unittest
from unittest.mock import patch
import poetry_service
class PoetryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent,prefix="test-poetry-")
  self.root=pathlib.Path(self.temp.name);assert self.root.parent==pathlib.Path(__file__).resolve().parent
  (self.root/"local-data").mkdir();self.catalog=poetry_service.catalog()
  (self.root/"local-data"/"poetry-catalog.json").write_text(json.dumps(self.catalog),"utf8")
  self.mock=patch.object(poetry_service,"ROOT",self.root);self.mock.start()
 def tearDown(self):self.mock.stop();self.temp.cleanup()
 def test_chronological_day_assignment_stays_fixed_when_marked(self):
  d=poetry_service.data();self.assertEqual(len(d["poems"]),78);self.assertEqual(d["task"]["order"],1)
  pid=d["task"]["id"];poetry_service.save({"id":pid,"done":True})
  saved=poetry_service.data();self.assertEqual(saved["completed"],1);self.assertEqual(saved["task"]["id"],pid)
  tomorrow=(poetry_service.today()+poetry_service.dt.timedelta(days=1)).isoformat()
  self.assertEqual(poetry_service.data(tomorrow)["task"]["order"],2)
 def test_user_text_persists_and_invalid_id_rejected(self):
  pid=poetry_service.data()["task"]["id"]
  poetry_service.save({"id":pid,"text":"用户录入原文\n第二行","personalNote":"易错字"})
  self.assertEqual(poetry_service.data()["task"]["text"],"用户录入原文\n第二行")
  self.assertEqual(poetry_service.data()["task"]["personalNote"],"易错字")
  with self.assertRaises(ValueError):poetry_service.save({"id":"missing","done":True})
if __name__=="__main__":unittest.main()
