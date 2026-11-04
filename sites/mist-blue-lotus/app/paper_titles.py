"""Bilingual paper titles only; never translates notes or abstracts."""
import contextlib,hashlib,json,re,sqlite3,threading
import study_service as study
import topic_library as library
LOCK=threading.Lock()

@contextlib.contextmanager
def translation_guard():
 # A separate database avoids holding the study/reader databases during network IO.
 # SQLite releases this lock on process exit, including an interrupted translation.
 with LOCK,contextlib.closing(sqlite3.connect(study.DB.with_name('paper-title-lock.sqlite'),timeout=120)) as c:
  c.execute('CREATE TABLE IF NOT EXISTS title_lock(id INTEGER PRIMARY KEY)');c.commit()
  c.execute('BEGIN IMMEDIATE')
  try:yield
  finally:c.rollback()

def remember_title(result):
 if result.get('error') or not result.get('titleZh'):return
 import local_app,json
 with contextlib.closing(local_app.db()) as c,c:
  row=c.execute('SELECT body FROM papers WHERE id=?',(result['paperId'],)).fetchone()
  if row:
   p=json.loads(row[0])
   if p.get('title','').strip()==result['title']:
    for key in ('titleZh','titleEn'):
     if result.get(key) and not p.get(key):p[key]=result[key]
    c.execute('UPDATE papers SET body=? WHERE id=?',(json.dumps(p,ensure_ascii=False),result['paperId']))

def hydrate_titles(papers):
 import json
 with study.connection() as c:
  saved={r[0]:json.loads(r[1]) for r in c.execute("SELECT id,body FROM records WHERE kind='paper-title'")}
 with contextlib.closing(library.reader_service.connection()) as c:
  translations={r[0]:r[1] for r in c.execute('SELECT hash,zh FROM translations')}
 updates={}
 for p in papers:
  title=p.get('title','').strip();key=hashlib.sha256(title.encode()).hexdigest();cached=saved.get(key,{})
  if cached.get('title')!=title:cached={}
  if re.search(r'[\u4e00-\u9fff]',title) and not p.get('titleZh'):p['titleZh']=title
  if not p.get('titleZh'):p['titleZh']=cached.get('titleZh') or translations.get(key,'')
  if not p.get('titleEn'):p['titleEn']=cached.get('titleEn') or (title if not re.search(r'[\u4e00-\u9fff]',title) else '')
  if title and p.get('titleZh') and p.get('titleEn'):
   value=dict(title=title,titleZh=p['titleZh'],titleEn=p['titleEn'],provider=cached.get('provider','已保存译名'))
   if any(cached.get(k)!=value[k] for k in ('title','titleZh','titleEn')):updates[key]=value
 if updates:
  with study.connection() as c:
   c.executemany("INSERT INTO records VALUES('paper-title',?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",[(key,json.dumps(value,ensure_ascii=False)) for key,value in updates.items()])
 return papers

def bilingual_title(data):
 pid=study.text(data.get('paperId',''),200)
 p=study.resolve('paper',pid)
 title=p.get('title','').strip()
 if not title:raise ValueError('论文标题为空')
 zh=p.get('titleZh','').strip();en=p.get('titleEn','').strip()
 chinese=bool(re.search(r'[\u4e00-\u9fff]',title))
 if chinese:zh=zh or title
 else:en=en or title
 result=dict(paperId=pid,title=title,titleZh=zh,titleEn=en,provider='原始题录')
 with translation_guard():
  cache_id=hashlib.sha256(title.encode()).hexdigest()
  with study.connection() as c:
   stored=c.execute("SELECT body FROM records WHERE kind='paper-title' AND id=?",(cache_id,)).fetchone()
  if stored:
   cached=json.loads(stored[0])
   if cached.get('title')==title and cached.get('titleZh') and cached.get('titleEn'):
    result={**cached,'paperId':pid,'titleZh':zh or cached['titleZh'],'titleEn':en or cached['titleEn']}
    remember_title(result)
    return result
  # Reuse titles already saved on another record, even before it was opened here.
  if not zh or not en:
   import local_app
   with contextlib.closing(local_app.db()) as c:
    rows=c.execute("SELECT body FROM papers WHERE title=? AND json_extract(body,'$.titleZh') IS NOT NULL",(title,)).fetchall()
   for row in rows:
    known=json.loads(row[0]);zh=zh or known.get('titleZh','');en=en or known.get('titleEn','')
   known=hydrate_titles([dict(p,titleZh=zh,titleEn=en)])[0]
   zh=known.get('titleZh','');en=known.get('titleEn','');result.update(titleZh=zh,titleEn=en)
  try:
   if not zh:result['titleZh']=library.translate_text(en)
   if not en:result['titleEn']=translate_english(zh)
   if not zh or not en:result['provider']='机器翻译，请对照原文核对'
  except Exception as e:
   limited=getattr(getattr(e,'response',None),'status_code',None)==429
   result['error']='在线翻译限流或额度已用完，原始标题已保留' if limited else '标题翻译暂不可用，原始标题已保留'
  if not result.get('error') and result.get('titleZh') and result.get('titleEn'):
   with study.connection() as c:
    c.execute("INSERT INTO records VALUES('paper-title',?,?,0) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",(cache_id,json.dumps(result,ensure_ascii=False)))
 remember_title(result)
 return result

def translate_english(text):
 import requests
 key=hashlib.sha256(('zh-en:'+text).encode()).hexdigest()
 with contextlib.closing(library.reader_service.connection()) as c:
  row=c.execute('SELECT zh FROM translations WHERE hash=?',(key,)).fetchone()
 if row:return row[0]
 r=requests.get('https://translate.googleapis.com/translate_a/single',params={'client':'gtx','sl':'zh-CN','tl':'en','dt':'t','q':text},timeout=12)
 r.raise_for_status();value=''.join(x[0] for x in r.json()[0] if x and x[0])
 if not value.strip():raise ValueError('没有英文译名')
 with contextlib.closing(library.reader_service.connection()) as c:
  c.execute('INSERT OR REPLACE INTO translations VALUES(?,?,?,?)',(key,text,value,'Google zh-en'));c.commit()
 return value
