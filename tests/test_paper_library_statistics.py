import unittest,tempfile,pathlib,gc,json
from unittest.mock import patch
import study_service as study,local_app,reading_journal

class LibraryStatisticsTests(unittest.TestCase):
 def test_catalog_union_and_current_completed_tasks(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)
   with patch.object(local_app,'DATA',root),patch.object(study,'DB',root/'study.sqlite'),patch.object(study,'atlas_papers',return_value=[{'id':'catalog-a'},{'id':'atlas-only'}]):
    local_app.absorb([dict(id='catalog-a',title='Read paper'),dict(id='catalog-b',title='Unread paper')])
    tasks={t['id']:{'done':True} for t in reading_journal.definitions()}
    with study.connection() as c:
     for ident,value in [('catalog-a',dict(readDate='2026-10-21',tasks=tasks)),('catalog-b',dict(readDate='2026-10-21',tasks={})),('orphan-paper',dict(readDate='2026-10-21',tasks=tasks))]:c.execute('INSERT INTO records VALUES(?,?,?,0)',('paper-knowledge',ident,json.dumps(dict(id=ident,**value))))
    self.assertEqual(reading_journal.statistics(),dict(total=2,read=1,unread=1,todayRead=int(study.today()=='2026-10-21'),todayUnread=0))
    tasks['problem']['done']=False
    with study.connection() as c:c.execute("UPDATE records SET body=? WHERE kind='paper-knowledge' AND id='catalog-a'",(json.dumps(dict(id='catalog-a',readDate='2026-10-21',tasks=tasks)),))
    self.assertEqual(reading_journal.statistics(),dict(total=2,read=0,unread=2,todayRead=0,todayUnread=0))
   gc.collect()
