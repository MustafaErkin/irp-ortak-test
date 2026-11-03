"""158 kabul sınaması: yalnız 5544 üzerindeki ayrı TEST veritabanı.
Gerçek pg_cron dışarıdan kurulmuş olmalıdır; HTTP kabulünde otomatik tick yok.
"""
import sys,os,json,time,threading,socket,contextlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import psycopg
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[3]
DSN=os.environ['IRP_TEST_DB']
STATE={'dsn':DSN,'name':DSN.rsplit('/',1)[-1]}
assert DSN.startswith('postgresql://postgres@localhost:5544/irp_web_t20_test_')
sys.path.insert(0,str(ROOT/'istemci/web/test'));sys.path.insert(0,str(ROOT))
from yerel_api import Database,ApiServer,ApiHandler,SocketPeer
from tarayici import Browser,page,click,field,submit
from senaryo1_sina import profile
from test.oynatici.urun_surucu import UrunSurucu
OUT=Path(os.environ.get('IRP_MOTOR_TEST_OUT','/tmp/irp_motor_yama'));OUT.mkdir(parents=True,exist_ok=True);START=time.monotonic()
def stamp():return round(time.monotonic()-START,4)
def sqlrun(query,args=(),fetch=True):
 with psycopg.connect(DSN) as c:
  assert c.execute('SELECT test.ortam()').fetchone()[0]=='TEST'
  q=c.execute(query,args or None)
  return q.fetchall() if q.description else None
class DB(Database):
 def __init__(self):
  self.dsn=DSN;self.name=STATE['name'];self.port=5544;self.empty=True;self.calls=[];self.events=[];self.errors=[];self.trace=[];self.case='setup';self.profiling=False
 def driver(self):
  def connect():
   c=psycopg.connect(self.dsn,autocommit=True)
   if self.profiling:c.execute("SET track_functions='pl'")
   return c
  return UrunSurucu(baglanti_fabrikasi=connect)
 def rpc(self,person,name,params):
  before=time.monotonic();at=stamp()
  try:
   r=super().rpc(person,name,params)
   row={'case':self.case,'at':at,'person':person,'name':name,'veri':params.get('veri'),'seconds':round(time.monotonic()-before,4),'hesap':r.get('hesap') if isinstance(r,dict) else None}
   if name=='olay_ekle':row.update(code=params['olay']['eylem_kodu'],event=params['olay']['olay_kimligi'],result={k:r.get(k) for k in ('sonuc','kod','hesap','tekrar','alindi')});self.events.append(row)
   self.trace.append(row);return r
  except Exception as e:
   self.trace.append({'case':self.case,'at':at,'name':name,'veri':params.get('veri'),'seconds':round(time.monotonic()-before,4),'error':type(e).__name__});raise
 def tick(self):
  start=time.monotonic();r=Database.tick(self);self.trace.append({'case':self.case,'at':stamp(),'name':'motor_tick','seconds':round(time.monotonic()-start,4)});return r
 def pending(self):return sqlrun('SELECT bekleyen_sinir IS NOT NULL FROM motor.durum')[0][0]
 def drain(self):
  for _ in range(40):
   if not self.pending():return
   self.tick()
  raise RuntimeError('Yerel hesap tamamlanamadı')
 def dump(self,name):
  (OUT/(name+'.json')).write_text(json.dumps({'trace':self.trace,'events':self.events},ensure_ascii=False,default=str,indent=2))
class Actor:
 def __init__(self,db):self.db=db;self.letters={};self.counts=defaultdict(int);self.run='SABIT'
 def event(self,person,code,data,targets=()):
  if person not in self.letters:self.letters[person]=self.db.rpc(person,'cihaz_kaydol',{'cihaz':'ANALIZ-'+self.run+'-'+person})
  now=str(self.db.rpc(person,'simdi',{}));dt=datetime.fromisoformat(now);self.counts[person]=max(self.counts[person],int(sqlrun("SELECT coalesce(max(substring(olay_kimligi from 12 for 4)::int),0) FROM public.olaylar WHERE kim=%s AND olay_kimligi LIKE %s",(person,f'{person}-{dt:%y%m%d}____-{self.letters[person]}'))[0][0]))+1
  e={'olay_kimligi':f'{person}-{dt:%y%m%d}{self.counts[person]:04d}-{self.letters[person]}','kim':person,'adina':None,'cihaz':'MAS-'+person,'oldugu_an':now,'bildigi_son_hal_ani':now,'eylem_kodu':code,'eylem_versiyonu':1,'girdiler':data,'neyin_ustunde':[{'tur':k,'kimlik':v} for k,v in targets],'kanit':[],'duzelttigi_olay':None,'giris_sekli':'LISTE','pc_ulasma_ani':None,'saat_dilimi':'+03:00','uygulama_surumu':'WEB-0.1.0','yol':'DISARIDA'}
  required=sqlrun('SELECT kapilar_v3.liste_hedefleri(%s)',(Jsonb(e),))[0][0] or []
  for k in required:
   if not any(h['tur']=='LISTE' and h['kimlik']==k for h in e['neyin_ustunde']):e['neyin_ustunde'].append({'tur':'LISTE','kimlik':k})
  for h in e['neyin_ustunde']:
   v=self.db.rpc(person,'oku',{'veri':h['tur'],'hedef':h['kimlik'],'g':{}})['deger'];assert v,h;h['surum']=v.get('surum')
  return e
 def send(self,person,code,data,targets=(),drain=False):
  event=self.event(person,code,data,targets);r=self.db.rpc(person,'olay_ekle',{'olay':event})
  if drain:self.db.drain()
  return event,r
class Handler(ApiHandler):
 def do_POST(self):
  if not self.path.startswith('/rest/v1/rpc/'):return super().do_POST()
  params=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or b'{}');name=self.path.rsplit('/',1)[-1];person=self.headers.get('Authorization','').removeprefix('Bearer LOCAL.')
  if name=='simdi':person='K001'
  if person not in self.server.roles:return self.respond({'message':'Oturum'},401)
  try:
   if name=='olay_ekle' and self.server.hold_next:
    delay=self.server.hold_next;self.server.hold_next=0;ready=threading.Event()
    def hold():
     with psycopg.connect(DSN) as c:c.execute('SELECT pg_advisory_xact_lock(202620,1)');ready.set();time.sleep(delay)
    threading.Thread(target=hold,daemon=True).start();ready.wait(5)
   r=self.server.database.rpc(person,name,params)
   if name=='olay_ekle' and self.server.drop_next:
    self.server.drop_next-=1;self.connection.shutdown(socket.SHUT_RDWR);self.close_connection=True;return
   self.respond(r)
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception as e:
   msg=('IRP|YETKI|' if isinstance(e,PermissionError) else '')+str(e)
   self.server.database.errors.append((person,name,type(e).__name__,msg));self.respond({'message':msg},400)
class Server(ApiServer):
 def __init__(self,db):
  super().__init__(db,ROOT/'istemci/web/build');self.RequestHandlerClass=Handler;self.hold_next=0;self.drop_next=0;self.suppress_signal=False;self.stop=threading.Event();self.signal_log=[];self.next_tick=None;self.interval=60;self.pending_only=False
  threading.Thread(target=self.serve_forever,daemon=True).start();threading.Thread(target=self.signals,daemon=True).start()
 def signals(self):
  last=sqlrun('SELECT coalesce(max(kimlik),0) FROM public.degisim_sinyalleri')[0][0]
  while not self.stop.wait(.12):
   try:
    rows=sqlrun('SELECT kimlik,kanal FROM public.degisim_sinyalleri WHERE kimlik>%s ORDER BY kimlik',(last,))
    if rows:last=rows[-1][0]
    for _,channel in rows:
     self.signal_log.append({'at':stamp(),'case':self.database.case,'channel':channel,'suppressed':self.suppress_signal})
     if self.suppress_signal:continue
     for peer in list(self.peers):
      for topic in list(peer.topics):
       if topic=='realtime:irp-web-'+channel:
        try:peer.send({'topic':topic,'event':'postgres_changes','payload':{'data':{'record':{}}},'ref':None})
        except OSError:pass
   except Exception:pass
 def close(self):self.stop.set();self.shutdown();self.server_close()
