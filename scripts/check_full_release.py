"""Audit upload candidates; ignored runtime data is never included."""
from pathlib import Path
import json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode('utf-8').split('\0')
files=[ROOT/n for n in set(names) if n and (ROOT/n).is_file()]
forbidden={'local-data','local-data-backups','course-materials','courses-private','pasted-images','__pycache__','.env','node_modules'}
private={'news_service.py','news.js','news.css','idea_service.py','research-ideas.js','research-ideas.css','create_learning_templates.ps1','test_news_service.py','test_idea_service.py'}
errors=[]
for p in files:
 rel=p.relative_to(ROOT)
 if set(rel.parts)&forbidden or p.name in private or p.suffix.lower() in {'.db','.sqlite','.sqlite3','.ppt','.pptx','.pdf','.log','.pyc','.zip'} or re.search(r'\.sqlite(?:3)?-(?:wal|shm)$',p.name):errors.append(f'Private/runtime candidate: {rel}')
app=ROOT/'sites/mist-blue-lotus/app'
for p in files:
 if not p.is_relative_to(app) or p.suffix not in {'.py','.html','.css','.js','.mjs'} or 'vendor' in p.parts:continue
 text=p.read_text(encoding='utf-8-sig')
 if re.search(r'[CD]:[/\\](?:Users|000_CV_projects|000_workwork|language|nvm4w)',text):errors.append(f'Private machine path: {p.relative_to(app)}')
 if re.search(r'127\.0\.0\.1:(?:876[6-9]|8770)',text):errors.append(f'Private service reference: {p.relative_to(app)}')
assert json.loads((app/'web/scholar-profiles.json').read_text(encoding='utf-8'))==[]
assert json.loads((app/'web/scholar-publications.json').read_text(encoding='utf-8'))=={'people':[],'papers':[]}
assert 'SEEDS=[]' in (app/'learning_service.py').read_text(encoding='utf-8')
if errors:raise SystemExit('\n'.join(errors))
print(f'PASS: {len(files)} upload candidates; isolated ports, no private databases or course materials.')
