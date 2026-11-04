"""Topic-first browsing of conference and personally selected papers."""
import collections
import paper_scope
from research_taxonomy import canonical_topic_id,TOPIC_ALIASES
import copy
import contextlib
import hashlib
import json
import re
import threading
import sqlite3
import time
from pathlib import Path
import conference_catalog as conferences
import knowledge_service as knowledge
import reading_journal
import reader_service
import study_service as study

TRANSLATION_LOCK = threading.Lock()
INDEX_LOCK = threading.Lock()
INDEX = None
INDEX_SIGNATURE = None
GOOGLE_RETRY_AT = 0
SNAPSHOT_LOCK=threading.RLock()
SNAPSHOT=None
SNAPSHOT_KEY=None

def conference_rows():
    global INDEX,INDEX_SIGNATURE
    signature=(conferences.signature(),tuple(conferences.VENUES),hashlib.sha256(repr(conferences.RULES).encode()).hexdigest())
    with INDEX_LOCK:
        if INDEX is not None and signature==INDEX_SIGNATURE:return INDEX
        disk=conferences.ROOT/'local-data/topic-classification-cache.json'
        stamp=json.dumps(signature)
        cached_rows={}
        try:
            saved=json.loads(disk.read_text(encoding='utf-8'))
            if json.loads(saved['signature'])[-1]==signature[-1]:cached_rows=saved['rows']
            if saved['signature']==stamp:
                INDEX=saved['rows'];INDEX_SIGNATURE=signature;return INDEX
        except (OSError,ValueError,KeyError):pass
        with contextlib.closing(sqlite3.connect(conferences.ROOT/'local-data/library.sqlite')) as c:
            raw=c.execute('SELECT body FROM papers WHERE venue IN ('+','.join('?' for _ in conferences.VENUES)+')',conferences.VENUES).fetchall()
        result={}
        for r in raw:
            p=json.loads(r[0]);old=cached_rows.get(p['id'],{});p['categories']=p['foundationCategories'] if p.get('foundationCategories') else old['categories'] if old.get('title')==p['title'] and old.get('venue')==p.get('venue') and old.get('categories') else conferences.classify_paper({'title':p['title'],'venue':p.get('venue')});p['arxivUrl']=conferences.arxiv_link(p);p['conference']=True;result[p['id']]=p
        INDEX=result;INDEX_SIGNATURE=signature
        try:
            tmp=disk.with_suffix('.tmp');tmp.write_text(json.dumps(dict(signature=stamp,rows=result),ensure_ascii=False),encoding='utf-8');tmp.replace(disk)
        except OSError:pass
        return INDEX

def topic_index():
    roots = [{'id':cid,'name':label.split(' / ')[0],'parentId':None,'auto':True,
              'children':[{'id':cid+':'+sid,'name':name,'parentId':cid,'auto':True} for sid,name,_ in subs]}
             for cid,label,subs in conferences.RULES]
    roots.append(dict(id='other',name='待分类',parentId=None,auto=True,children=[]))
    custom = [dict(n,auto=False) for n in knowledge.taxonomy()['nodes'] if n['kind']=='topic' and n['id'] not in TOPIC_ALIASES]
    return roots,custom

def matches(p, ident, custom):
    if not ident:return True
    if ident in {n['id'] for n in custom}:
        descendants={ident}
        for _ in range(3):descendants.update(n['id'] for n in custom if n.get('parentId') in descendants)
        return bool(descendants.intersection(p.get('topicIds',[])))
    return any(ident==c or ident==c+':'+s for c,s in p['categories'])

def cached_translation(text):
    if not text:return ''
    if re.search(r'[\u4e00-\u9fff]',text) and not re.search(r'[A-Za-z]{4}',text):return text
    with contextlib.closing(reader_service.connection()) as c:
        r=c.execute('SELECT zh FROM translations WHERE hash=?',(hashlib.sha256(text.encode()).hexdigest(),)).fetchone()
    return r[0] if r else ''

def snapshot_key():
    paths=[paper_scope.PATH,study.DB,Path(str(study.DB)+'-wal')]
    return (str(study.DB),study.today(),conferences.signature(),tuple(conferences.VENUES),tuple((p.stat().st_size,p.stat().st_mtime_ns) if p.exists() else None for p in paths))

def library_snapshot():
    global SNAPSHOT,SNAPSHOT_KEY
    with SNAPSHOT_LOCK:
        key=snapshot_key()
        if SNAPSHOT is not None and key==SNAPSHOT_KEY:return SNAPSHOT
        roots,custom=topic_index()
        personal=reading_journal.statistics(include_items=True)['items'];selected={p['id']:p for p in personal}
        with study.connection() as c:annotations={p['id']:p for p in study.records(c,'paper-knowledge')}
        rows={ident:dict(p) for ident,p in conference_rows().items()}
        for p in personal:
            if p['id'] not in rows:rows[p['id']]=dict(study.resolve('paper',p['id']),conference=False)
        parents={n['id']:n.get('parentId') for n in custom};conference_counts=collections.Counter();personal_counts=collections.Counter();memberships={};by_topic=collections.defaultdict(list)
        for p in list(rows.values()):
            if paper_scope.reason(p):rows.pop(p['id'],None);continue
            p['categories']=p.get('foundationCategories') or p.get('categories') or conferences.classify_paper(p)
            p['topicIds']=annotations.get(p['id'],{}).get('topicIds',[])
            p['inToday']=selected.get(p['id'],{}).get('inToday',False);p['personal']=p['id'] in selected;p['read']=selected.get(p['id'],{}).get('read',False)
            labels={canonical_topic_id(label) for c,s in p['categories'] for label in (c,c+':'+s)}
            for ident in p['topicIds']:
                seen=set()
                while ident and ident not in seen:seen.add(ident);labels.add(canonical_topic_id(ident));ident=parents.get(ident)
            memberships[p['id']]=labels
            if p['conference']:conference_counts.update(labels)
            elif p['personal']:personal_counts.update(labels)
            by_topic[''].append(p)
            for ident in labels:by_topic[ident].append(p)
        for n in [*roots,*[c for t in roots for c in t['children']],*custom]:n.update(conferenceCount=conference_counts[n['id']],personalCount=personal_counts[n['id']])
        SNAPSHOT=dict(roots=roots,custom=custom,rows=list(rows.values()),byTopic=by_topic,views={},totalConference=sum(p['conference'] for p in rows.values()),totalPersonal=sum(p['personal'] and not p['conference'] for p in rows.values()))
        SNAPSHOT_KEY=snapshot_key()
        return SNAPSHOT

def batch_translations(papers):
    texts={p.get(k,'') for p in papers for k in ('title','summary') if p.get(k)}
    hashes={hashlib.sha256(t.encode()).hexdigest():t for t in texts};found={}
    if hashes:
        with contextlib.closing(reader_service.connection()) as c:
            for key,zh in c.execute('SELECT hash,zh FROM translations WHERE hash IN ('+','.join('?' for _ in hashes)+')',list(hashes)):found[hashes[key]]=zh
    return found

def browse(topic='',source='conference',venue='',year='',query='',page=0,state='all'):
    topic=canonical_topic_id(topic);snapshot=library_snapshot();roots,custom=snapshot['roots'],snapshot['custom'];topical=snapshot['byTopic'].get(topic,[])
    viewkey=(topic,source)
    if viewkey not in snapshot['views']:
        candidates=[p for p in topical if p['conference']] if source=='conference' else [p for p in topical if p['personal'] and not p['conference']]
        snapshot['views'][viewkey]=(candidates,collections.Counter(p.get('venue') for p in candidates),sorted({2027,2026,2025}|{int(p['year']) for p in candidates if str(p.get('year','')).isdigit()},reverse=True),sum(p['conference'] for p in topical),sum(p['personal'] and not p['conference'] for p in topical))
    candidates,venue_counts,available_years,conference_count,personal_count=snapshot['views'][viewkey]
    year_counts=collections.Counter(str(p.get('year')) for p in candidates if not venue or p.get('venue')==venue)
    venues=[dict(name=v,count=venue_counts[v]) for v in conferences.VENUES]
    years=[dict(year=y,count=year_counts[str(y)]) for y in available_years]
    query=query.casefold();filtered=[p for p in candidates if (not venue or p.get('venue')==venue) and (not year or str(p.get('year'))==str(year)) and (state=='all' or p['read']==(state=='read')) and (not query or query in (p['title']+' '+str(p.get('authors',''))).casefold())]
    def section(p):return next((c+':'+s for c,s in p['categories'] if topic==c or topic==c+':'+s),':'.join(p['categories'][0]))
    filtered.sort(key=lambda p:(section(p),-int(p.get('year') or 0),p['title'].casefold()))
    page=max(0,min(int(page),max(0,(len(filtered)-1)//20)));page_rows=filtered[page*20:(page+1)*20];translations=batch_translations(page_rows)
    import paper_titles
    output=paper_titles.hydrate_titles([dict(p,titleZh=p.get('titleZh') or translations.get(p['title'],''),summaryZh=translations.get(p.get('summary',''),'')) for p in page_rows])
    return dict(topics=copy.deepcopy(roots),customTopics=copy.deepcopy(custom),venues=venues,years=years,papers=output,count=len(filtered),page=page,pageSize=20,
                allConferenceCount=snapshot['totalConference'],allPersonalCount=snapshot['totalPersonal'],
                conferenceCount=conference_count,personalCount=personal_count,
                classification='系统 Topic 根据标题关键词初步分类，可跨类、待复核；我的 Topic 使用阅读任务中保存的人工分类。顶会论文与日常添加论文分开统计。')

def translate_text(text):
    global GOOGLE_RETRY_AT
    cached=cached_translation(text)
    if cached or not text:return cached
    import requests
    zh='';provider='Google 在线机器翻译'
    if time.time()>=GOOGLE_RETRY_AT:
        try:
            response=requests.get('https://translate.googleapis.com/translate_a/single',params={'client':'gtx','sl':'en','tl':'zh-CN','dt':'t','q':text},timeout=12)
            response.raise_for_status()
            zh=''.join(x[0] for x in response.json()[0] if x and x[0])
        except Exception:GOOGLE_RETRY_AT=time.time()+600
    if not zh:
        # A separate provider is used when Google is unavailable; never retry-loop a rate limit.
        if len(text)>480:raise ValueError('摘要翻译暂不可用，保留原文')
        response=requests.get('https://api.mymemory.translated.net/get',params={'q':text,'langpair':'en|zh-CN'},timeout=12)
        response.raise_for_status();value=response.json()
        if int(value.get('responseStatus',0))!=200 or value.get('quotaFinished'):raise ValueError('备用翻译服务今日额度已用完')
        zh=value.get('responseData',{}).get('translatedText','');provider='MyMemory 在线机器翻译'
    if not zh.strip():raise ValueError('翻译服务未返回内容')
    with contextlib.closing(reader_service.connection()) as c:
        c.execute('INSERT OR REPLACE INTO translations VALUES(?,?,?,?)',(hashlib.sha256(text.encode()).hexdigest(),text,zh,provider));c.commit()
    return zh

def translate(data):
    # Only public conference metadata may be sent to the existing online translation provider.
    pid=study.text(data.get('paperId',''),200)
    p=study.resolve('paper',pid)
    if p.get('venue') not in conferences.VENUES:raise ValueError('这里只翻译已收录会议论文的公开标题与摘要')
    import paper_titles
    result=paper_titles.bilingual_title({'paperId':pid})
    result['summaryZh']=cached_translation(p.get('summary',''))
    with TRANSLATION_LOCK:
        try:
            result['summaryZh']=translate_text(p.get('summary',''))
        except Exception:result['error']='中文翻译暂不可用，可点击重试；英文原文仍保留。'
    return result
