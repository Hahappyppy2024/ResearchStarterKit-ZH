import unittest,tempfile,pathlib,json,base64,io
from unittest.mock import patch
from PIL import Image
import workspace_content as w,study_service as s
class WorkspaceTests(unittest.TestCase):
 def test_blog_folder_hierarchy_dates_and_legacy_notes(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   old=w.save('blog-post',dict(title='Existing note',content='Keep my text'))
   root=w.save('blog-folder',dict(name='Research',parentId=''))
   child=w.save('blog-folder',dict(name='Paper notes',parentId=root['id']))
   note=w.save('blog-post',dict(title='Dated note',content='# Heading',folderId=child['id'],noteDate='2026-10-23'))
   with self.assertRaises(ValueError):w.save('blog-folder',dict(root,parentId=child['id']))
   with self.assertRaises(ValueError):w.save('blog-post',dict(note,noteDate='2026-02-30'))
   with self.assertRaises(ValueError):w.save('blog-post',dict(note,folderId='unknown'))
   saved=w.save('blog-post',dict(note,archived=True))
   self.assertEqual(w.listing('blog-post')['archived'][0]['folderId'],child['id'])
   self.assertEqual(w.listing('blog-post')['items'][0]['content'],old['content'])
 def test_blog_trash_restore_and_lab_topics(self):
  import knowledge_service as k
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   topic=k.save_node(dict(kind='topic',name='Lab Topic',en='Test definition'))
   lab=w.save('research-lab',dict(name='Lab',topicIds=[topic['id']]))
   self.assertEqual(lab['topicIds'],[topic['id']])
   with self.assertRaises(ValueError):w.save('research-lab',dict(lab,topicIds=['unknown']))
   note=w.save('blog-post',dict(title='Keep',content='Body ![image](local.png)',tags='tag'))
   removed=w.save('blog-post',dict(note,deleted=True,archived=True))
   listing=w.listing('blog-post');self.assertFalse(listing['items']);self.assertFalse(listing['archived']);self.assertEqual(listing['trash'][0]['id'],note['id'])
   restored=w.save('blog-post',dict(removed,deleted=False,archived=False))
   self.assertEqual(restored['content'],note['content']);self.assertFalse(w.listing('blog-post')['trash'])
 def test_scholar_creation_lab_membership_duplicate_and_edit_conflict(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   lab=w.save('research-lab',dict(name='QA laboratory'))
   person=w.save_scholar(dict(name='新增学者 QA',en='Unique QA Scholar',institution='QA University',labIds=[lab['id']],research='Research notes'))
   loaded=next(p for p in w.scholar_directory()['people'] if p['id']==person['id'])
   self.assertEqual(loaded['labIds'],[lab['id']]);self.assertEqual(loaded['institution'],'QA University')
   with self.assertRaises(ValueError):w.save_scholar(dict(name='Duplicate',en='Unique QA Scholar'))
   with self.assertRaises(ValueError):w.save_scholar(dict(person,revision=0))
   with self.assertRaises(ValueError):w.save_scholar(dict(name='Invalid lab',labIds=['missing']))
   with self.assertRaises(ValueError):w.save_scholar(dict(name='Unsafe URL',source='javascript:alert(1)'))
   edited=w.save_scholar(dict(person,institution='Updated University',labIds=[]))
   self.assertEqual(edited['revision'],2);self.assertEqual(edited['labIds'],[])
   self.assertEqual(next(p for p in w.scholar_directory()['people'] if p['id']==person['id'])['research'],'Research notes')
 def test_chinese_only_scholar_and_remote_avatar(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   person=w.save_scholar(dict(name='仅中文 QA',photoUrl='https://official.example/photo.jpg',source='https://official.example/profile'))
   self.assertEqual(person['en'],'')
   self.assertEqual(w.scholar_photo(person['id'])['image'],'https://official.example/photo.jpg')
 def test_method_articles_and_bookmarks_roundtrip(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   article=w.save('method-post',dict(title='Writing advice',category='writing',content='# My notes',noteDate='2026-10-23'))
   self.assertEqual(w.listing('method-post')['items'][0]['content'],'# My notes')
   with self.assertRaises(ValueError):w.save('method-post',dict(article,category='unknown'))
   with self.assertRaises(ValueError):w.save('method-post',dict(article,noteDate='2026-02-30'))
   resource=w.save('method-resource',dict(title='Guide',category='writing',url='https://official.example/guide',resourceType='article',favorite=True,seedId='resource-test'))
   self.assertTrue(resource['favorite']);self.assertEqual(resource['seedId'],'resource-test')
   with self.assertRaises(ValueError):w.save('method-resource',dict(resource,url='javascript:alert(1)'))
   archived=w.save('method-resource',dict(resource,archived=True));self.assertFalse(w.listing('method-resource')['items'])
   restored=w.save('method-resource',dict(archived,archived=False));self.assertEqual(restored['url'],resource['url'])
 def test_method_workflow_steps_and_legacy_preservation(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'):
   legacy=w.save('method-post',dict(title='Legacy',category='writing',content='Preserve text'))
   article=w.save('method-post',dict(title='Introduction notes',category='writing',stepId='introduction',content='My evidence',noteDate='2026-10-23'))
   self.assertEqual(article['stepId'],'introduction')
   with self.assertRaises(ValueError):w.save('method-post',dict(article,category='experiments'))
   edited=w.save('method-post',dict(article,category='experiments',stepId='analysis'))
   restored=w.save('method-post',dict(w.save('method-post',dict(edited,archived=True)),archived=False))
   self.assertEqual(restored['content'],'My evidence');self.assertEqual(restored['stepId'],'analysis')
   saved=next(p for p in w.listing('method-post')['items'] if p['id']==legacy['id'])
   self.assertEqual(saved['content'],'Preserve text');self.assertNotIn('stepId',saved)
 def test_only_web_portraits_are_exposed(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'ROOT',pathlib.Path(folder)):
   root=pathlib.Path(folder);(root/'web').mkdir();(root/'local-data/scholar-photos').mkdir(parents=True)
   (root/'web/scholar-profiles.json').write_text(json.dumps([dict(id='person',name='Name',en='Name')]),encoding='utf-8')
   file=root/'local-data/scholar-photos/person.json'
   file.write_text(json.dumps(dict(image='image',report=True,source='https://official.example')),encoding='utf-8')
   self.assertFalse(w.scholar_photo('person')['image'])
   file.write_text(json.dumps(dict(image='image',report=False,source='https://official.example')),encoding='utf-8')
   self.assertEqual(w.scholar_photo('person')['image'],'image')
   with self.assertRaises(ValueError):w.scholar_photo('../secret')
 def test_blog_lab_revision_archive_and_images(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(s,'DB',pathlib.Path(folder)/'study.sqlite'),patch.object(w,'ROOT',pathlib.Path(folder)/'images'):
   p=w.save('blog-post',{'title':'Draft','content':'Local note'})
   self.assertEqual(w.listing('blog-post')['items'][0]['content'],'Local note')
   with self.assertRaises(ValueError):w.save('blog-post',dict(p,revision=0))
   p=w.save('blog-post',dict(p,archived=True));self.assertFalse(w.listing('blog-post')['items'])
   lab=w.save('research-lab',dict(name='User defined lab',institution='Institution',scholars='Researcher',paperIds=['paper-a']))
   self.assertEqual(lab['paperIds'],['paper-a'])
   stream=io.BytesIO();Image.new('RGB',(4,4)).save(stream,'PNG')
   result=w.paste_image({'image':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()})
   content,kind=w.image_file(result['id']);self.assertEqual(kind,'image/png');self.assertEqual(content,stream.getvalue())
   with self.assertRaises(ValueError):w.paste_image({'image':'data:image/svg+xml;base64,AAAA'})
   with self.assertRaises(ValueError):w.image_file('../secret')
if __name__=='__main__':unittest.main()
