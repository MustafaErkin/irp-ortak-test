"""Proje–Etap–Plan kabulü: gerçek SQL, ayrı firma, normal ekran eylemleri.
Sahte yerel Auth taşıması kullanılır; canlı firma/telefon değişmez.
"""
import json
from pathlib import Path
import threading
from tarayici import Browser,page,click,field,submit
from senaryo1_sina import profile,assign,approve,wait_state
from yerel_api import Database,ApiServer

OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/asama1_revize_kanit'

def verify_server(db,stage):
 from datetime import datetime
 from collections import defaultdict
 letters={};counts=defaultdict(int)
 def send(person,code,data,targets=()):
  if person not in letters:letters[person]=db.rpc(person,'cihaz_kaydol',{'cihaz':'proje-plan-sql-'+person})
  now=str(db.rpc(person,'simdi',{}));stamp=datetime.fromisoformat(now);counts[person]+=1
  hs=[{'tur':kind,'kimlik':key,'surum':db.rpc(person,'oku',{'veri':kind,'hedef':key,'g':{}})['deger'].get('surum')} for kind,key in targets]
  e={'olay_kimligi':f'{person}-{stamp:%y%m%d}{counts[person]:04d}-{letters[person]}','kim':person,'adina':None,'cihaz':'MAS-'+person,'oldugu_an':now,'bildigi_son_hal_ani':now,'eylem_kodu':code,'eylem_versiyonu':1,'girdiler':data,'neyin_ustunde':hs,'kanit':[],'duzelttigi_olay':None,'giris_sekli':'LISTE','pc_ulasma_ani':None,'saat_dilimi':'+03:00','uygulama_surumu':'WEB-0.1.0','yol':'DISARIDA'}
  r=db.rpc(person,'olay_ekle',{'olay':e});db.tick();return r
 r=send('K004','ETAP.DEGISTIRDIM',{'degisenler':{'sorumlu':'K001'}},[('ETAP',stage['kimlik'])]);assert r['kod']=='YETKI',r
 r=send('K004','ETAP.DEGISTIRDIM',{'degisenler':{'sorumlu':'K004'}},[('ETAP',stage['kimlik'])]);assert r['sonuc']=='BASARILI',r
 r=send('K001','ETAP.DEGISTIRDIM',{'degisenler':{'sorumlu':'K001'}},[('ETAP',stage['kimlik'])]);assert r['sonuc']=='BASARILI',r
 r=send('K004','ETAP.DEGISTIRDIM',{'degisenler':{'ad':stage['ad']+' Kontrol','sorumlu':'K001'}},[('ETAP',stage['kimlik'])]);assert r['sonuc']=='BASARILI',r
 r=send('K001','PROJE.ACTIM',{'kod':'PP-01','ad':'Eski Kod'});assert r['kod']=='DURUM' and r['alan_hatalari'][0]['path']=='kod',r
 r=send('K001','ETAP.TANIMLADIM',{'proje':'PP-02','ad':'Kapalı Etap','birim':stage['birim'],'sorumlu':'K004','baslangic':'2026-12-01','bitis':'2026-12-02','hedef_saat':8});assert r['kod']=='DURUM' and 'kapalı' in r['mesaj'],r
 r=send('K041','PROJE.ACTIM',{'kod':'YETKISIZ','ad':'Açılamaz'});assert r['kod']=='YETKI' and 'alan_hatalari' not in r,r
 # Çalışan başkasının ücretini yeni okuma kapısından da alamaz.
 try:
  employee=db.rpc('K041','oku',{'veri':'WEB_KISI','hedef':'K004','g':{}})['deger'];assert 'brut_maas' not in employee,employee
 except PermissionError:pass
 manager=db.rpc('K004','oku',{'veri':'WEB_KISI','hedef':'K017','g':{}})['deger'];assert 'brut_maas' not in manager,manager

def run():
 db=server=b=None
 checks=[];completed=False
 try:
  db=Database(empty=True);server=ApiServer(db,Path(__file__).resolve().parents[1]/'build')
  threading.Thread(target=server.serve_forever,daemon=True).start();b=Browser(width=1440,height=1000);b.ws.settimeout(60)
  b.navigate(f'http://127.0.0.1:{server.server_port}/');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
  def ok(name):checks.append(name);print('GEÇTİ: '+name,flush=True)
  def open_op(code):b.wait("!document.querySelector('#dialogs dialog')");click(b,'[data-code="'+code+'"]');b.wait("!!document.querySelector('dialog[open] form')")
  def text():return b.js('document.body.innerText')
  def create(code,name):
   open_op('PROJE.ACTIM');field(b,'kod',code);field(b,'ad',name);field(b,'musteri','Deneme Müşterisi');field(b,'sorumlu','K004');field(b,'teslim_tarihi','15122026');submit(b)
   b.wait('document.querySelector(".project-summary h2")?.textContent==='+json.dumps(name),40)
   assert not b.js("!!document.querySelector('dialog[open]')")
  def select_text(path,txt):
   value=b.js("[...document.querySelector('[data-path="+path+"]').options].find(o=>o.textContent.includes("+json.dumps(txt)+"))?.value")
   assert value,(path,txt);field(b,path,value)
  def stage(name,unit,start,end):
   open_op('ETAP.TANIMLADIM');assert b.js("document.querySelector('[data-path=proje]').readOnly")
   field(b,'ad',name);select_text('birim',unit);field(b,'sorumlu','K004');field(b,'baslangic',start);field(b,'bitis',end);field(b,'hedef_saat',8);submit(b)
   b.wait(json.dumps(name)+"===document.querySelector('.project-timeline-row:last-child strong')?.textContent || [...document.querySelectorAll('.project-timeline-row strong')].some(x=>x.textContent==="+json.dumps(name)+")")
  page(b,'projects');open_op('PROJE.ACTIM');click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=kod]').getAttribute('aria-invalid')==='true'");click(b,'dialog[open] [data-cancel]');ok('Boş proje alanları doğru yerde vurgulanıyor')
  create('PP-01','Proje Plan Denemesi');ok('Proje başarıdan sonra açılıyor; etap formu kendiliğinden açılmıyor')
  assert b.js("document.querySelectorAll('[data-code=\"ETAP.TANIMLADIM\"]').length")==1
  assert b.js("[...document.querySelectorAll('.tabs .tab')].map(x=>x.textContent)")==['Etaplar ve Plan','İşler','Ekip','Belgeler']
  ok('Tek Etap Ekle ve dört sekme')
  open_op('ETAP.TANIMLADIM');field(b,'ad','Ofis Hazırlığı');select_text('birim','Ofis');field(b,'baslangic','10.12.2026');field(b,'bitis','09.12.2026');field(b,'hedef_saat',8)
  assert b.js("document.querySelector('[data-date-picker=baslangic]').value")=='2026-12-10'
  assert b.js("document.querySelector('[data-date-picker=baslangic]').tabIndex")==-1
  b.js("document.querySelector('[data-path=baslangic]').focus()")
  b.call('Input.dispatchKeyEvent',type='keyDown',key='Tab',code='Tab',windowsVirtualKeyCode=9);b.call('Input.dispatchKeyEvent',type='keyUp',key='Tab',code='Tab',windowsVirtualKeyCode=9)
  assert b.js("document.activeElement.dataset.path")=='bitis'
  ok('Elle tarih takvime eşitlenir; Tab doğrudan sonraki alana gider')
  click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=bitis]').getAttribute('aria-invalid')==='true'");assert 'önce olamaz' in text();click(b,'dialog[open] [data-cancel]');ok('Geçersiz etap aralığı doğru mesaj ve alanla engelleniyor')
  stage('Ofis Hazırlığı','Ofis','07122026','10122026');stage('Atölye Hazırlığı','Atölye','11122026','15122026');ok('İki etap, mevcut ay dışında ve onaysızken Gantt görünür')
  b.js("document.querySelector('#project-period').scrollIntoView({block:'center'})");b.screenshot(OUT/'01_hazirlanan_plan.png')
  b.js("document.querySelector('#project-period [name=bas]').value='01.01.2027';document.querySelector('#project-period [name=bit]').value='31.01.2027';document.querySelector('#project-period [name=bit]').dispatchEvent(new Event('input',{bubbles:true}))");click(b,'#project-period [type=submit]');b.wait("document.body.innerText.includes('Bu Dönemde Etap Yok')");click(b,'[data-action=project-range]');b.wait("document.querySelectorAll('.project-timeline-row').length===2");ok('Dönem filtresi ve tüm projeye dönüş çalışır')
  stages=db.rpc('K001','oku',{'veri':'ETAPLAR','hedef':'PP-01','g':{}})['deger'];first=next(e for e in stages if e['ad']=='Ofis Hazırlığı');second=next(e for e in stages if e['ad']=='Atölye Hazırlığı')
  click(b,'[data-action=stage-plan-task][data-id="'+second['kimlik']+'"]');b.wait("!!document.querySelector('#task-editor')")
  assert b.js("document.querySelector('[data-path=ad]').value")=='Atölye Hazırlığı Etabı Planlama'
  assert b.js("document.querySelector('[data-path=etap]').value")==second['kimlik'];ok('İkinci etap doğru görev bağlamına taşınıyor')
  field(b,'teslim_tarihi','06122026');assign(b);ok('Planlama görevi normal atama ve gözden geçirme yoluyla gönderiliyor')
  page(b,'projects');open_op('PROJE.KAPATTIM');assert not b.js("!!document.querySelector('#operation-target')");click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('dialog[open] .form-error')?.textContent.includes('Açık işler')");assert 'Atölye Hazırlığı Etabı Planlama' in text();click(b,'dialog[open] [data-cancel]');ok('Açık görev kapanışı engelliyor ve adı gösteriliyor')
  open_op('PLAN.ONAYLADIM');assert 'Ofis Hazırlığı' in b.js("document.querySelector('#plan-review-host').innerText");submit(b);b.wait("document.querySelector('.project-history summary')?.textContent.includes('(1)')");ok('İlk plan onayı ve geçmişi')
  profile(b,'K004','Yönetici');page(b,'tasks');b.wait("document.body.innerText.includes('Atölye Hazırlığı Etabı Planlama')")
  task=db.rpc('K004','oku',{'veri':'WEB_GOREVLER','hedef':None,'g':{}})['deger'];task=next(t for t in task if t['ad']=='Atölye Hazırlığı Etabı Planlama')
  click(b,'tr[data-id="'+task['kimlik']+'"]');click(b,'[data-code="GOREV.KABUL_ETTIM"]');b.wait("!document.querySelector('[data-code=\"GOREV.KABUL_ETTIM\"]')");b.wait("document.querySelector('[data-tab=open]')?.textContent==='İşlerim (1)'");ok('Diğer rol görevini görüyor ve kabul ediyor; sekme sayacı güncellenir')
  page(b,'projects');click(b,'[data-action=project-open][data-id="PP-01"]');open_op('ETAP.DEGISTIRDIM');assert not b.js("[...document.querySelector('[data-path=\"degisenler.sorumlu\"]').options].some(o=>o.value==='K001')");assert not b.js("!!document.querySelector('#operation-target')");assert not b.js("!!document.querySelector('[data-path=\"degisenler.proje\"]')");field(b,'degisenler.bitis','12122026');field(b,'degisenler.hedef_saat',12);submit(b);b.wait("document.body.innerText.includes('Bitiş, Hedef emek değişti')");ok('Yönetici etap düzenliyor; hedef tekrar sorulmuyor ve farklar görünüyor')
  open_op('PLAN.ONAYLADIM');assert '*' in b.js("document.querySelector('[data-path=gerekce]').closest('label').innerText");click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=gerekce]').getAttribute('aria-invalid')==='true'");field(b,'gerekce','Etap süresi güncellendi.');submit(b);b.wait("document.querySelector('.project-history summary')?.textContent.includes('(2)')");click(b,'.project-history>summary');b.screenshot(OUT/'02_plan_gecmisi.png');ok('Gerekçeli revizyon; ilk ve son plan korunuyor')
  profile(b,'K001','CEO');page(b,'projects');click(b,'[data-action=project-list]') if b.js("!!document.querySelector('[data-action=project-list]')") else None
  create('PP-02','Proje Plan Denemesi');open_op('PROJE.KAPATTIM');submit(b);b.wait("document.querySelector('.project-summary')?.textContent.includes('Kapalı')");assert not b.js("!!document.querySelector('[data-code=\"ETAP.TANIMLADIM\"]')");click(b,'[data-action=project-list]');click(b,'[data-action=project-filter][data-filter=closed]');assert 'PP-02' in text();ok('Kapalı proje geçmişte bulunuyor; yeni etap eylemi yok')
  open_op('PROJE.ACTIM');field(b,'kod','PP-02');field(b,'ad','Aynı Kod');click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=kod]').getAttribute('aria-invalid')==='true'");assert 'daha önce kullanılmış' in text();click(b,'dialog[open] [data-cancel]');ok('Kapalı projenin kodu tekrar kullanılamıyor; Kod alanı vurgulu')
  click(b,'[data-action=project-filter][data-filter=open]');click(b,'[data-action=project-open][data-id="PP-01"]');click(b,'[data-action=tab][data-tab=team]');open_op('PROJE.ERISIM_VERDIM');field(b,'kisi','K041');field(b,'gerekce','Proje belgeleri için.');submit(b);b.wait("!!document.querySelector('[data-action=project-remove-access][data-id=K041]')");click(b,'[data-action=project-remove-access][data-id=K041]');assert b.js("document.querySelector('[data-path=kisi]').readOnly");field(b,'gerekce','Deneme erişimi tamamlandı.');submit(b);b.wait("!document.querySelector('[data-action=project-remove-access][data-id=K041]')");ok('Ekipten ek erişim veriliyor ve ilgili kişi satırından kaldırılıyor')
  for tab in ['jobs','objects','stages']:click(b,'[data-action=tab][data-tab='+tab+']')
  # Sidebar explicit click always returns to the section root.
  click(b,'.nav-link[data-page=projects]');b.wait("!!document.querySelector('[data-action=project-filter]')")
  click(b,'[data-action=project-open][data-id="PP-01"]');ok('Aynı sol menüye tekrar tıklama proje listesine döner')
  assert not b.errors,b.errors
  ok('İşler/Ekip/Belgeler/Plan sekmelerinde JavaScript hatası yok')
  open_op('PROJE.DEGISTIRDIM');assert not b.js("!!document.querySelector('#operation-target')");field(b,'degisenler.ad','Güncellenen Proje');submit(b);b.wait("document.querySelector('.project-summary h2')?.textContent==='Güncellenen Proje'");ok('Seçili proje adı düzenlenir')
  open_op('PROJE.KOD_DEGISTIRDIM');assert not b.js("!!document.querySelector('[data-path=ek]')");field(b,'kod','PP-03');field(b,'gerekce','İşletme kodu düzeltildi.');submit(b);b.wait("document.querySelector('.project-summary')?.textContent.includes('PP-03')");ok('İşletmenin proje kodu değişir; aynı proje ve etaplar korunur')
  click(b,'.nav-link[data-page=projects]');b.wait("!!document.querySelector('[data-action=project-filter]')")
  b.js('''window.originalFetch=window.fetch;window.failProjectRead=false;window.fetch=async(...a)=>{const body=JSON.parse(a[1]?.body||'{}');if(window.failProjectRead&&body.veri==='PROJELER')throw new TypeError('Simulated read outage');const r=await window.originalFetch(...a);if(body.olay?.eylem_kodu==='PROJE.ACTIM')window.failProjectRead=true;return r;};''')
  open_op('PROJE.ACTIM');field(b,'kod','PP-DELAY');field(b,'ad','Geciken Liste');field(b,'teslim_tarihi','15122026');submit(b)
  b.wait("document.body.innerText.includes('Proje İşlemi Alındı')",60)
  assert 'Geciken Liste' in text();assert not b.js("!!document.querySelector('.project-summary')")
  b.js('window.fetch=window.originalFetch;window.failProjectRead=false;')
  click(b,'[data-action=project-refresh]');b.wait("document.querySelector('.project-summary h2')?.textContent==='Geciken Liste'",40)
  ok('Kabulden sonra liste kesilince doğru proje bekleme bilgisi ve tekrar açmadan sonuç')
  click(b,'.nav-link[data-page=projects]');b.wait("!!document.querySelector('[data-action=project-filter]')")
  b.js('''window.originalFetch=window.fetch;window.lostResponses=0;window.fetch=async(...a)=>{const body=JSON.parse(a[1]?.body||'{}');const r=await window.originalFetch(...a);if(body.olay?.eylem_kodu==='PROJE.ACTIM'&&window.lostResponses++<2)throw new TypeError('Simulated lost response');return r;};''')
  open_op('PROJE.ACTIM');field(b,'kod','PP-LOST');field(b,'ad','Yanıt Kaybı');field(b,'teslim_tarihi','15122026');click(b,'dialog [type=submit]')
  b.wait("document.querySelector('dialog [type=submit]')?.textContent==='Sonucu Doğrula'",90)
  click(b,'dialog [type=submit]');b.wait("document.querySelector('.project-summary h2')?.textContent==='Yanıt Kaybı'",60)
  b.js('window.fetch=window.originalFetch')
  assert len([p for p in db.rpc('K001','oku',{'veri':'PROJELER'})['deger'] if p['kod']=='PP-LOST'])==1
  ok('İki kayıp yanıt sonrası aynı formdan doğrulama; yalnız bir proje')
  assert len(db.rpc('K001','oku',{'veri':'ETAPLAR','hedef':'PP-01','g':{}})['deger'])==2
  verify_server(db,second)
  ok('SQL: yinelenen kod ve kapalı proje doğru nedenle reddedilir; yetki sınırı korunur')
  profile(b,'K004','Yönetici');page(b,'tasks');click(b,'[data-action=tab][data-tab=open]');click(b,'tr[data-id="'+task['kimlik']+'"]');click(b,'[data-code="GOREV.TAMAMLADIM"]');b.wait("!!document.querySelector('dialog[open] form')");submit(b);wait_state(db,'GOREV',task['kimlik'],'ONAY_BEKLIYOR','K004');ok('Plan onayından ayrı görev teslimi dosyasız yapılır')
  profile(b,'K001','CEO');page(b,'approvals');approve(b,db,'GOREV',task['kimlik'],person='K001');page(b,'projects');click(b,'[data-action=project-open][data-id="PP-01"]');open_op('PROJE.KAPATTIM');submit(b);b.wait("document.querySelector('.project-summary')?.textContent.includes('Kapalı')");ok('Görev teslimi onaylanınca proje kapanır; plan geçmişi kalır')
  completed=True
 finally:
  if b:
   if not completed:
    print('SON EKRAN:',b.js('document.body.innerText.slice(-2500)'),flush=True);b.screenshot(OUT/'hata.png')
   b.close()
  if server:server.shutdown();server.server_close()
  if db:db.close()
  OUT.mkdir(parents=True,exist_ok=True);(OUT/'sonuc.json').write_text(json.dumps({'tamamlandi':completed,'gecen':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':run()
