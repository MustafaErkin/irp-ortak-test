from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import sys,threading,json
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'istemci/web/test'));from tarayici import Browser
class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(R/'istemci/web/build'),**kw)
 def log_message(self,*_):pass
 def do_GET(self):
  if self.path=='/form-test':
   text=b'<!doctype html><html><body><div id="toasts"></div></body></html>';self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(text)
  else:super().do_GET()
s=ThreadingHTTPServer(('127.0.0.1',0),H);threading.Thread(target=s.serve_forever,daemon=True).start();b=Browser()
try:
 b.navigate(f'http://127.0.0.1:{s.server_port}/form-test')
 b.wait("location.pathname==='/form-test' && document.readyState==='complete'")
 schema=json.loads((R/'referans/eylem_semalari.json').read_text())
 b.js('window.schemas='+json.dumps(schema))
 b.js("""(async()=>{const {bindForm,operationSchema}=await import('./forms.js');const d=document.createElement('dialog');document.body.append(d);d.innerHTML='<div id="fields"></div>';d.showModal();window.values={not:'Korunan gerekçe',revizyon_ver:false};const client={people:[{kimlik:'K041',ad:'Ofis Çalışanı'}],units:[],projects:[],context:{},cached:()=>[]};bindForm(d.querySelector('#fields'),()=>operationSchema('GOREV.REDDETTIM',schemas,values),values,{client,code:'GOREV.REDDETTIM',refs:{KISI:client.people}});window.ready=true})()""")
 b.wait('window.ready===true')
 b.js("document.querySelector('details').open=true;document.querySelector('[data-add=sorumlular]').click()")
 assert b.js('document.activeElement.dataset.path')=='sorumlular.0.tur'
 b.js("document.querySelector('[data-add=sorumlular]').click()")
 assert b.js('document.activeElement.dataset.path')=='sorumlular.1.tur'
 b.js("document.querySelector('[data-remove][data-index=\"1\"]').click()")
 assert b.js('document.activeElement.dataset.path')=='sorumlular.0.tur'
 b.js("document.querySelector('[data-remove]').click()")
 assert b.js('document.activeElement.dataset.add')=='sorumlular'
 assert b.js("document.querySelector('details').open && document.querySelector('[data-path=not]').value==='Korunan gerekçe'")
 assert not b.errors,b.errors
 (R/'codex/sonuclar/tur21_kanit/form_durumu.json').write_text(json.dumps({'tamamlandi':True,'kontroller':['Yeni satırın ilk alanına odak','Silmede komşu satıra odak','Son satır silinince Satır Ekle odağı','Açık bölüm ve gerekçe korunur']},ensure_ascii=False,indent=2))
 print('Ortak form: ekleme, silme, son satır ve odak kontrolleri geçti.')
except Exception:
 print('JS',b.errors,'AĞ',b.network_errors,flush=True);raise
finally:b.close();s.shutdown();s.server_close()
