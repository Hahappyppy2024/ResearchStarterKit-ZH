"""Persist user research directions next to the local library."""
import json,pathlib,sqlite3,uuid,contextlib
from video_topics import RULES as VIDEO_RULES
DB=pathlib.Path(__file__).resolve().parent/"local-data"/"library.sqlite"
BUILTINS=[
 ("区块链",'all:blockchain OR all:"distributed ledger" OR all:"smart contract" OR all:"decentralized finance"'),
 ("Agent",'all:agent OR all:agentic'),
 ("Object Detection",'all:"object detection"'),
 ("Agent OS",'all:"agent operating system" OR all:AgentOS OR all:AIOS'),
 ("Agent Security",'all:"prompt injection" OR all:"agent security" OR all:"agent safety" OR all:"memory poisoning" OR all:"tool poisoning" OR all:"MCP security" OR all:"multi-agent security"'),
 ("AI Safety",'all:"AI safety" OR all:"LLM safety" OR all:"safety alignment" OR all:"jailbreak" OR all:"red teaming" OR all:"deceptive alignment"'),
 ("Agent Harness",'all:"agent harness" OR all:"agent runtime"'),
 *[(name,query) for name,label,pattern,query in VIDEO_RULES],
 ("丁霄汉 · 剪枝",'au:"Xiaohan Ding" AND (all:pruning OR all:sparsity)'),
 ("世界模型",'all:"world model" OR all:"world models" OR all:"latent dynamics" OR all:"model-based reinforcement learning"'),
 ("模型可解释性",'all:interpretability OR all:explainability OR all:"mechanistic interpretability" OR all:"feature attribution" OR all:"sparse autoencoder"')]

LABELS={
 "区块链":("区块链","Blockchain"),
 "世界模型":("世界模型","World Models"),
 "模型可解释性":("模型可解释性","Model Interpretability"),
 "Agent":("智能体","Agent"),
 "Object Detection":("目标检测","Object Detection"),
 "Agent OS":("智能体操作系统","Agent OS"),
 "Agent Security":("智能体安全","Agent Security"),
 "AI Safety":("AI 安全","AI Safety"),
 "Agent Harness":("智能体运行框架","Agent Harness"),
 "Video Understanding":("视频理解","Video Understanding"),
 "Video Generation":("视频生成","Video Generation"),
 "Video Editing":("视频编辑","Video Editing"),
 "Video Retrieval":("视频查找","Video Retrieval"),
 "丁霄汉 · 剪枝":("丁霄汉 · 剪枝","Xiaohan Ding · Pruning"),
 "农业遥感检测":("农业遥感检测","Agricultural Remote Sensing Detection"),
 "强化学习":("强化学习","Reinforcement Learning")}

def bilingual(name,zh=None,en=None):
 fallback=LABELS.get(name,(name,name if name.isascii() else "英文名称待填写"))
 return {"nameZh":zh or fallback[0],"nameEn":en or fallback[1]}

@contextlib.contextmanager
def connection():
 c=sqlite3.connect(DB,timeout=30)
 c.execute("CREATE TABLE IF NOT EXISTS research_topics(id TEXT PRIMARY KEY,name TEXT UNIQUE COLLATE NOCASE,query TEXT,name_zh TEXT,name_en TEXT)")
 columns={row[1] for row in c.execute("PRAGMA table_info(research_topics)")}
 for column in ("name_zh","name_en"):
  if column not in columns:
   try:c.execute("ALTER TABLE research_topics ADD COLUMN "+column+" TEXT")
   except sqlite3.OperationalError as e:
    if "duplicate column name" not in str(e).lower():c.close();raise
 try:
  with c:yield c
 finally:c.close()

def list_topics():
 rows=[{"id":"builtin-"+str(i),"name":name,"query":query,"builtin":True,**bilingual(name)} for i,(name,query) in enumerate(BUILTINS)]
 with connection() as c:rows += [{"id":pid,"name":name,"query":q,"builtin":False,**bilingual(name,zh,en)} for pid,name,q,zh,en in c.execute("SELECT id,name,query,name_zh,name_en FROM research_topics ORDER BY rowid")]
 return rows

def make_query(groups):
 # Each line is an AND group; comma-separated alternatives within it use OR.
 lines=[x.strip() for x in groups.splitlines() if x.strip()]
 if not lines or len(lines)>8:raise ValueError("请填写 1–8 行英文检索词。")
 built=[]
 for line in lines:
  terms=[x.strip() for x in line.replace("，",",").split(",") if x.strip()]
  if not terms or len(terms)>12:raise ValueError("每行请填写 1–12 个关键词或短语。")
  if any(len(x)>100 or any(ch in x for ch in '\"\\\x00') for x in terms):raise ValueError("关键词过长或含不支持的字符。")
  built.append("("+" OR ".join('all:"'+x+'"' for x in terms)+")")
 return " AND ".join(built)

def add_topic(name,keywords,name_en=None):
 if not isinstance(name,str) or not 1<=len(name.strip())<=60:raise ValueError("方向名称需为 1–60 个字。")
 name=name.strip()
 if any(x["name"].casefold()==name.casefold() for x in list_topics()):raise ValueError("这个方向已经存在。")
 if not isinstance(keywords,str) or len(keywords)>3000:raise ValueError("请填写英文检索词。")
 if name_en is not None and (not isinstance(name_en,str) or len(name_en.strip())>120):raise ValueError("英文名称不能超过 120 个字符。")
 names=bilingual(name,en=name_en.strip() if name_en else None)
 query=make_query(keywords)
 with connection() as c:c.execute("INSERT INTO research_topics(id,name,query,name_zh,name_en) VALUES(?,?,?,?,?)",("custom-"+uuid.uuid4().hex,name,query,names["nameZh"],names["nameEn"]))
 return {"name":name,"query":query,**names}
