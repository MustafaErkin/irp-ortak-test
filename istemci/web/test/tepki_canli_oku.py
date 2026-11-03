"""Kurulu webi ayrı profilde izler. İş yazmaz, kullanıcı tarayıcısına dokunmaz.
Süre/metaveri dışında cevap, oturum veya anahtar saklamaz.
"""
from pathlib import Path
import json, sys, time
sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser, page
OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/tepki_arastirma_kanit'
OUT.mkdir(parents=True,exist_ok=True)
b=Browser();b.ws.settimeout(60)
try:
 b.call('Page.addScriptToEvaluateOnNewDocument',source="""
window.__latencyReadOnly=true;window.__latency=[];
const BaseSocket=window.WebSocket;
window.WebSocket=class extends BaseSocket{constructor(...args){super(...args);this.addEventListener('message',e=>{try{const m=JSON.parse(e.data);if(m.event==='postgres_changes')window.__latency.push({kind:'signal',t0:performance.now(),phase:window.__latencyPhase??'passive',topic:m.topic})}catch{}})}};
const fetchBefore=window.fetch;window.fetch=(...a)=>{if(String(a[0]).includes('/rpc/olay_ekle'))throw Error('Salt okuma');return fetchBefore(...a)};
""")
 b.navigate('http://localhost:8080/?kip=gosterim')
 b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
 b.js("(async()=>{const {BrowserStore}=await import('./client.js');const c=await(await fetch('ayar.json')).json();const s=await BrowserStore.open(c.senaryo?'irp-is-web-v1:'+c.senaryo:'irp-is-web-v1');await s.put('installation','T20-READ-CHECK')})()")
 b.navigate('http://localhost:8080/?kisi=K009#workshop')
 b.wait("document.querySelector('.user-copy strong')?.textContent==='Ekip Lideri'&&!document.querySelector('.loading-line')",60)
 b.js((Path(__file__).parent/'tepki_olcum.js').read_text())
 b.js("window.__latencyPhase='initial';document.querySelector('[data-filter=unit]').value='IMALAT';document.querySelector('[data-filter=unit]').dispatchEvent(new Event('change',{bubbles:true}))")
 b.wait("!!window.__latencyClient&&!document.querySelector('.loading-line')",60)
 for i in range(3):
  b.js(f"window.__latencyPhase='refresh-{i+1}';window.__latencyClient.refresh().catch(e=>window.__latency.push({{kind:'refresh-error',phase:window.__latencyPhase,code:e.code}}))")
  time.sleep(1)
 b.js("window.__latencyPhase='passive'")
 end=time.monotonic()+180
 while time.monotonic()<end:
  time.sleep(5)
  trace=b.js('window.__latency')
  (OUT/'canli_tarama.json').write_text(json.dumps({'tamamlandi':False,'rows':trace},ensure_ascii=False,indent=2))
 (OUT/'canli_tarama.json').write_text(json.dumps({'tamamlandi':True,'rows':b.js('window.__latency'),'tarayici_hata_sayisi':len(b.errors)},ensure_ascii=False,indent=2))
 print('Canlı salt okuma süreleri ve 3 dakika değişiklik sinyali izlendi; iş olayı gönderilmedi.')
finally:
 try:
  trace=b.js('window.__latency')
  (OUT/'canli_tarama_son.json').write_text(json.dumps({'rows':trace,'tarayici_hata_sayisi':len(b.errors)},ensure_ascii=False,indent=2))
 finally:b.close()
