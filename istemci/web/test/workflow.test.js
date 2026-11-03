import test from 'node:test';
import assert from 'node:assert/strict';
import {Workflow} from '../workflow.js';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
test('yavaş açılan işlemde çift tıklama tek pencere üretir; kapanınca yeniden açılır',async()=>{
 const flow=Object.create(Workflow.prototype),ready=deferred();let calls=0;
 const dialog=new EventTarget();flow.runOperation=async()=>{calls++;await ready.promise;return dialog;};
 const first=flow.operation('PROJE.ACTIM');await flow.operation('PROJE.ACTIM');assert.equal(calls,1);
 ready.resolve();await first;await flow.operation('PROJE.ACTIM');assert.equal(calls,1);
 dialog.dispatchEvent(new Event('close'));await flow.operation('PROJE.ACTIM');assert.equal(calls,2);
});
test('açılış hatasında kilit kalmaz',async()=>{
 const flow=Object.create(Workflow.prototype);let calls=0;flow.runOperation=async()=>{if(++calls===1)throw new Error('okunamadı');};
 await assert.rejects(flow.operation('IZIN.TALEP_ETTIM'),/okunamadı/);await flow.operation('IZIN.TALEP_ETTIM');assert.equal(calls,2);
});
