"""Gerçek pg_cron ile iki rol, gecikme, kayıp yanıt ve başarı zamanı.
Önce motor_yama_sina; ayrı canlı kopyasında /tmp setup.json kullanılır.
"""
from motor_yama_ortami import *
S=json.loads((OUT/'setup.json').read_text());RUN=str(int(time.time()));CODE_SIGNAL='YS-'+RUN;CODE_ACK='YA-'+RUN;db=DB();db.drain();server=Server(db);b=ceo=None;results=[]
INSTR='''window.diag={toasts:[],rpc:[],zero:performance.now()};const originalFetch=window.fetch;window.fetch=async(...a)=>{const begin=performance.now();let body={};try{body=JSON.parse(a[1]?.body||'{}')}catch{}const name=String(a[0]).split('/').pop();try{const r=await originalFetch(...a);if(String(a[0]).includes('/rpc/')){const v=await r.clone().json();diag.rpc.push({at:begin-diag.zero,duration:performance.now()-begin,name,veri:body.veri,code:body.olay?.eylem_kodu,event:body.olay?.olay_kimligi,hesap:v?.hesap,sonuc:v?.sonuc,kod:v?.kod,tekrar:v?.tekrar,durum:v?.durum,id:body.olay_kimligi});}return r}catch(e){diag.rpc.push({at:begin-diag.zero,name,error:e.name});throw e}};addEventListener('DOMContentLoaded',()=>{const seen=new WeakSet();new MutationObserver(()=>{document.querySelectorAll('#toasts .toast').forEach(e=>{if(!seen.has(e)){seen.add(e);diag.toasts.push({at:performance.now()-diag.zero,text:e.innerText})}})}).observe(document.body,{subtree:true,childList:true});});'''
BOOT_SLOT=0
def boot(person):
 global BOOT_SLOT
 slot=BOOT_SLOT;BOOT_SLOT+=1;x=Browser(1360,950);x.ws.settimeout(90)
 try:
  x.call('Page.addScriptToEvaluateOnNewDocument',source=INSTR)
  url=f'http://127.0.0.1:{server.server_port}/';x.navigate(url+'?kip=gosterim');x.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",40)
  x.js("(async()=>{const {BrowserStore}=await import('./client.js');const config=await(await fetch('ayar.json')).json();const s=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');await s.put('installation',"+json.dumps('YAMA-TARAYICI-'+str(slot))+");})()")
  x.navigate(url+f'?kisi={person}');x.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60);return x
 except BaseException:x.close();raise
def openproject(x):
 page(x,'projects')
 if x.js("!!document.querySelector('[data-action=project-list]')"):click(x,'[data-action=project-list]')
 click(x,'[data-action=project-open][data-id="DG-P"]');x.wait("document.querySelector('.project-summary h2')?.textContent==='Motor Analiz Projesi'&&!document.querySelector('.loading-line')",40)
def op(x,code,identifier=None):
 x.wait("!document.querySelector('dialog[open]')");sel='[data-code='+json.dumps(code)+']'+(' [unused]' if False else '')
 if identifier:sel+='[data-id='+json.dumps(identifier)+']'
 click(x,sel);x.wait("!!document.querySelector('dialog[open]')",30)
def start(case,x,hold=2.4,signals=True):
 db.case=case;assert not db.pending();server.hold_next=hold;server.suppress_signal=not signals;x.js('diag={toasts:[],rpc:[],zero:performance.now()}');return stamp()
def state(kind,id,field):
 table={'ETAP':'etaplar','GOREV':'gorevler','PROJE':'projeler'}[kind]
 return sqlrun('SELECT hal->>%s FROM public.'+table+' WHERE anahtar=%s',(field,id))[0][0]

def observe(case,x,begin,backend,expected,frontend,others=(),timeout=20):
 d={'case':case,'published_s':None,'screen_s':None,'other_s':[None for _ in others]};end=time.monotonic()+timeout
 while time.monotonic()<end:
  elapsed=stamp()-begin
  if d['published_s'] is None and backend()==expected:d['published_s']=round(elapsed,3)
  if d['screen_s'] is None and x.js(frontend):d['screen_s']=round(elapsed,3)
  for i,(other,expr) in enumerate(others):
   if d['other_s'][i] is None and other.js(expr):d['other_s'][i]=round(elapsed,3)
  diag=x.js('diag');success=[t for t in diag['toasts'] if 'tamamlandı' in t['text'] or 'onaylandı' in t['text']]
  if d['published_s'] is not None and d['screen_s'] is not None and all(t is not None for t in d['other_s']) and success:break
  time.sleep(.1)
 d['browser']=x.js('diag');d['events']=[r for r in db.events if r['case']==case]
 d['success_toasts']=[{'s':round(t['at']/1000,3),'text':t['text']} for t in d['browser']['toasts'] if 'tamamlandı' in t['text'] or 'onaylandı' in t['text']]
 receipts=[r for r in d['browser']['rpc'] if r.get('name')=='islem_sonucu' and r.get('durum')=='TAMAMLANDI']
 assert d['published_s'] is not None and d['screen_s'] is not None and all(t is not None for t in d['other_s']),(case,'Sonuç ekranda yok',x.js("document.querySelector('dialog[open] .form-error')?.innerText"))
 assert d['success_toasts'] and receipts,(case,'Doğrulanmış başarı yok',d['browser']['toasts'])
 source={e['event'] for e in d['events'] if e['result']['sonuc']=='BASARILI'}
 assert source and {r['id'] for r in receipts}>=source
 proof=max(min((r['at']+r['duration'])/1000 for r in receipts if r['id']==oid) for oid in source)
 assert all(t['s']+.002>=proof for t in d['success_toasts']),(case,'Yayından önce başarı',proof,d['success_toasts'])
 d['yayindan_once_basari']=False;results.append(d)
 print(json.dumps({k:v for k,v in d.items() if k not in ('browser','events')},ensure_ascii=False),flush=True)
 return d

try:
 a=Actor(db)
 if state('ETAP',S['stage'],'bitis')!='2026-12-12':
  _,r=a.send('K001','ETAP.DEGISTIRDIM',{'degisenler':{'bitis':'2026-12-12'}},[('ETAP',S['stage'])],drain=True);assert r['sonuc']=='BASARILI',r
 # Önceki SQL teslim sınamasıyla aynı görevi yeniden teslim etmeyiz.
 row={'ad':'Tarayıcı Yama Görevi','is_tanimi':'Yalnız ayrı test','kisi':'K004','nereye':'PROJE','proje':'DG-P','etap':S['stage'],'teslim_tarihi':'2026-12-10','zaman_degeri':1,'zorluk':2,'onay_gerekli':True,'onaylayan':'K001','dosya_gerekli':False,'oncelik':'NORMAL','on_kosul':[]}
 assigned,r=a.send('K001','GOREV.ATADIM',{'gorevler':[row]},drain=True);assert r['sonuc']=='BASARILI',r;S['task']=assigned['olay_kimligi']+'/1'
 _,r=a.send('K004','GOREV.KABUL_ETTIM',{},[('GOREV',S['task'])],drain=True);assert r['sonuc']=='BASARILI'
 # Saat işinin dakika başına denk gelmesi kısa devam ölçüsünü gizlemesin.
 sqlrun("UPDATE cron.job SET active=false WHERE jobname='irp-motor-saat'")
 b=boot('K001');openproject(b)
 op(b,'ETAP.DEGISTIRDIM',S['stage']);field(b,'degisenler.bitis','13122026');begin=start('B1 Etap Bitişi',b);click(b,'dialog[open] [type=submit]')
 observe('B1 Etap Bitişi',b,begin,lambda:state('ETAP',S['stage'],'bitis'),'2026-12-13',"document.querySelector('.project-workspace .data-table tbody tr')?.cells[3].innerText.includes('13 Ara')")
 new_stage_name='Yama Etabı '+str(int(time.time()));op(b,'ETAP.TANIMLADIM');field(b,'ad',new_stage_name);field(b,'birim',S['unit']);field(b,'sorumlu','K004');field(b,'baslangic','14122026');field(b,'bitis','16122026');field(b,'hedef_saat',4);begin=start('B2 Yeni Etap',b);click(b,'dialog[open] [type=submit]')
 observe('B2 Yeni Etap',b,begin,lambda:sqlrun("SELECT count(*) FROM public.etaplar WHERE hal->>'proje'='DG-P' AND hal->>'ad'=%s",(new_stage_name,))[0][0],1,"[...document.querySelectorAll('.project-workspace .data-table tbody tr')].some(r=>r.innerText.includes("+json.dumps(new_stage_name)+"))")
 op(b,'PLAN.ONAYLADIM');field(b,'gerekce','Yama kabul sınaması');before=len(db.rpc('K001','oku',{'veri':'PLAN','hedef':'DG-P','g':{'surumler':True}})['deger']['surumler']);begin=start('B3 Plan Onayı',b);click(b,'dialog[open] [type=submit]')
 observe('B3 Plan Onayı',b,begin,lambda:len(db.rpc('K001','oku',{'veri':'PLAN','hedef':'DG-P','g':{'surumler':True}})['deger']['surumler']),before+1,'document.querySelector(".project-history>summary")?.innerText.includes('+json.dumps('('+str(before+1)+')')+')')
 ceo=boot('K001');page(ceo,'approvals');profile(b,'K004','Yönetici');page(b,'tasks');click(b,'[data-action=tab][data-tab=open]');click(b,'tr[data-id='+json.dumps(S['task'])+']');op(b,'GOREV.TAMAMLADIM',S['task']);begin=start('B4 Teslim İki Rol',b);click(b,'dialog[open] [type=submit]')
 approve='[data-action=quick-approve][data-id='+json.dumps(S['task'])+']'
 observe('B4 Teslim İki Rol',b,begin,lambda:state('GOREV',S['task'],'durum'),'ONAY_BEKLIYOR',"document.querySelector('.task-detail')?.innerText.includes('Onay bekliyor')",[(ceo,'!!document.querySelector('+json.dumps(approve)+')')])
 click(ceo,approve);ceo.wait("!!document.querySelector('dialog[open] [data-continue]')");begin=start('B5 Onay İki Rol',ceo);click(ceo,'dialog[open] [data-continue]')
 observe('B5 Onay İki Rol',ceo,begin,lambda:state('GOREV',S['task'],'durum'),'BITTI','!document.querySelector('+json.dumps(approve)+')',[(b,'!document.querySelector('+json.dumps('.task-workspace tr[data-id='+json.dumps(S['task'])+']')+')')])
 profile(b,'K001','CEO');openproject(b);op(b,'PROJE.KOD_DEGISTIRDIM');field(b,'kod',CODE_SIGNAL);field(b,'gerekce','Sinyal kesintisi');begin=start('B6 Sinyal Yok',b,signals=False);click(b,'dialog[open] [type=submit]')
 observe('B6 Sinyal Yok',b,begin,lambda:state('PROJE','DG-P','kod'),CODE_SIGNAL,"document.querySelector('.project-summary')?.innerText.includes("+json.dumps(CODE_SIGNAL)+")")
 op(b,'ETAP.DEGISTIRDIM',S['stage']);field(b,'degisenler.bitis','14122026');b.call('Network.emulateNetworkConditions',offline=False,latency=200,downloadThroughput=-1,uploadThroughput=-1);begin=start('B7 Ağ Gecikmesi',b);click(b,'dialog[open] [type=submit]')
 observe('B7 Ağ Gecikmesi',b,begin,lambda:state('ETAP',S['stage'],'bitis'),'2026-12-14',"document.querySelector('.project-workspace .data-table tbody tr')?.cells[3].innerText.includes('14 Ara')")
 b.call('Network.emulateNetworkConditions',offline=False,latency=0,downloadThroughput=-1,uploadThroughput=-1)
 op(b,'PROJE.KOD_DEGISTIRDIM');field(b,'kod',CODE_ACK);field(b,'gerekce','Yanıt kaybı');before=sqlrun('SELECT count(*) FROM public.olaylar')[0][0];begin=start('B8 Yanıt İki Kez Kayıp',b);server.drop_next=2;click(b,'dialog[open] [type=submit]')
 b.wait("document.querySelector('dialog[open] [type=submit]')?.textContent==='Sonucu Doğrula'",20);click(b,'dialog[open] [type=submit]')
 d=observe('B8 Yanıt İki Kez Kayıp',b,begin,lambda:state('PROJE','DG-P','kod'),CODE_ACK,"document.querySelector('.project-summary')?.innerText.includes("+json.dumps(CODE_ACK)+")")
 assert sqlrun('SELECT count(*) FROM public.olaylar')[0][0]-before==1;assert len(d['events'])==3;assert len({e['event'] for e in d['events']})==1
 # İşçi gerçekten durmuşsa 15 saniye sonunda alındı açıklaması; sahte başarı yok.
 op(b,'ETAP.DEGISTIRDIM',S['stage']);field(b,'degisenler.bitis','15122026');sqlrun("UPDATE cron.job SET active=false WHERE jobname='irp-motor-bekleyen'");begin=start('B9 Uzun Bekleme',b);click(b,'dialog[open] [type=submit]');b.wait("!document.querySelector('dialog[open]')",25)
 assert b.js("!!document.querySelector('#toasts .toast.info[role=status]')");diag=b.js('diag');assert not any('tamamlandı' in t['text'] for t in diag['toasts']);assert any('sonucu henüz doğrulanamadı' in t['text'] for t in diag['toasts']);assert state('ETAP',S['stage'],'bitis')=='2026-12-14'
 sqlrun("UPDATE cron.job SET active=true WHERE jobname='irp-motor-bekleyen'");b.wait("document.querySelector('.project-workspace .data-table tbody tr')?.cells[3].innerText.includes('15 Ara')",15)
 results.append({'case':'B9 Uzun Bekleme','sonuc':'GECTI','erken_basari':False,'yeniden_gondermeden_toparlandi':True})
 assert not b.errors and not ceo.errors,(b.errors,ceo.errors)
 b.screenshot(OUT/'yama_sonuc.png');print('Dokuz gerçek tarayıcı akışı geçti.',flush=True)
finally:
 sqlrun("UPDATE cron.job SET active=true WHERE jobname IN ('irp-motor-saat','irp-motor-bekleyen')")
 (OUT/'motor_yama_ekran.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str));db.dump('ekran_trace')
 for browser in (b,ceo):
  if browser:
   try:browser.close()
   except Exception:pass
 server.close()
