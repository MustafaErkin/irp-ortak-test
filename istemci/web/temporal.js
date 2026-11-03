// Görünüm bölge ayarından bağımsız; taşıma biçimi ISO ve İstanbul saatidir.
export function validDay(value){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value??''))return false;
 const [y,m,d]=value.split('-').map(Number);
 return y>=1900&&y<=9999&&m>=1&&m<=12&&d>=1&&d<=new Date(Date.UTC(y,m,0)).getUTCDate();
}
export const validTime=value=>/^([01]\d|2[0-3]):[0-5]\d$/.test(value??'');
export function parseTemporal(value,kind){
 if(!value)return undefined;
 if(kind==='time')return value;
 const parts=value.trim().match(/^(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}:\d{2}))?$/);
 if(!parts)return value; // Eksik yazı korunur; tamamlanmış tarih varsayılmaz.
 const day=`${parts[3]}-${parts[2]}-${parts[1]}`;
 if(!validDay(day)||kind==='datetime-local'&&!validTime(parts[4]))return value;
 return kind==='date'?day:`${day}T${parts[4]}:00+03:00`;
}
export function displayTemporal(value,kind){
 if(!value)return '';
 if(kind==='time')return String(value).slice(0,5);
 const match=String(value).match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}:\d{2}))?/);
 if(!match)return value;
 return `${match[3]}.${match[2]}.${match[1]}`+(kind==='datetime-local'?` ${match[4]??''}`:'');
}
export function validTemporal(value,kind){
 if(kind==='date')return validDay(value);
 if(kind==='time')return validTime(value);
 return typeof value==='string'&&validDay(value.slice(0,10))&&validTime(value.slice(11,16))&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)&&Number.isFinite(Date.parse(value));
}
export function nextDay(day){
 if(!validDay(day))throw new Error('Geçerli bir tarih girin.');
 const date=new Date(day+'T00:00:00Z');date.setUTCDate(date.getUTCDate()+1);return date.toISOString().slice(0,10);
}
export function leavePayload(values,person){
 const {saat_belirle,baslangic_saati,bitis_saati,...result}=values;
 const hours=saat_belirle||values.tur==='SAATLIK';
 return {...result,kisi:person,baslangic:`${values.baslangic}T${hours?baslangic_saati:'00:00'}:00+03:00`,bitis:`${hours?values.bitis:nextDay(values.bitis)}T${hours?bitis_saati:'00:00'}:00+03:00`};
}
export const LEAVE_TYPES=[{value:'YILLIK',text:'Yıllık İzin'},{value:'SAATLIK',text:'Saatlik İzin'},{value:'MAZERET',text:'Mazeret İzni'}];
export function overtimeTargets(refs,person){
 return ['IS','GOREV'].flatMap(tur=>(refs[tur]??[]).filter(r=>(r.kisi===person||r.kisiler?.includes(person))&&r.tur!=='ONAY'&&r.durum!=='IPTAL').map(r=>({tur,kimlik:r.kimlik,ad:r.ad??r.islem??r.is_tanimi??'İş'})));
}

// Sekiz rakamla yazma, takvim ve dolu gün/ay/yıl bölümünün üzerine yazma.
export function maskTemporal(text,kind){
 const digits=String(text).replace(/\D/g,'').slice(0,kind==='date'?8:kind==='time'?4:12);
 const sizes=kind==='time'?[2,2]:kind==='date'?[2,2,4]:[2,2,4,2,2];
 let at=0,out='';
 for(let i=0;i<sizes.length&&at<digits.length;i++){
  if(i)out+=kind==='time'||i===4?':':i===3?' ':'.';
  out+=digits.slice(at,at+sizes[i]);at+=sizes[i];
 }
 return out;
}
export function bindTemporalInput(input){
 const kind=input.dataset.temporal;
 if(!kind)return;
 const ranges=kind==='time'?[[0,2],[3,5]]:kind==='date'?[[0,2],[3,5],[6,10]]:[[0,2],[3,5],[6,10],[11,13],[14,16]];
 let replace=false,typing=false,selectedPart=null;
 const selectPart=()=>{
  if(!validTemporal(parseTemporal(input.value,kind),kind))return;
  const at=input.selectionStart??0,part=ranges.find(([a,b])=>at<=b)??ranges.at(-1);
  input.setSelectionRange(...part);selectedPart=part;replace=true;
 };
 input.addEventListener('click',selectPart);
 input.addEventListener('focus',()=>{if(validTemporal(parseTemporal(input.value,kind),kind)){input.select();replace=false;}});
 input.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||['ArrowLeft','ArrowRight','Home','End','Backspace','Delete'].includes(e.key)){replace=false;typing=false;selectedPart=null;}});
 input.addEventListener('beforeinput',e=>{
  if(e.inputType!=='insertText'||!/^\d$/.test(e.data??''))return;
  // Chrome seçili yazıya tıklamadan sonra imleci gecikmeli daraltabilir.
  const [start,end]=replace&&selectedPart?selectedPart:[input.selectionStart,input.selectionEnd];
  if(replace&&start!==end){
   e.preventDefault();input.setRangeText(e.data,start,end,'end');replace=false;typing=true;
   input.dispatchEvent(new Event('input',{bubbles:true}));return;
  }
 });
 input.addEventListener('input',()=>{
  // Bölüm düzenlemede ay/yılın kalan kısmını kaydırma.
  const full=input.value.match(kind==='date'?/^(\d{1,2})\.(\d{1,2})\.(\d{1,4})$/:kind==='time'?/^(\d{1,2}):(\d{1,2})$/:/^(\d{1,2})\.(\d{1,2})\.(\d{1,4}) (\d{1,2}):(\d{1,2})$/);
  if(typing&&full){
   const at=input.selectionStart,part=ranges.find(([a,b])=>at<=b)??ranges.at(-1);
   if(at===part[1]){const next=ranges[ranges.indexOf(part)+1];if(next){input.setSelectionRange(...next);selectedPart=next;replace=true;}typing=false;}
   return;
  }
  const before=input.value.slice(0,input.selectionStart).replace(/\D/g,'').length;
  input.value=maskTemporal(input.value,kind);
  let cursor=0,count=0;while(cursor<input.value.length&&count<before){if(/\d/.test(input.value[cursor]))count++;cursor++;}
  if(/[.: ]/.test(input.value[cursor]??''))cursor++;
  input.setSelectionRange(cursor,cursor);
 });
 input.addEventListener('blur',()=>{
  const pattern=kind==='date'?/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/:kind==='time'?/^(\d{1,2}):(\d{1,2})$/:/^(\d{1,2})\.(\d{1,2})\.(\d{4}) (\d{1,2}):(\d{1,2})$/;
  const parts=input.value.match(pattern);
  if(parts){input.value=maskTemporal(parts.slice(1).map(v=>v.padStart(2,'0')).join(''),kind);input.dispatchEvent(new Event('input',{bubbles:true}));}
  typing=false;replace=false;
 });
}

// Tek Tab durağı; Alt+Down ile yerel takvim. Fare tıklamasından önce de eşitlenir.
export function bindDatePicker(text,picker){
 if(!text||!picker)return;
 picker.tabIndex=-1;
 const sync=()=>{const value=parseTemporal(text.value,'date');picker.value=validTemporal(value,'date')?value:'';};
 text.addEventListener('input',sync);
 text.addEventListener('keydown',e=>{if(e.altKey&&e.key==='ArrowDown'){e.preventDefault();sync();try{picker.showPicker?.();}catch{}}});
 picker.addEventListener('pointerdown',sync);
 picker.addEventListener('click',()=>{sync();try{picker.showPicker?.();}catch{}});
 picker.addEventListener('change',()=>text.focus());
 sync();
}
