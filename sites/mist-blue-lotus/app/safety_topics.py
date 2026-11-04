"""Explainable title/abstract keyword tags; never overwrite saved user categories."""
import json,pathlib,re
RULES=json.loads((pathlib.Path(__file__).resolve().parent/'web'/'safety-taxonomy.json').read_text(encoding='utf-8'))
def safety_topics(paper):
 title=paper.get('title','').casefold();abstract=paper.get('summary','').casefold()
 matches=[]
 for i,rule in enumerate(RULES):
  field='title' if re.search(rule['pattern'],title) else 'abstract' if re.search(rule['pattern'],abstract) else None
  if field:matches.append((0 if field=='title' else 1,i,{'name':rule['name'],'field':field,'question':rule['question']}))
 return [m[2] for m in sorted(matches)]
