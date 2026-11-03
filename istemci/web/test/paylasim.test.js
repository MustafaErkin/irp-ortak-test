import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePeople,accessKey} from '../erisim.js';
const people=()=>['K001','K004','K009','K041','K017','K031'].map(kod=>({kod,sifre:'yalniz-test-sifresi',etiket:'aktarilan ad',yetki:'yonetici'}));
test('paylaşım yalnız dört web profilini alır, dış dosyadan rol/alan enjekte edilmez',()=>{
 const result=validatePeople(people());
 assert.deepEqual(result.map(p=>p.kod),['K001','K004','K009','K041']);
 assert.equal(result[0].etiket,'CEO');
 assert.equal(result.some(p=>'yetki' in p),false);
});
test('eksik, çoğul veya şifresiz profil sessizce kullanılmaz',()=>{
 assert.throws(()=>validatePeople(null));
 assert.throws(()=>validatePeople(people().slice(1)));
 assert.throws(()=>validatePeople([...people(),people()[0]]));
 const rows=people();rows[0].sifre='';assert.throws(()=>validatePeople(rows));
});
test('farklı senaryonun erişimi aynı anahtara yazılmaz',()=>{
 assert.notEqual(accessKey({senaryo:'a'}),accessKey({senaryo:'b'}));
});
