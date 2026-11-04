import unittest,tempfile,pathlib
from unittest.mock import patch
import study_service as study,workspace_content as content,paper_affiliations as links
class PaperAffiliationsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=patch.object(study,'DB',pathlib.Path(self.tmp.name)/'test.sqlite');self.db.start()
  self.resolve=patch.object(study,'resolve',return_value=dict(id='paper-one',title='Public paper',authors='Alice',venue='arXiv'));self.resolve.start()
  self.people=patch.object(content,'scholar_directory',return_value=dict(people=[dict(id='alice',name='Alice')]));self.people.start()
  self.lab=content.save('research-lab',dict(name='A lab',paperIds=['other-paper']))
 def tearDown(self):self.people.stop();self.resolve.stop();self.db.stop();self.tmp.cleanup()
 def test_roundtrip_updates_lab_backlinks_and_does_not_touch_queue(self):
  saved=links.save(dict(paperId='paper-one',labIds=[self.lab['id']],scholarIds=['alice'],affiliationText='Verified on first page',source='https://example.org/paper'))
  self.assertEqual(saved['revision'],1);self.assertEqual(links.listing('paper-one')['record']['scholarIds'],['alice'])
  lab=content.listing('research-lab')['items'][0];self.assertEqual(lab['paperIds'],['other-paper','paper-one']);self.assertEqual(lab['revision'],2)
  with study.connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM queue').fetchone()[0],0)
  removed=links.save(dict(saved,labIds=[],scholarIds=[]));self.assertEqual(content.listing('research-lab')['items'][0]['paperIds'],['other-paper']);self.assertEqual(removed['revision'],2)
 def test_legacy_lab_association_is_visible_and_removable(self):
  content.save('research-lab',dict(self.lab,paperIds=['paper-one','other-paper']))
  self.assertEqual(links.listing('paper-one')['record']['labIds'],[self.lab['id']])
  links.save(dict(paperId='paper-one',labIds=[],scholarIds=[]));self.assertEqual(content.listing('research-lab')['items'][0]['paperIds'],['other-paper'])
 def test_rejects_missing_ids_conflicts_and_unverified_publication(self):
  for data in [dict(labIds=['missing']),dict(scholarIds=['missing']),dict(publicationStatus='published'),dict(source='javascript:bad')]:
   with self.assertRaises(ValueError):links.save(dict(paperId='paper-one',**data))
  saved=links.save(dict(paperId='paper-one',labIds=[],scholarIds=[],publicationStatus='published',publishedVenue='ICSE 2026'))
  self.assertEqual(saved['publishedVenue'],'ICSE 2026')
  with self.assertRaises(ValueError):links.save(dict(saved,revision=0))
if __name__=='__main__':unittest.main()
