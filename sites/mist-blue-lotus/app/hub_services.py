"""Launch the full public workspace from this checkout only."""
import concurrent.futures,os,pathlib,subprocess,sys,threading,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
SERVICES=[
 {"id":"daily","name":"每日努力","port":8866,"command":[sys.executable,str(ROOT/'local_app.py'),'serve','--port','8866']},
 {"id":"projects","name":"项目实验本","port":8870,"command":[sys.executable,str(ROOT/'projects_server.py')]},
 {"id":"library","name":"会议文献库","port":8867,"command":[sys.executable,str(ROOT/'local_app.py'),'serve','--port','8867','--literature']},
 {"id":"poetry","name":"毛主席诗词","port":8868,"command":[sys.executable,str(ROOT/'local_app.py'),'serve','--port','8868','--poetry']},
 {"id":"atlas","name":"论文脉络","port":8866,"alias":True}]
LOCK=threading.Lock();ERRORS={}
def check(s):
 url=f"http://127.0.0.1:{s['port']}/"
 try:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=2) as r:ready=r.status==200
 except Exception:ready=False
 return dict(id=s['id'],name=s['name'],url=url,ready=ready,error=ERRORS.get(s['id']))
def status():
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:return list(pool.map(check,SERVICES))
def ensure_services():
 if not LOCK.acquire(blocking=False):return
 try:
  (ROOT/'local-data').mkdir(exist_ok=True)
  for s in SERVICES:
   if s.get('alias') or check(s)['ready']:continue
   try:
    kwargs={'cwd':str(ROOT)}
    if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
    with open(ROOT/'local-data'/('hub-'+s['id']+'.log'),'ab') as log:
     subprocess.Popen(s['command'],stdout=log,stderr=log,**kwargs)
    ERRORS.pop(s['id'],None)
   except Exception as e:ERRORS[s['id']]=str(e)
 finally:LOCK.release()
