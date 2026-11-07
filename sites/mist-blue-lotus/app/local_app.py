"""Local research library. Standard-library runtime; all writes stay on this PC."""
import argparse, datetime as dt, hashlib, http.server, json, os, pathlib, re
import sqlite3, subprocess, threading, time, urllib.parse, urllib.request, uuid, sys, contextlib
import xml.etree.ElementTree as ET
import paper_scope

ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/"local-data"; DATA.mkdir(exist_ok=True)
PORT=8866
WEB=ROOT/"web"
if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
TOPICS=["Agent","Object Detection","Agent OS","Agent Security","Agent Harness","Video Understanding","丁霄汉 · 剪枝"]
LOCK=threading.Lock()
JOB={"running":False,"message":"尚未运行","lastRun":None}
def now(): return dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
def write_json(path,obj):
    tmp=path.with_suffix(".tmp"); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path)
def read_json(path,default=None):
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:return default
def db():
    c=sqlite3.connect(DATA/"library.sqlite",timeout=60)
    c.execute("PRAGMA journal_mode=WAL")
    c.create_function("paper_visible",1,paper_scope.sql_visibility())
    c.execute("CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY,title TEXT,venue TEXT,year INTEGER,body TEXT,zotero_key TEXT,import_state TEXT DEFAULT 'pending')")
    c.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)")
    return c
def absorb(papers):
    with db() as c:
        for p in papers:
            if paper_scope.reason(p):paper_scope.archive([p]);continue
            if not p.get("id") or not p.get("title"):continue
            old=c.execute('SELECT body FROM papers WHERE id=?',(p['id'],)).fetchone()
            if old:
                saved=json.loads(old[0])
                if saved.get('curatedBibliography') and re.sub(r'\W+','',saved.get('title','').casefold())==re.sub(r'\W+','',p['title'].casefold()):
                    p=dict(p)
                    for key in ('curatedBibliography','title','titleZh','authors','venue','year','publicationType','published','publishedAt','metadataSource','curationNote','source','pdf','arxivUrl','scholarIds'):
                        if key in saved:p[key]=saved[key]
                if saved.get('title')==p['title']:
                    p=dict(p)
                    if saved.get('foundation'):
                        for key in ('foundation','foundationModel','foundationCategories','metadataSource','publicationType','venue','year'):
                            if key in saved:p[key]=saved[key]
                    for key in ('titleZh','titleEn'):
                        if not p.get(key) and saved.get(key):p[key]=saved[key]
            c.execute("INSERT INTO papers(id,title,venue,year,body) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,venue=excluded.venue,year=excluded.year,body=excluded.body",
                (p["id"],p["title"],p.get("venue","arXiv"),int(p.get("year",p.get("published","2026")[:4])),json.dumps(p,ensure_ascii=False)))
def ingest_files():
    for p in DATA.glob("????-??-??.json"):
        absorb(read_json(p,{}).get("papers",[]))
    conf=read_json(DATA/"conferences.json",{})
    absorb(conf.get("papers",[]))
def zrequest(path,body=None):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers={"Zotero-API-Version":"3","Zotero-Allowed-Request":"true","X-Zotero-Connector-API-Version":"3"}
    if body is not None:headers["Content-Type"]="application/json"
    req=urllib.request.Request("http://127.0.0.1:23119"+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with opener.open(req,timeout=120) as r:
        b=r.read();return json.loads(b) if b else {}
def zotero_status():
    try:
        t=zrequest("/connector/getSelectedCollection",{})
        zrequest("/api/users/0/items?limit=1")
        return {"connected":True,"personal":t["libraryID"]==1,"target":t["libraryName"],"message":"Zotero 本机连接正常"}
    except Exception as e:return {"connected":False,"message":"请打开 Zotero，并在设置 → 高级中启用允许本机其他应用通信。","error":str(e)[:180]}
def import_running():
    try:
        with import_lock():return False
    except RuntimeError:return True
def norm(s):return re.sub(r"\W+","",s.casefold())
def existing_zotero():
    index={};start=0
    while True:
        rows=zrequest("/api/users/0/items/top?limit=100&start="+str(start))
        for row in rows:
            d=row.get("data",{});key=row["key"]
            if d.get("title"):index["title:"+norm(d["title"])]=key
            if d.get("url"):index["url:"+d["url"].rstrip("/")]=key
            for tag in d.get("tags",[]):
                if tag["tag"].startswith("research-id:"):index[tag["tag"]]=key
        if len(rows)<100:break
        start+=100
    return index
def creators(authors):
    if isinstance(authors,str):authors=re.split(r",\s*|;\s*",authors)
    out=[]
    for author in authors or []:
        name=author.strip()
        if not name:continue
        parts=name.rsplit(" ",1)
        out.append({"creatorType":"author","firstName":parts[0],"lastName":parts[1]} if len(parts)==2 else {"creatorType":"author","lastName":name,"fieldMode":1})
    return out
def zotero_item(p,batch):
    venue=p.get("venue","arXiv");year=str(p.get("year",p.get("published","2026")[:4]))
    tags=["Research Local",f"会议/{venue}",f"年份/{year}",f"{venue}/{year}","research-id:"+p["id"],"research-batch:"+batch]
    tags += ["主题/"+t for t in p.get("topics",["其他"])]
    if venue!="arXiv":tags.append("主题分类/自动待复核")
    item={"id":p["id"],"itemType":"conferencePaper" if venue!="arXiv" else "journalArticle",
        "title":p["title"],"creators":creators(p.get("authors",[])),"date":p.get("published") or year,
        "url":p.get("source",""),"abstractNote":p.get("summary",""),"tags":[{"tag":t} for t in tags],
        "extra":"Research Local ID: "+p["id"],"attachments":[]}
    if venue!="arXiv":item["conferenceName"]=venue+" "+year;item["proceedingsTitle"]=venue+" "+year
    else:item["publicationTitle"]="arXiv"
    # Zotero 8 Connector accepts linked web resources while ignoring file downloads.
    # This is a URL shortcut, not an imported PDF file.
    if p.get("pdf"):item["attachments"]=[{"title":"官方 PDF（链接，精读时下载）","url":p["pdf"],"mimeType":"text/html","snapshot":False}]
    return item
@contextlib.contextmanager
def import_lock():
    import msvcrt
    with open(DATA/"import.lock","a+b") as f:
        if f.seek(0,2)==0:f.write(b"0");f.flush()
        f.seek(0)
        try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError("另一个导入任务正在运行，请稍后重试。")
        try:yield
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
def sync_zotero(limit=0,only_id=None):
    if read_json(DATA/"import-paused.json",{}).get("paused"):return {"paused":True,"message":"Zotero 导入已暂停，可浏览本地分类。"}
    with import_lock():return _sync_zotero(limit,only_id)
def _sync_zotero(limit=0,only_id=None):
    status=zotero_status()
    if not status.get("connected"):raise RuntimeError(status["message"])
    if not status.get("personal"):raise RuntimeError("请在 Zotero 选择“我的文库”后重试；不会向群组库写入。")
    index=existing_zotero();done=0;skipped=0
    with db() as c:
        query="SELECT id,body FROM papers WHERE import_state!='saved'"
        args=[]
        if only_id:query+=" AND id=?";args.append(only_id)
        query+=" ORDER BY year DESC,id"
        if limit:query+=" LIMIT ?";args.append(limit)
        rows=c.execute(query,args).fetchall()
    for offset in range(0,len(rows),30):
        if read_json(DATA/"import-paused.json",{}).get("paused"):return {"paused":True,"saved":done,"existing":skipped}
        batch=str(uuid.uuid4());pending=[]
        with db() as c:
            for pid,body in rows[offset:offset+30]:
                p=json.loads(body);key=index.get("research-id:"+pid) or index.get("url:"+p.get("source","").rstrip("/")) or index.get("title:"+norm(p["title"]))
                if key:c.execute("UPDATE papers SET zotero_key=?,import_state='saved' WHERE id=?",(key,pid));skipped+=1
                else:pending.append(p)
        if not pending:continue
        # Check target again immediately before each write; never write to a group.
        if zrequest("/connector/getSelectedCollection",{})["libraryID"]!=1:raise RuntimeError("Zotero 已切换到群组库，导入暂停。")
        session="research-"+batch
        zrequest("/connector/saveItems",{"sessionID":session,"uri":"http://127.0.0.1:8866/","items":[zotero_item(p,batch) for p in pending]})
        # Remove transient selected-collection placement; keep personal-library root.
        zrequest("/connector/updateSession",{"sessionID":session,"target":"L1"})
        saved=zrequest("/api/users/0/items?tag="+urllib.parse.quote("research-batch:"+batch))
        found={}
        for row in saved:
            for tag in row.get("data",{}).get("tags",[]):
                if tag["tag"].startswith("research-id:"):found[tag["tag"][12:]]=row["key"]
        with db() as c:
            for p in pending:
                if p["id"] not in found:continue
                key=found[p["id"]];index["research-id:"+p["id"]]=key;index["title:"+norm(p["title"])]=key
                c.execute("UPDATE papers SET zotero_key=?,import_state='saved' WHERE id=?",(key,p["id"]));done+=1
        if len(found)<len(pending):raise RuntimeError("部分条目尚未回读确认；已保留队列，重试前会检查 Zotero 去重。")
        JOB["message"]=f"已导入 {done} 篇，去重 {skipped} 篇"
        write_json(DATA/"sync-status.json",{"at":now().isoformat(),"saved":done,"skipped":skipped,"remaining":len(rows)-offset-len(pending)})
        time.sleep(.2)
    return {"saved":done,"existing":skipped}
def classify(text,authors=""):
    t=text.lower();result=[]
    for topic,pattern in [
        ("Agent",r"\bagents?\b|agentic|multi-agent"),
        ("Object Detection",r"object detection|open.vocabulary detect|detr\b"),
        ("Agent OS",r"agent operating system|agentos|\baios\b|agent kernel"),
        ("Agent Security",r"prompt injection|agent.{0,35}(secur|safety)|tool.{0,20}poison"),
        ("Agent Harness",r"harness|agent.{0,30}(runtime|scaffold|orchestrat)")]:
        if re.search(pattern,t):result.append(topic)
    from video_topics import video_topics
    result.extend(tag['name'] for tag in video_topics({'title':text}))
    if re.search(r"prun(?:e|ed|ing)|spars(?:e|ity)|filter compression",t) and re.search(r"\bxiaohan\s+ding\b|丁霄汉",authors,re.I):result.append("丁霄汉 · 剪枝")
    return result or ["其他"]
def fetch(url):
    # curl uses the user's existing proxy and certificate store; no shell interpolation.
    result=subprocess.run(["curl.exe","--fail","--silent","--show-error","--location","--max-time","90",url],capture_output=True)
    if result.returncode:raise RuntimeError("来源访问失败："+urllib.parse.urlparse(url).hostname)
    return result.stdout
def update_arxiv(only_topic=None):
    from topics_service import list_topics
    configured=list_topics()
    if only_topic:configured=[t for t in configured if t["name"]==only_topic]
    if not configured:raise ValueError("研究方向不存在")
    entries={};sources=[];ns={"a":"http://www.w3.org/2005/Atom"}
    if only_topic:
        previous=read_json(DATA/(now().date().isoformat()+".json"),{})
        entries={p["id"].removeprefix("arxiv-"):p for p in previous.get("papers",[])}
        sources=[x for x in previous.get("sources",[]) if x.get("topic")!=only_topic]
    for direction in configured:
        q=direction["query"]
        url="https://export.arxiv.org/api/query?"+urllib.parse.urlencode({"search_query":q,"start":0,"max_results":100,"sortBy":"lastUpdatedDate","sortOrder":"descending"})
        root=ET.fromstring(fetch(url))
        for e in root.findall("a:entry",ns):
            source=e.findtext("a:id","",ns).replace("http:","https:")
            match=re.search(r"/abs/(\d{4}\.\d{4,5})(?:v\d+)?$",source)
            if not match:continue
            aid=match[1];published=e.findtext("a:published","",ns)[:10];updated=e.findtext("a:updated","",ns)[:10]
            if not updated or (now().date()-dt.date.fromisoformat(updated)).days>7:continue
            title=" ".join(e.findtext("a:title","",ns).split());abstract=" ".join(e.findtext("a:summary","",ns).split())
            topics=classify(title+" "+abstract, ", ".join(x.findtext("a:name","",ns) for x in e.findall("a:author",ns)))
            if direction["name"] not in topics:topics.append(direction["name"])
            topics=[t for t in topics if t!="其他"]
            if aid in entries:topics=list(dict.fromkeys(entries[aid].get("topics",[])+topics))
            author_details=[{"name":x.findtext("a:name","",ns),"affiliations":[a.text.strip() for a in x.findall("{http://arxiv.org/schemas/atom}affiliation") if a.text and a.text.strip()]} for x in e.findall("a:author",ns)]
            entries[aid]={"authorDetails":author_details,"id":"arxiv-"+aid,"title":title,"authors":", ".join(x.findtext("a:name","",ns) for x in e.findall("a:author",ns)),"source":"https://arxiv.org/abs/"+aid,"pdf":"https://arxiv.org/pdf/"+aid,"published":published,"updated":updated,"venue":"arXiv","year":int(published[:4]),"summary":abstract,"topics":topics,"section":"recent","authorTier":3,"priority":"P2","rankReason":"自动抓取的相关新论文；作者影响力尚待人工核实。","influenceEvidence":"待核实，未依据姓名猜测影响力。","evidenceSources":[]}
        sources.append({"topic":direction["name"],"query":q,"url":url,"checkedAt":now().isoformat()});time.sleep(3.2)
    paper_scope.archive(list(entries.values()))
    papers=sorted(paper_scope.filter_papers(list(entries.values())),key=lambda p:p["updated"],reverse=True)
    digest={"date":now().date().isoformat(),"checkedAt":now().isoformat(),"note":"arXiv 自动更新：检索最近更新的前 100 条/查询，保留近 7 天；主题为关键词初筛，作者影响力待核实。原文摘要未自动改写。","coverage":{t:f"本次匹配 {sum(t in p['topics'] for p in papers)} 篇；关键词分类待复核。" for t in [x["name"] for x in list_topics()]},"papers":papers,"sources":sources}
    # No partial success date if any source failed; preserve existing digest on failure.
    write_json(DATA/(digest["date"]+".json"),digest);absorb(papers)
    from weekly_arxiv import archive_local
    archive_local()
    return {"arxiv":len(papers)}
def run_job(kind,only_id=None,only_topic=None):
    if not LOCK.acquire(blocking=False):return False
    JOB.update(running=True,message="正在执行："+kind)
    def work():
        try:
            ingest_files()
            result=update_arxiv(only_topic) if kind=="arxiv" else {}
            if kind=="weekly":
                from weekly_arxiv import fetch_week
                result=fetch_week(only_id,force=True)
            if kind=="morning":
                import weekly_arxiv
                weekly_arxiv.update_daily_archives(force=True)
                result=weekly_arxiv.daily_check()
            if kind in ("arxiv","sync"):result.update(sync_zotero(only_id=only_id))
            JOB.update(message=json.dumps(result,ensure_ascii=False),lastRun=now().isoformat())
        except Exception as e:JOB.update(message=str(e),lastRun=now().isoformat())
        finally:JOB["running"]=False;write_json(DATA/"last-job.json",JOB);LOCK.release()
    threading.Thread(target=work,daemon=True).start();return True
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,data,status=200,kind="application/json"):
        body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode() if kind=="application/json" else data
        import theme_assets
        body=theme_assets.inject(body,kind)
        self.send_response(status);self.send_header("Content-Type",kind+"; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.study_cors();self.end_headers();self.wfile.write(body)
    def study_cors(self):
        origin=self.headers.get("Origin","")
        if self.path.startswith("/api/study/") and origin in ("http://127.0.0.1:8866","http://127.0.0.1:8867","http://127.0.0.1:8870","http://127.0.0.1:8873","http://127.0.0.1:8891","http://127.0.0.1:8869"):
            self.send_header("Access-Control-Allow-Origin",origin);self.send_header("Vary","Origin")
            self.send_header("Access-Control-Allow-Headers","Content-Type");self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
    def do_OPTIONS(self):
        if not self.path.startswith("/api/study/") or not self.trusted():return self.reply({"error":"禁止跨站请求"},403)
        return self.reply({"ok":True})
    def trusted(self):
        host=self.headers.get("Host","")
        return host in (f"127.0.0.1:{PORT}",f"localhost:{PORT}") and (self.headers.get("Origin",f"http://{host}")==f"http://{host}" or (self.path.startswith("/api/study/") and self.headers.get("Origin") in ("http://127.0.0.1:8866","http://127.0.0.1:8867","http://127.0.0.1:8870","http://127.0.0.1:8873","http://127.0.0.1:8891","http://127.0.0.1:8869")))
    def do_GET(self):
        if not self.trusted():return self.reply({"error":"仅允许本机同源请求"},403)
        path=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(path.query)
        if path.path in ('/api/study/course-attachments','/api/study/course-attachment-file'):
            try:
                import course_attachments as attachments
                course=q.get('courseId',[''])[0];unit=q.get('unit',[''])[0]
                if path.path.endswith('-file'):
                    data,kind=attachments.read(course,unit,q.get('id',[''])[0]);return self.reply(data,kind=kind)
                return self.reply(attachments.listing(course,unit))
            except (ValueError,KeyError,OSError) as e:return self.reply({'error':str(e)},400)
        import theme_assets
        shared=theme_assets.asset(path.path)
        if shared:return self.reply(shared[0],kind=shared[1])
        if path.path=='/api/study/memos':
            import memo_service
            return self.reply(memo_service.listing())
        if path.path.startswith("/api/study/"):
            try:
                import study_service as study
                value=lambda key,default="":q.get(key,[default])[0]
                if path.path=='/api/study/daily-paper-statistics':
                    import daily_paper_statistics
                    return self.reply(daily_paper_statistics.snapshot(value('date')))
                if path.path=='/api/study/paper-original':
                    import paper_pdf
                    return self.reply(paper_pdf.prepare(value('paperId')))
                if path.path=='/api/study/paper-pdf':
                    import paper_pdf
                    return self.reply(paper_pdf.cached_file(value('paperId')).read_bytes(),kind='application/pdf')
                if path.path=='/api/study/course-materials':return self.reply(study.course_materials(value('id')))
                if path.path=='/api/study/course-poster':return self.reply(study.course_poster(value('id'),value('source')),kind='image/jpeg')
                import knowledge_service as knowledge
                if path.path=='/api/study/scholar-papers':
                    import scholar_papers
                    return self.reply(scholar_papers.listing(value('scholarId'),value('labId')))
                if path.path=='/api/study/paper-affiliations':
                    import paper_affiliations
                    return self.reply(paper_affiliations.listing(value('paperId')))
                if path.path=='/api/study/scholar-photo':
                    import workspace_content
                    return self.reply(workspace_content.scholar_photo(value('id')))
                if path.path=='/api/study/scholar-directory':
                    import workspace_content
                    return self.reply(workspace_content.scholar_directory())
                if path.path=='/api/study/paper-scope-trash':return self.reply(paper_scope.listing())
                if path.path=='/api/study/topic-library':
                    import topic_library
                    return self.reply(topic_library.browse(value('topic'),value('source','conference'),value('venue'),value('year'),value('q'),value('page',0),value('state','all')))
                if path.path in ('/api/study/method-posts','/api/study/method-resources'):
                    import workspace_content
                    return self.reply(workspace_content.listing('method-post' if path.path.endswith('method-posts') else 'method-resource'))
                if path.path=='/api/study/research-ideas':
                    return self.reply({'error':'该私有模块不在公开版本中'},404)
                if path.path=='/api/study/news-posts':
                    return self.reply({'error':'该私有模块不在公开版本中'},404)
                if path.path in ('/api/study/blog-posts','/api/study/blog-folders','/api/study/research-labs'):
                    import workspace_content
                    return self.reply(workspace_content.listing('blog-post' if path.path.endswith('blog-posts') else 'blog-folder' if path.path.endswith('blog-folders') else 'research-lab'))
                if path.path=='/api/study/paste-image':
                    import workspace_content
                    content,kind=workspace_content.image_file(value('id'));return self.reply(content,kind=kind)
                if path.path=='/api/study/paper-library-statistics':
                    import reading_journal
                    return self.reply(reading_journal.statistics(include_items=True))
                if path.path=='/api/study/paper-progress':
                    import paper_progress
                    return self.reply(paper_progress.listing(value('ids').split(',') if value('ids') else []))
                if path.path=='/api/study/paper-featured':
                    import paper_progress
                    return self.reply(paper_progress.featured())
                if path.path=='/api/study/reading-queue-status':
                    date=study.valid_date(value('date',study.today()))
                    with study.connection() as c:ids=[p['paperId'] for p in study.reading_queue(c,date)]
                    return self.reply(dict(date=date,ids=ids))
                if path.path=='/api/study/task-cat':
                    face=value('face')
                    if face not in ('smile','cry'):raise ValueError('小猫状态无效')
                    return self.reply((ROOT/'web'/'assets'/('task-cat-'+face+'.png')).read_bytes(),kind='image/png')
                if path.path=='/api/study/paper-questions':
                    import paper_questions
                    return self.reply(paper_questions.listing(value('date',None),value('paperId'),value('mode','all')))
                if path.path=='/api/study/flash-statistics':
                    import flash_review
                    return self.reply(flash_review.statistics())
                if path.path in ('/api/study/daily-quiz','/api/study/paper-quiz-selection'):
                    import daily_quiz
                    return self.reply(daily_quiz.plan(value('date',None)) if path.path.endswith('/daily-quiz') else daily_quiz.selection(value('paperId')))
                if path.path=="/api/study/read-papers":
                    import reading_journal
                    return self.reply(reading_journal.library())
                if path.path=="/api/study/reading-review":
                    import reading_journal
                    return self.reply(reading_journal.review(value("kind","day"),value("date",study.today())))
                if path.path=="/api/study/datasets":
                    import research_assets
                    return self.reply(research_assets.datasets())
                if path.path=="/api/study/methodology-image":
                    import research_assets
                    file,mime=research_assets.figure_file(value("id"))
                    return self.reply(file.read_bytes(),kind=mime)
                if path.path in ("/api/study/taxonomy-status","/api/study/taxonomy-trash"):
                    import taxonomy_lifecycle
                    return self.reply(taxonomy_lifecycle.status(value("id")) if path.path.endswith("status") else taxonomy_lifecycle.archived())
                if path.path=="/api/study/taxonomy":return self.reply(knowledge.taxonomy())
                if path.path=="/api/study/paper-knowledge":return self.reply(knowledge.get_paper(value("id")))
                if path.path=="/api/study/paper-week":return self.reply(knowledge.paper_week(value("date",None)))
                if path.path=="/api/study/edges":return self.reply(dict(edges=knowledge.edges([value("id")] if value("id") else [])))
                if path.path=="/api/study/problem-comparison":
                    import problem_comparison
                    return self.reply(problem_comparison.snapshot(value("mapId","read-library")))
                if path.path=="/api/study/lineages":
                    import lineage_service
                    return self.reply(lineage_service.detail(value("id")) if value("id") else lineage_service.all_maps())
                if path.path=="/api/study/state":return self.reply(study.state(value("date",None)))
                if path.path=="/api/study/course-bibliography":return self.reply(study.course_bibliography(value("id")))
                if path.path=="/api/study/resources":return self.reply(study.catalog(value("q"),value("kind"),value("page",0),value('venue')))
                if path.path=="/api/study/resource":return self.reply(study.resolve(value("kind"),value("id")))
                if path.path=="/api/study/task":return self.reply(study.task_detail(value("paperId"),value("taskId")))
                return self.reply({"error":"不存在"},404)
            except (ValueError,KeyError,TypeError) as e:return self.reply({"error":str(e)},400)
        if path.path=="/api/conferences":
            from conference_catalog import navigation
            return self.reply(navigation(q.get("refresh",[""])[0]=="1"))
        if path.path=="/api/conference-library":
            try:
                from conference_catalog import browse
                return self.reply(browse(int(q.get("year",["2026"])[0]),q.get("venue",["CVPR"])[0],q.get("category",[""])[0],q.get("subcategory",[""])[0],q.get("q",[""])[0],int(q.get("page",["0"])[0])))
            except ValueError as e:return self.reply({"error":str(e)},400)
        if path.path=="/api/poetry":
            try:
                from poetry_service import data
                return self.reply(data(q.get("date",[None])[0]))
            except ValueError:return self.reply({"error":"日期格式无效"},400)
        if path.path=="/api/research-practice":
            try:
                from research_practice import get_day
                return self.reply(get_day(q.get("date",[None])[0]))
            except ValueError as e:return self.reply({"error":str(e)},400)
        if path.path=="/api/research-pond":
            import research_pond
            return self.reply(research_pond.state())
        if path.path=="/api/research-pet":
            import research_pet
            return self.reply(research_pet.state())
        if path.path=="/api/arxiv/safety-starters":
            import paper_classification
            data=read_json(DATA/'security-starters.json',{'papers':[]})
            data['papers']=paper_classification.decorate(data.get('papers',[]))
            return self.reply(data)
        if path.path=="/api/arxiv/days":
            import weekly_arxiv
            return self.reply(weekly_arxiv.list_days())
        if path.path=="/api/arxiv/day":
            try:
                import weekly_arxiv
                return self.reply(weekly_arxiv.get_day(q.get('date',[weekly_arxiv.today()])[0]))
            except (ValueError,TypeError) as e:return self.reply({'error':str(e)},400)
        if path.path=="/api/arxiv/weeks":
            from weekly_arxiv import list_weeks
            return self.reply(list_weeks())
        if path.path=="/api/arxiv/week":
            try:
                from weekly_arxiv import get_week
                return self.reply(get_week(q.get("week",[None])[0],q.get("kind",["new"])[0]))
            except ValueError as e:return self.reply({"error":str(e)},400)
        if path.path=="/api/topics":
            from topics_service import list_topics
            return self.reply({"topics":list_topics(),"job":JOB})
        if path.path=="/api/reader":
            try:
                from reader_service import reader
                return self.reply(reader(q.get("id",[""])[0]))
            except ValueError as e:return self.reply({"error":str(e)},404)
        if path.path=="/api/papers":
            date=q.get("date",[""])[0];files=sorted(DATA.glob("????-??-??.json"))
            p=DATA/(date+".json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}",date) else DATA/"missing"
            exact=p.exists()
            if not exact:p=files[-1] if files else p
            digest=read_json(p)
            if digest:digest={**digest,'papers':paper_scope.filter_papers(digest.get('papers',[]))}
            return self.reply({'digest':digest,'exact':exact})
        if path.path=="/api/status":
            with db() as c:
                total=c.execute("SELECT count(*) FROM papers WHERE paper_visible(body)=1").fetchone()[0]
                saved=c.execute("SELECT count(*) FROM papers WHERE import_state='saved' AND paper_visible(body)=1").fetchone()[0]
                groups=[{"venue":v,"year":y,"count":n} for v,y,n in c.execute("SELECT venue,year,count(*) FROM papers WHERE paper_visible(body)=1 GROUP BY venue,year")]
            current=dict(JOB if JOB["lastRun"] or JOB["running"] else read_json(DATA/"last-job.json",JOB))
            paused=read_json(DATA/"import-paused.json",{}).get("paused",False)
            if paused:current.update(running=False,message="Zotero 导入已暂停；当前仅浏览本地论文分类。")
            elif import_running():current.update(running=True,message=f"正在批量导入 Zotero，已保存/已有 {saved} 篇；可关闭网页，后台继续。")
            return self.reply({"zotero":zotero_status(),"total":total,"saved":saved,"pending":total-saved,"importPaused":paused,"groups":groups,"job":current,"sources":read_json(DATA/"conferences.json",{}).get("sources",[])})
        if path.path=="/api/library":
            where=['paper_visible(body)=1'];args=[]
            for key in ("venue","year"):
                if q.get(key,[""])[0]:where.append(key+"=?");args.append(q[key][0])
            if q.get("q",[""])[0]:where.append("title LIKE ?");args.append("%"+q["q"][0]+"%")
            if q.get("topic",[""])[0]:
                where.append("EXISTS (SELECT 1 FROM json_each(papers.body,'$.topics') WHERE value=?)")
                args.append(q["topic"][0])
            clause=" WHERE "+" AND ".join(where) if where else ""
            try:page=max(0,int(q.get("page",["0"])[0]))
            except ValueError:page=0
            with db() as c:
                count=c.execute("SELECT count(*) FROM papers"+clause,args).fetchone()[0]
                rows=c.execute("SELECT body,zotero_key FROM papers"+clause+" ORDER BY year DESC,title LIMIT 30 OFFSET ?",args+[page*30]).fetchall()
            return self.reply({"count":count,"page":page,"papers":[dict(json.loads(b),zoteroKey=k) for b,k in rows]})
        static={" /":"","/": "index.html"}
        name="index.html" if path.path=="/" else path.path.lstrip("/")
        asset_root=ROOT/"web" if WEB.name=="web-literature" and name in ("timeline-nesting.mjs","paper-catalog-actions.js","catalog-actions.mjs","todos.mjs","required-reading-updates.js","paper-title.js","paper-title-model.mjs","paper-labs.js","paper-reader.js","paper-knowledge.js","related-papers.js","dataset-ui.js","paper-assets.js","paper-research.js","paper-quiz-ui.js","auto-card-merge.mjs","paper-questions-ui.js","paper-reader.css","paper-tasks.mjs","course-picker.js","paper-task-definitions.json","paper-relations.mjs","reading-history.mjs","schedule.mjs") else WEB
        p=(asset_root/name).resolve()
        if not p.is_relative_to(asset_root.resolve()) or not p.is_file():return self.reply({"error":"不存在"},404)
        import mimetypes
        return self.reply(p.read_bytes(),kind=mimetypes.guess_type(p.name)[0] or "application/octet-stream")
    def do_POST(self):
        upload_path=urllib.parse.urlsplit(self.path)
        if upload_path.path=="/api/study/paper-pdf-upload":
            if not self.trusted():return self.reply({'error':'Local uploads only'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=50*1024*1024:return self.reply({'error':'PDF size limit: 50 MB'},413)
                import paper_uploads
                q=urllib.parse.parse_qs(upload_path.query)
                return self.reply(paper_uploads.upload(q.get('paperId',[''])[0],q.get('name',[''])[0],self.rfile.read(length)))
            except (ValueError,KeyError,OSError) as e:return self.reply({'error':str(e)},400)
        if upload_path.path=="/api/study/course-attachment-upload":
            if not self.trusted():return self.reply({'error':'只允许本机上传'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=50*1024*1024:return self.reply({'error':'单个文件最大 50 MB'},413)
                import course_attachments as attachments
                q=urllib.parse.parse_qs(upload_path.query)
                return self.reply(attachments.upload(q.get('courseId',[''])[0],q.get('unit',[''])[0],q.get('name',[''])[0],self.rfile.read(length)))
            except (ValueError,KeyError,OSError) as e:return self.reply({'error':str(e)},400)
        upload_path=urllib.parse.urlsplit(self.path)
        if upload_path.path=="/api/study/methodology-upload":
            if not self.trusted():return self.reply({"error":"只允许本机上传"},403)
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 0<length<=8*1024*1024:return self.reply({"error":"图片最大 8 MB"},413)
                import research_assets
                query=urllib.parse.parse_qs(upload_path.query)
                return self.reply(research_assets.upload_figure(query.get("paperId",[""])[0],self.rfile.read(length)))
            except (ValueError,KeyError,TypeError) as e:return self.reply({"error":str(e)},400)
        if not self.trusted() or self.headers.get("Content-Type")!="application/json":return self.reply({"error":"只允许本机 JSON 请求"},403)
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length>12000000:return self.reply({"error":"请求过大"},413)
            body=json.loads(self.rfile.read(length))
            if self.path=="/api/research-pond":
                import research_pond
                return self.reply(research_pond.release(body))
            if self.path=="/api/research-pet":
                import research_pet
                return self.reply(research_pet.act(body))
            if self.path.startswith("/api/study/"):
                import study_service as study
                action=self.path.rsplit("/",1)[-1]
                if action=='paper-scope-restore':return self.reply(paper_scope.restore(body))
                if action=='memo':
                    import memo_service
                    return self.reply(memo_service.save(body))
                if action=='course-category':return self.reply(study.save_course_category(body))
                if action=='paper-affiliations':
                    import paper_affiliations
                    return self.reply(paper_affiliations.save(body))
                if action=='paper-title':
                    import paper_titles
                    return self.reply(paper_titles.bilingual_title(body))
                if action=='library-translate':
                    import topic_library
                    return self.reply(topic_library.translate(body))
                if action=='scholar':
                    import workspace_content
                    return self.reply(workspace_content.save_scholar(body))
                if action=='research-idea':
                    return self.reply({'error':'该私有模块不在公开版本中'},404)
                if action=='news-post':
                    return self.reply({'error':'该私有模块不在公开版本中'},404)
                if action in ('blog-post','blog-folder','research-lab','method-post','method-resource','paste-image'):
                    import workspace_content
                    return self.reply(workspace_content.paste_image(body) if action=='paste-image' else workspace_content.save(action,body))
                if action=='paper-read-status':
                    import paper_progress
                    result=paper_progress.save(body)
                    if result['read']:
                        try:
                            import research_pet
                            research_pet.state()
                        except Exception as e:print('Research cat reward sync:',str(e),flush=True)
                    return self.reply(result)
                if action=='paper-featured':
                    import paper_progress
                    return self.reply(paper_progress.save_featured(body))
                if action=='reading-library-select':return self.reply(study.select_reading_paper(body))
                if action=='paper-library-archive':
                    import reading_journal
                    return self.reply(reading_journal.archive_personal(body))
                if action=='paper-question':
                    import paper_questions
                    return self.reply(paper_questions.save(body))
                if action in ('paper-quiz-selection','daily-quiz-answer'):
                    import daily_quiz
                    return self.reply(daily_quiz.select(body) if action=='paper-quiz-selection' else daily_quiz.answer(body))
                if action=="reading-review":
                    import reading_journal
                    return self.reply(reading_journal.save_review(body))
                if action=="taxonomy-archive":
                    import taxonomy_lifecycle
                    return self.reply(taxonomy_lifecycle.archive(body))
                if action in ("problem-comparison-confirm","problem-comparison-synthesis"):
                    import problem_comparison
                    return self.reply(problem_comparison.confirm(body) if action.endswith("confirm") else problem_comparison.save_synthesis(body))
                import knowledge_service as knowledge
                import research_assets
                knowledge_actions={"dataset":research_assets.save_dataset,"dataset-topics":research_assets.assign_dataset_topics,"taxonomy":knowledge.save_node,"paper-knowledge":knowledge.save_paper,"paper-quiz-answer":knowledge.paper_attempt}
                if action in knowledge_actions:
                    result=knowledge_actions[action](body)
                    if action=='paper-knowledge' and result.get('completed'):
                        try:
                            import research_pet
                            research_pet.state()
                        except Exception as e:print('Research cat reward sync:',str(e),flush=True)
                    return self.reply(result)
                if action=="read-library":
                    import lineage_service
                    return self.reply(lineage_service.read_library(body))
                if action in ("lineage","lineage-archive"):
                    import lineage_service
                    return self.reply(lineage_service.save(body) if action=="lineage" else lineage_service.archive(body))
                if action in ("course","problem","comparison"):return self.reply(study.save_record(action,body))
                actions={"paper":study.save_paper,"link":study.add_link,"queue":study.add_queue,"queue-remove":study.remove_queue,"archive":study.archive}
                if action not in actions:return self.reply({"error":"不存在"},404)
                return self.reply(actions[action](body))
            if self.path=="/api/poetry":
                from poetry_service import save
                return self.reply(save(body))
            if self.path=="/api/research-practice/task":
                from research_practice import save_task
                return self.reply(save_task(body))
            if self.path=="/api/arxiv/curation":
                from weekly_arxiv import save_curation
                return self.reply(save_curation(body))
            if self.path=="/api/topics":
                from topics_service import add_topic
                result=add_topic(body.get("name"),body.get("keywords"),body.get("nameEn"))
                result["started"]=run_job("arxiv",only_topic=result["name"]) if body.get("fetchNow",True) else False
                return self.reply(result)
            if self.path=="/api/reader/note":
                from reader_service import save_note
                return self.reply(save_note(body.get("id",""),body.get("note","")))
            if self.path=="/api/reader/translate":
                from reader_service import translate
                return self.reply(translate(body.get("id","")))
            if self.path=="/api/ingest":ingest_files();return self.reply({"ok":True})
            if self.path=="/api/jobs":
                kind=body.get("kind")
                if kind not in ("sync","arxiv","weekly","morning"):return self.reply({"error":"无效任务"},400)
                return self.reply({"started":run_job(kind,body.get("id"),body.get("topic"))})
            return self.reply({"error":"不存在"},404)
        except Exception as e:return self.reply({"error":str(e)},400)
def main():
    global PORT,WEB
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["serve","daily","sync","ingest","status"]);parser.add_argument("--limit",type=int,default=0)
    parser.add_argument("--port",type=int,default=8866);parser.add_argument("--literature",action="store_true");parser.add_argument("--poetry",action="store_true")
    args=parser.parse_args();
    with db():pass
    PORT=args.port;WEB=ROOT/("web-poetry" if args.poetry else "web-literature" if args.literature else "web");ingest_files()
    if args.command=="serve":
        server=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
        if PORT==8866 and not args.literature and not args.poetry and not os.environ.get("RESEARCH_PUBLIC_PREVIEW"):
            from weekly_arxiv import worker
            threading.Thread(target=worker,daemon=True).start()
        print(f"http://127.0.0.1:{PORT}",flush=True);server.serve_forever()
    elif args.command=="status":print(json.dumps(zotero_status(),ensure_ascii=False))
    elif args.command=="ingest":print("Local catalog updated.")
    else:
        try:
            if args.command=="daily" and not zotero_status().get("connected"):
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
                raise RuntimeError("请先自行启动并连接 Zotero")
                time.sleep(8)
            result=update_arxiv() if args.command=="daily" else {}
            result.update(sync_zotero(args.limit));print(json.dumps(result,ensure_ascii=False))
            write_json(DATA/"last-job.json",{"running":False,"message":json.dumps(result,ensure_ascii=False),"lastRun":now().isoformat()})
        except Exception as e:
            write_json(DATA/"last-job.json",{"running":False,"message":str(e),"lastRun":now().isoformat()})
            raise
if __name__=="__main__":main()
