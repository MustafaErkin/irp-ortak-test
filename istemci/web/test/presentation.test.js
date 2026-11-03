import test from 'node:test';
import assert from 'node:assert/strict';
import {displayText} from '../presentation.js';
import {notificationId,notificationContent} from '../notifications.js';
import {eventTable} from '../olaylar.js';
import {summaryTasks} from '../daily_summary.js';

const visible=html=>html.replace(/<[^>]*>/g,' ');
test('gömülü kimlikler ve kişi/olay kodları okunur ad olur; iş verisi değişmez',()=>{
 const source='Onay: K001-2610300002-U / K041 / GOREV.TAMAMLADIM',names={'K001-2610300002-U':'Etapları Planla',K041:'Ofis Çalışanı'};
 assert.equal(displayText(source,id=>names[id]),'Onay: Etapları Planla / Ofis Çalışanı / Görevi Teslim Et');
 assert.equal(source,'Onay: K001-2610300002-U / K041 / GOREV.TAMAMLADIM');
 assert.equal(displayText('K001-2610300002-U',id=>id.startsWith('K001-')?source:null),'Onay: İlgili İş / Çalışan / Görevi Teslim Et');
 assert.equal(displayText('2611001 — Montaj İstasyonu'),'2611001 — Montaj İstasyonu');
 assert.equal(displayText('TEKNIK.PDF ve GOREV.PDF'),'TEKNIK.PDF ve GOREV.PDF');
 assert.equal(displayText('KURULUM.TAMAMLADIM'),'Kurulumu Tamamla');
});
test('gün sonu kaynak adında da kimlik olsa görünür metne sızmaz',()=>{
 const id='K041-2610300003-U',rows=summaryTasks({gorevler:{[id]:{durum:'BITTI'}}},[{kimlik:id,ad:'Onay: K001-2610300002-U'}]);
 assert.doesNotMatch(rows[0].ad,/K\d{3}/);
 assert.equal(rows[0].kimlik,id);
});
test('çekirdek görüldü dış kimliği ve modül kimliği aynı sözleşmede korunur',()=>{
 const row={doguran_olay:'K001-2610300002-U',kural:'R30',alici:'K004'};
 assert.equal(notificationId(row),'K001-2610300002-U/R30/K004');
 assert.equal(notificationId({...row,kimlik:'M3/KABUL/NESNE%3AParca/K004'}),'M3/KABUL/NESNE%3AParca/K004');
 assert.equal(notificationId({}),null);
});
test('bildirimde ham kişi kodu yerine gerekçe ve ilgili iş görünür',()=>{
 const row={kaynak:'CEKIRDEK',doguran_olay:'K001-2610300002-U',kural:'R30',alici:'K004',metin:'K041'};
 const content=notificationContent(row,()=> 'Ofis Çalışanı',[{doguran_olay:row.doguran_olay,kisi:'K041',ad:'Teknik Resmi Hazırlayın'}]);
 assert.equal(content.title,'Yeni İş Ataması');
 assert.match(content.text,/Ofis Çalışanı.*yeni iş atandı.*Teknik Resmi Hazırlayın/);
 assert.doesNotMatch(content.text,/K041|R30|GOREV\./);
 assert.equal(notificationContent({kaynak:'M3',kural:'R30',metin:'Parçanın teklifi hazır.'}).text,'Parçanın teklifi hazır.');
});
test('bağımsız olay penceresi de yalnız işlemin anlaşılır adını gösterir',()=>{
 const html=eventTable([{olay:'K001-2610300002-U',kim:'K001',ad:'CEO',eylem:'GOREV.ATADIM',ulasma:'2026-10-31T10:00:00+03:00',neyin_ustunde:[{etiket:'Onay: K001-2610300002-U'}]}]);
 assert.match(visible(html),/Görev Ata/);
 assert.doesNotMatch(visible(html),/K\d{3}|GOREV\.ATADIM|Olay Kimliği|[Bb]ulut/);
});
