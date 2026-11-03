"""Tur3.1: gerçek kabul/ret, veri korunumu ve hesap bekleyen sıra işlemi.
Yalnız geçici yerel firma. Canlı sisteme veya kullanıcı notlarına erişmez.
"""
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json, threading, time, sys
import psycopg
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from yerel_api import Database,ApiServer
from tarayici import Browser,page,click,field,submit
from senaryo1_sina import profile
OUT=HERE.parents[2]/'codex/sonuclar/tur31_kanit'

def run():
 db=server=b=None;checks=[];complete=False;delays=[]
 try:
  db=Database(empty=True);letters={};counts=defaultdict(int)
  def ok(s):checks.append(s);print('GEÇTİ: '+s,flush=True)
  def read(kind,key=None,person='K004'):return db.rpc(person,'oku',{'veri':kind,'hedef':key,'g':{}})['deger']
  def sql(q,args=None):
   with psycopg.connect(db.dsn) as c:
    x=c.execute(q,args);return x.fetchall() if x.description else []
  def event(code,g,targets=(),person='K004'):
   if person not in letters:letters[person]=db.rpc(person,'cihaz_kaydol',{'cihaz':'T31-SQL-'+person})
   now=str(db.rpc(person,'simdi',{}));dt=datetime.fromisoformat(now);counts[person]+=1
   hs=[{'tur':k,'kimlik':v,'surum':read(k,v,person).get('surum')} for k,v in targets]
   return {'olay_kimligi':f'{person}-{dt:%y%m%d}{counts[person]:04d}-{letters[person]}','kim':person,'adina':None,'cihaz':'MAS-'+person,'oldugu_an':now,'bildigi_son_hal_ani':now,'eylem_kodu':code,'eylem_versiyonu':1,'girdiler':g,'neyin_ustunde':hs,'kanit':[],'duzelttigi_olay':None,'giris_sekli':'LISTE','pc_ulasma_ani':None,'saat_dilimi':'+03:00','uygulama_surumu':'WEB-0.1.0','yol':'DISARIDA'}
  def send(code,g,targets=(),person='K004',reject=None):
   e=event(code,g,targets,person);r=db.rpc(person,'olay_ekle',{'olay':e})
   if reject:
    assert r['sonuc']=='REDDEDILDI' and r['kod']=='DURUM',r
    assert reject in r.get('mesaj',''),r
    assert 'Nesnenin durumu bu işleme uygun değil' not in r['mesaj']
    assert not sql('SELECT 1 FROM public.olaylar WHERE olay_kimligi=%s',(e['olay_kimligi'],))
   else:assert r['sonuc']=='BASARILI',r
   db.tick();return e,r
  day=datetime.fromisoformat(str(db.rpc('K001','simdi',{}))).date()
  send('PROJE.ACTIM',{'kod':'T31','ad':'Tur3.1 Kabul Kontrolü','sorumlu':'K004','baslangic_tarihi':str(day),'teslim_tarihi':str(day+timedelta(days=14))},person='K001')
  def create(name,**kw):
   e,_=send('IS.TANIMLADIM',{'isler':[{'islem':name,'birim':'IMALAT','nereye':'PROJE','proje':'T31','tur':'SURELI','tahmini_sure_dk':60,'onay_gerekli':True,'onay_beklet':False,**kw}]})
   return e['olay_kimligi']
  jobs=[create(n) for n in ['A','B','C']]
  for pos,j in enumerate(jobs,1):send('IS.ATADIM',{'kisi':'K017','sira':pos},[('IS',j),('LISTE','K017')])
  before={k:sql('SELECT motor.oku(%s,%s)',('YAYIN',k))[0][0] for k in ['isler','listeler','kisi_durumu','araliklar']}
  edit={'degisenler':{'is_tanimi':'Başlıktan ayrı iş açıklaması'}}
  e,_=send('IS.DEGISTIRDIM',edit,[('IS',jobs[1])])
  after={k:sql('SELECT motor.oku(%s,%s)',('YAYIN',k))[0][0] for k in before}
  before['isler'][jobs[1]]['is_tanimi']='Başlıktan ayrı iş açıklaması'
  assert before['isler'][jobs[1]]['surum']!=after['isler'][jobs[1]]['surum']
  for state in (before,after):
   for row in state['isler'].values():row.pop('surum',None)
   for row in state['kisi_durumu'].values():row.pop('son_hesap_ani',None)
  assert before==after,'Açıklama dışında iş/sıra/kişi/zaman değişti'
  (OUT/'duzenleme_farki.json').write_text(json.dumps({'korundu':True,'degisenler':['İş açıklaması','Değişen işin sürümü','Son hesap zamanı']},ensure_ascii=False,indent=2))
  r=db.rpc('K004','olay_ekle',{'olay':e});assert r.get('tekrar') is True
  assert sql('SELECT count(*) FROM public.olaylar WHERE olay_kimligi=%s',(e['olay_kimligi'],))[0][0]==1
  ok('Açıklama düzenlendi; başlık, sıralar, kişi hali ve emek aralıkları aynı; tekrarda tek olay')
  for bad,reason,path in [({'is_tanimi':42},'metin','degisenler.is_tanimi'),({'tur':'ANLIK'},'türü',''),({'birim':'OFIS'},'birimi',''),({'kisi_sayisi':2},'kişi sayısı','')]:
   _,r=send('IS.DEGISTIRDIM',{'degisenler':bad},[('IS',jobs[1])],reject=reason)
   if path:assert r['alan_hatalari'][0]['path']==path
  ok('Hatalı açıklama tipi ve düzenlenemeyen tür/birim/kişi sayısı somut nedenle reddedilir')
  invalid={'degisenler':{'on_isler':[jobs[1]]}}
  _,r=send('IS.DEGISTIRDIM',invalid,[('IS',jobs[1])],reject='birbirini bekler')
  assert r['alan_hatalari'][0]['path']=='degisenler.on_isler'
  send('IS.ONAYLADIM',{},[('IS',jobs[1])],reject='onayı beklemiyor')
  send('IS.REDDETTIM',{'not':'Düzeltin'},[('IS',jobs[1])],reject='onayı beklemiyor')
  send('IS.DEVAM_ONAYLADIM',{},[('IS',jobs[1])],reject='devam izni beklemiyor')
  send('IS.ATADIM',{'kisi':'K017','sira':4},[('IS',jobs[1]),('LISTE','K017')],reject='zaten')
  send('IS.DEVRETTIM',{'kimden':'K017','kime':'K017','kime_sira':2},[('IS',jobs[1]),('LISTE','K017')],reject='farklı')
  ok('Döngülü önkoşul, yanlış onay/ret/devam, tekrar atama ve kendine devir ayrı nedenler verir')
  # Gerçek SQL'in bekleyen hesap cevabı, sonra doğal motor devamı.
  server=ApiServer(db,HERE.parent/'build');threading.Thread(target=server.serve_forever,daemon=True).start()
  b=Browser();b.ws.settimeout(60);b.navigate(f'http://127.0.0.1:{server.server_port}')
  b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
  profile(b,'K004','Yönetici');page(b,'workshop')
  b.js("(()=>{const x=document.querySelector('[data-filter=unit]');x.value='IMALAT';x.dispatchEvent(new Event('change',{bubbles:true}));})()")
  b.wait("!document.querySelector('.loading-line')")
  original=db.rpc;attempts=[];armed=True;drained=threading.Event()
  def busy(person,name,params):
   nonlocal armed
   if name=='olay_ekle' and params['olay']['eylem_kodu']=='IS.SIRALADIM':
    if armed:
     armed=False
     sql('UPDATE motor.durum SET bekleyen_sinir=son_yayin_ani WHERE tek')
     def drain():time.sleep(2);db.tick();drained.set()
     threading.Thread(target=drain,daemon=True).start()
    r=original(person,name,params);attempts.append((params['olay'],r));return r
   return original(person,name,params)
  db.rpc=busy
  def reorder(position):
   click(b,f'[data-job="{jobs[1]}"] [data-action=job-menu]');b.wait("!!document.querySelector('.work-detail')")
   click(b,'dialog[open] [data-code="IS.SIRALADIM"]');b.wait("!!document.querySelector('[data-path=position] option[value=\"3\"]')&&!document.querySelector('dialog[open] [type=submit]').disabled")
   field(b,'position',position);start=time.monotonic();submit(b);b.wait("!document.querySelector('.loading-line')");delays.append(round(time.monotonic()-start,3))
  reorder(3);assert drained.wait(10)
  assert len(attempts)>1 and any(r.get('kod')=='HESAP_BEKLIYOR' for _,r in attempts)
  assert all(e==attempts[0][0] for e,_ in attempts)
  assert read('LISTE','K017')['isler'][2]['kimlik']==jobs[1]
  assert sql('SELECT count(*) FROM public.olaylar WHERE olay_kimligi=%s',(attempts[0][0]['olay_kimligi'],))[0][0]==1
  reorder(2);assert read('LISTE','K017')['isler'][1]['kimlik']==jobs[1]
  assert not b.js("document.querySelector('.form-error')?.textContent")
  db.rpc=original
  ok('Gerçek hesap beklemesinde pencere aynı olayla sürer; B üçüncü sonra ikinci sırada, tek olay/işlem')
  # Çalışan akışı, gece dahil gerçek zamanla; takvime ek mesai eklenmez.
  window=read('TELEFON',person='K017')['calisma_penceresi']
  now=datetime.fromisoformat(str(db.rpc('K017','simdi',{})))
  outside=not any(datetime.fromisoformat(a)<=now<datetime.fromisoformat(z) for a,z in window['mesai'])
  if read('TELEFON',person='K017')['son_hal']['durum']=='MESAI_DISI':send('MESAI.GIRDIM',{},person='K017')
  send('IS.BASLADIM',{},[('IS',jobs[0])],person='K017')
  send('IS.DEGISTIRDIM',{'degisenler':{'on_isler':[jobs[1]]}},[('IS',jobs[0])],reject='başlanmış')
  send('IS.DEGISTIRDIM',{'degisenler':{'is_tanimi':'Çalışırken açıklama güncellemesi'}},[('IS',jobs[0])])
  assert read('IS',jobs[0])['durum']=='CALISILIYOR'
  send('IS.TAMAMLADIM',{},[('IS',jobs[0])],person='K017')
  assert read('IS',jobs[0])['durum']=='ONAY_BEKLIYOR'
  send('IS.DEGISTIRDIM',{'degisenler':{'onay_gerekli':False}},[('IS',jobs[0])],reject='onay koşulları')
  send('IS.ONAYLADIM',{},[('IS',jobs[0])])
  send('IS.DEGISTIRDIM',edit,[('IS',jobs[0])],reject='tamamlanmış')
  send('IS.IPTAL_ETTIM',{'gerekce':'Test bitti'},[('IS',jobs[1])])
  send('IS.DEGISTIRDIM',edit,[('IS',jobs[1])],reject='iptal')
  assert read('TELEFON',person='K017')['calisma_penceresi']['mesai']==window['mesai']
  ok('Çalışırken açıklama, önkoşul koruması, teslim/onay, bitmiş/iptal iş koruması; takvim değişmedi')
  assert not sql("SELECT 1 FROM public.isleme_hatalari WHERE NOT coalesce((hal->>'cozuldu')::boolean,false)")
  (OUT/'gece_siniri.json').write_text(json.dumps({'gercek_saat':str(now),'mesai_disinda':outside,'takvim_degisti':False,'basla_teslim_onay':True},ensure_ascii=False,indent=2))
  complete=True
 finally:
  OUT.mkdir(parents=True,exist_ok=True)
  (OUT/'kapi_sonuc.json').write_text(json.dumps({'tamamlandi':complete,'kontroller':checks,'siralama_saniye':delays},ensure_ascii=False,indent=2))
  if b:
   if not complete:
    try:b.screenshot(OUT/'kapi_hata.png');(OUT/'kapi_hata.txt').write_text(b.js('document.body.innerText'))
    except Exception:pass
   b.close()
  if server:server.shutdown();server.server_close()
  if db:db.close()
if __name__=='__main__':run()
