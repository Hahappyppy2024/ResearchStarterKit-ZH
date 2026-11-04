import pathlib,tempfile,unittest
from unittest.mock import patch
import study_service as study
import research_pond as pond

class PondTests(unittest.TestCase):
 def test_same_paper_aliases_and_repeated_release_only_count_once(self):
  papers=[dict(id='arxiv-2401.12345',title='Same Paper',completedDate='2026-10-27'),dict(id='catalog-id',title='Same Paper',source='https://arxiv.org/abs/2401.12345v2',completedDate='2026-10-27')]
  with tempfile.TemporaryDirectory(dir=study.ROOT/'local-data') as temp,patch.object(pond,'DB',pathlib.Path(temp)/'pond.sqlite'),patch.object(pond,'completed_items',return_value=papers):
   state=pond.state();self.assertEqual(state['readyCount'],1)
   ident=state['ready'][0]['id'];first=pond.release(dict(fishId=ident));second=pond.release(dict(fishId=ident))
   self.assertEqual(first['releasedCount'],1);self.assertEqual(second['releasedCount'],1);self.assertTrue(second['alreadyReleased']);self.assertEqual(second['readyCount'],0)
   with patch.object(pond,'completed_items',return_value=[]):self.assertEqual(pond.state()['releasedCount'],1)
 def test_uncompleted_pending_fish_cannot_be_released(self):
  papers=[dict(id='paper',title='Paper',completedDate='2026-10-27')]
  with tempfile.TemporaryDirectory(dir=study.ROOT/'local-data') as temp,patch.object(pond,'DB',pathlib.Path(temp)/'pond.sqlite'):
   with patch.object(pond,'completed_items',return_value=papers):ident=pond.state()['ready'][0]['id']
   with patch.object(pond,'completed_items',return_value=[]):
    with self.assertRaises(ValueError):pond.release(dict(fishId=ident))

if __name__=='__main__':unittest.main()
