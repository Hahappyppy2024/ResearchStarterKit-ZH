"""One shared taxonomy for conference library and arXiv display."""
import json,re
from pathlib import Path
DATA=json.loads((Path(__file__).resolve().parent/'web/research-taxonomy.json').read_text(encoding='utf-8'))
RULES=[(r['id'],r['label'],[(s['id'],s['name'],s['pattern']) for s in r['subtopics']]) for r in DATA['roots'] if r['id']!='other']
COMPILED=[(r,s,re.compile(s['pattern'],re.I)) for r in DATA['roots'] for s in r['subtopics'] if r['id']!='other']
def research_topics(paper):
    title=paper.get('title','');text=title+' '+(paper.get('summary') or '')
    hits=[]
    for root,sub,pattern in COMPILED:
        if pattern.search(text):hits.append({'id':root['id']+':'+sub['id'],'name':sub['name'],'parentId':root['id'],'parentName':root['name'],'field':'title' if pattern.search(title) else 'abstract'})
    return sorted(hits,key=lambda h:(h['parentId']!='interpretability',h['field']!='title')) or [{'id':'other:unclassified','name':'待细分','parentId':'other','parentName':'待分类','field':'unclassified'}]

TOPIC_ALIASES={alias:r["id"] for r in DATA["roots"] for alias in r.get("legacyIds",[])}
def canonical_topic_id(ident):return TOPIC_ALIASES.get(ident,ident)
