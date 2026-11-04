import json
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import conference_catalog as catalog


class ConferenceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        (root / "local-data").mkdir()
        papers = [
            {"id":"c1","title":"Agent Security and Object Detection","venue":"CVPR","year":2026,"authors":"A. Author","summary":"Prompt injection for tool use","source":"https://example.org/one"},
            {"id":"c2","title":"A New Research Direction","venue":"CVPR","year":2026,"authors":"B. Author"},
            {"id":"a1","title":"Agent Security and Object Detection","venue":"arXiv","year":2026,"source":"https://arxiv.org/abs/2601.12345"},
            {"id":"old","title":"Graph Neural Networks","venue":"ICML","year":2025},
        ]
        with sqlite3.connect(root / "local-data/library.sqlite") as db:
            db.execute("CREATE TABLE papers (body TEXT, venue TEXT)")
            db.executemany("INSERT INTO papers VALUES (?,?)",[(json.dumps(p),p["venue"]) for p in papers])
        db.close()
        self.root = patch.object(catalog,"ROOT",root)
        self.root.start()
        catalog.CACHE = None

    def tearDown(self):
        self.root.stop()
        catalog.CACHE = None
        self.tmp.cleanup()

    def test_years_include_empty_future_and_preserve_archive(self):
        years = catalog.navigation()["years"]
        self.assertEqual([y["year"] for y in years],[2027,2026,2025])
        self.assertTrue(all(c["count"]==0 for c in years[0]["conferences"]))
        self.assertEqual(catalog.browse(2027,"CVPR")["papers"],[])
        self.assertEqual(catalog.browse(2025,"ICML")["count"],1)

    def test_acl_present_and_venues_alphabetical(self):
        venues=[c['venue'] for c in catalog.navigation()['years'][0]['conferences']]
        self.assertIn('ACL',venues)
        self.assertEqual(venues,sorted(venues,key=str.casefold))

    def test_hierarchy_filters_multilabel_and_pagination(self):
        all_rows = catalog.browse(2026,"CVPR")
        self.assertEqual(all_rows["total"],2)
        self.assertEqual(catalog.browse(2026,"CVPR","vision","detection")["count"],1)
        self.assertEqual(catalog.browse(2026,"CVPR","agents","agentsecurity")["count"],1)
        self.assertEqual(catalog.browse(2026,"CVPR",query="B. Author",page=99)["page"],0)
        self.assertEqual(catalog.browse(2026,"CVPR","other")["count"],1)

    def test_arxiv_only_from_known_links_or_matching_local_title(self):
        rows=catalog.browse(2026,"CVPR")["papers"]
        self.assertEqual(next(p for p in rows if p["id"]=="c1")["arxivUrl"],"https://arxiv.org/abs/2601.12345")
        self.assertEqual(next(p for p in rows if p["id"]=="c2")["arxivUrl"],"")
        self.assertEqual(catalog.arxiv_link({"pdf":"javascript:alert(1)"}),"")


if __name__ == "__main__":
    unittest.main()
