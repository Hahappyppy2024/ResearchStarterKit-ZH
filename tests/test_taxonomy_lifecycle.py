import json,pathlib,tempfile,unittest
from unittest.mock import patch
import study_service as study
import taxonomy_lifecycle as lifecycle

class LifecycleTests(unittest.TestCase):
 def test_empty_leaf_archive_restore_keeps_definition(self):
  with tempfile.TemporaryDirectory(dir=study.ROOT/'local-data') as temp,patch.object(study,'DB',pathlib.Path(temp)/'study.sqlite'):
   node=dict(id='leaf',kind='topic',name='Empty',en='Empty',revision=1,parentId=None)
   with study.connection() as c:
    c.execute('INSERT INTO records VALUES(?,?,?,0)',('taxonomy','leaf',json.dumps(node)))
    c.execute('INSERT INTO records VALUES(?,?,?,0)',('lineage','taxonomy-leaf',json.dumps(dict(paperIds=[],paths=[]))))
   self.assertTrue(lifecycle.status('leaf')['canArchive'])
   lifecycle.archive(dict(id='leaf',revision=1))
   self.assertEqual(lifecycle.archived()['items'],[node])
   lifecycle.archive(dict(id='leaf',revision=1,restore=True))
   with study.connection() as c:self.assertEqual(study.records(c,'taxonomy'),[node])
 def test_children_and_paper_references_block_removal(self):
  with tempfile.TemporaryDirectory(dir=study.ROOT/'local-data') as temp,patch.object(study,'DB',pathlib.Path(temp)/'study.sqlite'):
   with study.connection() as c:
    for n in [dict(id='parent',kind='topic',name='Parent',en='Parent',revision=1),dict(id='child',kind='topic',name='Child',en='Child',revision=1,parentId='parent')]:
     c.execute('INSERT INTO records VALUES(?,?,?,0)',('taxonomy',n['id'],json.dumps(n)))
    c.execute('INSERT INTO records VALUES(?,?,?,0)',('paper-knowledge','paper',json.dumps(dict(id='paper',topicIds=['child']))))
   for ident in ('parent','child'):
    self.assertFalse(lifecycle.status(ident)['canArchive'])
    with self.assertRaises(ValueError):lifecycle.archive(dict(id=ident,revision=1))

if __name__=='__main__':unittest.main()
