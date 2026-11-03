"""216: kurulu görev ayrıntısı için salt okunur gerçek tarayıcı kontrolü."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser,page,click
from senaryo1_sina import profile
OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/tur2_ofis_kanit'
b=Browser();checks=[]
try:
 b.navigate('http://localhost:8080/?kip=gosterim');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",45)
 b.js("(async()=>{const {BrowserStore}=await import('./client.js');const config=await (await fetch('ayar.json')).json();const store=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');await store.put('installation','T20-READ-CHECK')})()")
 b.navigate('http://localhost:8080/?kisi=K004');b.wait("document.querySelector('.user-copy strong')?.textContent==='Yönetici'&&!document.querySelector('.loading-line')",60)
 for role,name in [('K004','Yönetici'),('K041','Ofis Çalışanı')]:
  if role!='K004':profile(b,role,name)
  page(b,'tasks');assert not b.js("!!document.querySelector('.nav-link[data-page=templates]')")
  found=False
  for tab in ['open','waiting','done']:
   click(b,'[data-action=tab][data-tab='+tab+']')
   if tab=='done':click(b,'[data-action=tasks-history]')
   if not b.js("!!document.querySelector('.task-workspace tbody tr')"):continue
   click(b,'.task-workspace tbody tr');b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')",45)
   assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
   for section in ['info','notes','files']:
    click(b,'[data-action=task-section][data-section='+section+']');b.wait("!!document.querySelector('.task-section-body') && !/okunuyor…/.test(document.querySelector('.task-section-body').textContent)",45)
    assert not b.js(r"/K[0-9]{3}-[0-9]+|GOREV\.[A-Z_]+/.test(document.querySelector('#main').innerText)")
   assert b.js('document.documentElement.scrollWidth<=innerWidth+1');b.screenshot(OUT/('canli_'+role+'_ayrinti.png'))
   checks.append(name+': mevcut görev, üç ayrıntı bölümü, gerçek izinli okuma, kod sızıntısı/taşma yok');found=True;break
  assert found,'Mevcut görev seçilemedi: '+name
 assert not b.errors,b.errors
 (OUT/'canli_ayrinti.json').write_text(json.dumps({'tamamlandi':True,'gecen':checks},ensure_ascii=False,indent=2));print('\n'.join(checks))
except Exception:
 print('Ekran:',b.js('document.querySelector("#main").innerText.slice(-1800)'));b.screenshot(OUT/'canli_hata.png');raise
finally:b.close()
