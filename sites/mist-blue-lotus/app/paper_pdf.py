"""On-demand local viewing of public paper PDFs; no bulk downloads."""
import hashlib,pathlib,re,subprocess,threading,urllib.parse,uuid
import reader_service
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=ROOT/'local-data'/'paper-pdf-cache'
HOSTS={'arxiv.org','export.arxiv.org','openaccess.thecvf.com','proceedings.mlr.press','papers.nips.cc','proceedings.neurips.cc','openreview.net','leon.bottou.org'}
LOCK=threading.Lock()
def original_url(p):
    url=p.get('pdf') or p.get('source') or ''
    parsed=urllib.parse.urlsplit(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme!='https' or host not in HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('该来源暂不支持内嵌预览，请使用“直接打开原文”。')
    if host in ('arxiv.org','export.arxiv.org'):
        match=re.fullmatch(r'/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?',parsed.path)
        if not match:raise ValueError('arXiv 论文链接格式无效')
        return 'https://arxiv.org/pdf/'+match[1]
    if not parsed.path.lower().endswith('.pdf') and not(host=='openreview.net' and parsed.path=='/pdf'):raise ValueError('未找到可直接预览的 PDF，请使用“直接打开原文”。')
    return urllib.parse.urlunsplit(parsed._replace(fragment=''))
def cache_path(p):return CACHE/(hashlib.sha256(original_url(p).encode()).hexdigest()+'.pdf')
def cached_file(ident):
    from paper_uploads import local_file
    local=local_file(ident)
    if local:return local
    p=reader_service.paper(ident);path=cache_path(p)
    if not path.is_file():raise ValueError('原文尚未加载，请点击重试加载原文')
    return path

def prepare(ident):
    from paper_uploads import local_file
    local=local_file(ident)
    if local:return {'url':'/api/study/paper-pdf?'+urllib.parse.urlencode({'paperId':ident}),'source':'local-upload','bytes':local.stat().st_size}
    p=reader_service.paper(ident);url=original_url(p);path=cache_path(p)
    with LOCK:
        if not path.is_file():
            CACHE.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.'+uuid.uuid4().hex+'.part')
            try:
                result=subprocess.run(['curl.exe' if __import__('os').name=='nt' else 'curl','-f','-sS','-L','--compressed','--proto','=https','--proto-redir','=https','--connect-timeout','15','--max-time','80','--max-filesize','60000000','-o',str(temp),url],capture_output=True,timeout=90)
                if result.returncode:raise ValueError('原文加载暂未成功，可重试或直接打开官方原文。')
                with temp.open('rb') as f:header=f.read(1024)
                if b'%PDF-' not in header:raise ValueError('来源返回的不是 PDF，可直接打开官方页面查看。')
                if temp.stat().st_size>60000000:raise ValueError('原文文件较大，请直接打开官方原文。')
                temp.replace(path)
            finally:
                if temp.exists():temp.unlink()
    return {'url':'/api/study/paper-pdf?'+urllib.parse.urlencode({'paperId':ident}),'source':url,'bytes':path.stat().st_size}
