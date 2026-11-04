"""Chronological poetry plan and progress from the user's workbook."""
import contextlib,datetime as dt,json,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parent
TZ=dt.timezone(dt.timedelta(hours=8))

def today():return dt.datetime.now(TZ).date()
def catalog():
 path=ROOT/"local-data"/"poetry-catalog.json"
 return json.loads(path.read_text("utf8")) if path.is_file() else {"poems":[],"scope":"尚未导入诗词目录","ordering":"按创作时间"}
@contextlib.contextmanager
def connection():
 c=sqlite3.connect(ROOT/"local-data"/"poetry.sqlite",timeout=30)
 try:
  c.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)")
  c.execute("CREATE TABLE IF NOT EXISTS progress(id TEXT PRIMARY KEY,done INTEGER,memorized_at TEXT,text TEXT DEFAULT '',note TEXT DEFAULT '')")
  c.execute("INSERT OR IGNORE INTO settings VALUES('start_date',?)",(today().isoformat(),))
  for p in catalog()["poems"]:c.execute("INSERT OR IGNORE INTO progress(id,done,memorized_at) VALUES(?,?,?)",(p["id"],int(p["memorized"]),p["memorizedAt"]))
  with c:yield c
 finally:c.close()

def data(date=None):
 day=dt.date.fromisoformat(date) if date else today();source=catalog()
 with connection() as c:
  start=dt.date.fromisoformat(c.execute("SELECT value FROM settings WHERE key='start_date'").fetchone()[0])
  states={pid:{"done":bool(done),"memorizedAt":at,"text":text,"personalNote":note} for pid,done,at,text,note in c.execute("SELECT id,done,memorized_at,text,note FROM progress")}
 poems=[dict(p,**states[p["id"]],plannedDate=(start+dt.timedelta(days=i)).isoformat()) for i,p in enumerate(source["poems"])]
 index=(day-start).days;task=poems[index] if 0<=index<len(poems) else None
 return {"date":day.isoformat(),"today":today().isoformat(),"startDate":start.isoformat(),"reminderTime":"07:45","task":task,"poems":poems,"completed":sum(p["done"] for p in poems),"scope":source["scope"],"ordering":source["ordering"]}

def save(body):
 pid=body.get("id")
 if pid not in {p["id"] for p in catalog()["poems"]}:raise ValueError("诗词不存在")
 with connection() as c:
  if "done" in body:
   if not isinstance(body["done"],bool):raise ValueError("背诵状态无效")
   c.execute("UPDATE progress SET done=?,memorized_at=? WHERE id=?",(int(body["done"]),today().isoformat() if body["done"] else None,pid))
  if "text" in body or "personalNote" in body:
   for key,column in [("text","text"),("personalNote","note")]:
    if key in body:
     value=body[key]
     if not isinstance(value,str) or len(value)>100000:raise ValueError("内容过长")
     c.execute("UPDATE progress SET "+column+"=? WHERE id=?",(value,pid))
 return {"saved":True}
if __name__=="__main__":
 if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf8")
 d=data();print(json.dumps({"date":d["date"],"task":d["task"],"completed":d["completed"],"total":len(d["poems"])},ensure_ascii=False))
