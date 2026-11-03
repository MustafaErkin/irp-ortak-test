"""MVP çalışan telefonu: gerçek motor + yetkili ve tutarlı okuma kapısı.
Geçici yerel veritabanı; canlı firma/telefon üzerinde test verisi oluşturmaz.
Dart kabul testinin kullanacağı gerçek önce/sonra paketlerini de üretir.
"""
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json, sys, threading, time
import psycopg
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from yerel_api import Database
ROOT=HERE.parents[2]
OUT=ROOT/'codex/sonuclar/telefon_calisan_mvp'
FIXTURE=ROOT/'istemci/uygulama/test/fikstur/telefon_esitle_sql.json'

def run():
 db=None;checks=[];cases=[];complete=False
 def ok(s): checks.append(s);print('GEÇTİ: '+s,flush=True)
 try:
  db=Database(empty=True);letters={};counts=defaultdict(int)
  def sql(q,args=None):
   with psycopg.connect(db.dsn) as c:
    x=c.execute(q,args);return x.fetchall() if x.description else []
  def rpc(person,name,params={}):return db.rpc(person,name,params)
  def packet(person='K017',ids=()):
   d=db.driver()
   try:return d._cagir('SELECT public.telefon_esitle(%s)',(list(ids),),kisi=person)
   finally:d.kapat()
  def read(kind,key=None,person='K004'):return rpc(person,'oku',{'veri':kind,'hedef':key,'g':{}})['deger']
  def event(code,g={},targets=(),person='K004'):
   if person not in letters:letters[person]=rpc(person,'cihaz_kaydol',{'cihaz':'PHONE-MVP-'+person})
   now=(datetime.fromisoformat(str(rpc(person,'simdi')))+timedelta(seconds=1)).isoformat()
   sql('SELECT test.saat(%s,%s,false)',(now,now))
   dt=datetime.fromisoformat(now);counts[person]+=1
   hs=[{'tur':k,'kimlik':v,'surum':None if person in ('K017','K031') else read(k,v,person).get('surum')} for k,v in targets]
   return {'olay_kimligi':f'{person}-{dt:%y%m%d}{counts[person]:04d}-{letters[person]}','kim':person,'adina':None,'cihaz':('TEL-' if person in ('K017','K031') else 'MAS-')+person,'oldugu_an':now,'bildigi_son_hal_ani':now,'eylem_kodu':code,'eylem_versiyonu':1,'girdiler':g,'neyin_ustunde':hs,'kanit':[],'duzelttigi_olay':None,'giris_sekli':'LISTE','pc_ulasma_ani':None,'saat_dilimi':'+03:00','uygulama_surumu':'MVP-TEST','yol':'DISARIDA'}
  def send(code,g={},targets=(),person='K004'):
   e=event(code,g,targets,person);r=rpc(person,'olay_ekle',{'olay':e});assert r['sonuc']=='BASARILI',r
   db.tick();return e,r
  day=datetime.fromisoformat(str(rpc('K001','simdi'))).date()
  # Sabit mesai sınırını/saat geçişini sınamadan bağımsız tut; gerçek motor aynı saatle işler.
  sql('SELECT test.saat(%s,%s,false)',(f'{day}T11:00:00+03:00',f'{day}T11:00:00+03:00'))
  send('PROJE.ACTIM',{'kod':'PHONE','ad':'Telefon Gerçek Motor Denemesi','sorumlu':'K004','baslangic_tarihi':str(day),'teslim_tarihi':str(day+timedelta(days=14))},person='K001')
  def create(name,**kw):
   e,_=send('IS.TANIMLADIM',{'isler':[{'islem':name,'birim':'IMALAT','nereye':'PROJE','proje':'PHONE','tur':'SURELI','tahmini_sure_dk':60,'onay_gerekli':False,**kw}]})
   return e['olay_kimligi']
  jobs=[create('Onaysız İş'),create('Bekletmeyen Onay',onay_gerekli=True,onay_beklet=False),create('Bekleten Onay',onay_gerekli=True,onay_beklet=True),create('Sıradaki İş')]
  for pos,j in enumerate(jobs,1):send('IS.ATADIM',{'kisi':'K017','sira':pos},[('IS',j),('LISTE','K017')])
  def case(name,code,g={},job=None,person='K017'):
   before=packet(person);e=event(code,g,[('IS',job)] if job else [],person)
   receipt=rpc(person,'olay_ekle',{'olay':e});assert receipt['sonuc']=='BASARILI',receipt
   db.tick();after=packet(person,[e['olay_kimligi']]);assert after['olay_sonuclari'][e['olay_kimligi']]=='TAMAMLANDI',after
   cases.append({'ad':name,'once':before,'olay':e,'makbuz':receipt,'sonra':after})
   return after['telefon']['deger']
  if read('TELEFON',person='K017')['son_hal']['durum']=='MESAI_DISI':case('Mesai Girişi','MESAI.GIRDIM')
  case('Başla','IS.BASLADIM',job=jobs[0])
  case('Mola','IS.MOLA_VERDIM',job=jobs[0]);case('Moladan Devam','IS.DEVAM_ETTIM',job=jobs[0])
  case('Duruş','IS.ARIZA_BILDIRDIM',{'neden':'DURUS_NEDENI.MAKINE_CNC'},job=jobs[0])
  assert packet()['telefon']['deger']['son_hal']['devam_izni'] is False
  send('IS.DEVAM_ONAYLADIM',{},[('IS',jobs[0])],person='K009')
  assert packet()['telefon']['deger']['son_hal']['devam_izni'] is True
  case('Duruştan Devam','IS.DEVAM_ETTIM',job=jobs[0])
  p=case('Onaysız Teslim','IS.TAMAMLADIM',job=jobs[0]);assert jobs[0] not in p['liste'] and p['son_hal']['durum']=='CALISMIYOR'
  case('İkinci İş Başla','IS.BASLADIM',job=jobs[1])
  p=case('Bekletmeyen Teslim','IS.TAMAMLADIM',job=jobs[1]);assert jobs[1] not in p['liste'] and p['son_hal']['durum']=='CALISMIYOR'
  case('Üçüncü İş Başla','IS.BASLADIM',job=jobs[2])
  p=case('Bekleten Teslim','IS.TAMAMLADIM',job=jobs[2]);assert p['son_hal']['durum']=='ONAY_BEKLIYOR'
  send('IS.ONAYLADIM',{},[('IS',jobs[2])],person='K009')
  p=packet()['telefon']['deger'];assert p['son_hal']['durum']=='CALISMIYOR' and p['liste'][0]==jobs[3]
  case('Dördüncü Başla','IS.BASLADIM',job=jobs[3])
  case('Dördüncü Teslim','IS.TAMAMLADIM',job=jobs[3])
  instant=create('Anlık İş',tur='ANLIK')
  prerequisite=create('Önkoşul Havuzda')
  locked=create('Önkoşula Bağlı',on_isler=[prerequisite])
  for pos,j in enumerate([instant,locked],1):send('IS.ATADIM',{'kisi':'K017','sira':pos},[('IS',j),('LISTE','K017')])
  p=case('Anlık Teslim Sonrası Ön İş Bekleme','IS.TAMAMLADIM',job=instant)
  assert p['liste'][0]==locked and p['isler'][locked]['kilitli'] is True
  ok('Başla, mola, devam, duruş, lider izni ve üç teslim türü gerçek motorda doğrulandı')
  # Saha da aynı çalışan kapısını kullanır; yalnız yetkili işlerini görür.
  field=create('Saha Montajı',birim='KURULUM',onay_gerekli=True,onay_beklet=True)
  send('IS.ATADIM',{'kisi':'K031','sira':1},[('IS',field),('LISTE','K031')])
  if read('TELEFON',person='K031')['son_hal']['durum']=='MESAI_DISI':case('Saha Mesai','MESAI.GIRDIM',person='K031')
  case('Saha Başla','IS.BASLADIM',job=field,person='K031')
  case('Saha Mola','IS.MOLA_VERDIM',job=field,person='K031')
  assert set(packet('K031')['telefon']['deger']['isler']).isdisjoint(jobs)
  assert packet('K031',[cases[0]['olay']['olay_kimligi']])['olay_sonuclari'][cases[0]['olay']['olay_kimligi']]=='BULUNAMADI'
  p=packet('K031')['telefon']['deger'];assert p['isler'][field]['proje_adi']=='Telefon Gerçek Motor Denemesi'
  ok('Saha ayrı kişi/iş görünürlüğü, başkasının olayı gizliliği ve proje adı doğrulandı')
  case('Saha Devam','IS.DEVAM_ETTIM',job=field,person='K031')
  case('Saha Teslim','IS.TAMAMLADIM',job=field,person='K031')
  send('IS.REDDETTIM',{'not':'Montajı tekrar kontrol edin'},[('IS',field)],person='K009')
  case('Saha Yeniden İşleme','IS.DEVAM_ETTIM',job=field,person='K031')
  case('Saha Yeniden Teslim','IS.TAMAMLADIM',job=field,person='K031')
  # Yayın yazarı kilidi tutarken okuma bekler; son hal/olay sonucu yarım karışmaz.
  lock=psycopg.connect(db.dsn);lock.execute('SELECT pg_advisory_xact_lock(202620,1)')
  entered=threading.Event();done=threading.Event();errors=[]
  def reader():
   entered.set()
   try:packet()
   except Exception as e:errors.append(type(e).__name__)
   finally:done.set()
  t=threading.Thread(target=reader);t.start();entered.wait();time.sleep(.15)
  assert not done.is_set(),'Okuma yayın kilidini atladı'
  lock.commit();lock.close();assert done.wait(10);t.join();assert not errors,errors
  ok('Eşzamanlı yayın sırasında paket yarım durum okumaz; kilit kalkınca devam eder')
  # Salt okunurluk ve rol sınırı.
  before=sql('SELECT count(*) FROM public.olaylar')[0][0];packet();assert before==sql('SELECT count(*) FROM public.olaylar')[0][0]
  for role,expected in [('anon',False),('authenticated',True),('service_role',False)]:
   assert sql("SELECT has_function_privilege(%s,'public.telefon_esitle(text[])','EXECUTE')",(role,))[0][0]==expected
  assert not sql("SELECT 1 FROM public.isleme_hatalari WHERE NOT coalesce((hal->>'cozuldu')::boolean,false)")
  ok('Kapı olay üretmez; yalnız authenticated yetkisi; motor işleme hatası yok')
  FIXTURE.write_text(json.dumps({'kaynak':'Gerçek yerel SQL162 ve motor; sentetik firma', 'vakalar':cases},ensure_ascii=False,indent=2))
  complete=True
 finally:
  OUT.mkdir(parents=True,exist_ok=True);(OUT/'sql_sonuc.json').write_text(json.dumps({'tamamlandi':complete,'kontroller':checks,'vaka_sayisi':len(cases)},ensure_ascii=False,indent=2))
  if db:db.close()
if __name__=='__main__':run()
