"""Loopback-only notebook service. No PDF, model or log files are copied."""
import http.server,json,mimetypes,pathlib,urllib.parse
import projects_service as service
import learning_service as learning
import interview_practice as interviews
import learning_workflow as workflow
ROOT=pathlib.Path(__file__).resolve().parent;WEB=ROOT/'web-projects';PORT=8870
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def trusted(self,task=False):
  host=self.headers.get('Host','');origin=self.headers.get('Origin',f'http://{host}')
  return host in (f'127.0.0.1:{PORT}',f'localhost:{PORT}') and (origin==f'http://{host}' or task and origin=='http://127.0.0.1:8866')
 def reply(self,data,kind='application/json',code=200):
  body=json.dumps(data,ensure_ascii=False).encode() if kind=='application/json' else data if isinstance(data,bytes) else data.encode('utf-8')
  import theme_assets
  body=theme_assets.inject(body,kind)
  self.send_response(code);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  if urllib.parse.urlsplit(self.path).path=='/api/project-task' and self.headers.get('Origin')=='http://127.0.0.1:8866':self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8866');self.send_header('Vary','Origin')
  self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(path.query)
  if not self.trusted(path.path=='/api/project-task'):return self.reply({'error':'仅允许本机同源访问'},code=403)
  import theme_assets
  shared=theme_assets.asset(path.path)
  if shared:return self.reply(shared[0],shared[1])
  try:
   if path.path=='/api/projects':return self.reply({'projects':service.list_projects(q.get('archived',['0'])[0]=='1')})
   if path.path=='/api/project-notes':
    import project_notes
    return self.reply(project_notes.listing(q.get('projectId',[''])[0]))
   if path.path=='/api/project':return self.reply(service.project_detail(q.get('id',[''])[0]))
   if path.path=='/api/project-papers':
    import project_papers
    return self.reply(project_papers.listing(q.get('projectId',[''])[0]))
   if path.path=='/api/project-paper-resources':
    import study_service
    return self.reply(study_service.catalog(q.get('q',[''])[0],'paper',q.get('page',['0'])[0]))
   if path.path=='/api/project-task':
    ident=q.get('id',[''])[0]
    return self.reply(learning.task_detail(ident) if ident.startswith('learning-') else service.task_detail(ident))
   if path.path=='/api/learning/study-session':return self.reply(workflow.session(q.get('date',[None])[0],q.get('mode',['flash'])[0]))
   if path.path=='/api/learning/completed-weekly-quiz':return self.reply(workflow.weekly(q.get('date',[None])[0]))
   if path.path=='/api/learning/modules':return self.reply({'modules':learning.list_modules()})
   if path.path=='/api/learning/notebook':
    import module_notebook
    return self.reply(module_notebook.get(q.get('id',[''])[0]))
   if path.path.startswith('/module-assets/'):
    import module_notebook
    file=module_notebook.file(path.path.rsplit('/',1)[-1])
    # Code is always delivered as plain text, never executed or served as HTML.
    return self.reply(file.read_bytes(),mimetypes.guess_type(file.name)[0] if file.suffix in ('.png','.jpg','.jpeg','.webp') else 'text/plain')
   if path.path=='/api/learning/evening-quiz':return self.reply(interviews.get_evening(q.get('date',[None])[0]))
   if path.path=='/api/learning/weekly-quiz':return self.reply(interviews.get_week(q.get('date',[None])[0]))
   if path.path=='/api/learning/interviews':return self.reply(interviews.get_day(q.get('date',[None])[0]))
   if path.path=='/api/learning/module':return self.reply(learning.detail(q.get('id',[''])[0]))
   if path.path=='/api/learning/slide':return self.reply(learning.editable_slide(q.get('id',[''])[0],q.get('index',['0'])[0]))
   if path.path.startswith('/learning-files/'):
    parts=path.path.split('/',3)
    file=learning.file_path(parts[2],parts[3]);return self.reply(file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
   if path.path=='/api/export':return self.reply(service.export_project(q.get('id',[''])[0],q.get('format',['md'])[0]),'text/csv' if q.get('format',['md'])[0]=='csv' else 'text/markdown')
   if path.path in ('/learning','/learning/'):return self.reply((ROOT/'web-learning'/'index.html').read_bytes(),'text/html')
   if path.path.startswith('/learning-static/'):
    file=(ROOT/'web-learning'/path.path.removeprefix('/learning-static/')).resolve()
    if not file.is_relative_to((ROOT/'web-learning').resolve()) or not file.is_file():return self.reply({'error':'不存在'},code=404)
    return self.reply(file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
   file=(WEB/('index.html' if path.path=='/' else path.path.lstrip('/'))).resolve()
   if not file.is_relative_to(WEB.resolve()) or not file.is_file():return self.reply({'error':'不存在'},code=404)
   return self.reply(file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
  except ValueError as e:return self.reply({'error':str(e)},code=400)
 def do_POST(self):
  if self.path=='/api/learning/module-asset':
   if not self.trusted() or self.headers.get('Content-Type')!='application/octet-stream':return self.reply({'error':'请求无效'},code=403)
   try:
    import module_notebook
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=8*1024*1024:raise ValueError('附件需在 8 MB 以内')
    return self.reply(module_notebook.upload(self.headers.get('X-Module-Id',''),self.headers.get('X-Item-Id',''),urllib.parse.unquote(self.headers.get('X-File-Name','')),self.rfile.read(length)))
   except (ValueError,TypeError) as e:return self.reply({'error':str(e)},code=400)
  if self.path=='/api/learning/upload':
   if not self.trusted() or self.headers.get('Content-Type')!='application/octet-stream':return self.reply({'error':'请求无效'},code=403)
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=50*1024*1024:raise ValueError('文件需在 50 MB 以内')
    return self.reply(learning.import_deck(self.headers.get('X-Module-Id',''),urllib.parse.unquote(self.headers.get('X-File-Name','')),self.rfile.read(length)))
   except (ValueError,TypeError) as e:return self.reply({'error':str(e)},code=400)
  if not self.trusted() or self.headers.get('Content-Type')!='application/json':return self.reply({'error':'仅允许本机 JSON 请求'},code=403)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>(8000000 if self.path=='/api/project-note' else 500000):raise ValueError('记录过大')
   data=json.loads(self.rfile.read(length))
   if self.path=='/api/project-note':
    import project_notes
    return self.reply(project_notes.save(data))
   if self.path=='/api/project-paper':
    import project_papers
    return self.reply(project_papers.save(data))
   if self.path in ('/api/learning/notebook','/api/learning/module-quiz'):
    import module_notebook
    return self.reply(module_notebook.save(data) if self.path.endswith('/notebook') else module_notebook.select(data))
   if self.path=='/api/learning/retry':
    return self.reply(learning.refresh_deck(data))
   action={'/api/project':service.save_project,'/api/task':service.save_task,'/api/log':service.save_log,'/api/archive':service.archive,'/api/learning/module':learning.save_module,'/api/learning/deck':learning.save_deck,'/api/learning/archive':learning.archive_deck,'/api/learning/open':learning.open_deck,'/api/learning/slide':learning.save_slide,'/api/learning/card':learning.save_flashcard,'/api/learning/card/archive':learning.archive_flashcard,'/api/learning/interview-attempt':workflow.submit,'/api/learning/interview':interviews.save_card,'/api/learning/interview-bank':interviews.add_bank}.get(self.path)
   if not action:raise ValueError('接口不存在')
   return self.reply(action(data))
  except (ValueError,TypeError,KeyError) as e:return self.reply({'error':str(e)},code=400)
if __name__=='__main__':
 import threading
 def daily_interview_worker():
  previous=None
  while True:
   try:
    current=interviews.today()
    if current!=previous:interviews.get_day(current);previous=current
   except Exception as e:print('Daily interview preparation failed:',str(e),flush=True)
   threading.Event().wait(60)
 threading.Thread(target=daily_interview_worker,daemon=True).start()
 print(f'http://127.0.0.1:{PORT}',flush=True)
 http.server.ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
