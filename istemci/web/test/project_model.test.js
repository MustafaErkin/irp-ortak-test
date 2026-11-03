import test from 'node:test';
import assert from 'node:assert/strict';
import {projectIssues,projectRange,planningTask,projectLabel} from '../project_model.js';
import {maskTemporal} from '../temporal.js';
const project={kimlik:'P1',ad:'Makine',kod:'PR1',aktif:true,sorumlu:'K004',kod_gecmisi:[{kod:'ESKI'}]};
test('proje kod geçmişi kapandıktan veya değiştikten sonra da korunur',()=>{
 for(const kod of ['PR1','ESKI'])assert.equal(projectIssues('PROJE.ACTIM',{kod},{projects:[{...project,aktif:false}]} )[0].path,'kod');
 assert.deepEqual(projectIssues('PROJE.ACTIM',{kod:'YENI'},{projects:[project]}),[]);
});
test('etap tarih hatası düzenlemede doğru alana, kapanış engeli iş adına bağlanır',()=>{
 const issue=projectIssues('ETAP.DEGISTIRDIM',{degisenler:{bitis:'2026-11-02'}},{record:{proje:'P1',baslangic:'2026-11-03'},projects:[project]});
 assert.equal(issue[0].path,'degisenler.bitis');
 assert.match(projectIssues('PROJE.KAPATTIM',{}, {record:project,projects:[project],tasks:[{proje:'P1',ad:'Çizimleri Hazırla',durum:'ATANDI'}]})[0].message,/Çizimleri Hazırla/);
});
test('plan revizyonu gerekçe ister; ilk onay etap ister; kapalı proje görünür durum taşır',()=>{
 assert.match(projectIssues('PLAN.ONAYLADIM',{proje:'P1'},{projects:[project]})[0].message,/etap/);
 assert.equal(projectIssues('PLAN.ONAYLADIM',{proje:'P1'},{projects:[project],stages:[{proje:'P1'}],plan:{surumler:[{}]}})[0].path,'gerekce');
 assert.match(projectLabel({...project,aktif:false}),/PR1.*Kapalı/);
});
test('görev seçilen ikinci etabı ve sorumlusunu taşır; dönem bütün etapları kapsar',()=>{
 const stage={kimlik:'E2',ad:'Montaj',sorumlu:'K009',baslangic:'2026-12-01',bitis:'2027-01-05'};
 assert.deepEqual(planningTask(stage,project),{ad:'Montaj Etabı Planlama',is_tanimi:'Montaj etabının tarihlerini ve hedef emeğini düzenleyin. Hazırladığınız planı değerlendirmeye sunun.',nereye:'PROJE',proje:'P1',etap:'E2',kisi:'K009',dosya_gerekli:false});
 assert.deepEqual(projectRange({...project,baslangic_tarihi:'2026-11-01'},[stage],'2026-11-02'),{bas:'2026-11-01',bit:'2027-01-05'});
});
test('rakamları doğal tarih/saat görünümüne çevirir; yarım yıl tamamlanmış sayılmaz',()=>{
 assert.equal(maskTemporal('07112026','date'),'07.11.2026');assert.equal(maskTemporal('07.11.2','date'),'07.11.2');assert.equal(maskTemporal('0930','time'),'09:30');
});
