"""Çalışan kurulumda yalnız normal menülerden okuma; iş olayı oluşturmaz."""
import json
from tarayici import Browser,page,click
from senaryo1_sina import profile

def run():
 b=Browser();b.ws.settimeout(90);phase="Açılış"
 try:
  b.navigate('http://localhost:8080/?kip=gosterim');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",45)
  b.js("(async()=>{const {BrowserStore}=await import('./client.js');const config=await (await fetch('ayar.json')).json();const store=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');await store.put('installation','T20-READ-CHECK')})()")
  b.navigate('http://localhost:8080/?kisi=K001');b.wait("document.querySelector('.user-copy strong')?.textContent==='CEO'&&!document.querySelector('.loading-line')",60)
  for code,title in [('K001','CEO'),('K004','Yönetici')]:
   phase=title+' rol geçişi'
   if code!='K001':profile(b,code,title)
   phase=title+' proje listesi'
   page(b,'projects');b.wait("!!document.querySelector('[data-action=project-filter]')&&!document.querySelector('.loading-line')")
   assert not b.js("document.querySelector('.notice.warn')?.textContent")
   if b.js("!!document.querySelector('[data-action=project-open]')"):
    phase=title+' proje ayrıntısı'
    click(b,'[data-action=project-open]');b.wait("!!document.querySelector('.project-summary')&&!document.querySelector('.loading-line')")
    assert b.js("document.querySelectorAll('.tabs [data-action=tab]').length")==4
    for tab in ['stages','jobs','team','objects']:
     phase=title+' sekme '+tab
     click(b,'[data-action=tab][data-tab='+tab+']');assert not b.js("document.querySelector('.notice.warn')?.textContent")
    click(b,'[data-action=project-list]')
   click(b,'[data-action=project-filter][data-filter=closed]')
   assert not b.errors,'Canlı ekran JavaScript hatası'
   print('GEÇTİ: Canlı '+title+' proje listesi, ayrıntı ve dört sekme',flush=True)
 except Exception as error:
  print('Canlı okuma tamamlanamadı: '+type(error).__name__+' / '+phase+'; gizli bağlantı ayrıntısı yazdırılmadı.',flush=True);raise SystemExit(1)
 finally:b.close()
if __name__=='__main__':run()
