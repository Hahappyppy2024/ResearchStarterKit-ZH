import contextlib,io,json,pathlib,tempfile,unittest
from unittest.mock import patch
import local_app,paper_uploads,paper_pdf
from pypdf import PdfWriter
class UploadTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='upload-test-',dir=pathlib.Path.cwd());self.root=pathlib.Path(self.temp.name);self.patchers=[patch.object(local_app,'DATA',self.root),patch.object(paper_uploads,'ROOT',self.root/'uploads'),patch('study_service.resolve',return_value={'id':'paper-a','title':'Fixture'})]
  for p in self.patchers:p.start()
  with contextlib.closing(local_app.db()) as c,c:
   for ident in ('paper-a','paper-b'):c.execute('INSERT INTO papers(id,title,body) VALUES(?,?,?)',(ident,'Fixture',json.dumps({'id':ident,'title':'Fixture','notes':'preserve'})))
  writer=PdfWriter();writer.add_blank_page(width=300,height=400);stream=io.BytesIO();writer.write(stream);self.data=stream.getvalue()
 def tearDown(self):
  for p in reversed(self.patchers):p.stop()
  self.temp.cleanup()
 def test_uploaded_pdf_is_per_paper_and_reader_never_fetches_remote(self):
  paper_uploads.upload('paper-a','../../fixture.pdf',self.data)
  with patch('subprocess.run',side_effect=AssertionError('Network download must not run')):
   result=paper_pdf.prepare('paper-a');self.assertIn('paper-a',result['url']);self.assertEqual(paper_pdf.cached_file('paper-a').read_bytes(),self.data)
  self.assertIsNone(paper_uploads.local_file('paper-b'))
  with contextlib.closing(local_app.db()) as c:record=json.loads(c.execute('SELECT body FROM papers WHERE id=?',('paper-a',)).fetchone()[0])
  self.assertTrue(record['uploadedPdf']);self.assertEqual(record['notes'],'preserve')
  meta=json.loads((paper_uploads.folder('paper-a')/'current.json').read_text(encoding='utf-8'));self.assertEqual(meta['name'],'fixture.pdf')
 def test_rejects_wrong_extension_invalid_pdf_and_empty_file(self):
  for name,data in [('x.ppt',self.data),('x.pdf',b'not pdf'),('x.pdf',b'')]:
   with self.assertRaises(ValueError):paper_uploads.upload('paper-a',name,data)
  self.assertIsNone(paper_uploads.local_file('paper-a'))
 def test_http_upload_and_pdf_reader_endpoints(self):
  import http.server,threading,urllib.request,urllib.error
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),local_app.Handler)
  with patch.object(local_app,'PORT',server.server_port):
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    base='http://127.0.0.1:'+str(server.server_port)
    request=urllib.request.Request(base+'/api/study/paper-pdf-upload?paperId=paper-a&name=fixture.pdf',data=self.data,headers={'Content-Type':'application/octet-stream'},method='POST')
    with urllib.request.urlopen(request) as response:self.assertTrue(json.load(response)['saved'])
    with urllib.request.urlopen(base+'/api/study/paper-original?paperId=paper-a') as response:result=json.load(response)
    with urllib.request.urlopen(base+result['url']) as response:self.assertEqual(response.read(),self.data);self.assertIn('application/pdf',response.headers['Content-Type'])
    bad=urllib.request.Request(base+'/api/study/paper-pdf-upload?paperId=paper-a&name=fixture.pdf',data=self.data,headers={'Content-Type':'application/octet-stream','Origin':'https://untrusted.example'},method='POST')
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(bad)
    self.assertEqual(error.exception.code,403)
   finally:server.shutdown();server.server_close();thread.join()
 def test_replacement_keeps_same_reading_identity(self):
  paper_uploads.upload('paper-a','first.pdf',self.data);first=paper_uploads.local_file('paper-a');paper_uploads.upload('paper-a','second.pdf',self.data);self.assertNotEqual(first,paper_uploads.local_file('paper-a'));self.assertIn('paper-a',paper_pdf.prepare('paper-a')['url'])
if __name__=='__main__':unittest.main()
