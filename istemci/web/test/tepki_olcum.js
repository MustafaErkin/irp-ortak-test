// Yalnız ayrı araştırma tarayıcısına Runtime.evaluate ile yüklenir; ürüne girmez.
(async()=>{
 const {IrpClient}=await import('./client.js'),{Workspace}=await import('./pages.js');
 const records=window.__latency??=[];let seq=0;
 const now=()=>Math.round(performance.now()*1000)/1000;
 function wrap(proto,name,kind,meta=()=>({})){
  const old=proto[name];if(!old||old.__latency)return;
  const fn=function(...args){
   if(this instanceof IrpClient)window.__latencyClient=this;
   if(this instanceof Workspace)window.__latencyWorkspace=this;
   const row={id:++seq,kind,name,t0:now(),phase:window.__latencyPhase??'passive',...meta(args,this)};records.push(row);
   const end=(r,error)=>{row.t1=now();row.ms=row.t1-row.t0;if(error)row.error=error.code??error.name;else if(r&&typeof r==='object'){for(const k of ['hesap','sonuc','kod','durum','yayin_ani','hesap_ani'])if(r[k]!=null)row[k]=r[k];}return r;};
   try{const r=old.apply(this,args);if(r?.then)r.then(v=>end(v),e=>end(null,e));else end(r);return r;}catch(e){end(null,e);throw e;}
  };fn.__latency=true;proto[name]=fn;
 }
 for(const name of ['base','refresh','pageReads','resolveTargets','write','afterAccepted','waitForPublication','persistCache'])wrap(IrpClient.prototype,name,'client',a=>({...(name==='pageReads'?{reads:a[0].map(r=>r[0])}:{}),...(name==='write'?{code:a[0]}:{})}));
 wrap(IrpClient.prototype,'rpc','rpc',a=>({rpc:a[0],veri:a[1]?.veri??null,target:a[1]?.hedef??null}));
 wrap(IrpClient.prototype,'request','http',a=>({rpc:a[0].split('?')[0].split('/').at(-1),veri:a[1]?.body?.veri??null,target:a[1]?.body?.hedef??null}));
 wrap(IrpClient.prototype,'emit','emit',a=>({event:a[0]}));
 wrap(Workspace.prototype,'load','workspace',(_,w)=>({page:w.page}));
 wrap(Workspace.prototype,'render','render',(_,w)=>({page:w.page}));
 const oldFetch=window.fetch;window.fetch=function(...args){
  if(window.__latencyReadOnly&&String(args[0]).includes('/rpc/olay_ekle'))throw Error('Salt okuma araştırmasında iş yazımı engellendi.');
  return oldFetch.apply(this,args);
 };
 return true;
})()
