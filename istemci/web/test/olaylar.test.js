import test from 'node:test';
import assert from 'node:assert/strict';
import {EventReader} from '../olaylar.js';

test('bağımsız izleyici önceki işlerden sonra başlar ve aynı olayı iki kez göstermez',async()=>{
 const calls=[],responses=[{son:85,olaylar:[{olay:'kurulum',sira:85}]},{son:87,olaylar:[{olay:'proje',sira:86},{olay:'etap',sira:87}]},{son:88,olaylar:[{olay:'etap',sira:87},{olay:'atama',sira:88}]}];
 const reader=new EventReader(async(_,g)=>{calls.push(g.sonra);return responses.shift();});
 assert.deepEqual(await reader.read(),[]);
 assert.equal(reader.newIds.size,0);
 assert.deepEqual((await reader.read()).map(r=>r.olay),['etap','proje']);
 assert.deepEqual([...reader.newIds].sort(),['etap','proje']);
 assert.deepEqual((await reader.read()).map(r=>r.olay),['atama','etap','proje']);
 assert.deepEqual([...reader.newIds],['atama']);
 assert.deepEqual(calls,[0,85,87]);
 reader.clear();
 assert.deepEqual(reader.rows,[]);
 assert.equal(reader.newIds.size,0);
 assert.equal(reader.cursor,88);
});

test('bağlantı kesilince izleyicinin okuma yeri ve görülen olaylar korunur',async()=>{
 let offline=false;
 const reader=new EventReader(async()=>{if(offline)throw Error('Bağlantı');return {son:5,olaylar:[]};});
 await reader.read();reader.rows=[{olay:'teslim',sira:5}];offline=true;
 await assert.rejects(reader.read());
 assert.equal(reader.cursor,5);
 assert.equal(reader.rows[0].olay,'teslim');
});
