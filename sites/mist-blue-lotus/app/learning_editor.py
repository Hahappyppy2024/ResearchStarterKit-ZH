"""Edit ordinary PPTX text boxes without changing other ZIP parts or namespaces."""
import hashlib,io,pathlib,posixpath,threading,zipfile
from xml.dom import minidom
import xml.etree.ElementTree as ET
A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
LOCK=threading.Lock()
def slide_names(z):
 import re
 fallback=sorted([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)],key=lambda n:int(re.search(r'(\d+)\.xml$',n)[1]))
 if 'ppt/_rels/presentation.xml.rels' not in z.namelist():return fallback
 rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('ppt/_rels/presentation.xml.rels')) if r.get('TargetMode')!='External'}
 result=[]
 for element in ET.fromstring(z.read('ppt/presentation.xml')).findall('.//{'+P+'}sldId'):
  target=rels.get(element.get('{'+R+'}id'),'');name=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'ppt/'+target)
  if name in fallback:result.append(name)
 return result if result else fallback
def revision(content):return hashlib.sha256(content).hexdigest()
def parse(content):
 if b'<!DOCTYPE' in content.upper():raise ValueError('不支持含 DTD 的 PPT 内容')
 return minidom.parseString(content)
def shapes(doc):
 result={}
 for sp in doc.getElementsByTagNameNS(P,'sp'):
  props=sp.getElementsByTagNameNS(P,'cNvPr');bodies=[n for n in sp.childNodes if n.nodeType==n.ELEMENT_NODE and n.namespaceURI==P and n.localName=='txBody']
  if not props or not bodies or bodies[0].getElementsByTagNameNS(A,'fld'):continue
  result[props[0].getAttribute('id')]=(props[0].getAttribute('name'),bodies[0])
 return result
def paragraphs(body):return [n for n in body.childNodes if n.nodeType==n.ELEMENT_NODE and n.namespaceURI==A and n.localName=='p']
def paragraph_text(p):
 result=[]
 for n in p.childNodes:
  if n.nodeType!=n.ELEMENT_NODE:continue
  if n.namespaceURI==A and n.localName=='br':result.append('\n')
  else:
   for t in n.getElementsByTagNameNS(A,'t'):result.extend(c.data for c in t.childNodes if c.nodeType==c.TEXT_NODE)
 return ''.join(result)
def get_slide(source,index):
 raw=source.read_bytes()
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=slide_names(z)
  if not 0<=index<len(names):raise ValueError('页面不存在')
  doc=parse(z.read(names[index]));fields=[dict(id=ident,name=name,text='\n'.join(paragraph_text(p) for p in paragraphs(body))) for ident,(name,body) in shapes(doc).items()]
 marker=source.parent/'web-edit-revision.txt'
 return dict(index=index,revision=revision(raw),fields=fields,canUndo=(source.parent/'source-before-web-edit.pptx').exists() and marker.exists() and marker.read_text()==revision(raw))
def edit_text(body,text):
 doc=body.ownerDocument;old=paragraphs(body);lines=text.split('\n')
 for i,line in enumerate(lines):
  original=old[min(i,len(old)-1)] if old else None
  p=original.cloneNode(True) if original else doc.createElementNS(A,'a:p')
  p.setAttribute('xmlns:a',A)
  runs=p.getElementsByTagNameNS(A,'r');style=None
  if runs:
   props=runs[0].getElementsByTagNameNS(A,'rPr')
   if props:style=props[0].cloneNode(True)
  for child in list(p.childNodes):
   if child.nodeType!=child.ELEMENT_NODE or child.namespaceURI!=A or child.localName not in ('pPr','endParaRPr'):p.removeChild(child)
  run=doc.createElementNS(A,'a:r')
  if style:run.appendChild(style)
  t=doc.createElementNS(A,'a:t');t.setAttribute('xml:space','preserve');t.appendChild(doc.createTextNode(line));run.appendChild(t)
  end=next((n for n in p.childNodes if n.nodeType==n.ELEMENT_NODE and n.localName=='endParaRPr'),None)
  if end:p.insertBefore(run,end)
  else:p.appendChild(run)
  if old:body.insertBefore(p,old[0])
  else:body.appendChild(p)
 for p in old:body.removeChild(p)
def save_slide(source,index,expected,fields):
 if not isinstance(fields,list) or len(fields)>300:raise ValueError('文本框数量无效')
 with LOCK:
  raw=source.read_bytes()
  if revision(raw)!=expected:raise ValueError('PPT 已被其他窗口或 PowerPoint 修改，请重新打开编辑页后再保存')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=slide_names(z)
   if not 0<=index<len(names):raise ValueError('页面不存在')
   name=names[index];doc=parse(z.read(name));items=shapes(doc);seen=set()
   for field in fields:
    ident=field.get('id');text=field.get('text')
    if ident in seen or ident not in items or not isinstance(text,str) or len(text)>50000 or any(ord(c)<32 and c not in '\t\n\r' for c in text):raise ValueError('文本框内容无效')
    seen.add(ident);body=items[ident][1]
    if text!='\n'.join(paragraph_text(p) for p in paragraphs(body)):edit_text(body,text)
   output=io.BytesIO()
   with zipfile.ZipFile(output,'w') as target:
    for part in z.infolist():target.writestr(part,doc.toxml(encoding='UTF-8') if part.filename==name else z.read(part.filename))
  temp=source.with_suffix('.tmp');temp.write_bytes(output.getvalue())
  backup=source.parent/'source-before-web-edit.pptx';backup.write_bytes(raw)
  try:temp.replace(source)
  except PermissionError:raise ValueError('PPT 正在被 PowerPoint 占用，请先关闭该文件再保存')
  (source.parent/'web-edit-revision.txt').write_text(revision(output.getvalue()))
  return revision(output.getvalue())
def undo(source,expected):
 with LOCK:
  if revision(source.read_bytes())!=expected:raise ValueError('PPT 已发生变化，请重新打开编辑页')
  backup=source.parent/'source-before-web-edit.pptx'
  marker=source.parent/'web-edit-revision.txt'
  if not marker.exists() or marker.read_text()!=expected:raise ValueError('PPT 后来又被修改，无法直接撤销这次网页编辑')
  if not backup.exists():raise ValueError('没有可撤销的网页编辑')
  temp=source.with_suffix('.tmp');temp.write_bytes(backup.read_bytes())
  try:temp.replace(source)
  except PermissionError:raise ValueError('请先在 PowerPoint 关闭此文件')
  backup.unlink()
  marker.unlink()
