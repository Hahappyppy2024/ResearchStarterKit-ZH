import contextlib
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import topic_library as lib
import study_service as study

class TopicLibraryTests(unittest.TestCase):
    def test_sources_descendants_multilabel_and_pagination(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(study,'DB',pathlib.Path(folder)/'study.sqlite'):
            papers={str(i):dict(id=str(i),title='Agent security '+str(i),venue='ICLR',year=2026,categories=[('agents','agentsecurity'),('safety','security')],conference=True) for i in range(24)}
            personal=[dict(id='manual',title='My paper',read=False,inToday=True)]
            nodes=[dict(id='mine',name='My topic',kind='topic',parentId=None),dict(id='child',name='Child',kind='topic',parentId='mine')]
            with study.connection() as c:
                lib.knowledge.put(c,'paper-knowledge',dict(id='manual',topicIds=['child']))
            with patch.object(lib,'conference_rows',return_value=papers),patch.object(lib.knowledge,'taxonomy',return_value={'nodes':nodes}),patch.object(lib.reading_journal,'statistics',return_value={'items':personal}),patch.object(study,'resolve',return_value=dict(id='manual',title='My paper',summary='Object detection',year=2026,venue='self')),patch.object(lib,'batch_translations',return_value={}):
                first=lib.browse('safety',venue='ICLR',year='2026')
                self.assertEqual((first['count'],len(first['papers'])),(24,20))
                self.assertEqual(len(lib.browse('safety',page=1)['papers']),4)
                self.assertEqual(lib.browse('mine',source='personal')['papers'][0]['id'],'manual')
                self.assertEqual(lib.browse('mine',source='personal')['personalCount'],1)
                self.assertEqual(lib.browse('mine',source='conference')['count'],0)
                self.assertEqual(lib.browse('safety',state='read')['count'],0)

    def test_snapshot_reused_then_invalidated_by_saved_study_data(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(study,'DB',pathlib.Path(folder)/'study.sqlite'):
            papers={'c':dict(id='c',title='Test',venue='ICSE',year=2026,categories=[('software','general')],conference=True)}
            with patch.object(lib,'conference_rows',return_value=papers),patch.object(lib.knowledge,'taxonomy',return_value={'nodes':[]}),patch.object(lib.reading_journal,'statistics',return_value={'items':[]}) as stats,patch.object(lib,'batch_translations',return_value={}):
                a=lib.browse(venue='ICSE');b=lib.browse(venue='ICSE')
                self.assertEqual(stats.call_count,1)
                self.assertFalse(a['papers'][0]['inToday'])
                a['topics'][0]['name']='Do not mutate cached sidebar'
                self.assertNotEqual(lib.browse()['topics'][0]['name'],a['topics'][0]['name'])
                with study.connection() as c:lib.knowledge.put(c,'cache-test',dict(id='changed'))
                stats.return_value={'items':[dict(id='c',read=True,inToday=True)]}
                result=lib.browse(venue='ICSE')
                self.assertTrue(result['papers'][0]['inToday']);self.assertTrue(result['papers'][0]['read'])
                self.assertEqual(stats.call_count,2)

    def test_security_topic_matches_cybersecurity_and_vulnerabilities(self):
        import conference_catalog as catalog
        self.assertIn(('safety','security'),catalog.classify_paper({'title':'Finding software vulnerabilities with language models'}))
        self.assertIn(('safety','security'),catalog.classify_paper({'title':'Cybersecurity agents for intrusion detection'}))
        self.assertTrue(any(n['id']=='safety' and n['name']=='安全' for n in lib.topic_index()[0]))

    def test_translation_reuses_cache_and_rejects_personal_notes(self):
        with patch.object(study,'resolve',return_value={'venue':'self','title':'Private note'}):
            with self.assertRaises(ValueError):lib.translate({'paperId':'private'})
        with tempfile.TemporaryDirectory() as folder:
            def connection():
                c=sqlite3.connect(pathlib.Path(folder)/'translations.sqlite')
                c.execute('CREATE TABLE IF NOT EXISTS translations(hash TEXT PRIMARY KEY,en TEXT,zh TEXT,provider TEXT)');return c
            class Response:
                def raise_for_status(self):pass
                def json(self):return [[['智能体安全','Agent security']]]
            with patch.object(lib.reader_service,'connection',side_effect=connection),patch('requests.get',return_value=Response()) as request:
                self.assertEqual(lib.translate_text('Agent security'),'智能体安全')
                self.assertEqual(lib.translate_text('Agent security'),'智能体安全')
                self.assertEqual(request.call_count,1)

if __name__=='__main__':unittest.main()
