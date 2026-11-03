// Temel proje görünümü. Ortak motor kurallarını veya modül planını değiştirmez.
export const projectOpen=p=>!!p&&p.aktif!==false;
export function sortProjectJobs(rows){
 const stamp=value=>Number.isFinite(Date.parse(value))?Date.parse(value):0;
 return [...rows].sort((a,b)=>stamp(b.bitis_ani)-stamp(a.bitis_ani)||stamp(b.atama_ani??b.olusma_ani)-stamp(a.atama_ani??a.olusma_ani));
}
export const projectLabel=p=>[p.ad,p.kod,p.ek,projectOpen(p)?'Açık':'Kapalı'].filter(Boolean).join(' · ');
export const projectOperations=new Set(['PROJE.ACTIM','PROJE.DEGISTIRDIM','PROJE.KOD_DEGISTIRDIM','PROJE.KAPATTIM','PROJE.ERISIM_VERDIM','PROJE.ERISIM_KALDIRDIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM','PLAN.ONAYLADIM']);
export function projectRange(project,stages,today){
 const dates=[project?.baslangic_tarihi,project?.teslim_tarihi,...stages.flatMap(e=>[e.baslangic,e.bitis])].filter(Boolean).map(x=>String(x).slice(0,10)).sort();
 return {bas:dates[0]??today,bit:dates.at(-1)??today};
}
export function planningTask(stage,project){
 return {ad:stage.ad+' Etabı Planlama',is_tanimi:stage.ad+' etabının tarihlerini ve hedef emeğini düzenleyin. Hazırladığınız planı değerlendirmeye sunun.',nereye:'PROJE',proje:project.kimlik??project.kod,etap:stage.kimlik,kisi:stage.sorumlu??project.sorumlu,dosya_gerekli:false};
}
export function projectIssues(code,g,{projects=[],record=null,stages=[],tasks=[],works=[],plan={}}={}){
 const issues=[],add=(path,message)=>issues.push({path,message});
 const id=x=>x?.kimlik??x?.kod;
 const changed=code.endsWith('DEGISTIRDIM'),value=changed?{...record,...g.degisenler}:g,prefix=changed?'degisenler.':'';
 const pid=code.startsWith('ETAP.')?value.proje:g.proje??id(record),p=projects.find(x=>id(x)===pid);
 if(['PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM'].includes(code)&&projects.some(p=>[{kod:p.kod,ek:p.ek},...(p.kod_gecmisi??[])].some(x=>x.kod===g.kod&&(x.ek??'')===(g.ek??''))))add('kod','Bu proje kodu daha önce kullanılmış. Başka bir kod girin.');
 if(['ETAP.TANIMLADIM','ETAP.DEGISTIRDIM','PLAN.ONAYLADIM','PROJE.DEGISTIRDIM','PROJE.KAPATTIM'].includes(code)&&p&&!projectOpen(p))add(code.startsWith('ETAP.')?'proje':'','Bu proje kapalı. Geçmişi görüntüleyebilirsiniz; bu işlem yapılamaz.');
 if(code.startsWith('ETAP.')&&value.baslangic&&value.bitis&&value.baslangic>value.bitis)add(prefix+'bitis','Bitiş tarihi başlangıçtan önce olamaz.');
 if(code==='PLAN.ONAYLADIM'){
  if(!stages.some(e=>e.proje===pid))add('','Planı onaylamak için önce en az bir etap oluşturun.');
  if(plan.surumler?.length&&!g.gerekce?.trim())add('gerekce','Yeni plan sürümü için değişiklik gerekçesini yazın.');
 }
 if(code==='PROJE.KAPATTIM'){
  const open=[...tasks,...works].filter(x=>x.proje===pid&&!['BITTI','IPTAL'].includes(x.durum));
  if(open.length)add('','Proje kapatılamıyor. Açık işler: '+open.map(x=>x.ad??x.islem??x.is_tanimi??'İş').join(', ')+'.');
 }
 return issues;
}
