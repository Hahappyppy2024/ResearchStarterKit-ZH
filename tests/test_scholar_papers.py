import unittest,tempfile,pathlib,json,gc
from unittest.mock import patch
import study_service as study,local_app,workspace_content as content,scholar_papers as papers
class ScholarPaperTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.patches=[patch.object(study,'DB',self.root/'study.sqlite'),patch.object(local_app,'DATA',self.root),patch.object(papers,'STATIC',self.root/'static.json'),patch.object(papers,'TRACKING',self.root/'tracking.json'),patch.object(content,'scholar_directory',return_value={'people':[dict(id='a',name='Alice',en='Alice Author',labIds=[]),dict(id='b',name='Bob',en='Bob Writer',labIds=[])]})]
  for p in self.patches:p.start()
  (self.root/'static.json').write_text(json.dumps(dict(people=[dict(id='a',name='Alice',en='Alice Author')],papers=[dict(id='official',person='a',title='Official work',status='ICLR 2025',type='论文',year=2025,url='https://example.org/paper')])) ,encoding='utf-8')
  (self.root/'tracking.json').write_text(json.dumps(dict(scholars=[dict(personId='a',papers=[dict(id='2601.12345',title='Tracked work',authors=['Alice Author'],published='2026-01-10',url='https://arxiv.org/abs/2601.12345')])])),encoding='utf-8')
  local_app.absorb([dict(id='local-a',title='Existing Alice work',authors='Alice Author, Other Author',venue='CVPR'),dict(id='not-alice',title='Different author',authors='Alice Authorson',venue='CVPR'),dict(id='local-b',title='Bob work',authors='Bob Writer',venue='ICML')])
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  gc.collect();self.tmp.cleanup()
 def test_scholar_includes_collected_tracked_and_existing_library_without_lab_links(self):
  result=papers.listing('a')['papers'];ids={p['id'] for p in result}
  self.assertEqual(ids,{'scholar-work-official','arxiv-2601.12345','local-a'})
  self.assertNotIn('local-b',ids);self.assertNotIn('not-alice',ids)
 def test_lab_uses_explicit_members_and_paper_associations(self):
  lab=content.save('research-lab',dict(name='Lab',university='University',scholars='Alice Author',paperIds=['local-b']))
  ids={p['id'] for p in papers.listing(lab_id=lab['id'])['papers']}
  self.assertIn('local-b',ids);self.assertIn('scholar-work-official',ids)
  self.assertEqual(content.listing('research-lab')['items'][0]['university'],'University')
 def test_leader_is_persisted_and_included_as_lab_member(self):
  lab=content.save('research-lab',dict(name='PI Lab',leaders='Alice Author',scholars=''))
  saved=next(l for l in content.listing('research-lab')['items'] if l['id']==lab['id'])
  self.assertEqual(saved['leaders'],'Alice Author')
  ids={p['id'] for p in papers.listing(lab_id=lab['id'])['papers']}
  self.assertIn('scholar-work-official',ids)
  self.assertNotIn('local-b',ids)
 def test_invalid_selection_and_metadata_resolution(self):
  with self.assertRaises(ValueError):papers.listing('unknown')
  with self.assertRaises(ValueError):papers.listing(lab_id='unknown')
  self.assertEqual(study.resolve('paper','arxiv-2601.12345')['title'],'Tracked work')
  with study.connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM queue').fetchone()[0],0)
if __name__=='__main__':unittest.main()
