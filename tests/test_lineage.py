import unittest,tempfile,pathlib,unittest.mock as mock,json,gc
import lineage_service as l,study_service as s,local_app
class LineageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=pathlib.Path(self.temp.name);self.patchers=[mock.patch.object(s,'DB',root/'study.sqlite'),mock.patch.object(local_app,'DATA',root),mock.patch.object(s,'ATLAS',root)]
  for p in self.patchers:p.start()
  self.p=s.save_paper(dict(title='Test paper',authors='Author'))
 def tearDown(self):
  gc.collect()
  for p in self.patchers[::-1]:p.stop()
  self.temp.cleanup()
 def test_topic_problem_independent(self):
  a=l.save(dict(name='Detection',kind='topic',paperIds=[self.p['id']]));b=l.save(dict(name='Small-object misses',kind='problem'))
  a=l.save(dict(a,paths=[dict(name='Start here',ids=[self.p['id']],relation='Reading order',evidence='My learning plan')]))
  self.assertEqual(l.detail(a['id'])['papers'][0]['title'],'Test paper');self.assertFalse(l.detail(b['id'])['papers']);self.assertFalse(l.detail(b['id'])['map']['paths'])
  with self.assertRaises(ValueError):l.save(dict(a,paperIds=[]))
 def test_every_classification_has_independent_map_without_overwriting_edits(self):
  import knowledge_service as k
  with s.connection() as c:k.put(c,'taxonomy',dict(id='existing-child',kind='topic',name='子主题',en='Subtopic',parentId=None,revision=1))
  m=next(m for m in l.all_maps()['items'] if m['id']=='taxonomy-existing-child')
  self.assertEqual(m['paperIds'],[])
  changed=l.save(dict(m,description='My own notes'))
  self.assertEqual(l.detail(m['id'])['map']['description'],'My own notes')
  l.archive(dict(id=m['id']))
  self.assertNotIn(m['id'],[item['id'] for item in l.all_maps()['items']])
 def test_archive_conflict_and_restore(self):
  a=l.save(dict(name='Agent',kind='topic'));l.save(dict(a,description='Updated'))
  with self.assertRaises(ValueError):l.save(a)
  l.archive(dict(id=a['id']));self.assertFalse(l.all_maps()['items']);self.assertEqual(len(l.all_maps()['archived']),1)
  l.archive(dict(id=a['id'],restore=True));self.assertEqual(l.all_maps()['items'][0]['description'],'Updated')
 def test_existing_problem_import_once(self):
  p=s.save_record('problem',dict(name='Existing problem',question='What fails?',paperIds=[self.p['id']]))
  result=l.all_maps()['items'];self.assertEqual(len(result),1);self.assertEqual(result[0]['name'],p['name']);self.assertEqual(result[0]['kind'],'problem')
  revised=l.save(dict(result[0],description='My own lineage notes'));self.assertEqual(l.all_maps()['items'][0]['description'],'My own lineage notes')
 def test_original_catalog_priority_and_untouched_map_recovery(self):
  original=dict(id='alpha',title='Original title',topic='agent',subtopic='Reasoning',year=2017,level='基础',short='Alpha')
  (s.ATLAS/'papers.json').write_text(json.dumps([original]),encoding='utf-8')
  (s.ATLAS/'foundations.json').write_text(json.dumps([dict(original,title='Derived title',topic='common')]),encoding='utf-8')
  (s.ATLAS/'topics.json').write_text('[]',encoding='utf-8')
  catalog=s.atlas_papers();self.assertEqual(len(catalog),1);self.assertEqual(catalog[0]['title'],'Original title');self.assertEqual(catalog[0]['level'],'基础');self.assertEqual(catalog[0]['topics'][0],'agent')
  old=dict(id='topic-agent',kind='topic',name='Agent',description='',paperIds=[],paths=[],revision=1)
  with s.connection() as c:
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage','topic-agent',json.dumps(old)))
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage-meta','seed-v1','{}'))
  obj=l.all_maps()['items'][0];self.assertEqual(obj['paperIds'],['atlas-alpha'])
  edited=l.save(dict(obj,paperIds=[],description='User deliberately removed this paper'))
  with s.connection() as c:c.execute("DELETE FROM records WHERE kind='lineage-meta' AND id='original-catalog-v2'")
  obj=l.all_maps()['items'][0];self.assertFalse(obj['paperIds']);self.assertEqual(obj['description'],edited['description'])
 def test_recover_omitted_paper_preserves_edited_path_order(self):
  original=[dict(id='alpha',title='Alpha',topic='agent',year=2017),dict(id='beta',title='Beta',topic='agent',year=2022)]
  (s.ATLAS/'papers.json').write_text(json.dumps(original),encoding='utf-8')
  (s.ATLAS/'foundations.json').write_text(json.dumps([dict(original[0],topic='common')]),encoding='utf-8')
  (s.ATLAS/'topics.json').write_text(json.dumps([dict(id='agent',name='Agent',paths=[dict(name='Language to action',ids=['alpha','beta'])])]),encoding='utf-8')
  evidence='原有 Paper Atlas 的编辑阅读路径；不是已核实的引用关系。'
  obj=dict(id='topic-agent',kind='topic',name='Agent',description='User notes',paperIds=['atlas-beta'],paths=[dict(id='custom',name='My custom order',ids=['atlas-beta'],relation='My relation',evidence='My evidence'),dict(id='seed',name='Language to action',ids=['atlas-beta'],relation='阅读顺序',evidence=evidence)],revision=2)
  with s.connection() as c:
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage',obj['id'],json.dumps(obj)))
   c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage-meta','seed-v1','{}'))
  result=l.all_maps()['items'][0];self.assertEqual(result['description'],'User notes');self.assertEqual(result['paths'][0],obj['paths'][0]);self.assertEqual(result['paths'][1]['ids'],['atlas-alpha','atlas-beta']);self.assertEqual(result['revision'],3)
  with s.connection() as c:backup=json.loads(c.execute("SELECT body FROM records WHERE kind='lineage-meta' AND id='initial-membership-v3'").fetchone()[0]);self.assertEqual(backup['before'][0]['revision'],2)
 def test_read_library_requires_complete_and_organized_notes(self):
  import reading_journal
  other=s.save_paper(dict(title='Unread paper'))
  self.assertFalse(l.read_library(dict(ids=[self.p['id']]))['papers'])
  tasks={t['id']:{'done':True} for t in reading_journal.definitions()}
  obj=dict(id=self.p['id'],tasks=tasks,readDate='2026-10-23',topicIds=[])
  with s.connection() as c:c.execute('INSERT INTO records VALUES(?,?,?,0)',('paper-knowledge',obj['id'],json.dumps(obj)))
  self.assertFalse(l.read_library(dict(ids=[self.p['id']]))['papers'])
  obj['topicIds']=['topic-test']
  with s.connection() as c:c.execute("UPDATE records SET body=? WHERE kind='paper-knowledge' AND id=?",(json.dumps(obj),obj['id']))
  result=l.read_library(dict(ids=[]))
  self.assertEqual([p['id'] for p in result['papers']],[self.p['id']])
  self.assertNotIn(other['id'],[p['id'] for p in result['papers']])
  with self.assertRaises(ValueError):l.read_library(dict(ids=[None]))
if __name__=='__main__':unittest.main()
