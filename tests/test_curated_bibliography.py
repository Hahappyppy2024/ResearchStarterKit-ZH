import json,sqlite3,unittest
from unittest.mock import patch
import local_app

class CuratedBibliographyTest(unittest.TestCase):
 def test_reingest_preserves_verified_venue_and_authorship(self):
  c=sqlite3.connect(':memory:')
  c.execute('CREATE TABLE papers(id TEXT PRIMARY KEY,title TEXT,venue TEXT,year INTEGER,body TEXT)')
  saved=dict(id='paper',title='Video Feature Prediction',venue='TMLR',year=2024,authors='Verified Authors',curatedBibliography=True,source='https://arxiv.org/abs/2404.08471')
  c.execute('INSERT INTO papers VALUES(?,?,?,?,?)',('paper',saved['title'],'TMLR',2024,json.dumps(saved)));c.commit()
  with patch.object(local_app,'db',return_value=c),patch.object(local_app.paper_scope,'reason',return_value=''):
   local_app.absorb([dict(id='paper',title='video feature prediction',venue='ICLR',year=2025,authors='Old metadata')])
  row=c.execute('SELECT venue,year,body FROM papers').fetchone()
  self.assertEqual(row[:2],('TMLR',2024));self.assertEqual(json.loads(row[2])['authors'],'Verified Authors');c.close()

if __name__=='__main__':unittest.main()
