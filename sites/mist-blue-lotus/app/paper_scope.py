"""User-requested subject exclusions with a recoverable local archive."""
import json,re,threading,datetime
from pathlib import Path
PATH=Path(__file__).resolve().parent/'local-data'/'paper-scope-trash.json'
LOCK=threading.RLock()
PATTERNS=[('地理与地球科学',r'earth embeddings|land surface|\bgeograph(?:y|ic|ical)\b|\bgeospatial\b|\bgeolog(?:y|ical)\b|\bgeoscien|\bsoil\b|\bhydrolog|\boceanograph|\bclimate\b|地理学|地球科学|土壤|陆地表面'),('法学',r'\blegal\b|\blawyers?\b|\bjudicial\b|\bjurisprudence\b|\blitigation\b|\blegislation\b|regulatory obligations|(?<![算方])法学|法律|司法|律师'),('化学',r'\bchemistr(?:y|ies)\b|\bchemical\b|\bmolecular (?:synthesis|reaction|design|optimization)\b|\bcatalys|\belectrochem|计算化学|有机化学|无机化学|物理化学|电化学|化学(?:反应|合成|分子|性质|键|实验|研究|模拟|计算|材料)|分子合成|催化')]
# Preserve the user's established computer-vision applications.
CV=r'object detect|target detect|agricultur|crop|farmland|remote.sensing detect|aerial.{0,20}detect|目标检测|农业|农作物|遥感.{0,12}检测'
def state():
 try:return json.loads(PATH.read_text(encoding='utf-8'))
 except FileNotFoundError:return {'archived':{},'restored':[]}
def raw_reason(p):
 if p.get('id')=='arxiv-2610.32617':return '地理与地球科学'
 titles=[str(p.get(k) or '') for k in ('titleEn','title','titleZh')]
 title=next((t for t in titles if re.search(r'[A-Za-z]{3}',t)),next((t for t in titles if t),''))
 if re.search(CV,title,re.I):return ''
 return next((label for label,pat in PATTERNS if re.search(pat,title,re.I)),'')
_CACHE=(None,set())
def restored_ids():
 global _CACHE
 stamp=PATH.stat().st_mtime_ns if PATH.exists() else 0
 if stamp!=_CACHE[0]:_CACHE=(stamp,set(state().get('restored',[])))
 return _CACHE[1]
def reason(p):return '' if p.get('id') in restored_ids() else raw_reason(p)
def visible_json(body):
 try:return int(not reason(json.loads(body)))
 except (ValueError,TypeError):return 1
def sql_visibility():
 # Snapshot restore exceptions once per connection, not once for every SQL row.
 allowed=set(restored_ids())
 def visible(body):
  try:
   p=json.loads(body);return int(p.get('id') in allowed or not raw_reason(p))
  except (ValueError,TypeError):return 1
 return visible
def filter_papers(papers):return [p for p in papers if not reason(p)]
def archive(papers):
 with LOCK:
  data=state();added=0
  for p in papers:
   why=reason(p)
   if why and p.get('id') and p['id'] not in data['archived']:
    data['archived'][p['id']]={'paper':p,'reason':why,'archivedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()};added+=1
  if added:
   PATH.parent.mkdir(exist_ok=True,parents=True);tmp=PATH.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');tmp.replace(PATH)
 return added
def listing():
 d=state();restored=set(d.get('restored',[]));items=[dict(id=i,title=r['paper']['title'],reason=r['reason']) for i,r in d['archived'].items() if i not in restored]
 return {'items':items,'count':len(items)}
def restore(data):
 ident=data.get('paperId','')
 with LOCK:
  d=state()
  if ident not in d['archived']:raise ValueError('回收记录不存在')
  d['restored']=list(dict.fromkeys(d.get('restored',[])+[ident]));tmp=PATH.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8');tmp.replace(PATH)
 return {'ok':True}
