import test from 'node:test';
import assert from 'node:assert/strict';
import {Workflow} from '../workflow.js';
test('tamamlanan sayacı İstanbul gününde değişir; açık görev ve geçmiş korunur',()=>{
 const rows=[{kimlik:'a',kisi:'K1',durum:'ACIK'},{kimlik:'b',kisi:'K1',durum:'ATANDI'},{kimlik:'c',kisi:'K1',durum:'BITTI',bitis_ani:'2026-11-01T21:30:00Z'},{kimlik:'d',kisi:'K1',durum:'BITTI',bitis_ani:'2026-11-01T20:59:00Z'}];
 let tabs,visible;const w={refs:{GOREV:rows},c:{person:'K1',today:'2026-11-02'},state:{tab:'done'},tabs:r=>(tabs=r,''),taskTable:r=>(visible=r,'')};
 Workflow.prototype.tasks.call(w);
 assert.equal(tabs[0][1],'Kabul Bekleyenler (1)');assert.equal(tabs[1][1],'İşlerim (1)');assert.equal(tabs[2][1],'Tamamlananlar (Bugün: 1)');assert.equal(visible.length,1);
 w.c.today='2026-11-03';Workflow.prototype.tasks.call(w);assert.equal(tabs[1][1],'İşlerim (1)');assert.equal(tabs[2][1],'Tamamlananlar (Bugün: 0)');assert.equal(visible.length,0);
 w.state.doneDay='';Workflow.prototype.tasks.call(w);assert.equal(visible.length,2);
});
