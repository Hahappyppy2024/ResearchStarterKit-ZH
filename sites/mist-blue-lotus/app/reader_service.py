"""Paper notes and sentence-aligned translation cache, stored only on this PC."""
import datetime,hashlib,json,pathlib,re,sqlite3
ROOT=pathlib.Path(__file__).resolve().parent

def connection():
 c=sqlite3.connect(ROOT/"local-data"/"reader.sqlite",timeout=30)
 c.execute("CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,content TEXT,updated TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS translations(hash TEXT PRIMARY KEY,en TEXT,zh TEXT,provider TEXT)")
 return c

def sentences(text):
 return [x.strip() for x in re.split(r'(?<=[.!?。！？])\s+(?=[A-Z“"(\u4e00-\u9fff])',re.sub(r"\s+"," ",text or "")) if x.strip()]

def paper(pid):
 with sqlite3.connect(ROOT/"local-data"/"library.sqlite") as c:
  row=c.execute("SELECT body FROM papers WHERE id=?",(pid,)).fetchone()
 if not row:raise ValueError("论文不存在")
 return json.loads(row[0])

def reader(pid):
 p=paper(pid);pairs=[]
 with connection() as c:
  for en in sentences(p.get("summary","")):
   row=c.execute("SELECT zh,provider FROM translations WHERE hash=?",(hashlib.sha256(en.encode()).hexdigest(),)).fetchone()
   pairs.append({"en":en,"zh":row[0] if row else None,"provider":row[1] if row else None})
  note=c.execute("SELECT content,updated FROM notes WHERE id=?",(pid,)).fetchone()
 return {"id":pid,"title":p["title"],"authors":p.get("authors",""),"pdf":p.get("pdf") or p.get("source"),"pairs":pairs,"note":note[0] if note else "","noteUpdated":note[1] if note else None}

def save_note(pid,content):
 paper(pid)
 if not isinstance(content,str) or len(content)>100000:raise ValueError("笔记过长")
 updated=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with connection() as c:c.execute("INSERT INTO notes VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET content=excluded.content,updated=excluded.updated",(pid,content,updated))
 return {"saved":True,"updated":updated}

def translate(pid):
 import requests
 data=reader(pid)
 for pair in data["pairs"]:
  if pair["zh"]:continue
  try:
   r=requests.get("https://translate.googleapis.com/translate_a/single",params={"client":"gtx","sl":"en","tl":"zh-CN","dt":"t","q":pair["en"]},timeout=15)
   if r.status_code==429:return {"reader":reader(pid),"error":"在线翻译服务当前限流（429），请稍后重试；英文摘要和笔记仍可使用。"}
   r.raise_for_status();value=r.json();zh="".join(x[0] for x in value[0] if x and x[0])
   if not zh.strip():raise ValueError("empty translation")
   with connection() as c:c.execute("INSERT OR REPLACE INTO translations VALUES(?,?,?,?)",(hashlib.sha256(pair["en"].encode()).hexdigest(),pair["en"],zh,"Google 在线机器翻译"))
  except Exception:return {"reader":reader(pid),"error":"暂时无法连接在线翻译服务；英文摘要和笔记仍可使用，可稍后重试。"}
 return {"reader":reader(pid)}
