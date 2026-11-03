// Yalnız ortak host kullanılır. Üretim modülü kendi Python API'sini sağlar;
// buradaki /ornek yolu ortak çekirdeğin yeni bir kapısı değildir.
export async function ac(host){
 let context=host.baglam,closed=false,epoch=0;
 const drafts=new Map(),dialogs=new Set();
 const {esc,panel,table,empty,errorBox,date,badge,modal,headingCase}=host.ui;
 const root=host.kok;
 function render(value,error=''){
  if(closed)return;
  const rows=value?.etaplar??[],title=value?.proje?.ad??context.projeler.find(p=>p.kimlik===context.proje)?.ad??'Proje';
  const data=error?errorBox(error):rows.length?table([
   {label:'Etap',render:r=>'<strong>'+esc(r.ad)+'</strong>'},
   {label:'Hedef Bitiş',render:r=>date(r.bitis)},
   {label:'Sorumlu',render:r=>esc(host.ui.ad(r.sorumlu))},
   {label:'Durum',render:r=>badge(r.durum)},
   {label:'İşlem',render:()=>'<button type="button" class="btn small" data-ornek-islem="ayrinti">Ayrıntı</button>'}
  ],rows):empty('Henüz Etap Yok','Proje planınız hazırlandığında etaplar burada görünür.');
  root.innerHTML='<div class="ornek-modul">'+panel(title,data,'<button type="button" class="btn" data-ornek-islem="yenile">Yenile</button>')+
   panel('Çalışma Notu','<div class="panel-body"><label class="field"><span>Taslak Not</span><textarea data-ornek-not rows="4" placeholder="Çalışma notunuzu yazın">'+esc(drafts.get(context.proje)??'')+'</textarea></label></div>')+'</div>';
  headingCase(root);
 }
 async function load(){
  const ownEpoch=++epoch,project=context.proje;
  try{
   const value=await host.istek('/projeler/'+encodeURIComponent(project)+'/ornek');
   if(closed||ownEpoch!==epoch||context.proje!==project)return;
   render(value);
  }catch(error){if(!closed&&ownEpoch===epoch)render(null,error.message);}
 }
 const input=event=>{if(event.target.matches('[data-ornek-not]'))drafts.set(context.proje,event.target.value);};
 const click=event=>{
  const action=event.target.closest('[data-ornek-islem]')?.dataset.ornekIslem;
  if(action==='yenile')void load();
  if(action==='ayrinti'){
   const row=event.target.closest('tr'),name=row.querySelector('strong')?.textContent??'Etap';
   const dialog=modal(name,'<p>Etap ayrıntısı bu ortak pencere düzeninde gösterilir.</p>');
   dialogs.add(dialog);dialog.addEventListener('close',()=>dialogs.delete(dialog),{once:true});
  }
 };
 root.addEventListener('input',input);root.addEventListener('click',click);
 await load();
 return {
  async refresh(next){if(closed)return;context=next;await load();},
  dispose(){closed=true;epoch++;root.removeEventListener('input',input);root.removeEventListener('click',click);for(const d of dialogs)d.close();dialogs.clear();drafts.clear();}
 };
}
