"""Durable weekly snapshots. Metadata only; never downloads PDFs or writes Zotero."""
import contextlib,datetime as dt,hashlib,json,pathlib,re,sqlite3,threading,time,urllib.parse
import xml.etree.ElementTree as ET
from agent_topics import agent_feed_paper
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'local-data';DB=DATA/'weekly-arxiv.sqlite';LOCK=threading.RLock()
FETCH_LOCK=threading.Lock()
DATE_NOTE='按 arXiv API published（第一版提交处理日期）归档，不等同于公开公告日；后续版本另列为更新。历史合集仅覆盖已采集或已检索的方向。'

def date_value(value):
 try:return dt.date.fromisoformat(value[:10])
 except (ValueError,TypeError):raise ValueError('日期格式无效')

def monday(value):
 d=date_value(value);return (d-dt.timedelta(days=d.weekday())).isoformat()

def today():return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
def timestamp():return dt.datetime.now(dt.timezone.utc).isoformat()

@contextlib.contextmanager
def connection():
 DB.parent.mkdir(exist_ok=True,parents=True)
 with LOCK,contextlib.closing(sqlite3.connect(DB,timeout=60)) as c,c:
  c.execute('CREATE TABLE IF NOT EXISTS snapshots(week TEXT,id TEXT,kind TEXT,body TEXT,PRIMARY KEY(week,id,kind))')
  c.execute('CREATE TABLE IF NOT EXISTS weeks(week TEXT PRIMARY KEY,body TEXT)')
  c.execute('CREATE TABLE IF NOT EXISTS sources(path TEXT PRIMARY KEY,stamp TEXT)')
  c.execute('CREATE TABLE IF NOT EXISTS curation(week TEXT PRIMARY KEY,body TEXT)')
  c.execute('CREATE TABLE IF NOT EXISTS morning_runs(date TEXT PRIMARY KEY,body TEXT)')
  yield c

def store(c,p,observed,min_week=None):
 import paper_scope
 if paper_scope.reason(p):paper_scope.archive([p]);return
 if p.get('venue')!='arXiv' or not re.fullmatch(r'arxiv-\d{4}\.\d{4,5}',p.get('id','')):return
 try:published=date_value(p.get('published',''));updated=date_value(p.get('updated') or p['published'])
 except ValueError:return
 first=monday(published.isoformat());changed=monday(updated.isoformat())
 candidates=[]
 if not min_week or first>=min_week:candidates.append((first,'new'))
 if updated>published and (not min_week or changed>=min_week):candidates.append((changed,'update'))
 for week,kind in candidates:
  if week>monday(today()):continue
  body={**p,'archiveKind':kind,'originalWeek':first,'archivedAt':observed}
  old=c.execute('SELECT body FROM snapshots WHERE week=? AND id=? AND kind=?',(week,p['id'],kind)).fetchone()
  if old:
   previous=json.loads(old[0]);body=previous
   # Preserve the first captured content while allowing additional topic membership.
   body['topics']=list(dict.fromkeys(previous.get('topics',[])+p.get('topics',[])))
   if kind=='update' and p.get('updated','')>previous.get('updated',''):body={**p,'archiveKind':kind,'originalWeek':first,'archivedAt':observed}
   c.execute('UPDATE snapshots SET body=? WHERE week=? AND id=? AND kind=?',(json.dumps(body,ensure_ascii=False),week,p['id'],kind))
  else:c.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(week,p['id'],kind,json.dumps(body,ensure_ascii=False)))

def archive_local():
 files=sorted(DATA.glob('????-??-??.json'))
 # Import what the local digests actually cover; do not fabricate earlier complete weeks.
 earliest=monday(files[0].stem) if files else monday(today())
 earliest=(date_value(earliest)-dt.timedelta(days=7)).isoformat()
 with connection() as c:
  for file in files:
   stamp=str(file.stat().st_mtime_ns)+':'+str(file.stat().st_size)
   if c.execute('SELECT stamp FROM sources WHERE path=?',(file.name,)).fetchone()==(stamp,):continue
   try:digest=json.loads(file.read_text(encoding='utf-8-sig'))
   except (ValueError,OSError):continue
   for p in digest.get('papers',[]):store(c,p,digest.get('checkedAt',timestamp()),earliest)
   c.execute('INSERT OR REPLACE INTO sources VALUES(?,?)',(file.name,stamp))
  # Even an empty completed week remains selectable and can be fetched later.
  for week in (monday(today()),(date_value(monday(today()))-dt.timedelta(days=7)).isoformat()):
   c.execute('INSERT OR IGNORE INTO weeks VALUES(?,?)',(week,json.dumps({'status':'local','note':'由本机已有清单归档；尚未完成该周独立检索。'},ensure_ascii=False)))

def list_days():
 archive_local()
 grouped={}
 with connection() as c:
  for (body,) in c.execute("SELECT body FROM snapshots WHERE kind='new'"):
   p=agent_feed_paper(json.loads(body))
   if p is None:continue
   try:date=date_value(p.get('published') or p.get('publishedAt','')).isoformat()
   except (ValueError,TypeError):continue
   if date<=today():grouped.setdefault(date,set()).add(p['id'])
 for offset in range(7):grouped.setdefault((date_value(today())-dt.timedelta(days=offset)).isoformat(),set())
 return dict(days=[dict(date=d,count=len(grouped[d])) for d in sorted(grouped,reverse=True)],dateNote=DATE_NOTE)

def get_day(date):
 date=date_value(date).isoformat()
 if date>today():raise ValueError('不能查看未来日期的论文流')
 week=get_week(date)
 papers=[p for p in week['papers'] if (p.get('published') or p.get('publishedAt',''))[:10]==date]
 check=daily_check(today())
 return dict(date=date,papers=papers,meta=week['meta'],dailyCheck={k:v for k,v in check.items() if k not in ('papers','count')},dateNote=DATE_NOTE,archiveSource='本机持久化首版快照',count=len(papers))

def list_weeks():
 archive_local()
 with connection() as c:
  keys={r[0] for r in c.execute('SELECT DISTINCT week FROM snapshots')}|{r[0] for r in c.execute('SELECT week FROM weeks')}
  result=[]
  for week in sorted(keys,reverse=True):
   iso=date_value(week).isocalendar();end=(date_value(week)+dt.timedelta(days=6)).isoformat()
   counts={}
   for kind,body in c.execute('SELECT kind,body FROM snapshots WHERE week=?',(week,)):
    if agent_feed_paper(json.loads(body)) is not None:counts[kind]=counts.get(kind,0)+1
   row=c.execute('SELECT body FROM weeks WHERE week=?',(week,)).fetchone();meta=json.loads(row[0]) if row else {'status':'local','note':'由本机已有清单归档，覆盖范围有限。'}
   result.append(dict(start=week,end=end,label=f'{iso.year} 年第 {iso.week:02} 周 · {week[5:]}—{end[5:]}',draft=week==monday(today()),newCount=counts.get('new',0),updateCount=counts.get('update',0),**meta))
 return {'weeks':result,'defaultWeek':(date_value(monday(today()))-dt.timedelta(days=7)).isoformat(),'dateNote':DATE_NOTE}

def get_week(value=None,kind='new'):
 archive_local();week=monday(value or (date_value(monday(today()))-dt.timedelta(days=7)).isoformat())
 if kind not in ('new','update'):raise ValueError('合集类型无效')
 with connection() as c:
  papers=[json.loads(r[0]) for r in c.execute('SELECT body FROM snapshots WHERE week=? AND kind=? ORDER BY id DESC',(week,kind))]
  row=c.execute('SELECT body FROM curation WHERE week=?',(week,)).fetchone();curation=json.loads(row[0]) if row else {'notes':'','picks':None}
 meta=next((w for w in list_weeks()['weeks'] if w['start']==week),None)
 import paper_classification
 papers=paper_classification.decorate([visible for p in papers if (visible:=agent_feed_paper(p)) is not None])
 return {'week':week,'kind':kind,'papers':papers,'meta':meta,'dateNote':DATE_NOTE,'curation':curation}

def save_curation(data):
 week=monday(data.get('week',''));notes=data.get('notes');picks=data.get('picks')
 if not isinstance(notes,str) or len(notes)>50000:raise ValueError('周总结需在 50000 字符以内')
 if not isinstance(picks,list) or len(picks)>10000 or any(not isinstance(p,str) or not re.fullmatch(r'arxiv-\d{4}\.\d{4,5}',p) for p in picks):raise ValueError('精选论文格式无效')
 with connection() as c:
  valid={r[0] for r in c.execute('SELECT id FROM snapshots WHERE week=?',(week,))}
  if not set(picks)<=valid:raise ValueError('精选中包含不属于该周的论文')
  body=dict(notes=notes,picks=list(dict.fromkeys(picks)),updatedAt=timestamp())
  c.execute('INSERT OR REPLACE INTO curation VALUES(?,?)',(week,json.dumps(body,ensure_ascii=False)))
 return body

def fetch_week(value=None,force=False,fetcher=None,pause=time.sleep):
 with FETCH_LOCK:return _fetch_week(value,force,fetcher,pause)

def _fetch_week(value=None,force=False,fetcher=None,pause=time.sleep):
 """Fetch submittedDate range with pagination; publish coverage only after all topics succeed."""
 from topics_service import list_topics
 import local_app as app
 week=monday(value or (date_value(monday(today()))-dt.timedelta(days=7)).isoformat());end=date_value(week)+dt.timedelta(days=6)
 configured=list_topics();signature=hashlib.sha256(json.dumps([(t['name'],t['query']) for t in configured]).encode()).hexdigest()
 with connection() as c:
  row=c.execute('SELECT body FROM weeks WHERE week=?',(week,)).fetchone();meta=json.loads(row[0]) if row else {}
  if not force and not meta.get('error') and meta.get('signature')==signature and meta.get('lastAttemptDate')==today():return {'week':week,'cached':True}
 fetcher=fetcher or app.fetch;papers={};sources=[];ns={'a':'http://www.w3.org/2005/Atom','o':'http://a9.com/-/spec/opensearch/1.1/'}
 try:
  for topic in configured:
   start=0;total=None
   while total is None or start<total:
    query=f'({topic["query"]}) AND submittedDate:[{week.replace("-","")}0000 TO {end.isoformat().replace("-","")}2359]'
    url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode(dict(search_query=query,start=start,max_results=100,sortBy='submittedDate',sortOrder='ascending'))
    for attempt in range(3):
     try:
      payload=fetcher(url);break
     except Exception:
      if attempt==2:raise
      pause(3.2*(attempt+1))
    root=ET.fromstring(payload);entries=root.findall('a:entry',ns)
    raw_total=root.findtext('o:totalResults',None,ns)
    if raw_total is None:raise RuntimeError('arXiv 返回内容缺少总条数，保留已有合集。')
    total=int(raw_total)
    if start<total and not entries:raise RuntimeError('arXiv 分页返回为空，未标记检索完成。')
    for entry in entries:
     source=entry.findtext('a:id','',ns);match=re.search(r'/abs/(\d{4}\.\d{4,5})(?:v\d+)?$',source)
     if not match:raise RuntimeError('arXiv 返回了无法识别的论文条目。')
     aid=match[1];published=entry.findtext('a:published','',ns);updated=entry.findtext('a:updated','',ns)
     if not published or not week<=published[:10]<=end.isoformat():continue
     title=' '.join(entry.findtext('a:title','',ns).split());summary=' '.join(entry.findtext('a:summary','',ns).split())
     authors=[a.findtext('a:name','',ns) for a in entry.findall('a:author',ns)];details=[{'name':a.findtext('a:name','',ns),'affiliations':[x.text.strip() for x in a.findall('{http://arxiv.org/schemas/atom}affiliation') if x.text]} for a in entry.findall('a:author',ns)]
     topics=list(dict.fromkeys((papers.get(aid,{}).get('topics',[]))+[t for t in app.classify(title+' '+summary,', '.join(authors)) if t!='其他']+[topic['name']]))
     papers[aid]=dict(id='arxiv-'+aid,title=title,summary=summary,authors=', '.join(authors),authorDetails=details,source='https://arxiv.org/abs/'+aid,pdf='https://arxiv.org/pdf/'+aid,published=published[:10],updated=updated[:10],publishedAt=published,updatedAt=updated,venue='arXiv',year=int(published[:4]),topics=topics)
    start+=len(entries);pause(3.2)
   sources.append(dict(topic=topic['name'],query=query,total=total))
  at=timestamp()
  with connection() as c:
   for p in papers.values():store(c,p,at,week)
   c.execute('INSERT OR REPLACE INTO weeks VALUES(?,?)',(week,json.dumps(dict(status='fetched',signature=signature,lastAttemptDate=today(),checkedAt=at,sources=sources,note='已分页检索全部已配置方向的 API 可见结果；分类为关键词初筛，可能有漏收或误收。'),ensure_ascii=False)))
  app.absorb(list(papers.values()))
  return {'week':week,'papers':len(papers)}
 except Exception as e:
  with connection() as c:
   meta.update(error=str(e),lastAttemptDate=today())
   c.execute('INSERT OR REPLACE INTO weeks VALUES(?,?)',(week,json.dumps(meta,ensure_ascii=False)))
  raise

def daily_check(date=None):
 date=date_value(date or today()).isoformat()
 if date>today():raise ValueError('不能查看未来采集日期')
 with connection() as c:
  row=c.execute('SELECT body FROM morning_runs WHERE date=?',(date,)).fetchone()
 return json.loads(row[0]) if row else dict(date=date,status='pending',note='尚无当天完成的采集记录，09:00 后本机服务会检查。')

def record_morning(results,errors=None):
 date=today()
 result=dict(date=date,status='partial' if errors else 'complete',checkedAt=timestamp(),errors=errors or [],weeks=results,note='按论文真实首版日期归档；采集日期仅记录检查时间。')
 with connection() as c:c.execute('INSERT OR REPLACE INTO morning_runs VALUES(?,?)',(date,json.dumps(result,ensure_ascii=False)))
 return result

def update_daily_archives(force=False):
 """Refresh the current week daily, and catch delayed indexing in the last full week."""
 current=monday(today());previous=(date_value(current)-dt.timedelta(days=7)).isoformat()
 results=[];errors=[]
 for week in (current,previous):
  try:results.append(fetch_week(week,force=force and week==current))
  except Exception as e:errors.append(str(e));print('Daily arXiv archive:',week,str(e),flush=True)
 record_morning(results,errors)
 return results

def worker():
 """Existing local service owns the job; catches up after PC downtime. No recurring cloud task."""
 while True:
  try:
   now=dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
   if (now.hour,now.minute)>=(9,0) and daily_check().get('status')!='complete':update_daily_archives(force=True)
  except Exception as e:
   print('Weekly arXiv archive:',str(e),flush=True)
  time.sleep(60 if daily_check().get('status') in ('complete','pending') else 1800)
