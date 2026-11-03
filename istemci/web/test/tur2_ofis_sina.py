"""Tur2: ayrı boş firmada gerçek SQL + normal web düğmeleri. Canlı veri yazılmaz."""
from datetime import date,timedelta
from pathlib import Path
import json,sys,threading,time,traceback
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tarayici import Browser,page,click,field,submit
from yerel_api import Database,ApiServer
from senaryo1_sina import profile,record,wait_state,assign,approve
OUT=HERE.parents[2]/'codex/sonuclar/tur2_ofis_kanit'

def run():
 db=server=b=None;checks=[];complete=False
 deadline=(date.today()+timedelta(days=7)).strftime('%d.%m.%Y')
 end=(date.today()+timedelta(days=21)).strftime('%d.%m.%Y')
 try:
  db=Database(empty=True);server=ApiServer(db,HERE.parent/'build');threading.Thread(target=server.serve_forever,daemon=True).start()
  b=Browser();b.ws.settimeout(60);b.navigate(f'http://127.0.0.1:{server.server_port}/');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
  def ok(name):checks.append(name);print('GEÇTİ: '+name,flush=True)
  def text():return b.js('document.body.innerText')
  def op(code):
   click(b,'[data-code="'+code+'"]');b.wait("!!document.querySelector('dialog[open] form')")
  def add(name,onay=True,files=False):
   click(b,'[data-action=assign-add]');field(b,'ad',name);field(b,'is_tanimi','Ölçüleri kontrol edip sonucu teslim edin.');field(b,'proje','T2-01');field(b,'etap',stage['kimlik']);field(b,'kisi','K041');field(b,'teslim_tarihi',deadline);field(b,'zaman_degeri',2);field(b,'zorluk',2);field(b,'onay_gerekli',onay)
   if onay:field(b,'onaylayan','K004')
   field(b,'dosya_gerekli',files)
  def tasks():return db.rpc('K001','oku',{'veri':'WEB_GOREVLER'})['deger']
  def find(name):return next(x for x in tasks() if x['ad']==name)
  def select(task,tab='open'):
   page(b,'tasks');click(b,'[data-action=tab][data-tab='+tab+']');click(b,'tr[data-id="'+task['kimlik']+'"]');b.wait("!!document.querySelector('.task-heading') && !document.querySelector('.loading-line')")
  def section(key):
   click(b,'[data-action=task-section][data-section='+key+']');b.wait("!document.querySelector('.loading-line')")
  def accept(task):
   select(task,'waiting');opbutton='[data-code="GOREV.KABUL_ETTIM"]';click(b,opbutton);b.wait("!document.querySelector('.loading-line') && !document.querySelector('.task-heading')",35)
  def deliver(task,note='Ölçüler kontrol edildi.',file=None):
   select(task);op('GOREV.TAMAMLADIM');assert not b.js("!!document.querySelector('#operation-target')");field(b,'not',note)
   if file:
    root=b.call('DOM.getDocument')['root']['nodeId'];node=b.call('DOM.querySelector',nodeId=root,selector='#operation-files')['nodeId'];b.call('DOM.setFileInputFiles',nodeId=node,files=[str(file)])
   submit(b)
  page(b,'projects');op('PROJE.ACTIM');field(b,'kod','T2-01');field(b,'ad','Ofis Kabul Denemesi');field(b,'sorumlu','K004');field(b,'teslim_tarihi',end);submit(b);b.wait("document.querySelector('.project-summary h2')?.textContent==='Ofis Kabul Denemesi'",40)
  op('ETAP.TANIMLADIM');field(b,'ad','Ofis Etabı');field(b,'birim','MEK_TASARIM');field(b,'sorumlu','K004');field(b,'bitis',end);field(b,'hedef_saat',20);submit(b)
  stage=db.rpc('K001','oku',{'veri':'ETAPLAR','hedef':'T2-01'})['deger'][0]
  ok('Test ortamında proje/etap normal arayüzden hazırlandı')
  page(b,'settings');op('AYAR.YONLENDIRDIM');field(b,'birim','PLANLAMA');click(b,'[data-multi-path=kisiler][value=K004]');submit(b)
  profile(b,'K004','Yönetici');page(b,'assign');assert 'Şablon' not in text();add('Önce Kontrol',False)
  assert b.js("[...document.querySelectorAll('#task-editor .form-section h3')].map(x=>x.textContent)")==['İş Bilgileri','Atama ve Tarih','Teslim Koşulları']
  assert not b.js("!!document.querySelector('[data-path=onaylayan]')")
  field(b,'nereye','PROJE_DISI');assert not b.js("!!document.querySelector('[data-path=proje]') || !!document.querySelector('[data-path=etap]')")
  field(b,'nereye','PROJE');assert b.js("document.querySelector('[data-path=proje]').value")=='T2-01'
  assert b.js("document.querySelector('[data-path=etap]').value")==stage['kimlik']
  add('Bağlı Teslim',True);click(b,'[data-multi-path=on_kosul][value="@row:0"]')
  field(b,'zaman_degeri',0);click(b,'[data-action=assign-review]');b.wait("document.querySelector('[data-path=zaman_degeri]').getAttribute('aria-invalid')==='true'");assert not b.js("!!document.querySelector('dialog[open]')");field(b,'zaman_degeri',2)
  click(b,'[data-action=assign-review]');b.wait("!!document.querySelector('[data-assign]')");assert len(b.js("[...document.querySelectorAll('dialog[open] .data-table:first-child tbody tr')].map(x=>x.textContent)"))>=2
  assert 'Önce: Önce Kontrol' in text();b.screenshot(OUT/'01_atama_ozeti.png');click(b,'[data-assign]');b.wait("!document.querySelector('dialog[open]')",40)
  first=find('Önce Kontrol');second=find('Bağlı Teslim');assert second['on_kosul']==[first['kimlik']]
  ok('Gruplu form, bağlam, onaysız/proje dışı sadeleşme, alan hatası ve iki iş tek atama')
  profile(b,'K041','Ofis Çalışanı');accept(first);assert b.js("document.querySelector('.tabs .active')?.dataset.tab")=='waiting';accept(second);select(second)
  assert 'Önkoşullar tamamlanmadan teslim yapılamaz.' in text();assert 'Önce Kontrol' in text();assert not b.js("!!document.querySelector('[data-code=\"GOREV.TAMAMLADIM\"]')")
  assert record(db,'GOREV',second['kimlik'],'K041')['durum']=='ON_IS_BEKLIYOR'
  ok('Kabulde sekme sabit; açık işler sayılır; bağlı görevin bekleme nedeni ve adı görünür')
  section('notes');op('NOT.YAZDIM');assert b.js("getComputedStyle(document.querySelector('#note-kind').parentElement.parentElement).display")=='none'
  field(b,'metin','@');b.wait("!!document.querySelector('[data-mention=PLANLAMA]')");click(b,'[data-mention=PLANLAMA]');field(b,'metin','@Proje Yönetimi Ölçü bilgisini teyit eder misiniz?');submit(b)
  b.wait("document.querySelector('.task-note')?.textContent.includes('Kabul Bekliyor')",35);assert 'Yönetici' in text();b.screenshot(OUT/'02_not_istek.png')
  ok('Görev üzerinde @ birim isteği, doğru bağ ve görünür alıcı durumu')
  profile(b,'K004','Yönetici');noteTask=next(x for x in tasks() if x.get('tur')=='NOT' and x['kisi']=='K004');accept(noteTask)
  profile(b,'K041','Ofis Çalışanı');select(second);section('notes');b.wait("document.querySelector('.task-note')?.textContent.includes('1 İsteği Kabul Etti')")
  ok('@ isteğini yönetici kabul edince gönderen aynı görevde sonucu görür')
  deliver(first);wait_state(db,'GOREV',first['kimlik'],'BITTI','K041');wait_state(db,'GOREV',second['kimlik'],'ACIK','K041')
  select(second);assert b.js("!!document.querySelector('[data-code=\"GOREV.TAMAMLADIM\"]')")
  deliver(second,'İlk teslim: ölçü tablosu hazır.');wait_state(db,'GOREV',second['kimlik'],'ONAY_BEKLIYOR','K041');select(second);assert 'Teslim edildi. Onay bekleniyor.' in text();assert 'İlk teslim: ölçü tablosu hazır.' in text()
  b.screenshot(OUT/'03_teslim_bekliyor.png');ok('Dosyasız onaysız teslim tamamlar, önkoşul çözülür; onaylı teslim ayrı durumda ve notuyla görünür')
  profile(b,'K004','Yönetici');page(b,'approvals');click(b,'[data-action=inspect][data-id="'+second['kimlik']+'"]');b.wait("!!document.querySelector('dialog[open] .task-heading')")
  assert 'Ölçüleri kontrol edip sonucu teslim edin.' in text();assert 'İlk teslim: ölçü tablosu hazır.' in text()
  click(b,'dialog[open] [data-code="GOREV.REDDETTIM"]');b.wait("!!document.querySelector('dialog[open] form')")
  assert not b.js("!!document.querySelector('[data-path=kime]')");click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=not]').getAttribute('aria-invalid')==='true'")
  field(b,'not','İkinci ölçüyü de ekleyin.');submit(b);wait_state(db,'GOREV',second['kimlik'],'REDDEDILDI','K004')
  profile(b,'K041','Ofis Çalışanı');select(second);assert 'İkinci ölçüyü de ekleyin.' in text();section('files');assert 'Düzeltmeye Gönderildi' in text();assert 'İlk teslim: ölçü tablosu hazır.' in text()
  deliver(second,'İkinci ölçü de eklendi.');wait_state(db,'GOREV',second['kimlik'],'ONAY_BEKLIYOR','K041')
  ok('Onaylayan talimat/teslimi birlikte görür; gerekçesiz ret engellenir; aynı görev gerekçesi ve geçmişiyle döner')
  profile(b,'K004','Yönetici');page(b,'approvals');click(b,'[data-action=quick-approve][data-id="'+second['kimlik']+'"]');b.wait("!!document.querySelector('[data-continue]')");assert 'İkinci ölçü de eklendi.' in text();assert b.js("document.querySelector('[data-continue]').textContent")=='Teslimi Onayla';click(b,'[data-continue]');b.wait("!document.querySelector('dialog[open]')",40);wait_state(db,'GOREV',second['kimlik'],'BITTI')
  ok('Son teslim notuyla açık Onayla eylemi; tekrar teslimin geçmişi korunur')
  # Completed source remains selectable only as an already established continuation link.
  page(b,'projects');click(b,'[data-action=project-open][data-id="T2-01"]') if b.js("!!document.querySelector('[data-action=project-open][data-id=\"T2-01\"]')") else None
  click(b,'[data-action=tab][data-tab=works]') if b.js("!!document.querySelector('[data-action=tab][data-tab=works]')") else click(b,'[data-action=tab][data-tab=jobs]')
  click(b,'[data-action=inspect][data-id="'+second['kimlik']+'"]');b.wait("!!document.querySelector('dialog[open] .task-heading')");click(b,'dialog[open] [data-action=task-follow]');b.wait("!!document.querySelector('#task-editor')")
  assert b.js("document.querySelector('[data-path=ad]').value")=='Devam: Bağlı Teslim';assert b.js("document.querySelector('[data-path=etap]').value")==stage['kimlik'];assert b.js("document.querySelector('[data-multi-path=on_kosul][value='+CSS.escape("+json.dumps(second['kimlik'])+")+']')?.checked")
  click(b,'[data-action=assign-remove]');add('Dosyalı İş',True,True)
  assert not b.js("[...document.querySelectorAll('[data-multi-path=on_kosul]')].some(e=>"+json.dumps([first['kimlik'],second['kimlik']])+".includes(e.value))")
  assign(b);filetask=find('Dosyalı İş');ok('Devamda kaynak bağ/proje/etap korunur; yeni önkoşul listesi bitmiş işleri göstermez')
  profile(b,'K041','Ofis Çalışanı');accept(filetask);select(filetask);op('GOREV.TAMAMLADIM');click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('#operation-files').getAttribute('aria-invalid')==='true'");assert 'dosya gerekli' in text();click(b,'[data-cancel]')
  attachment=Path('/tmp/irp_tur2/teslim.txt');attachment.write_text('Tur2 teslim dosyası - teknik test')
  deliver(filetask,'Dosyalı teslim hazır.',attachment);wait_state(db,'GOREV',filetask['kimlik'],'ONAY_BEKLIYOR','K041');select(filetask);section('files');assert 'teslim.txt' in text();assert b.js("!!document.querySelector('[data-action=file]')&&!!document.querySelector('[data-action=download-file]')");click(b,'[data-action=download-file]')
  ok('Zorunlu dosya alanında uyarı; gerçek dosya yükleme, izinli liste ve indir düğmesi')
  profile(b,'K004','Yönetici');page(b,'approvals');click(b,'[data-action=inspect][data-id="'+filetask['kimlik']+'"]');b.wait("!!document.querySelector('dialog[open] .task-heading')");click(b,'dialog[open] [data-code="GOREV.REDDETTIM"]');b.wait("!!document.querySelector('dialog[open] form')");field(b,'not','Ayrı bir ek kontrol yapın.');field(b,'revizyon_ver',True);click(b,'[type=submit]');b.wait("document.querySelector('[data-path=kime]').getAttribute('aria-invalid')==='true'");field(b,'kime','K041');field(b,'yeni_teslim_tarihi',deadline);field(b,'zaman_degeri',1);submit(b)
  original=wait_state(db,'GOREV',filetask['kimlik'],'REVIZYONDA');revision=record(db,'GOREV',original['revizyon_gorevi']);assert revision['kaynak']==filetask['kimlik']
  profile(b,'K041','Ofis Çalışanı');accept(revision);deliver(revision,'Ek kontrol tamamlandı.',attachment);profile(b,'K004','Yönetici');page(b,'approvals');approve(b,db,'GOREV',revision['kimlik']);wait_state(db,'GOREV',filetask['kimlik'],'BITTI')
  ok('Ayrı revizyonun zorunlu alanları, kaynak bağı ve onayla ana görevin tamamlanması')
  profile(b,'K041','Ofis Çalışanı');select(first,'done');assert b.js("document.querySelector('[data-done-date]').value")==date.today().isoformat();click(b,'[data-action=tasks-history]');assert b.js("document.querySelector('[data-done-date]').value")==''
  b.js("const d=document.querySelector('[data-done-date]');d.value='2020-01-01';d.dispatchEvent(new Event('change',{bubbles:true}))");assert not b.js("!!document.querySelector('.task-workspace tbody tr')");click(b,'[data-action=tasks-today]');assert b.js("document.querySelectorAll('.task-workspace tbody tr').length")>=3
  assert b.js('document.documentElement.scrollWidth<=innerWidth+1');b.screenshot(OUT/'04_tamamlananlar.png')
  ok('Tamamlananlar Bugün açılır; geçmiş/tarih/bugüne dönüş ve masaüstü taşma kontrolü')
  # Only this test transport rejects the second group once, before database acceptance.
  profile(b,'K004','Yönetici');page(b,'assign');add('Kısmi Ofis',False);add('Kısmi Havuz',False);field(b,'olcum','SAAT');field(b,'birim','IMALAT')
  b.js("window.savedFetch=window.fetch;window.rejectPoolOnce=true;window.fetch=async(...a)=>{const body=JSON.parse(a[1]?.body||'{}');if(body.olay?.eylem_kodu==='IS.TANIMLADIM'&&window.rejectPoolOnce){window.rejectPoolOnce=false;return new Response(JSON.stringify({sonuc:'RED',kod:'YETKI',aciklama:'Sınama: ikinci grup reddedildi.'}),{status:200,headers:{'Content-Type':'application/json'}})}return window.savedFetch(...a)}")
  click(b,'[data-action=assign-review]');b.wait("!!document.querySelector('[data-assign]')");click(b,'[data-assign]');b.wait("!!document.querySelector('dialog .form-error')?.textContent",40)
  assert len([x for x in tasks() if x['ad']=='Kısmi Ofis'])==1
  assert not [x for x in db.rpc('K004','oku',{'veri':'WEB_ISLER'})['deger'] if x['islem']=='Kısmi Havuz']
  b.js('window.fetch=window.savedFetch');click(b,'[data-assign]');b.wait("!document.querySelector('dialog[open]')",40)
  assert len([x for x in tasks() if x['ad']=='Kısmi Ofis'])==1
  assert len([x for x in db.rpc('K004','oku',{'veri':'WEB_ISLER'})['deger'] if x['islem']=='Kısmi Havuz'])==1
  ok('Karma atamada ikinci grup reddedilince ilk grup tekrarlanmaz; kalan taslak bir kez gönderilir')
  page(b,'projects');click(b,'[data-action=project-open][data-id="T2-01"]') if b.js("!!document.querySelector('[data-action=project-open][data-id=\"T2-01\"]')") else None
  click(b,'[data-action=tab][data-tab=jobs]');click(b,'[data-action=inspect][data-id="'+first['kimlik']+'"]');b.wait("!!document.querySelector('dialog[open] .task-heading')");click(b,'[data-action=task-change]');b.wait("!!document.querySelector('#task-editor')")
  assert b.js("document.querySelector('[data-path=ad]').value")=='Değişiklik: Önce Kontrol';field(b,'teslim_tarihi',deadline);assign(b)
  change=find('Değişiklik: Önce Kontrol');assert change['degisiklik']['kaynak']==first['kimlik'];assert change['kimlik']!=first['kimlik']
  ok('Değişiklik işi ayrı görevdir; önceki bitmiş işi değiştirmez ve kaynağını taşır')
  # A sender sees receipt totals, not the recipient's otherwise private task identifiers.
  own=db.rpc('K041','oku',{'veri':'GOREV_AYRINTISI','hedef':second['kimlik']})['deger'];receipts=list(own['istekler'].values());assert receipts[0]['ozet']['kabul']==1
  assert receipts[0]['alicilar']==[] and receipts[0]['liste_tam'] is False
  manager=db.rpc('K004','oku',{'veri':'GOREV_AYRINTISI','hedef':second['kimlik']})['deger'];assert 'ozet' not in list(manager['istekler'].values())[0]
  ok('İstek toplamı yalnız gönderene açılır; yetkisi dışındaki alıcı görevi/kimliği açılmaz')
  try:db.rpc('K017','oku',{'veri':'GOREV_AYRINTISI','hedef':filetask['kimlik']});raise AssertionError('Yetkisiz görev ayrıntısı açıldı')
  except (PermissionError,Exception) as e:
   assert not isinstance(e,AssertionError),e
   assert 'YETKI' in str(e) or isinstance(e,PermissionError),e
  assert not b.errors,b.errors
  assert not db.errors,db.errors
  ok('Görev görünürlüğü sunucuda korunur; tarayıcı/HTTP çalışma hatası yok')
  complete=True
 finally:
  if b:
   if not complete:
    print('SON EKRAN:',b.js('document.body.innerText.slice(-3000)'),flush=True);print('HTTP:',db.errors[-4:] if db else [],flush=True);b.screenshot(OUT/'hata.png')
   b.close()
  if server:server.shutdown();server.server_close()
  if db:db.close()
  OUT.mkdir(parents=True,exist_ok=True);(OUT/'sonuc.json').write_text(json.dumps({'tamamlandi':complete,'gecen':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':run()
