import datetime,json,pathlib,tempfile,unittest,urllib.parse
from unittest.mock import patch
import weekly_arxiv as service

class WeeklyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
  self.patches=[patch.object(service,'DATA',self.root),patch.object(service,'DB',self.root/'weeks.sqlite'),patch.object(service,'today',return_value='2026-10-21')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_daily_worker_updates_current_week_and_previous_even_when_one_fails(self):
  with patch.object(service,'fetch_week',side_effect=[RuntimeError('offline'),{'week':'2026-10-12'}]) as fetch:
   result=service.update_daily_archives()
  self.assertEqual([c.args[0] for c in fetch.call_args_list],['2026-10-19','2026-10-12'])
  self.assertEqual(result,[{'week':'2026-10-12'}])
 def test_daily_check_does_not_reassign_paper_dates(self):
  with service.connection() as c:service.store(c,self.paper(),'2026-10-21T12:00:00+08:00')
  run=service.record_morning([{'week':'2026-10-12','papers':1}])
  self.assertNotIn('papers',run)
  self.assertEqual(service.get_day('2026-10-13')['count'],1)
  self.assertEqual(service.get_day('2026-10-21')['count'],0)
  self.assertEqual(service.daily_check()['status'],'complete')
 def paper(self,id='arxiv-2610.10001',published='2026-10-13',updated='2026-10-13',title='First snapshot'):
  return dict(id=id,title=title,venue='arXiv',year=2026,published=published,updated=updated,topics=['Agent'])
 def digest(self,date,papers):
  (self.root/(date+'.json')).write_text(json.dumps(dict(checkedAt=date+'T08:00:00+08:00',papers=papers)),encoding='utf-8')
 def test_week_boundary_snapshots_updates_and_id_dedup(self):
  self.assertEqual(service.monday('2027-01-01'),'2026-12-28')
  self.digest('2026-10-20',[self.paper(),self.paper(updated='2026-10-20'),self.paper('arxiv-2501.12345','2025-01-01','2026-10-20')])
  service.archive_local();old=service.get_week('2026-10-12');self.assertEqual(len(old['papers']),1)
  self.assertEqual(len(service.get_week('2026-10-19','update')['papers']),2)
  self.digest('2026-10-21',[{**self.paper(title='Changed later'),'topics':['Agent','Agent Harness']}]);service.archive_local()
  kept=service.get_week('2026-10-12')['papers'][0];self.assertEqual(kept['title'],'First snapshot');self.assertIn('Agent Harness',kept['topics'])
  self.assertEqual(service.list_weeks()['defaultWeek'],'2026-10-12')
  self.assertNotIn('2024-12-30',[w['start'] for w in service.list_weeks()['weeks']])
 def test_curation_is_per_week_and_rejects_unknown_ids(self):
  self.digest('2026-10-20',[self.paper()]);service.archive_local()
  service.save_curation(dict(week='2026-10-12',notes='Problem → method → next step',picks=['arxiv-2610.10001']))
  self.assertEqual(service.get_week('2026-10-12')['curation']['notes'],'Problem → method → next step')
  self.assertIsNone(service.get_week('2026-10-19')['curation']['picks'])
  with self.assertRaises(ValueError):service.save_curation(dict(week='2026-10-12',notes='',picks=['arxiv-2610.99999']))
 def test_daily_flow_archives_use_first_publication_not_collection_or_update_date(self):
  self.digest('2026-10-20',[self.paper(),self.paper(updated='2026-10-20'),self.paper('arxiv-2610.10002','2026-10-14','2026-10-14')])
  days=service.list_days()['days'];self.assertEqual([d for d in days if d['count']],[dict(date='2026-10-14',count=1),dict(date='2026-10-13',count=1)]);self.assertEqual(days[0],dict(date='2026-10-21',count=0))
  first=service.get_day('2026-10-13');self.assertEqual(first['count'],1);self.assertEqual(first['papers'][0]['title'],'First snapshot')
  self.assertEqual(service.get_day('2026-10-20')['count'],0)
  self.digest('2026-10-21',[self.paper(title='Changed later')]);service.archive_local()
  self.assertEqual(service.get_day('2026-10-13')['papers'][0]['title'],'First snapshot')
  with self.assertRaises(ValueError):service.get_day('2026-10-22')
 def feed(self,start,count,total=101):
  entries=''.join(f'<entry><id>https://arxiv.org/abs/2610.{10000+i}v1</id><title>Agent {i}</title><published>2026-10-13T12:00:00Z</published><updated>2026-10-13T12:00:00Z</updated><summary>agent tools</summary><author><name>A</name></author></entry>' for i in range(start,start+count))
  return f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>{total}</o:totalResults>{entries}</feed>'.encode()
 def test_paginated_range_and_no_zotero_write(self):
  calls=[]
  def fetch(url):
   q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query);calls.append(q);start=int(q['start'][0]);return self.feed(start,100 if start==0 else 1)
  with patch('topics_service.list_topics',return_value=[dict(name='Agent',query='all:agent OR all:agentic')]),patch('local_app.absorb') as absorb,patch('local_app.sync_zotero') as sync:
   result=service.fetch_week('2026-10-12',fetcher=fetch,pause=lambda _:None)
   self.assertEqual(result['papers'],101);self.assertEqual(len(calls),2);self.assertIn('(all:agent OR all:agentic) AND submittedDate:[202610120000 TO 202610182359]',calls[0]['search_query'][0]);self.assertEqual(calls[1]['start'],['100'])
   absorb.assert_called_once();sync.assert_not_called()
   cached=service.fetch_week('2026-10-12',fetcher=lambda _:self.fail('cached week was fetched again'));self.assertTrue(cached['cached'])
  self.assertEqual(len(service.get_week('2026-10-12')['papers']),101)
 def test_failed_pagination_keeps_archive_and_coverage(self):
  self.digest('2026-10-20',[self.paper()]);service.archive_local()
  def fetch(url):
   start=int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['start'][0])
   if start:raise RuntimeError('temporary network failure')
   return self.feed(0,100)
  with patch('topics_service.list_topics',return_value=[dict(name='Agent',query='all:agent')]):
   with self.assertRaises(RuntimeError):service.fetch_week('2026-10-12',fetcher=fetch,pause=lambda _:None)
  self.assertEqual(len(service.get_week('2026-10-12')['papers']),1)
  meta=service.get_week('2026-10-12')['meta'];self.assertNotEqual(meta.get('status'),'fetched');self.assertIn('network',meta['error'])

if __name__=='__main__':unittest.main()
