import unittest
import se_conferences as se
class SEConferenceTests(unittest.TestCase):
 def test_only_accepted_research_table_and_preserve_missing_abstract(self):
  html='''<table><tr><td>Program noise</td></tr></table><div id="event-overview"><table><tr><td><a href="#" data-event-modal="event-a">Test Generation</a><div class="prog-track">Research Papers</div><div class="performers"><a href="/profile/a">Author A</a>, <a href="/profile/b">Author B</a></div><a href="https://doi.org/10.1/example" class="publication-link">DOI</a></td></tr><tr><td><a data-event-modal="event-b">Keynote</a><div class="prog-track">Keynotes</div></td></tr></table></div>'''
  rows=se.parse(html,'ASE',2025,'https://conf.researchr.org/track/ase-2025/ase-2025-papers')
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['authors'],'Author A, Author B');self.assertEqual(rows[0]['summary'],'');self.assertEqual(rows[0]['source'],'https://doi.org/10.1/example')
  self.assertEqual(rows[0]['id'],se.parse(html,'ASE',2025,'https://conf.researchr.org/track/ase-2025/ase-2025-papers')[0]['id'])
 def test_missing_official_section_fails_without_replacing_existing_catalog(self):
  with self.assertRaises(ValueError):se.parse('<h1>Unavailable</h1>','ICSE',2026,'https://conf.researchr.org/')
if __name__=='__main__':unittest.main()
