"""Tur 2.1: ayrı firma, gerçek SQL, normal arayüz ve denetimli yayın gecikmesi."""
from datetime import date,timedelta
from pathlib import Path
import json,sys,threading,time,psycopg
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tarayici import Browser,page,click,field,submit
from yerel_api import Database,ApiServer
from senaryo1_sina import profile,record,wait_state,assign,approve
OUT=HERE.parents[2]/'codex/sonuclar/tur21_kanit'

def run():
 db=server=b=None;passed=[];complete=False;release=threading.Event();release.set()
 today=date.today();last=today+timedelta(days=25);end=(today+timedelta(days=35)).strftime('%d.%m.%Y')
 try:
  db=Database(empty=True);server=ApiServer(db,HERE.parent/'build');threading.Thread(target=server.serve_forever,daemon=True).start()
  b=Browser();b.ws.settimeout(60);b.navigate(f'http://127.0.0.1:{server.server_port}/');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
  def ok(name):passed.append(name);print('GEÇTİ: '+name,flush=True)
  def op(code):click(b,'[data-code="'+code+'"]');b.wait("!!document.querySelector('dialog[open] form')")
  def read(veri,hedef=None,g=None,person='K004'):return db.rpc(person,'oku',{'veri':veri,'hedef':hedef,'g':g or {}})['deger']
  def raw(query,params=()):
   d=db.driver()
   try:return d._cagir(query,params,kontrol=True)
   finally:d.kapat()
  def preview(rows):return read('ATAMA_YUKU',g={'satirlar':rows})
  sample={'kisi':'K041','zaman_degeri':60,'teslim_tarihi':last.isoformat()}
  before=raw('SELECT count(*) FROM public.olaylar');work=preview([sample]);assert raw('SELECT count(*) FROM public.olaylar')==before
  assert len(work['haftalar'])==4 and all(abs(float(w['yeni'])-15)<1e-8 for w in work['haftalar']),work
  assert all(abs(float(w['kapasite'])-45)<1e-8 for w in work['haftalar']),work
  combined=preview([sample,{**sample,'zaman_degeri':2,'teslim_tarihi':(today+timedelta(days=1)).isoformat()}]);assert len(combined['haftalar'])==4;assert abs(float(combined['haftalar'][0]['yeni'])-17)<1e-8
  assert abs(sum(float(w['yeni']) for w in combined['haftalar'])-62)<1e-8
  try:read('ATAMA_YUKU',g={'satirlar':[sample]},person='K041');raise AssertionError('Çalışana atama önizleme izni açıldı')
  except PermissionError:pass
  ok('60 saat / 20 eşit mesai günü = haftada 15; aynı haftada birleştirme, toplam korunumu, salt okuma ve yetki')
  # A half workday changes the weights without changing the engine formula.
  page(b,'calendar');op('GUN.TANIMLADIM');field(b,'tarih',(today+timedelta(days=2)).strftime('%d.%m.%Y'));field(b,'tur','YARIM_GUN');field(b,'ad','Yarım Mesai');field(b,'mesai_baslangic','08:00');field(b,'mesai_bitis','12:00')
  # Required empty array is an explicit no-break calendar choice.
  click(b,'[data-add=sabit_molalar]');field(b,'sabit_molalar.0.ad','Mola');field(b,'sabit_molalar.0.bas','10:00');field(b,'sabit_molalar.0.bit','10:15');submit(b)
  uneven=preview([sample]);expected_first=60*(36+3.75)/(171+3.75)
  assert abs(float(uneven['haftalar'][0]['yeni'])-expected_first)<1e-7,uneven
  assert abs(sum(float(x['yeni']) for x in uneven['haftalar'])-60)<1e-7
  page(b,'calendar');op('GUN.KALDIRDIM');field(b,'tarih',(today+timedelta(days=2)).strftime('%d.%m.%Y'));submit(b)
  ok('Normal mesai uzunluğu farklı günde 60 saat doğru ağırlıkla dağıldı; takvim geri alındı')
  for code,name in [('T21-A','Tur 2.1 Projesi'),('T21-B','İkinci Proje')]:
   page(b,'projects');
   if b.js("!!document.querySelector('[data-action=project-list]')"):click(b,'[data-action=project-list]')
   op('PROJE.ACTIM');field(b,'kod',code);field(b,'ad',name);field(b,'sorumlu','K004');field(b,'teslim_tarihi',end);submit(b);b.wait("document.querySelector('.project-summary h2')?.textContent==="+json.dumps(name),40)
   op('ETAP.TANIMLADIM');field(b,'ad',name+' Etabı');field(b,'birim','MEK_TASARIM');field(b,'sorumlu','K004');field(b,'bitis',end);field(b,'hedef_saat',20);submit(b)
  stageA=read('ETAPLAR','T21-A')[0]['kimlik'];stageB=read('ETAPLAR','T21-B')[0]['kimlik']
  profile(b,'K004','Yönetici');page(b,'assign');assert not b.js("!!document.querySelector('[data-search]')");assert not b.js("!!document.querySelector('.assignment-empty p,.assignment-empty h2')")
  click(b,'[data-action=assign-add]')
  for key in ['proje','kisi','teslim_tarihi','zaman_degeri','zorluk','onaylayan']:assert b.js('document.querySelector(\'[data-path='+key+']\').value')==''
  click(b,'[data-action=assign-review]');b.wait("!!document.querySelector('#task-editor [aria-invalid=true]')");assert not b.js("!!document.querySelector('dialog[open]')")
  field(b,'ad','Uzun Etap Dışı İş');field(b,'proje','T21-A');assert stageB not in b.js("[...document.querySelector('[data-path=etap]').options].map(x=>x.value)");assert b.js("document.querySelector('[data-path=etap]').selectedOptions[0].textContent")=='Seçiniz';field(b,'etap','@none')
  field(b,'kisi','K041');assert 'K041' not in b.js("[...document.querySelector('[data-path=onaylayan]').options].map(x=>x.value)")
  field(b,'teslim_tarihi',last.strftime('%d.%m.%Y'));field(b,'zaman_degeri',60);field(b,'zorluk',2);field(b,'onaylayan','K004')
  assert 'Tur 2.1 Projesi' in b.js("document.querySelector('.draft-project').textContent")
  click(b,'[data-action=assign-add]');assert b.js("document.querySelector('[data-path=proje]').value")==''
  field(b,'ad','Etaplı Kontrol');field(b,'proje','T21-B');field(b,'etap',stageB);field(b,'kisi','K041');field(b,'teslim_tarihi',(today+timedelta(days=8)).strftime('%d.%m.%Y'));field(b,'zaman_degeri',2);field(b,'zorluk',2);field(b,'onay_gerekli',False)
  click(b,'[data-action=assign-review]');b.wait("!!document.querySelector('[data-assign]')",40);assert 'Etap Dışı' in b.js('document.body.innerText');click(b,'.assignment-capacity summary');b.screenshot(OUT/'01_atama_ozeti.png');assert len(b.js("[...document.querySelectorAll('.assignment-capacity tbody tr')].map(x=>x.innerText)"))==4
  click(b,'[data-assign]');b.wait("!document.querySelector('dialog[open]')",40);jobs=read('WEB_GOREVLER');task=next(t for t in jobs if t['ad']=='Uzun Etap Dışı İş');assert not task.get('etap') and task['proje']=='T21-A'
  ok('İki proje, boş yeni iş, yıldız/alan hatası, Etap Dışı ve projeye göre etap, özet ve gerçek atama')
  profile(b,'K041','Ofis Çalışanı');page(b,'tasks');click(b,'tr[data-id="'+task['kimlik']+'"]');b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')")
  # Real engine publication is held by the local harness for >15s; no fake success response.
  release.clear();tick=db.tick;raw('SELECT test.butce(1,0.000001)')
  def slow_tick():release.wait(40);tick()
  db.tick=slow_tick
  before_accept=sum(code=='GOREV.KABUL_ETTIM' for _,code,_ in db.events)
  click(b,'[data-code="GOREV.KABUL_ETTIM"]');b.wait("document.querySelector('[data-code=\"GOREV.KABUL_ETTIM\"]')?.disabled===true")
  click(b,'[data-action=task-section][data-section=notes]');time.sleep(2)
  assert b.js("document.querySelector('[data-code=\"GOREV.KABUL_ETTIM\"]')?.disabled===true")
  assert 'İşleminiz sürüyor, lütfen bekleyin.' in b.js('document.body.innerText')
  assert b.js("Math.abs(document.querySelector('.loading-line').getBoundingClientRect().top-document.querySelector('.topbar').getBoundingClientRect().bottom)<1")
  b.screenshot(OUT/'02_bekleme.png');time.sleep(15)
  assert b.js("document.querySelector('[data-code=\"GOREV.KABUL_ETTIM\"]')?.disabled===true")
  b.js("document.querySelector('[data-code=\"GOREV.KABUL_ETTIM\"]').click()")
  raw('SELECT test.butce(NULL,NULL)');release.set();db.tick=tick;b.wait("!document.querySelector('.loading-line')",50)
  assert sum(code=='GOREV.KABUL_ETTIM' for _,code,_ in db.events)==before_accept+1
  assert record(db,'GOREV',task['kimlik'],'K041')['durum']=='ACIK'
  ok('Yayın 15 saniyeden fazla gecikse ve ekran yeniden çizilse de bekleme/kilit kalır; tek kabul olayı')
  click(b,'[data-action=tab][data-tab=open]');click(b,'tr[data-id="'+task['kimlik']+'"]');b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')");op('GOREV.TAMAMLADIM');assert 'İlgili Görev / Nesne' not in b.js('document.body.innerText');assert 'İlgili Görev' in b.js('document.body.innerText');field(b,'not','İlk deneme teslimi');submit(b)
  profile(b,'K004','Yönetici');page(b,'approvals')
  sel='[data-action=inspect][data-id="'+task['kimlik']+'"]';b.js('for(let i=0;i<2;i++)document.querySelector('+json.dumps(sel)+').click()');b.wait("!!document.querySelector('dialog[open] .task-heading')");time.sleep(2);assert b.js("document.querySelectorAll('dialog[open]').length")==1
  click(b,'dialog[open] [data-code="GOREV.REDDETTIM"]');b.wait("!!document.querySelector('[data-add=sorumlular]')")
  assert not b.js("!!document.querySelector('[data-path=sebep_olan]')")
  field(b,'not','Ölçü kontrolü düzeltilsin');click(b,'[data-form-section="Sorumluluk"] summary');click(b,'[data-add=sorumlular]')
  assert b.js("document.querySelector('[data-form-section=\"Sorumluluk\"]').open")
  assert b.js('document.activeElement.dataset.path')=='sorumlular.0.tur'
  field(b,'sorumlular.0.tur','KISI');field(b,'sorumlular.0.kimlik','K001');field(b,'sorumlular.0.yuzde',20)
  click(b,'[data-add=sorumlular]');field(b,'sorumlular.1.tur','KISI');field(b,'sorumlular.1.kimlik','K041');field(b,'sorumlular.1.yuzde',80)
  assert b.js("document.querySelector('[data-path=not]').value")=='Ölçü kontrolü düzeltilsin'
  b.screenshot(OUT/'03_sorumluluk.png');submit(b)
  responsibility=raw("SELECT coalesce(jsonb_agg(x),'[]') FROM okuma.satirlar('sorumluluklar')")
  (OUT/'sorumluluk.json').write_text(json.dumps(responsibility,ensure_ascii=False,indent=2,default=str))
  assert len(responsibility)==2,responsibility
  byperson={x['kimlik']:x for x in responsibility};assert byperson['K001']['dogrulandi'] is False and byperson['K041']['dogrulandi'] is True
  ok('Çift inceleme tek pencere; ret sırasında açık bölüm, odak ve girdiler korunur; ayrı revizyonsuz sorumluluk oluşur')
  profile(b,'K041','Ofis Çalışanı');page(b,'tasks');click(b,'[data-action=tab][data-tab=open]');click(b,'tr[data-id="'+task['kimlik']+'"]');b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')");op('GOREV.TAMAMLADIM');field(b,'not','Ölçü düzeltildi');submit(b)
  profile(b,'K004','Yönetici');page(b,'approvals');b.screenshot(OUT/'04_onay_listesi.png')
  click(b,'[data-action=quick-approve][data-id="'+task['kimlik']+'"]');b.wait("!!document.querySelector('[data-continue]')");assert 'Devam İşi Ver' in b.js('document.body.innerText');assert 'Talimatı, teslim notunu ve dosyaları inceleyin.' not in b.js('document.body.innerText')
  assert b.js("document.querySelector('[data-follow]').getBoundingClientRect().width")>=20
  click(b,'[data-continue]');b.wait("!document.querySelector('dialog[open]')",40);wait_state(db,'GOREV',task['kimlik'],'BITTI')
  status=read('PROJE_DURUM','T21-A');assert float(status['harcanan_emek'])>0;assert abs(float(status['harcanan_emek'])-float(status['etap_disi']['harcanan_emek']))<1e-8
  assert all(float(e['harcanan_emek'])==0 for e in status['etaplar'].values()),status
  page(b,'projects');click(b,'[data-action=project-open][data-id="T21-A"]');b.wait("!!document.querySelector('.project-summary')&&!document.querySelector('.loading-line')");assert 'Etap Dışı Harcanan Emek' in b.js('document.body.innerText');click(b,'[data-action=tab][data-tab=jobs]');assert 'Etap Dışı' in b.js('document.body.innerText')
  b.screenshot(OUT/'05_etap_disi.png');ok('Etapsız teslim/onay ve proje emeği korunur; etap toplamına gizlenmez; seçim kutusu ve onay düzeni')
  for person,title in [('K001','CEO'),('K004','Yönetici'),('K009','Ekip Lideri'),('K041','Ofis Çalışanı')]:
   profile(b,person,title)
   for width in [1440,960]:
    b.call('Emulation.setDeviceMetricsOverride',width=width,height=900,deviceScaleFactor=1,mobile=False);page(b,'overview')
    assert b.js("document.querySelectorAll('#sidebar-status').length===1&&!document.querySelector('.page-info .status-dot')")
    assert not b.js("!!document.querySelector('[data-search]')")
    assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
   page(b,'notifications');assert b.js("!!document.querySelector('[data-search]')")
  assert not b.errors,b.errors;assert not db.errors,db.errors
  ok('Dört web rolü, geniş/dar pencere, tek bağlantı, genel arama kaldırıldı ve Bildirimler istisnası korundu')
  future=(today+timedelta(days=35)).isoformat()+'T12:00:00+03:00'
  raw('SELECT test.saat(%s::timestamptz,%s::timestamptz,false)',(future,future))
  late=preview([{'kisi':'K041','teslim_tarihi':(today+timedelta(days=39)).isoformat(),'zaman_degeri':10}])
  assert any(w.get('geciken')==1 for w in late['uyarilar']),late
  assert all(float(w['yuk'])==0 for w in late['haftalar']),late
  (OUT/'geciken_okuma.json').write_text(json.dumps(late,ensure_ascii=False,indent=2))
  ok('Gerçek etabı olan açık iş gecikince ayrı uyarılır; geçmiş yük bu haftaya taşınmaz, biten görev sayılmaz')
  complete=True
 finally:
  release.set()
  if b:
   if not complete:
    print('SON EKRAN:',b.js('document.body.innerText.slice(-3800)'),flush=True);b.screenshot(OUT/'hata.png');print('HTTP:',db.errors if db else [],flush=True)
   b.close()
  if server:server.shutdown();server.server_close()
  if db:db.close()
  OUT.mkdir(parents=True,exist_ok=True);(OUT/'sonuc.json').write_text(json.dumps({'tamamlandi':complete,'gecen':passed},ensure_ascii=False,indent=2))
if __name__=='__main__':run()
