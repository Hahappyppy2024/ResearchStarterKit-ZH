import concurrent.futures,pathlib,tempfile,unittest
from unittest.mock import patch
import research_pet as pet
class PetTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.paper={'id':'arxiv-2610.12345','title':'A research paper','source':'https://arxiv.org/abs/2610.12345'};self.patches=[patch.object(pet,'DB',pathlib.Path(self.temp.name)/'pet.sqlite'),patch.object(pet,'completed_items',return_value=[self.paper]),patch.object(pet.study,'today',return_value='2026-10-24')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def spend(self,action,ident,amount=1):return pet.act(dict(action=action,requestId=ident,amount=amount))
 def test_unique_read_reward_aliases_and_repeated_read_toggles(self):
  self.assertEqual(pet.state()['shells'],1)
  with patch.object(pet,'completed_items',return_value=[self.paper,{**self.paper,'id':'zotero-copy','source':''}]):self.assertEqual(pet.state()['readings'],1)
  with patch.object(pet,'completed_items',return_value=[]):self.assertEqual(pet.state()['shells'],1)
  self.assertEqual(pet.state()['shells'],1)
 def test_exact_conversion_consumption_and_retry_idempotency(self):
  state=self.spend('exchange','request-exchange');self.assertEqual((state['shells'],state['food']),(0,1))
  self.assertEqual(self.spend('exchange','request-exchange')['food'],1)
  state=self.spend('feed','request-feeding');self.assertEqual((state['food'],state['fed']),(0,1))
  self.assertEqual(self.spend('feed','request-feeding')['fed'],1)
  with self.assertRaises(ValueError):self.spend('feed','another-request')
  with self.assertRaises(ValueError):self.spend('feed','request-exchange')
 def test_concurrent_spending_cannot_make_negative_balance(self):
  pet.state()
  def spend(i):
   try:self.spend('exchange','parallel-'+str(i));return True
   except ValueError:return False
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:success=list(pool.map(spend,range(2)))
  self.assertEqual(sum(success),1);self.assertEqual(pet.state()['food'],1)
 def test_publications_are_explicit_deduped_and_soft_deletable(self):
  record=dict(action='publication-add',title='My Paper',venue='A Conference',date='2026-10-20',author='co-first')
  saved=pet.act(record);ident=saved['publications'][0]['id'];self.assertTrue(saved['growth']['hum']);self.assertEqual(saved['shells'],1)
  with self.assertRaises(ValueError):pet.act(record)
  with self.assertRaises(ValueError):pet.act({**record,'title':'Future','date':'2026-10-25'})
  self.assertEqual(len(pet.act(dict(action='publication-remove',id=ident))['publications']),0)
  self.assertEqual(len(pet.act(dict(action='publication-restore',id=ident))['publications']),1)
 def test_growth_and_skills_have_no_wings_or_paid_requirements(self):
  self.assertEqual(pet.progress(0,0)['sprite'],0);self.assertTrue(pet.progress(5,0)['dance']);self.assertFalse(pet.progress(5,0)['hum']);self.assertTrue(pet.progress(20,0)['hum']);self.assertEqual(pet.progress(150,3)['name'],'音乐伙伴');self.assertLessEqual(pet.progress(150,3)['sprite'],2)
if __name__=='__main__':unittest.main()
