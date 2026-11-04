"""Local, explainable topic suggestions. No network, no reading-status writes."""
import re,json,hashlib
def match_topics(paper,rules):
 def normalized(value):return ' '+re.sub(r'[^\w\u4e00-\u9fff]+',' ',value.casefold()).strip()+' '
 title=normalized(paper.get('title',''));abstract=normalized(paper.get('summary',''));result=[]
 for rule in rules:
  hits=[];score=0
  for term in rule['terms']:
   token=normalized(term)
   if token in title:score+=4;hits.append({'term':term,'field':'title'})
   elif token in abstract:score+=1;hits.append({'term':term,'field':'abstract'})
  if score>=rule.get('threshold',3):result.append({'topicId':rule['topicId'],'score':score,'evidence':hits})
 return result

def decorate(papers):
 import paper_scope
 papers=paper_scope.filter_papers(papers)
 import study_service as study,paper_titles
 from safety_topics import safety_topics
 from agent_topics import agent_topics
 from video_topics import video_topics
 from detection_topics import detection_topics
 from research_taxonomy import research_topics
 with study.connection() as c:
  saved={r[0]:json.loads(r[1]) for r in c.execute("SELECT id,body FROM records WHERE kind='auto-classification'")}
 for p in papers:
  p['researchTopics']=research_topics(p)
  p['safetyTopics']=safety_topics(p)
  p['agentTopics']=agent_topics(p)
  p['videoTopics']=video_topics(p)
  p['detectionTopics']=detection_topics(p)
  if p['id'] in saved:
   record=saved[p['id']];p['autoClassification']=record;p['topicIds']=list(dict.fromkeys(p.get('topicIds',[])+record.get('topicIds',[])))
 return paper_titles.hydrate_titles(papers)
