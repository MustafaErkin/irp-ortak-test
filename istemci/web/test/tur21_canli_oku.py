"""218: kurulu webde yalnız okuma/önizleme; iş yazma HTTP çağrıları engellenir."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser,page,click,field
from senaryo1_sina import profile
OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/tur21_kanit'
b=Browser();checks=[]
try:
 b.call('Page.addScriptToEvaluateOnNewDocument',source="""window.blockedWrites=[];window.readTrace=[];const savedFetch=window.fetch;window.fetch=async(...args)=>{const url=String(args[0]);if(url.includes('/rpc/olay_ekle')){blockedWrites.push('İş olayı gönderimi');throw Error('Salt okuma kontrolü iş yazamaz.')}let body={};try{body=JSON.parse(args[1]?.body||'{}')}catch{}const row={name:url.includes('/rpc/')?url.split('/').at(-1):url.includes('/auth/')?'auth':'asset',veri:body.veri},start=performance.now();try{const r=await savedFetch(...args);row.status=r.status;return r;}catch(e){row.error=e.name;throw e;}finally{row.ms=Math.round(performance.now()-start);readTrace.push(row)}};""")
 b.navigate('http://localhost:8080/?kip=gosterim');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",45)
 b.js("(async()=>{const {BrowserStore}=await import('./client.js');const config=await (await fetch('ayar.json')).json();const store=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');await store.put('installation','T20-READ-CHECK')})()")
 b.navigate('http://localhost:8080/?kisi=K004');b.wait("document.querySelector('.user-copy strong')?.textContent==='Yönetici'&&!document.querySelector('.loading-line')",60)
 page(b,'assign');click(b,'[data-action=assign-add]');assert b.js("document.querySelector('[data-path=proje]').value")==''
 field(b,'ad','Yalnız Önizleme');pid=b.js("[...document.querySelector('[data-path=proje]').options].find(x=>x.textContent.includes('Çekirdek Denemesi'))?.value");assert pid
 field(b,'proje',pid);field(b,'kisi','K041');field(b,'teslim_tarihi','27.11.2026');field(b,'zaman_degeri',60);field(b,'zorluk',2);field(b,'onaylayan','K004')
 click(b,'[data-action=assign-review]');b.wait("!!document.querySelector('[data-assign]')",60);click(b,'.assignment-capacity summary');assert b.js("document.querySelectorAll('.assignment-capacity tbody tr').length")>=1
 assert 'Etap Dışı' in b.js('document.body.innerText');b.screenshot(OUT/'canli_onizleme.png');click(b,'[data-back]');click(b,'[data-action=assign-remove]')
 checks.append('Gerçek sunucuda boş form, Etap Dışı ve 60 saatlik haftalık salt okuma; Ata kullanılmadı')
 for person,title in [('K001','CEO'),('K004','Yönetici'),('K009','Ekip Lideri'),('K041','Ofis Çalışanı')]:
  profile(b,person,title);page(b,'tasks');assert not b.js("!!document.querySelector('[data-search],.page-info .status-dot')")
  assert not b.js("!!document.querySelector('#main>.notice.warn')?.textContent")
  assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
  checks.append(title+': kurulu görev ekranı okunur, tek bağlantı, taşma yok')
 page(b,'tasks');found=False
 for tab in ['open','waiting','done']:
  click(b,'[data-action=tab][data-tab='+tab+']')
  if tab=='done':click(b,'[data-action=tasks-history]')
  if not b.js("!!document.querySelector('.task-workspace tbody tr')"):continue
  click(b,'.task-workspace tbody tr');b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')",45)
  for section in ['info','notes','files']:
   click(b,'[data-action=task-section][data-section='+section+']');b.wait("!!document.querySelector('.task-section-body')&&!/okunuyor…/.test(document.querySelector('.task-section-body').textContent)",45)
  assert not b.js(r"/K[0-9]{3}-[0-9]+|GOREV\.[A-Z_]+/.test(document.querySelector('#main').innerText)")
  found=True;break
 assert found;checks.append('Mevcut ofis görevinin üç ayrıntı bölümü okunur; teknik kod sızıntısı yok')
 profile(b,'K004','Yönetici');page(b,'modules');assert not b.js("!!document.querySelector('#main>.notice.warn')?.textContent");checks.append('Mevcut modül sayfası okunur')
 assert not b.errors,b.errors;assert not b.js('window.blockedWrites'),b.js('window.blockedWrites')
 (OUT/'canli_oku.json').write_text(json.dumps({'tamamlandi':True,'gecen':checks},ensure_ascii=False,indent=2));print('\n'.join(checks))
except Exception:
 print('Okuma süreleri:',b.js('window.readTrace?.slice(-25)'));print('Ekran:',b.js('document.querySelector("#main")?.innerText.slice(-1400)'));b.screenshot(OUT/'canli_hata.png');raise
finally:b.close()
