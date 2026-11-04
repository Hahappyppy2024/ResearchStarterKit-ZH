"""Read collected scholar publications and tracked arXiv metadata without changing tracking."""
import contextlib,json,pathlib,re,unicodedata
import study_service as study
import workspace_content as content
TRACKING=pathlib.Path(__file__).resolve().parent/'local-data'/'scholar-tracking.json'
STATIC=pathlib.Path(__file__).resolve().parent/'web'/'scholar-publications.json'
def normalized(value):return ' '.join(unicodedata.normalize('NFKC',str(value)).casefold().split())
def author_matches(p,person):
 authors=p.get('authors',[]);authors=authors if isinstance(authors,list) else re.split(r'[,;，；]',authors)
 names={normalized(n) for n in (person.get('name'),person.get('en')) if n}
 return any(normalized(a) in names for a in authors)
def collected():
 try:data=json.loads(STATIC.read_text(encoding='utf-8'))
 except (OSError,ValueError):data={'people':[],'papers':[]}
 people={p['id']:p for p in data['people']};result=[]
 for item in data['papers']:
  link=item.get('url','');arxiv=re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})',link)
  status=item.get('status','');preprint=bool(re.search('预印本|审稿中|arXiv',status,re.I));venue='arXiv' if preprint else status.split(' · ')[0]
  p=dict(id='arxiv-'+arxiv[1] if arxiv else 'scholar-work-'+item['id'],title=item['title'],authors=people.get(item['person'],{}).get('en',''),year=item.get('year'),venue=venue,source=link,pdf=link if '/pdf/' in link else '',summary=item.get('summary',''),scholarIds=[item['person']],collectionEvidence=item.get('evidence',''),publicationNote=status)
  if arxiv:p['arxivUrl']='https://arxiv.org/abs/'+arxiv[1]
  result.append(p)
 try:tracked=json.loads(TRACKING.read_text(encoding='utf-8')).get('scholars',[])
 except (OSError,ValueError):tracked=[]
 for group in tracked:
  person=group.get('personId') or next((p['id'] for p in people.values() if normalized(p.get('en'))==normalized(group.get('author'))),None)
  if not person:continue
  for item in group.get('papers',[]):
   ident=item.get('id','');ident=ident if ident.startswith('arxiv-') else 'arxiv-'+ident
   result.append(dict(item,id=ident,source=item.get('url',''),venue='arXiv',year=int(item.get('published','0000')[:4]) if item.get('published','')[:4].isdigit() else 0,scholarIds=[person],collectionEvidence='已有学者追踪记录；不改变追踪设置或阅读状态'))
 return result

def resolve(ident):return next((p for p in collected() if p['id']==ident),None)
def listing(scholar_id='',lab_id=''):
 import local_app
 people=content.scholar_directory()['people'];person=next((p for p in people if p['id']==scholar_id),None)
 if scholar_id and not person:raise ValueError('学者不存在')
 with study.connection() as c:
  labs=study.records(c,'research-lab');refs=study.records(c,'paper-affiliations')
 lab=next((l for l in labs if l['id']==lab_id),None)
 if lab_id and lab_id not in ('all','unassigned') and not lab:raise ValueError('实验室不存在')
 members=[p for p in people if lab and (lab['id'] in p.get('labIds',[]) or any(normalized(name) in {normalized(p.get('name')),normalized(p.get('en'))} for name in (lab.get('scholars','')+'\n'+lab.get('leaders','')).splitlines() if name.strip()))]
 selected_people=[person] if person else members if lab else people
 explicit_ids={r['paperId'] for r in refs if (person and person['id'] in r.get('scholarIds',[])) or (lab and lab['id'] in r.get('labIds',[])) or (not person and not lab)}
 if not person:explicit_ids.update(i for l in ([lab] if lab else labs) for i in l.get('paperIds',[]))
 rows={}
 def add(p,verified=False):
  if not p or not p.get('title'):return
  if p['id'] in rows:
   old=rows[p['id']];incoming=p;p={**old,**p,'scholarIds':list(dict.fromkeys(old.get('scholarIds',[])+p.get('scholarIds',[])))}
   if old.get('venue') not in ('','arXiv',None) and incoming.get('venue')=='arXiv':p['venue']=old['venue']
  rows[p['id']]=p
 for ident in explicit_ids:
  try:add(study.resolve('paper',ident),True)
  except ValueError:pass
 for p in collected():
  if any(n['id'] in p.get('scholarIds',[]) for n in selected_people):add(p,True)
 # Include already collected unified-library records by full author name; label ambiguous matches.
 for p in selected_people:
  name=p.get('en') or p.get('name')
  if not name:continue
  with contextlib.closing(local_app.db()) as c:matches=c.execute('SELECT body FROM papers WHERE lower(body) LIKE ?',('%'+name.casefold()+'%',)).fetchall()
  for row in matches:
   item=json.loads(row[0])
   if not author_matches(item,p):continue
   if item['id'] not in rows:item['collectionEvidence']='完整作者署名匹配，身份与单位待核实'
   add(item)
 # Preserve explicit scholar links even when metadata authors are incomplete.
 byref={r['paperId']:r for r in refs}
 if person:rows={i:p for i,p in rows.items() if person['id'] in byref.get(i,{}).get('scholarIds',[]) or person['id'] in p.get('scholarIds',[]) or author_matches(p,person)}
 if lab_id=='unassigned':rows={i:p for i,p in rows.items() if not byref.get(i,{}).get('labIds') and not any(i in l.get('paperIds',[]) for l in labs)}
 # Collapse exact-title duplicates, retaining the existing library id and publication evidence.
 dedup={}
 for p in rows.values():
  key=normalized(p['title']);old=dedup.get(key)
  if old:
   merged={**p,**old};merged['scholarIds']=list(dict.fromkeys(old.get('scholarIds',[])+p.get('scholarIds',[])))
   if old.get('venue')=='arXiv' and p.get('venue') not in ('','arXiv'):merged.update(venue=p['venue'],publicationNote=p.get('publicationNote',''))
   dedup[key]=merged
  else:dedup[key]=p
 import paper_titles
 return dict(papers=paper_titles.hydrate_titles(list(dedup.values())),scope=person['name'] if person else lab['name'] if lab else '全部论文')
