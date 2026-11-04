"""Per-paper local PDFs, kept outside version control and never fetched remotely."""
import hashlib,json,os,uuid,io,contextlib
from pathlib import Path
import study_service as study
ROOT=Path(__file__).resolve().parent/'local-data'/'paper-uploads'
MAX_BYTES=50*1024*1024
def folder(ident):return ROOT/hashlib.sha256(ident.encode()).hexdigest()[:24]
def local_file(ident):
 meta=folder(ident)/'current.json'
 if not meta.is_file():return None
 obj=json.loads(meta.read_text(encoding='utf-8'));name=obj['file']
 if Path(name).name!=name or not name.endswith('.pdf'):raise ValueError('Invalid local PDF record')
 path=folder(ident)/name
 if not path.is_file():raise ValueError('Local PDF is missing; please upload it again')
 return path
def upload(ident,name,data):
 study.resolve('paper',ident)
 if Path(name).suffix.lower()!='.pdf':raise ValueError('Please choose a PDF file')
 if not 0<len(data)<=MAX_BYTES:raise ValueError('PDF files must be between 1 byte and 50 MB')
 if b'%PDF-' not in data[:1024] or b'%%EOF' not in data[-4096:]:raise ValueError('The uploaded file is not a valid PDF')
 try:
  from pypdf import PdfReader
 except ImportError:PdfReader=None
 if PdfReader:
  try:
   pdf=PdfReader(io.BytesIO(data))
   if pdf.is_encrypted and not pdf.decrypt(''):raise ValueError('Password-protected PDF: please upload an unlocked copy')
   if not len(pdf.pages):raise ValueError('The PDF has no pages')
  except ValueError:raise
  except Exception as exc:raise ValueError('The PDF could not be read; please check the file') from exc
 dest=folder(ident);dest.mkdir(parents=True,exist_ok=True);filename=uuid.uuid4().hex+'.pdf';path=dest/filename
 with path.open('xb') as f:f.write(data)
 obj=dict(paperId=ident,name=Path(name.replace(chr(92),'/')).name[:240],file=filename,size=len(data),uploadedAt=study.now())
 import local_app
 try:
  with contextlib.closing(local_app.db()) as c,c:
   row=c.execute('SELECT body FROM papers WHERE id=?',(ident,)).fetchone()
   if not row:raise ValueError('Paper record not found')
   paper=json.loads(row[0]);paper['uploadedPdf']=True;paper['uploadedPdfName']=obj['name']
   c.execute('UPDATE papers SET body=? WHERE id=?',(json.dumps(paper,ensure_ascii=False),ident))
  temp=dest/(uuid.uuid4().hex+'.json.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8');os.replace(temp,dest/'current.json')
 except Exception:
  path.unlink(missing_ok=True);raise
 return dict(saved=True,paperId=ident,name=obj['name'],size=len(data),readerUrl='paper.html?id='+__import__('urllib.parse',fromlist=['quote']).quote(ident))
