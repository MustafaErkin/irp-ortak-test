"""221: kurulu webde salt okuma, form önizlemesi; iş olayları engellenir."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser,page,click,field
from senaryo1_sina import profile
OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/tur3_atolye_kanit'
b=Browser();checks=[]
try:
 b.call('Page.addScriptToEvaluateOnNewDocument',source="""window.blockedWrites=[];const savedFetch=window.fetch;window.fetch=async(...args)=>{const url=String(args[0]);if(url.includes('/rpc/olay_ekle')){blockedWrites.push('İş olayı gönderimi');throw Error('Salt okuma kontrolü iş yazamaz.')}return savedFetch(...args)};""")
 b.navigate('http://localhost:8080/?kip=gosterim');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
 b.js("(async()=>{const {BrowserStore}=await import('./client.js');const config=await (await fetch('ayar.json')).json();const store=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');await store.put('installation','T20-READ-CHECK')})()")
 b.navigate('http://localhost:8080/?kisi=K009#workshop');b.wait("document.querySelector('.user-copy strong')?.textContent==='Ekip Lideri'&&!document.querySelector('.loading-line')",60)
 for person,name in [('K009','Ekip Lideri'),('K004','Yönetici'),('K001','CEO')]:
  profile(b,person,name);page(b,'workshop')
  b.js("(()=>{const e=document.querySelector('[data-filter=unit]');e.value='IMALAT';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
  b.wait("!document.querySelector('.loading-line')",45)
  assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
  assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
  assert b.js("document.querySelectorAll('#main [data-code=\"IS.TANIMLADIM\"]').length")==1
  if person=='K009':assert not b.js("!!document.querySelector('[data-drop-person=K009]')")
  click(b,'[data-code="IS.TANIMLADIM"]');b.wait("!!document.querySelector('dialog[open] [data-path=proje]')",30)
  assert b.js("document.querySelector('[data-path=proje]').value") == ''
  assert not b.js("!!document.querySelector('dialog[open] [data-path=kisi]')")
  field(b,'tur','ANLIK');assert not b.js("!!document.querySelector('dialog[open] [data-path=tahmini_sure_dk]')")
  click(b,'dialog[open] [data-cancel]');page(b,'team')
  assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
  checks.append(name+': gerçek havuz/ekip okunuyor; boş proje ve anlık iş formu doğru; olay gönderilmedi')
 profile(b,'K009','Ekip Lideri');page(b,'workshop')
 b.js("(()=>{const e=document.querySelector('[data-filter=unit]');e.value='KURULUM';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
 b.wait("!document.querySelector('.loading-line')",45)
 assert b.js("!!document.querySelector('[data-drop-person=K031]')")
 checks.append('Ekip Lideri gerçek Saha Çalışanı listesini de okuyabiliyor')
 b.screenshot(OUT/'04_kurulu_saha.png')
 profile(b,'K041','Ofis Çalışanı');page(b,'tasks')
 assert not b.js("!!document.querySelector('#main>.notice.warn')?.textContent")
 checks.append('Ofis Çalışanı mevcut görev ekranı okunuyor')
 profile(b,'K004','Yönetici');page(b,'modules')
 assert not b.js("!!document.querySelector('#main>.notice.warn')?.textContent")
 checks.append('Mevcut modül sayfası okunuyor')
 assert not b.errors,b.errors;assert not b.js('window.blockedWrites'),b.js('window.blockedWrites')
 (OUT/'canli_oku.json').write_text(json.dumps({'tamamlandi':True,'kontroller':checks},ensure_ascii=False,indent=2));print('\n'.join(checks))
finally:b.close()
