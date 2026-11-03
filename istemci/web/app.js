import {loadSharedConfig} from './erisim.js';
import {BrowserStore,IrpClient,validateConfig} from './client.js';
import {ProjectWorkspace as Workspace} from './projects.js';
import {esc,modal,toast,label,idOf,installUiBehavior,headingCase} from './ui.js';
import {icon} from './icons.js';
import {NAV,GROUP_LABELS} from './actions.js';
import {navigationCounts} from './navigation.js';

let client,workspace,config,configOffline=false;
const root=document.querySelector('#app');
const getJSON=async path=>{const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error('Uygulama dosyası okunamadı.');return r.json();};

async function main(){
 try{
  installUiBehavior();
  if('serviceWorker' in navigator)void navigator.serviceWorker.register('./service_worker.js').catch(()=>{});
  let store=await BrowserStore.open();
  const sampleMode=new URL(location.href).searchParams.get('kip')==='gosterim';
  const schemas=await getJSON('assets/eylem_semalari.json');
  const sample=sampleMode?await getJSON('assets/gosterim.json'):null;
  if(sampleMode)config={};else{try{config=validateConfig(await loadSharedConfig());await store.put('public-config',{supabase_url:config.supabase_url,supabase_anon:config.supabase_anon,senaryo:config.senaryo});}catch(error){configOffline=true;config=await store.get('public-config');if(!config)throw error;validateConfig(config);}}
  // Yeni boş firmanın sayacı ve önbelleği ayrı; önceki gösterinin günlüğü korunur.
  if(!sampleMode&&config.senaryo)store=await BrowserStore.open('irp-is-web-v1:'+config.senaryo);
  client=new IrpClient(store,schemas,config,sample);
  client.addEventListener('ready',showWorkspace);client.addEventListener('signedout',showLogin);client.addEventListener('status',showStatus);client.addEventListener('data',updateNavCounts);client.addEventListener('warning',e=>{if(e.detail.message&&!e.detail.message.includes('Bağlantı'))toast(e.detail.message,true);});
  if(sampleMode){await client.restore();return;}
  let saved=await store.get('session');if(saved&&config.senaryo&&saved.scenario!==config.senaryo){await store.remove('session');saved=null;}const pin=saved&&await store.get('pin:'+saved.person);
  if(saved&&pin&&!config.gosteri_kisileri?.length){await showUnlock(saved.person,pin);return;}
  if(await client.restore())return;
  const people=config.gosteri_kisileri??[];
  const choice=people.find(p=>p.kod===new URL(location.href).searchParams.get('kisi'))??people.find(p=>p.kod==='K001')??people[0];
  if(choice){try{await client.signIn(choice.kod,choice.sifre);return;}catch{}}
  showLogin();
 }catch(e){root.innerHTML=`<div class="boot"><div class="brand-mark">S</div><strong>Sibernetik IRP</strong><p>${esc(e.message)}</p><button class="btn" id="retry-start">Yeniden Dene</button></div>`;document.querySelector('#retry-start').onclick=()=>location.reload();}
}

function shell(){
 const allowed=workspace.allowedPages(),nav=NAV.filter(n=>allowed.includes(n.id));let group='';
 root.innerHTML=`<div class="app-shell erp-shell"><aside class="sidebar"><a href="#overview" class="brand"><div class="brand-mark">S</div><div><strong>Sibernetik IRP</strong><small>İŞ YÖNETİMİ</small></div></a><nav class="nav" aria-label="Ana gezinme">${nav.map(n=>{let header='';if(group!==n.group){group=n.group;header=`<div class="nav-label">${GROUP_LABELS[group]}</div>`;}return header+`<a class="nav-link" href="#${n.id}" data-page="${n.id}"><span class="nav-icon" aria-hidden="true">${icon(n.id)}</span><span data-nav-title="${esc(n.id)}">${esc(n.title)}</span></a>`;}).join('')}</nav><div class="sidebar-foot"><span id="sidebar-status"><span class="status-dot"></span>Çevrimiçi</span><span>Sibernetik IRP · İş Yönetimi</span></div></aside><header class="topbar"><div class="topbar-breadcrumb"><span>Çalışma Alanı</span><span>›</span><strong id="breadcrumb">Genel Bakış</strong></div>${client.readonly?'<span class="sample-label">Örnek veri</span>':''}<div class="topbar-user">${!client.readonly&&config.gosteri_kisileri?.length?`<label class="profile-switch"><span>Çalışma Profili</span><select id="profile-select" aria-label="Çalışma profili">${config.gosteri_kisileri.map(p=>`<option value="${esc(p.kod)}" ${p.kod===client.person?'selected':''}>${esc(p.etiket)}</option>`).join('')}</select></label>`:''}<span id="header-status" class="muted" style="font-size:10px"></span><div class="user-copy"><strong>${esc(client.readonly?'CEO':client.me.ad??client.person)}</strong><small>${esc(workspace.name(client.me.birim))}</small></div><button class="user-button" id="user-menu" aria-label="Hesap menüsü">⌄</button></div></header><div id="connection"></div><main class="content" id="main"></main></div>`;
 headingCase(root);document.querySelector('#user-menu').onclick=accountMenu;document.querySelector('#profile-select')?.addEventListener('change',e=>switchProfile(e.target.value));showStatus();
}
function showWorkspace(){workspace?.dispose();workspace=new Workspace(client);shell();const target=location.hash.replace(/^#/,'').split('/')[0]||'overview';void workspace.navigate(target);}
function updateNavCounts(){if(!client||!workspace)return;const counts=navigationCounts(client);for(const n of NAV){const el=document.querySelector('[data-nav-title="'+n.id+'"]');if(el)el.textContent=n.title+(counts[n.id]>0?' ('+counts[n.id]+')':'');}headingCase(document.querySelector('.nav'));}
function showStatus(){if(!client)return;updateNavCounts();const text=client.readonly?'Örnek veri':client.online?'Çevrimiçi':'Çevrimdışı';const sidebar=document.querySelector('#sidebar-status');if(sidebar)sidebar.innerHTML=`<span class="status-dot ${client.online?'':'offline'}"></span>${text}`;const h=document.querySelector('#header-status');if(h)h.textContent=client.pending?`${client.pending} işlem bekliyor`:client.calculating?'Sonuçlar güncelleniyor':'';const b=document.querySelector('#connection');if(b)b.innerHTML=!client.readonly&&!client.online?`<div class="connection-banner"><strong>Bağlantı yok.</strong> Son okunan bilgiler görüntüleniyor. Bildirdikleriniz bu bilgisayarda korunur; yönetim işlemleri bağlantı bekler.</div>`:'';}
function showLogin(message=''){
 root.innerHTML=`<div class="login"><section class="login-intro"><div class="toolbar"><div class="brand-mark">S</div><strong>Sibernetik IRP</strong></div><h1>İşin durumu,<br>aynı çalışma alanında.</h1><p>Projeler, ekipler ve yapılacak işler. Planlanan emek, gerçekleşen çalışma ve teslimler bir arada.</p></section><section class="login-form"><h2>Çalışma Alanına Giriş</h2><p>Çalışan kodunuz ve şifrenizle devam edin.</p><form id="login-form"><div class="form-error" role="alert">${esc(message)}</div><label class="field"><span>Çalışan kodu</span><input name="person" autocomplete="username" placeholder="Çalışan hesabınız" pattern="K[0-9]{3}" required></label><label class="field"><span>Şifre</span><input name="password" type="password" autocomplete="current-password" required></label><button class="btn primary" type="submit">Giriş Yap</button>${config?.gosteri_kisileri?.length?'<button class="btn" type="button" id="choose-account">Gösteri Kişisi Seç</button>':''}</form><p style="font-size:10px;margin-top:30px">Sibernetik IRP · İş Yönetimi</p></section></div>`;
 document.querySelector('#login-form').onsubmit=async e=>{e.preventDefault();const f=e.target,button=f.querySelector('[type=submit]');button.disabled=true;try{const person=f.person.value.toUpperCase(),pass=f.password.value;await client.signIn(person,pass);if(/^\d{6}$/.test(pass))await client.store.put('pin:'+person,await pinHash(pass));}catch(ex){f.querySelector('.form-error').textContent=ex.message;button.disabled=false;}};
 document.querySelector('#choose-account')?.addEventListener('click',chooseAccount);
}
async function pinHash(pin,salt=crypto.getRandomValues(new Uint8Array(16))){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(pin),'PBKDF2',false,['deriveBits']);const bits=new Uint8Array(await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:150000,hash:'SHA-256'},key,256));return {salt:[...salt],hash:[...bits]};}
async function showUnlock(person,pin){
 const saved=await client.store.get('cache:'+person),people=new Map(saved??[]).get('["KISILER",null,{}]')?.deger??[];
 showLogin();const f=document.querySelector('#login-form');f.person.value=person;f.person.closest('label').hidden=true;document.querySelector('.login-form p').textContent=(people.find(x=>idOf(x)===person)?.ad??person)+' · 6 rakamlı şifrenizle devam edin.';
 f.password.inputMode='numeric';f.password.maxLength=6;f.onsubmit=async e=>{e.preventDefault();const b=f.querySelector('[type=submit]');b.disabled=true;const candidate=await pinHash(f.password.value,new Uint8Array(pin.salt));if(!candidate.hash.every((x,i)=>x===pin.hash[i])){f.querySelector('.form-error').textContent='Şifreyi kontrol edin.';b.disabled=false;return;}if(!await client.restore())showLogin('Oturum yenilenemedi. Yeniden giriş yapın.');};
}
async function accountMenu(){if(configOffline&&navigator.onLine)await refreshConfig();const d=modal('Hesap',`<div class="mini-menu">${config.gosteri_kisileri?.length?'<button type="button" id="switch-account">Kişi Değiştir</button>':''}${!client.readonly?'<button type="button" id="password-change">Şifre Değiştir</button>':''}<button type="button" id="open-example">${client.readonly?'Canlı Çalışma Alanını Aç':'Örnek Veriyi Aç'}</button>${!client.readonly?'<button type="button" id="sign-out">Çıkış Yap</button>':''}</div>`);
 d.querySelector('#switch-account')?.addEventListener('click',()=>{d.close();chooseAccount();});d.querySelector('#sign-out')?.addEventListener('click',async()=>{d.close();try{await client.signOut();}catch(e){toast(e.message,true);}});d.querySelector('#password-change')?.addEventListener('click',()=>{d.close();changePassword();});d.querySelector('#open-example').onclick=()=>{d.close();const u=new URL(location.href);client.readonly?u.searchParams.delete('kip'):u.searchParams.set('kip','gosterim');u.hash='overview';window.open(u,'_blank','noopener');};
}
async function switchProfile(code){const p=config.gosteri_kisileri.find(p=>p.kod===code);if(!p||p.kod===client.person)return;const control=document.querySelector('#profile-select');try{control.disabled=true;if(!client.online||!navigator.onLine)throw new Error('Kişi değişimi için bağlantı gerekiyor.');if(client.pending&&!client.flushing)void client.flush();const until=Date.now()+30000;while((client.writing||client.flushing||client.pending)&&Date.now()<until)await new Promise(r=>setTimeout(r,150));await client.signIn(p.kod,p.sifre);}catch(e){toast(e.message,true);if(control.isConnected){control.value=client.person;control.disabled=false;}}}
function chooseAccount(){const people=config.gosteri_kisileri??[];const d=modal('Çalışma Kişisini Değiştir',`<p class="muted" style="font-size:12px;line-height:1.7;margin-bottom:16px">Seçtiğiniz kişinin yetkileriyle çalışma alanı açılır. İşleriniz korunur.</p><div class="form-error"></div><div class="mini-menu">${people.map(p=>`<button type="button" data-person="${esc(p.kod)}">${esc(p.etiket)}</button>`).join('')}</div>`);
 d.querySelectorAll('[data-person]').forEach(b=>b.onclick=async()=>{if(client.pending||client.writing||client.flushing){d.querySelector('.form-error').textContent='Gönderilmeyi bekleyen işlemler var. Bağlantı kurulduktan sonra kişi değiştirin.';return;}d.querySelectorAll('button').forEach(x=>x.disabled=true);const person=people.find(p=>p.kod===b.dataset.person);try{await client.signIn(person.kod,person.sifre);d.close();}catch{d.querySelector('.form-error').textContent='Bu kişiyle giriş yapılamadı. Bağlantıyı kontrol edin.';d.querySelectorAll('button').forEach(x=>x.disabled=false);}});
}
function changePassword(){const d=modal('Şifre Değiştir','<form id="new-password" class="stack"><div class="form-error"></div><label class="field"><span>Yeni şifre · 6 rakam</span><input name="password" type="password" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="new-password" required></label><label class="field"><span>Şifreyi tekrar girin</span><input name="again" type="password" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="new-password" required></label><button class="btn primary" type="submit">Şifreyi Değiştir</button></form>');d.querySelector('form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{if(f.password.value!==f.again.value)throw new Error('İki şifre aynı olmalı.');await client.request('/auth/v1/user',{method:'PUT',body:{password:f.password.value}});await client.store.put('pin:'+client.person,await pinHash(f.password.value));d.close();toast('Şifre değiştirildi.');}catch(ex){f.querySelector('.form-error').textContent=ex.message;}};}
document.addEventListener('click',e=>{const a=e.target.closest('.nav-link[data-page]');if(!a||!workspace||!client?.person)return;e.preventDefault();const page=a.dataset.page;workspace.projectList=true;workspace.projectFilter='open';workspace.periodDraft=null;if(location.hash==='#'+page)void workspace.navigate(page);else location.hash=page;});
window.addEventListener('hashchange',()=>{if(workspace&&client.person)void workspace.navigate(location.hash.slice(1).split('/')[0]||'overview');});
async function refreshConfig(){try{config=validateConfig(await loadSharedConfig());client.config=config;configOffline=false;}catch{}}
window.addEventListener('online',()=>{if(client){client.online=true;showStatus();void refreshConfig();void client.flush();void client.refresh().catch(()=>{});}});
window.addEventListener('offline',()=>{if(client){client.online=false;showStatus();}});
window.addEventListener('focus',()=>{if(client?.person&&!client.readonly){void client.refresh().catch(()=>{});void client.flush();}});
main();
