import unittest
from local_app import classify,zotero_item,TOPICS
class ResearchTests(unittest.TestCase):
    def test_classification(self):
        self.assertIn("Agent Security",classify("Prompt injection in tool agents"))
        self.assertIn("Object Detection",classify("Open-vocabulary detection with DETR"))
        self.assertEqual(classify("Protein folding"),["其他"])
    def test_links_never_bulk_download(self):
        p={"id":"x","title":"Test","authors":"A Name, B Name","venue":"CVPR","year":2025,"pdf":"https://example.org/a.pdf","source":"https://example.org/a","topics":["Object Detection"]}
        item=zotero_item(p,"test")
        self.assertIs(item["attachments"][0]["snapshot"],False)
        self.assertIn({"tag":"CVPR/2025"},item["tags"])
        self.assertEqual(len(item["creators"]),2)
if __name__=="__main__":unittest.main()
