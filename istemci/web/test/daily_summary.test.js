import test from 'node:test';
import assert from 'node:assert/strict';
import {summaryTime,summaryTasks,dailySummary} from '../daily_summary.js';
import {navigationCounts, navigationReads} from '../navigation.js';

test('gün özeti adları çözerken geçmiş özetin zaman ve durumunu güncel görevle ezmez',()=>{
 const summary={gorevler:{G1:{durum:'ACIK',kabul_ani:null,teslim_ani:null}}};
 const [row]=summaryTasks(summary,[{kimlik:'G1',ad:'Teknik Resim',durum:'BITTI',kabul_ani:'2026-10-31T10:00:00+03:00',teslim_ani:'2026-10-31T11:00:00+03:00'}]);
 assert.equal(row.ad,'Teknik Resim');assert.equal(row.durum,'ACIK');assert.equal(row.kabul_ani,null);assert.equal(row.teslim_ani,null);
});
test('aynı İstanbul gününde yalnız saat, farklı günde tarih ve saat gösterilir',()=>{
 assert.equal(summaryTime('2026-10-30T22:15:00Z','2026-10-31'),'01:15');
 assert.match(summaryTime('2026-10-30T10:00:00+03:00','2026-10-31'),/30.*2026.*10:00/);
 assert.equal(summaryTime(null,'2026-10-31'),'—');
});
test('gün özeti ham olay adlarını kullanıcı metnine taşımaz ve görevleri tablo yapar',()=>{
 const id='K041-2610300003-U',w={state:{day:'2026-10-30',person:'K004'},refs:{GOREV:[{kimlik:id,ad:'Onay: Teknik Resim',tur:'ONAY',proje:'P1',etap:'E1'}],IS:[]},name:x=>({K004:'Yönetici',P1:'Montaj İstasyonu',E1:'Ofis'})[x]??'—',value:()=>[]};
 const html=dailySummary(w,{kisi:'K004',gun:'2026-10-30',onay_durumu:'ONAY_GEREKMIYOR',ozet:{gorevler:{[id]:{durum:'BITTI',kabul_ani:null,teslim_ani:null,bitis_ani:'2026-10-30T19:48:00+03:00'}}}});
 const visible=html.replace(/<[^>]*>/g,' ');
 assert.match(html,/<table/);assert.match(visible,/Onay: Teknik Resim/);assert.match(visible,/19:48/);assert.match(visible,/Gerekmiyor/);
 assert.ok(!visible.includes(id));assert.ok(!html.includes('İşlem Ayrıntısı'));
});
test('sol menü sayıları yalnız ilgili kişinin bekleyen işlerinden gelir',()=>{
 const c={person:'K041',cached:(v,h,g)=>({ONAY_LISTESI:[{},{}],BILDIRIMLER:[{}, {gorulme_ani:'2026-10-30'}],GUN_ISLERI:[{}],WEB_GOREVLER:[{kisi:'K041',durum:'ATANDI'},{kisi:'K041',durum:'BITTI'},{kisi:'K041',tur:'ONAY',durum:'ACIK'},{kisi:'K004',durum:'ACIK'}]})[v]};
 assert.deepEqual(navigationCounts(c),{tasks:1,approvals:2,notifications:1});
 assert.ok(navigationReads('K041').some(([v,,g])=>v==='WEB_GOREVLER'&&g?.kisi==='K041'));
 assert.deepEqual(navigationCounts({...c,readonly:true}),{});
});
