"""Read-only hierarchical browsing of the existing local conference catalog."""
import collections
import contextlib
import json
import pathlib
import re
import sqlite3
import threading
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
VENUES = sorted(["AAAI", "NeurIPS", "ICML", "ICLR", "CVPR", "ICCV", "ACL", "ICSE", "FSE", "ASE", "ISSTA"], key=str.casefold)
from research_taxonomy import RULES
COMPILED = [(cid, label, [(sid, slabel, re.compile(pattern, re.I)) for sid,slabel,pattern in subs]) for cid,label,subs in RULES]
LOCK = threading.Lock()
CACHE = None
CACHED_SIGNATURE = None

def signature():
    paths=[ROOT/"local-data/library.sqlite", ROOT/"local-data/library.sqlite-wal", ROOT/"local-data/conferences.json", ROOT/"local-data/paper-scope-trash.json"]
    return tuple((p.stat().st_size,p.stat().st_mtime_ns) if p.exists() else None for p in paths)

def classify_paper(p):
    text = p.get("title", "") + " " + p.get("summary", "")
    labels = [(cid,sid) for cid,_,subs in COMPILED for sid,_,pattern in subs if pattern.search(text)]
    if p.get("venue") in ("ICSE","FSE","ASE","ISSTA") and not any(c=="software" for c,s in labels):labels.append(("software","general"))
    return labels or [("other", "unclassified")]

def title_key(title):
    return re.sub(r"\W+", "", unicodedata.normalize("NFKC", title).casefold())

def arxiv_link(p):
    for key in ("arxiv", "arxivUrl", "source", "pdf"):
        url = p.get(key, "")
        if isinstance(url,str) and re.match(r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/",url):
            return url.replace("http:","https:",1)
    return ""

def catalog(force=False):
    global CACHE, CACHED_SIGNATURE
    with LOCK:
        if CACHE is not None and not force and signature()==CACHED_SIGNATURE:
            return CACHE
        with contextlib.closing(sqlite3.connect(ROOT/"local-data/library.sqlite")) as c:
            rows = c.execute("SELECT body FROM papers WHERE venue IN ("+",".join("?" for _ in VENUES)+") OR venue='arXiv'", VENUES).fetchall()
        import paper_scope
        raw = paper_scope.filter_papers([json.loads(row[0]) for row in rows])
        arxiv = {title_key(p["title"]):arxiv_link(p) for p in raw if p.get("venue")=="arXiv" and arxiv_link(p)}
        groups = collections.defaultdict(list)
        for p in raw:
            if p.get("venue") not in VENUES: continue
            p = dict(p)
            p["categories"] = classify_paper(p)
            p["arxivUrl"] = arxiv_link(p) or arxiv.get(title_key(p["title"]), "")
            groups[(int(p["year"]),p["venue"])].append(p)
        for papers in groups.values(): papers.sort(key=lambda p:p["title"].casefold())
        try: sources = json.loads((ROOT/"local-data/conferences.json").read_text(encoding="utf-8"))["sources"]
        except (OSError,KeyError,ValueError): sources=[]
        CACHE = {"groups":dict(groups), "sources":{(int(s["year"]),s["venue"]):s for s in sources}}
        CACHED_SIGNATURE = signature()
        return CACHE

def navigation(force=False):
    data = catalog(force)
    years = sorted({2027,2026,2025}|{y for y,_ in data["groups"]},reverse=True)
    return {"years":[{"year":year,"conferences":[{"venue":v,"count":len(data["groups"].get((year,v),[]))} for v in VENUES]} for year in years],
            "classification":"基于本地标题和可用摘要的关键词多分类，非会议官方分类，待人工复核。"}

def browse(year, venue, category="", subcategory="", query="", page=0):
    if venue not in VENUES or year not in (2025,2026,2027): raise ValueError("请选择有效的年份与会议")
    data = catalog()
    papers = data["groups"].get((year,venue),[])
    counts = collections.Counter(pair for p in papers for pair in p["categories"])
    taxonomy=[]
    for cid,label,subs in RULES+[("other","待分类 / Other",[("unclassified","待细分","")])]:
        children=[{"id":sid,"label":slabel,"count":counts[(cid,sid)]} for sid,slabel,_ in subs]
        count=sum(1 for p in papers if any(c==cid for c,_ in p["categories"]))
        taxonomy.append({"id":cid,"label":label,"count":count,"children":children})
    filtered=[p for p in papers if (not category or any(c==category and (not subcategory or s==subcategory) for c,s in p["categories"])) and (not query or query.casefold() in (p["title"]+" "+str(p.get("authors",""))).casefold())]
    count=len(filtered)
    page=max(0,min(page,max(0,(count-1)//30)))
    return {"year":year,"venue":venue,"total":len(papers),"count":count,"page":page,"pageSize":30,"taxonomy":taxonomy,"papers":filtered[page*30:(page+1)*30],"source":data["sources"].get((year,venue))}
