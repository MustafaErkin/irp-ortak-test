// Modül ekranlarında ortak form/tablo/dosya davranışı. İş hesabı veya yeni oturum içermez.
export function editorTools(ui){
 const defs=new Map(),e=ui.esc;
 function options(rows){return (rows??[]).map(r=>typeof r==='string'?{value:r,label:r}:r);}
 function field(d,value,cell=false){
  const type=d.type??'text',name=e(d.key),v=value??d.default??'',label=cell?'':`<span>${e(d.label)}</span>`;
  const attrs=`name="${name}" data-editor-col="${name}" ${d.required?'required':''} ${d.readonly?'readonly':''} ${d.disabled?'disabled':''}`;
  let control;
  if(type==='select')control=`<select ${attrs} ${d.multiple?'multiple':''}>${d.multiple?'':`<option value="">${e(d.blank??'Seçin')}</option>`}${options(d.options).map(r=>`<option value="${e(r.value)}" ${(d.multiple?(Array.isArray(v)?v:[]).map(String).includes(String(r.value)):String(r.value)===String(v))?'selected':''}>${e(r.label)}</option>`).join('')}</select>`;
  else if(type==='textarea')control=`<textarea ${attrs} rows="${d.rows??3}">${e(v)}</textarea>`;
  else if(type==='checkbox')control=`<input type="checkbox" ${attrs} ${v?'checked':''}>`;
  else control=`<input ${attrs} type="${type==='integer'?'number':type}" ${type==='file'?'':`value="${e(v)}"`} ${d.min!=null?`min="${e(d.min)}"`:''} ${['number','integer'].includes(type)?`step="${type==='integer'?'1':e(d.step??'0.01')}"`:''} ${d.placeholder?`placeholder="${e(d.placeholder)}"`:''}>`;
  return `<label class="field ${type==='checkbox'?'module-check':''}">${label}${control}</label>`;
 }
 function fields(list,value={}){return '<div class="form-grid">'+list.map(d=>field(d,value[d.key])).join('')+'</div>';}
 function rowHtml(name,columns,row={}){return `<tr data-editor-row>${columns.map(d=>`<td ${d.type==='hidden'?'hidden':''}>${field(d,row[d.key],true)}</td>`).join('')}<td><button type="button" class="btn small" data-editor-remove aria-label="Satırı Kaldır">Kaldır</button></td></tr>`;}
 function rows(name,label,columns,values=[],{add=true}={}){
  defs.set(name,columns);
  return ui.panel(label,`<div class="table-wrap"><table class="data-table module-edit-table" data-editor-table="${e(name)}"><thead><tr>${columns.map(c=>`<th ${c.type==='hidden'?'hidden':''}>${e(c.label)}</th>`).join('')}<th></th></tr></thead><tbody>${values.map(r=>rowHtml(name,columns,r)).join('')}</tbody></table></div>`,add?`<button type="button" class="btn small" data-editor-add="${e(name)}">Satır Ekle</button>`:'');
 }
 function rowAction(target,scope){
  const remove=target.closest('[data-editor-remove]');if(remove){remove.closest('tr').remove();return true;}
  const add=target.closest('[data-editor-add]');if(add){const name=add.dataset.editorAdd,table=scope.querySelector(`[data-editor-table="${CSS.escape(name)}"]`);table.querySelector('tbody').insertAdjacentHTML('beforeend',rowHtml(name,defs.get(name)));return true;}
  return false;
 }
 function value(el,d){
  if(d.type==='checkbox')return !!el?.checked;
  if(d.type==='file')return el?.files?.[0]??null;
  if(d.multiple)return [...(el?.selectedOptions??[])].map(o=>d.numeric?Number(o.value):o.value);
  const v=el?.value??'';
  if(v==='')return d.nullable?null:d.type==='integer'?0:v;
  return d.type==='integer'||d.numeric?Number(v):v;
 }
 function read(scope,list){return Object.fromEntries(list.map(d=>[d.key,value(scope.querySelector(`[data-editor-col="${CSS.escape(d.key)}"]`),d)]));}
 function readRows(scope,name){return [...scope.querySelectorAll(`[data-editor-table="${CSS.escape(name)}"] tbody tr`)].map(row=>read(row,defs.get(name)));}
 async function fileBody(file,kayit){
  if(!file)return null;if(!file.size||file.size>1048576)throw Error('Dosya boş olmamalı ve en fazla 1 MB olmalı.');
  const bytes=new Uint8Array(await file.arrayBuffer());let text='';for(const byte of bytes)text+=String.fromCharCode(byte);
  return {kayit,ad:file.name,tur:file.type||'application/octet-stream',icerik_base64:btoa(text)};
 }
 function download(data,name){
  const blob=data instanceof Blob?data:new Blob([Uint8Array.from(atob(data.icerik_base64),x=>x.charCodeAt(0))],{type:data.tur||'application/octet-stream'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name||data.ad||'belge';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return {field,fields,rows,rowAction,read,readRows,fileBody,download};
}
