"""Single local entry point, with allowlisted service launch and iframe targets."""
import http.server,json,mimetypes,pathlib,threading,urllib.parse
import theme_assets
from hub_services import status,ensure_services
ROOT=pathlib.Path(__file__).resolve().parent;WEB=ROOT/"web-hub";PORT=8869
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def trusted(self):
  host=self.headers.get("Host","")
  return host in ("127.0.0.1:8869","localhost:8869") and self.headers.get("Origin","http://"+host)=="http://"+host
 def reply(self,body,kind="application/json",code=200):
  if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False).encode()
  body=theme_assets.inject(body,kind)
  self.send_response(code);self.send_header("Content-Type",kind+"; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff")
  if urllib.parse.urlsplit(self.path).path=='/api/theme' and self.headers.get('Origin') in theme_assets.ORIGINS:
   self.send_header('Access-Control-Allow-Origin',self.headers['Origin']);self.send_header('Vary','Origin');self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
  self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; frame-src http://127.0.0.1:8866 http://127.0.0.1:8873 http://127.0.0.1:8891 http://127.0.0.1:8867 http://127.0.0.1:8868 http://127.0.0.1:8870; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
  self.end_headers();self.wfile.write(body)
 def do_GET(self):
  if urllib.parse.urlsplit(self.path).path=='/api/theme':
   if self.headers.get('Host') not in ('127.0.0.1:8869','localhost:8869') or self.headers.get('Origin','http://'+self.headers.get('Host','')) not in theme_assets.ORIGINS:return self.reply({'error':'禁止访问'},code=403)
   return self.reply(theme_assets.preference())
  if not self.trusted():return self.reply({"error":"仅允许本机同源访问"},code=403)
  path=urllib.parse.urlsplit(self.path).path
  if path=='/api/theme':return self.reply(theme_assets.preference())
  shared=theme_assets.asset(path)
  if shared:return self.reply(shared[0],shared[1])
  if path=="/api/services":return self.reply({"services":status()})
  name="index.html" if path=="/" else path.lstrip("/");file=(WEB/name).resolve()
  if not file.is_relative_to(WEB.resolve()) or not file.is_file():return self.reply({"error":"不存在"},code=404)
  return self.reply(file.read_bytes(),mimetypes.guess_type(file.name)[0] or "application/octet-stream")
 def do_POST(self):
  if self.path=='/api/theme':
   if self.headers.get('Host') not in ('127.0.0.1:8869','localhost:8869') or self.headers.get('Origin','http://'+self.headers.get('Host','')) not in theme_assets.ORIGINS or self.headers.get('Content-Type')!='application/json':return self.reply({'error':'仅允许本地页面设置主题'},code=403)
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<1000:raise ValueError('无效请求')
    return self.reply(theme_assets.save(json.loads(self.rfile.read(length))))
   except (ValueError,TypeError):return self.reply({'error':'请选择绿色或蓝色'},code=400)
  if not self.trusted() or self.headers.get("Content-Type")!="application/json":return self.reply({"error":"仅允许本机 JSON 请求"},code=403)
  if self.path!="/api/services/start":return self.reply({"error":"不存在"},code=404)
  if int(self.headers.get("Content-Length","0"))>1000:return self.reply({"error":"请求过大"},code=413)
  self.rfile.read(int(self.headers.get("Content-Length","0")))
  threading.Thread(target=ensure_services,daemon=True).start();return self.reply({"started":True})
 def do_OPTIONS(self):
  if self.path!='/api/theme' or self.headers.get('Origin') not in theme_assets.ORIGINS or self.headers.get('Host') not in ('127.0.0.1:8869','localhost:8869'):return self.reply({'error':'禁止访问'},code=403)
  return self.reply({})
if __name__=="__main__":
 threading.Thread(target=ensure_services,daemon=True).start()
 http.server.ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
