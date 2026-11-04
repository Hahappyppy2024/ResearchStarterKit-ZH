import unittest,tempfile,pathlib,sqlite3,json,contextlib,gc,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import paper_titles as titles

class PaperTitlesTests(unittest.TestCase):
 def setUp(self):
  import local_app
  self.temp=tempfile.TemporaryDirectory();root=pathlib.Path(self.temp.name);(root/'local-data').mkdir()
  self.patches=[patch.object(titles.study,'DB',root/'local-data/study.sqlite'),patch.object(local_app,'DATA',root/'local-data'),patch.object(titles.library.reader_service,'ROOT',root)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  gc.collect();self.temp.cleanup()
 def test_english_title_translation_only_sends_title(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='An English Paper',summary='Do not translate this',note='Private note')),patch.object(titles.library,'translate_text',return_value='英文论文') as translate:
   result=titles.bilingual_title(dict(paperId='test',title='Injected text'))
   self.assertEqual(result['titleEn'],'An English Paper');self.assertEqual(result['titleZh'],'英文论文')
   translate.assert_called_once_with('An English Paper')
 def test_explicit_bilingual_metadata_needs_no_online_translation(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='Original',titleZh='中文标题',titleEn='Original')),patch.object(titles.library,'translate_text') as translate:
   self.assertEqual(titles.bilingual_title(dict(paperId='test'))['titleZh'],'中文标题');translate.assert_not_called()
 def test_failure_keeps_source_title(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='Original title')),patch.object(titles.library,'translate_text',side_effect=ValueError('offline')):
   result=titles.bilingual_title(dict(paperId='test'));self.assertEqual(result['titleEn'],'Original title');self.assertTrue(result['error'])
 def test_chinese_title_translates_to_english(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='中文论文')),patch.object(titles,'translate_english',return_value='Chinese paper') as translate:
   result=titles.bilingual_title(dict(paperId='test'));self.assertEqual(result['titleZh'],'中文论文');self.assertEqual(result['titleEn'],'Chinese paper');translate.assert_called_once_with('中文论文')
 def test_reverse_translation_uses_directional_cache(self):
  with tempfile.TemporaryDirectory() as folder:
   def connection():
    c=sqlite3.connect(pathlib.Path(folder)/'cache.sqlite');c.execute('CREATE TABLE IF NOT EXISTS translations(hash TEXT PRIMARY KEY,en TEXT,zh TEXT,provider TEXT)');return c
   class Response:
    def raise_for_status(self):pass
    def json(self):return [[['Chinese paper']]]
   with patch.object(titles.library.reader_service,'connection',side_effect=connection),patch('requests.get',return_value=Response()) as request:
    self.assertEqual(titles.translate_english('中文论文'),'Chinese paper');self.assertEqual(titles.translate_english('中文论文'),'Chinese paper');self.assertEqual(request.call_count,1)
 def test_concurrent_ids_share_one_persistent_translation(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='Shared title')),patch.object(titles.library,'translate_text',return_value='共享标题') as translate:
   with ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(lambda i:titles.bilingual_title({'paperId':str(i)}),range(4)))
   self.assertTrue(all(r['titleZh']=='共享标题' for r in results));translate.assert_called_once_with('Shared title')
  # A new lock and no frontend memory still read the saved database entry.
  with patch.object(titles,'LOCK',__import__('threading').Lock()),patch.object(titles.study,'resolve',return_value=dict(title='Shared title')),patch.object(titles.library,'translate_text',side_effect=AssertionError('Must reuse disk cache')):
   self.assertEqual(titles.bilingual_title({'paperId':'another-page'})['titleZh'],'共享标题')
 def test_conference_route_reuses_title_saved_by_another_page(self):
  venue=titles.library.conferences.VENUES[0]
  with patch.object(titles.study,'resolve',return_value=dict(title='Shared conference title',venue=venue)),patch.object(titles.library,'translate_text',return_value='会议标题') as translate:
   titles.bilingual_title({'paperId':'atlas'})
   result=titles.library.translate({'paperId':'library'})
   self.assertEqual(result['titleZh'],'会议标题');self.assertEqual(result['titleEn'],'Shared conference title')
   self.assertEqual([c.args[0] for c in translate.call_args_list if c.args[0]],['Shared conference title'])
 def test_legacy_saved_metadata_seeds_cache_for_other_ids(self):
  import local_app
  local_app.absorb([dict(id='old',title='Existing saved title',titleZh='已有译名')])
  with patch.object(titles.study,'resolve',return_value=dict(title='Existing saved title')),patch.object(titles.library,'translate_text',side_effect=AssertionError('Do not translate again')):
   self.assertEqual(titles.bilingual_title({'paperId':'new'})['titleZh'],'已有译名')
  self.assertEqual(titles.hydrate_titles([dict(title='Existing saved title')])[0]['titleZh'],'已有译名')
 def test_hydration_persists_known_titles_and_reuses_legacy_reader_cache(self):
  import hashlib
  with contextlib.closing(titles.library.reader_service.connection()) as c,c:
   c.execute('INSERT INTO translations VALUES(?,?,?,?)',(hashlib.sha256(b'Legacy title').hexdigest(),'Legacy title','旧缓存译名','test'))
  with patch.object(titles.library,'translate_text',side_effect=AssertionError('Hydration is offline')):
   titles.hydrate_titles([dict(title='Known title',titleZh='已知标题'),dict(title='Legacy title')])
   found=titles.hydrate_titles([dict(title='Known title'),dict(title='Legacy title')])
   self.assertEqual([p['titleZh'] for p in found],['已知标题','旧缓存译名'])
 def test_changed_title_and_failed_translation_do_not_cache_wrong_results(self):
  with patch.object(titles.study,'resolve',return_value=dict(title='First title')),patch.object(titles.library,'translate_text',return_value='首个标题'):
   titles.bilingual_title({'paperId':'same-id'})
  with patch.object(titles.study,'resolve',return_value=dict(title='Changed source title')),patch.object(titles.library,'translate_text',side_effect=ValueError('offline')):
   self.assertTrue(titles.bilingual_title({'paperId':'same-id'})['error'])
  with patch.object(titles.study,'resolve',return_value=dict(title='Changed source title')),patch.object(titles.library,'translate_text',return_value='新标题') as translate:
   self.assertEqual(titles.bilingual_title({'paperId':'same-id'})['titleZh'],'新标题');translate.assert_called_once()
 def test_separate_processes_do_not_translate_the_same_title_twice(self):
  script='''
import sys,pathlib
from unittest.mock import patch
import paper_titles as t,local_app
root=pathlib.Path(sys.argv[1]);t.study.DB=root/'local-data/study.sqlite';local_app.DATA=root/'local-data';t.library.reader_service.ROOT=root
def translate(text):
 with (root/'calls.txt').open('a',encoding='utf-8') as f:f.write('called\\n')
 return 'saved translation'
with patch.object(t.study,'resolve',return_value={'title':'Concurrent process title'}),patch.object(t.library,'translate_text',side_effect=translate):
 assert t.bilingual_title({'paperId':sys.argv[2]})['titleZh']=='saved translation'
'''
  processes=[subprocess.Popen([sys.executable,'-c',script,self.temp.name,str(i)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for i in range(2)]
  for process in processes:
   stdout,stderr=process.communicate(timeout=30);self.assertEqual(process.returncode,0,stderr.decode(errors='replace'))
  self.assertEqual((pathlib.Path(self.temp.name)/'calls.txt').read_text().splitlines(),['called'])
if __name__=='__main__':unittest.main()
