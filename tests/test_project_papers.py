import gc,tempfile,pathlib,unittest
from unittest.mock import patch
import projects_service as projects,study_service as study,local_app,project_papers as links,knowledge_service

class ProjectPaperTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=pathlib.Path(self.tmp.name);self.patches=[patch.object(projects,'DB_PATH',root/'projects.sqlite'),patch.object(study,'DB',root/'study.sqlite'),patch.object(study,'ATLAS',root/'empty'),patch.object(local_app,'DATA',root)]
  for p in self.patches:p.start()
  self.project=projects.save_project(dict(name='项目 A'));self.other=projects.save_project(dict(name='项目 B'))
 def tearDown(self):
  for p in self.patches:p.stop()
  gc.collect();self.tmp.cleanup()
 def test_new_shared_catalog_queue_dedup_and_multirelations(self):
  result=links.save(dict(projectId=self.project['id'],relationTypes=['reproduce','baseline'],paper=dict(title='Unique paper',authors='Author',source='https://example.org/paper',pdf='https://example.org/paper.pdf',summary='Summary')))
  ident=result['paper']['id'];self.assertEqual(study.resolve('paper',ident)['authors'],'Author');self.assertEqual(study.state()['queue'][0]['paperId'],ident)
  knowledge_service.save_paper(dict(paperId=ident,tasks={'problem':dict(answer='Keep this note')}))
  repeated=links.save(dict(projectId=self.project['id'],relationTypes=['module'],paper=dict(title='Unique paper',authors='Do not overwrite')))
  self.assertTrue(repeated['reused']);self.assertEqual(repeated['paper']['id'],ident);self.assertEqual(len(study.state()['queue']),1);self.assertEqual(len(links.listing(self.project['id'])['items']),1);self.assertEqual(set(repeated['link']['relationTypes']),{'reproduce','baseline','module'});self.assertEqual(knowledge_service.get_paper(ident)['tasks']['problem']['answer'],'Keep this note')
  links.save(dict(projectId=self.other['id'],paperId=ident,relationTypes=['dataset']))
  queued=study.state()['queue'][0];self.assertEqual(set(queued['projectIds']),{self.project['id'],self.other['id']});self.assertEqual(len(queued['projectRelations']),2)
 def test_publication_metadata_saved_to_shared_library(self):
  for title,venue,kind,year in [('Conference paper','CVPR','conference',2025),('Journal paper','IEEE TGRS','journal',2024)]:
   result=links.save(dict(projectId=self.project['id'],relationTypes=['background'],paper=dict(title=title,venue=venue,publicationType=kind,year=str(year))))
   paper=study.resolve('paper',result['paper']['id'])
   self.assertEqual((paper['venue'],paper['publicationType'],paper['year']),(venue,kind,year))
   self.assertIn(paper['id'],[p['id'] for p in study.catalog(venue=venue)['items']])
   with local_app.db() as c:
    stored=c.execute('SELECT venue,year FROM papers WHERE id=?',(paper['id'],)).fetchone()
   self.assertEqual(tuple(stored),(venue,year))
  for extra in ({'year':'oops'},{'venue':''},{'publicationType':'unknown'}):
   with self.assertRaises(ValueError):links.save(dict(projectId=self.project['id'],relationTypes=['background'],paper=dict(title='Invalid paper',**extra)))
 def test_revision_roles_and_archived_project(self):
  paper=study.save_paper(dict(title='Existing paper'));created=links.save(dict(projectId=self.project['id'],paperId=paper['id'],relationTypes=['uncertain']))
  changed=links.save(dict(projectId=self.project['id'],paperId=paper['id'],revision=created['link']['revision'],relationTypes=['foundation','improve']));self.assertEqual(changed['link']['relationTypes'],['foundation','improve'])
  with self.assertRaises(ValueError):links.save(dict(projectId=self.project['id'],paperId=paper['id'],revision=created['link']['revision'],relationTypes=['baseline']))
  for roles in ([],['unknown'],['uncertain','baseline']):
   with self.assertRaises(ValueError):links.save(dict(projectId=self.project['id'],paperId=paper['id'],relationTypes=roles))
  projects.archive(dict(kind='project',id=self.project['id']))
  with self.assertRaises(ValueError):links.save(dict(projectId=self.project['id'],paperId=paper['id'],relationTypes=['baseline']))
  self.assertEqual(len(links.listing(self.project['id'])['items']),1)
