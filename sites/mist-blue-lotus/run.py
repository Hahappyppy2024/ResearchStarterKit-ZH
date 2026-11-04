"""Start the same full local website with clean, isolated runtime data."""
import argparse,os,pathlib,runpy,sys,webbrowser,threading,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent/'app'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--no-browser',action='store_true');p.add_argument('--preview',action='store_true',help='Skip automatic arXiv fetches during verification');a=p.parse_args()
 if a.preview:os.environ['RESEARCH_PUBLIC_PREVIEW']='1'
 (ROOT/'local-data').mkdir(exist_ok=True)
 os.chdir(ROOT);sys.path.insert(0,str(ROOT))
 print('Full research desktop: http://127.0.0.1:8869/#daily',flush=True)
 if not a.no_browser:
  def open_when_ready():
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   for _ in range(100):
    try:
     with opener.open('http://127.0.0.1:8869/',timeout=1) as response:
      if response.status==200:
       webbrowser.open('http://127.0.0.1:8869/#daily');return
    except OSError:pass
    time.sleep(.3)
  threading.Thread(target=open_when_ready,daemon=True).start()
 runpy.run_path(str(ROOT/'hub_server.py'),run_name='__main__')
