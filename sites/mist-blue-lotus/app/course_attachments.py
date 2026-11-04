"""Private per-lesson document storage."""
import hashlib,json,uuid
from pathlib import Path
import study_service as study
ROOT=Path(__file__).resolve().parent/'local-data'/'course-attachments'
EXT={'.pdf':'application/pdf','.doc':'application/msword','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.ppt':'application/vnd.ms-powerpoint','.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation'}
def location(course,unit):
 with study.connection() as c:
  obj=study.row(c,'course',course)
  if unit not in obj['units']:raise ValueError('课次不存在')
 return ROOT/str(uuid.UUID(course))/hashlib.sha256(unit.encode()).hexdigest()[:20]
def listing(course,unit):
 folder=location(course,unit);items=[]
 for f in folder.glob('*.json'):
  item=json.loads(f.read_text(encoding='utf-8'));item['url']='/api/study/course-attachment-file?courseId='+course+'&unit='+__import__('urllib.parse',fromlist=['quote']).quote(unit)+'&id='+item['id'];items.append(item)
 return dict(items=sorted(items,key=lambda x:x['createdAt'],reverse=True),storagePath=str(folder))
def upload(course,unit,name,data):
 ext=Path(name).suffix.lower()
 if ext not in EXT:raise ValueError('支持 PDF、Word、PPT 文件')
 if not data or len(data)>50*1024*1024:raise ValueError('单个文件最大 50 MB')
 if ext=='.pdf' and not data.startswith(b'%PDF-'):raise ValueError('不是有效 PDF 文件')
 if ext in ('.docx','.pptx') and not data.startswith(b'PK'):raise ValueError('不是有效 Office 文件')
 if ext in ('.doc','.ppt') and not data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):raise ValueError('不是有效 Office 文件')
 folder=location(course,unit);folder.mkdir(parents=True,exist_ok=True);ident=uuid.uuid4().hex
 item=dict(id=ident,name=Path(name.replace(chr(92),'/')).name[:240],extension=ext,size=len(data),createdAt=study.now())
 (folder/(ident+ext)).write_bytes(data);(folder/(ident+'.json')).write_text(json.dumps(item,ensure_ascii=False),encoding='utf-8')
 return listing(course,unit)
def read(course,unit,ident):
 if len(ident)!=32 or any(x not in '0123456789abcdef' for x in ident):raise ValueError('附件编号无效')
 folder=location(course,unit);meta=json.loads((folder/(ident+'.json')).read_text(encoding='utf-8'));ext=meta['extension']
 return (folder/(ident+ext)).read_bytes(),EXT[ext]
