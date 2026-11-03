"""Aynı canlı oturumda geniş/sayfa/ilgili bölüm okumalarının süre karşılaştırması.
Yalnız ayrı tarayıcı; olay gönderimi yasak. Ürün kodu veya sunucu değişmez.
Bu araştırma, yeni yenileme politikasının kabul testi değildir.
"""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser
OUT=Path(__file__).resolve().parents[3]/'codex/sonuclar/tepki_arastirma_kanit'
b=Browser();b.ws.settimeout(75);result=[]
try:
 b.call('Page.addScriptToEvaluateOnNewDocument',source="window.__latencyReadOnly=true;const f=window.fetch;window.fetch=(...a)=>{if(String(a[0]).includes('/rpc/olay_ekle'))throw Error('Salt okuma');return f(...a)}")
 b.navigate('http://localhost:8080/?kip=gosterim');b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
 b.js("(async()=>{const {BrowserStore}=await import('./client.js');const c=await(await fetch('ayar.json')).json();const s=await BrowserStore.open(c.senaryo?'irp-is-web-v1:'+c.senaryo:'irp-is-web-v1');await s.put('installation','T20-READ-CHECK')})()")
 b.navigate('http://localhost:8080/?kisi=K009#workshop')
 b.wait("document.querySelector('.user-copy strong')?.textContent==='Ekip Lideri'&&!document.querySelector('.loading-line')",60)
 b.js((Path(__file__).parent/'tepki_olcum.js').read_text())
 b.js("document.querySelector('[data-filter=unit]').value='IMALAT';document.querySelector('[data-filter=unit]').dispatchEvent(new Event('change',{bubbles:true}))")
 b.wait("!!window.__latencyClient&&!document.querySelector('.loading-line')",60)
 b.js("window.__fullReads=window.__latencyClient.visible.map(r=>[...r])")
 for cycle in range(2):
  for mode in ['full','page','part','ping']:
   r=b.js("""(async()=>{
    const mode=MODE,c=window.__latencyClient;window.__latencyPhase=mode+'-'+CYCLE;
    const t0=performance.now(),start=window.__latency.length;let error;
    const reads=window.__fullReads;
    try{
     if(mode==='full')await c.refresh();
     else if(mode==='ping')await c.rpc('simdi',{});
     else await c.pageReads(mode==='page'?reads:reads.filter(r=>['HAVUZ','EKIP','LISTE'].includes(r[0])&&r[1]!=='K009'));
    }catch(e){error=e.code??e.name;}finally{c.visible=reads;}
    return {mode,cycle:CYCLE,ms:performance.now()-t0,error,reads:window.__latency.slice(start).filter(r=>r.kind==='rpc').map(r=>({rpc:r.rpc,veri:r.veri,ms:r.ms,error:r.error}))};
   })()""".replace('MODE',json.dumps(mode)).replace('CYCLE',str(cycle+1)))
   result.append(r);print(json.dumps({'mode':mode,'cycle':cycle+1,'ms':round(r['ms']),'calls':len(r['reads']),'error':r.get('error')},ensure_ascii=False),flush=True)
finally:
 (OUT/'canli_okuma_karsilastir.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 b.close()
