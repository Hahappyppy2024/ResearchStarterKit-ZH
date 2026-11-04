"""Shared local theme assets and the user's persistent palette choice."""
import json,pathlib,threading,re
ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/'web-shared'
SETTING=ROOT/'local-data'/'appearance.json'
LOCAL_PALETTE=ASSETS/'mist-blue-lotus.css'
LOCK=threading.Lock()
ORIGINS={f'http://127.0.0.1:{p}' for p in (8866,8867,8868,8869,8870,8891,8873,8872)}|{'http://localhost:8869'}
def inject(body,kind):
 if 'text/html' not in kind:return body
 body=re.sub(br'<html([^>]*)lang="[^"]*"',br'<html\1lang="zh-CN"',body,count=1)
 markup=b'<link rel="stylesheet" href="/research-theme.css"><script defer src="/research-theme.js"></script><script type="module" src="/research-file-drop.js"></script>'
 return body.replace(b'</head>',markup+b'</head>',1) if b'research-theme.js' not in body else body
def asset(path):
 if path in ('/paper-title.js','/paper-title-model.mjs'):return (ROOT/'web'/path.lstrip('/')).read_bytes(),'application/javascript'
 names={'/research-file-drop.js':('file-drop.js','application/javascript'),'/research-english.js':('english-ui.js','application/javascript'),'/research-english.json':('english-ui.json','application/json'),'/research-theme.js':('theme.js','application/javascript'),'/research-theme.css':('theme.css','text/css'),'/research-paste.js':('paste.js','application/javascript')}
 if path not in names:return None
 name,kind=names[path];body=(ASSETS/name).read_bytes()
 if path=='/research-theme.css' and preference()['theme']=='blue-mint':body+=b'\n'+LOCAL_PALETTE.read_bytes()
 return body,kind
def preference():
 try:theme=json.loads(SETTING.read_text(encoding='utf-8')).get('theme')
 except (OSError,ValueError,AttributeError):theme='blue-mint'
 return dict(theme='blue-mint' if theme=='blue-mint' and LOCAL_PALETTE.is_file() else 'blue')
def save(data):
 theme=data.get('theme')
 if theme not in ('blue','blue-mint'):raise ValueError('主题无效')
 if theme=='blue-mint' and not LOCAL_PALETTE.is_file():raise ValueError('本机柔彩配色文件不存在')
 with LOCK:
  SETTING.parent.mkdir(parents=True,exist_ok=True);tmp=SETTING.with_suffix('.tmp');tmp.write_text(json.dumps(dict(theme=theme)),encoding='utf-8');tmp.replace(SETTING)
 return dict(theme=theme)
