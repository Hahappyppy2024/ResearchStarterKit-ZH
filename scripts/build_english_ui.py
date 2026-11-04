"""Build a cached English UI dictionary from public-source labels only."""
import concurrent.futures,json,time,urllib.parse,urllib.request,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=ROOT/'sites/mist-blue-lotus/app'
labels=set()
for path in app.rglob('*'):
 if not path.is_file() or path.suffix not in ('.py','.html','.js','.mjs','.json') or any(part in path.parts for part in ('local-data','vendor','__pycache__')) or path.name=='english-ui.json':continue
 try:labels.update(re.findall(r'[\u3400-\u9fff]{2,}',path.read_text(encoding='utf-8-sig')))
 except UnicodeError:continue
source=sorted(labels)
out=ROOT/'sites/mist-blue-lotus/app/web-shared/english-ui.json'
existing=json.loads(out.read_text(encoding='utf-8')) if out.exists() else {}
remaining=[s for s in source if s not in existing];batches=[];batch=[];length=0
for s in remaining:
 if length+len(s)>1400 or len(batch)>=60:batches.append(batch);batch=[];length=0
 batch.append(s);length+=len(s)+1
if batch:batches.append(batch)
def work(batch):
 for attempt in range(3):
  try:
   q='\n'.join(batch);url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'zh-CN','tl':'en','dt':'t','q':q})
   with urllib.request.urlopen(url,timeout=25) as response:data=json.load(response)
   translated=''.join(x[0] for x in data[0] if x and x[0]).strip().split('\n')
   if len(translated)==len(batch):return dict(zip(batch,translated))
   # Preserve alignment rather than assigning a translation to the wrong label.
   result={}
   for row in data[0]:
    if row and len(row)>1 and row[1] and row[1].strip() in batch:result[row[1].strip()]=row[0].strip()
   return result
  except Exception:
   time.sleep(attempt+1)
 return {}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for i,result in enumerate(pool.map(work,batches),1):
  existing.update(result);out.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  if i%10==0:print('batches',i,'/',len(batches),'labels',len(existing),flush=True)
print('Finished labels',len(existing),'untranslated',len(set(source)-existing.keys()),flush=True)
