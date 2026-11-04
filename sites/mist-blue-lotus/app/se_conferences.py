"""Import public accepted research-track metadata; never downloads paper PDFs or syncs Zotero."""
import concurrent.futures,hashlib,json,re
from pathlib import Path
from urllib.parse import urljoin
import conference_sources as sources

TRACKS={
 ('ICSE',2025):'icse-2025-research-track',('ICSE',2026):'icse-2026-research-track',
 ('FSE',2025):'fse-2025-research-papers',('FSE',2026):'fse-2026-research-papers',
 ('ASE',2025):'ase-2025-papers',('ASE',2026):'ase-2026-research-track',
 ('ISSTA',2025):'issta-2025-papers',('ISSTA',2026):'issta-2026-research-papers',
}
def parse(text,venue,year,url):
 start=re.search(r'<div\b[^>]*id="event-overview"',text)
 if not start:raise ValueError('Official accepted-papers section missing')
 table=re.search(r'<table\b[^>]*>(.*?)</table>',text[start.start():],re.S)
 if not table:raise ValueError('Accepted-papers table missing')
 rows={}
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table[1],re.S):
  title=re.search(r'<a\b[^>]*data-event-modal="([^"]+)"[^>]*>(.*?)</a>',row,re.S)
  if not title:continue
  track=re.search(r'<div class="prog-track">(.*?)</div>',row,re.S)
  if not track or not re.search('Research',sources.clean(track[1]),re.I):continue
  authors=re.search(r'<div class="performers">(.*?)</div>',row,re.S)
  authors=', '.join(sources.clean(a) for a in re.findall(r'<a\b[^>]*>(.*?)</a>',authors[1],re.S)) if authors else ''
  links=[(urljoin(url,u),sources.clean(label)) for u,label in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',row,re.S) if u.startswith(('https://','http://','/details/'))]
  doi=next((u for u,label in links if 'doi.org/' in u),'')
  detail=next((u for u,label in links if '/details/' in u),'')
  preprint=next((u for u,label in links if label in ('Pre-print','DOI','Link to publication')),'')
  pdf=next((u for u,label in links if re.search(r'\.pdf(?:\?|$)|arxiv.org/pdf/|/doi/pdf/',u)),'')
  title_text=re.sub(r'<span\b.*?</span>','',title[2],flags=re.S)
  p=sources.paper(title_text,authors,doi or detail or preprint or url+'#event-overview',pdf,venue,year)
  p.update(id=venue.lower()+'-'+str(year)+'-'+hashlib.sha256(title[1].encode()).hexdigest()[:20],track='Research Track' if venue=='ICSE' else 'Research Papers',catalogSource=url,metadataNote='官方研究轨道已接收列表；未逐篇下载全文，未提供的摘要留空。')
  rows[p['id']]=p
 if not rows:raise ValueError('No accepted research papers parsed; existing records preserved')
 return list(rows.values())

def fetch_track(item):
 (venue,year),slug=item;url='https://conf.researchr.org/track/'+venue.lower()+'-'+str(year)+'/'+slug
 text=sources.fetch(url);rows=parse(text,venue,year,url)
 return rows,dict(venue=venue,year=year,count=len(rows),url=url,status='accepted_research_track',note='官方已接收研究轨道目录，不含其他轨道；仅保存题录及公开链接。')

def main():
 import local_app
 path=sources.ROOT/'local-data/se-conferences.json';prior=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(sources=[])
 statuses={(s['venue'],s['year']):s for s in prior['sources']}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={pool.submit(fetch_track,item):item[0] for item in TRACKS.items()}
  for future in concurrent.futures.as_completed(jobs):
   venue,year=jobs[future]
   try:
    rows,status=future.result();local_app.absorb(rows);statuses[(venue,year)]=status
    print(venue,year,'imported',len(rows),flush=True)
   except Exception as error:
    print(venue,year,'FAILED',str(error)[:250],flush=True)
    if (venue,year) not in statuses:statuses[(venue,year)]=dict(venue=venue,year=year,status='failed',note=str(error)[:350],count=0)
 path.write_text(json.dumps(dict(sources=list(statuses.values())),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
