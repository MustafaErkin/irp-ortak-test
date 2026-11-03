import {OPERATIONS} from './actions.js';

const systemTitles={'AYAR.SAAT_KAYDIRDIM':'Test Saatini Değiştir','KURULUM.TAMAMLADIM':'Kurulumu Tamamla'};
let displayResolver=()=>null;
export function setDisplayResolver(resolve){displayResolver=resolve;}

// Kimlikler işlem verisinde kalır; yalnız görünen yazı adlarla anlatılır.
export function displayText(value,resolve=displayResolver,seen=new Set()){
 const named=(id,fallback)=>{
  if(seen.has(id))return fallback;
  const name=resolve(id);
  return name&&name!==id?displayText(name,resolve,new Set([...seen,id])):fallback;
 };
 return String(value??'').replace(/\bK\d{3}-\d{10}-[A-Z](?:\/[A-Za-z0-9_-]+)*\b/g,id=>named(id,'İlgili İş'))
  .replace(/\bK\d{3}\b/g,id=>named(id,'Çalışan'))
  .replace(/\b[A-Z][A-Z0-9_]+\.[A-Z][A-Z0-9_]+\b/g,code=>OPERATIONS[code]?.title??systemTitles[code]??code);
}

export function formatVisible(root){
 if(!root)return;
 const walker=root.ownerDocument.createTreeWalker(root,4);let node;
 while((node=walker.nextNode())){
  if(node.parentElement?.closest('script,style,textarea,[contenteditable]'))continue;
  const text=displayText(node.nodeValue);if(text!==node.nodeValue)node.nodeValue=text;
 }
 root.querySelectorAll('[title],[aria-label],[placeholder]').forEach(el=>{
  for(const key of ['title','aria-label','placeholder'])if(el.hasAttribute(key))el.setAttribute(key,displayText(el.getAttribute(key)));
 });
}
