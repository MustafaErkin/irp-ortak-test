"""T30 gerçek SQL kabulü. Yalnız yeni, geçici test firmasını kullanır.

Yerel PostgreSQL erişimi gerektiğinden kaynak hazırlığı tek başına geçiş değildir.
Canlı firma, dosya deposu ve telefon bu betikle değiştirilmez.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from yerel_api import Database


def run():
    db = Database(empty=True)
    letters, counters = {}, defaultdict(int)
    def read(person, kind, target=None):
        return db.rpc(person, 'oku', {'veri':kind,'hedef':target,'g':{}})['deger']
    def send(person, code, data, targets=(), expected='BASARILI'):
        if person not in letters:
            letters[person] = db.rpc(person,'cihaz_kaydol',{'cihaz':'tur1-sql-'+person})
        now = str(db.rpc(person,'simdi',{}))
        stamp = datetime.fromisoformat(now)
        counters[person] += 1
        hs = [{'tur':kind,'kimlik':key,'surum':read(person,kind,key).get('surum')} for kind,key in targets]
        event = {'olay_kimligi':f'{person}-{stamp:%y%m%d}{counters[person]:04d}-{letters[person]}',
                 'kim':person,'adina':None,'cihaz':'MAS-'+person,'oldugu_an':now,'bildigi_son_hal_ani':now,
                 'eylem_kodu':code,'eylem_versiyonu':1,'girdiler':data,'neyin_ustunde':hs,'kanit':[],
                 'duzelttigi_olay':None,'giris_sekli':'LISTE','pc_ulasma_ani':None,'saat_dilimi':'+03:00',
                 'uygulama_surumu':'WEB-0.1.0','yol':'DISARIDA'}
        result = db.rpc(person,'olay_ekle',{'olay':event})
        assert result['sonuc']==expected, (code,result)
        db.tick()
        return event['olay_kimligi'],result
    try:
        now = datetime.fromisoformat(str(db.rpc('K001','simdi',{})))
        today = now.date().isoformat()
        tomorrow = (now.date()+timedelta(days=1)).isoformat()
        week = (now.date()+timedelta(days=7)).isoformat()
        # Kurulum ana verisi, boş iş firmasında kullanılabilir.
        assert any(t.get('kod',t.get('kimlik'))=='BELGE' for t in read('K001','WEB_BAGLAM')['nesne_turleri'])
        assert {r['kod'] for r in read('K041','KODLAR') if r.get('liste')=='IZIN'} >= {'YILLIK','SAATLIK','MAZERET'}
        send('K001','PROJE.ACTIM',{'kod':'KONTROL-T1','ad':'Tur 1 Teknik Kabul','sorumlu':'K004','baslangic_tarihi':today,'teslim_tarihi':week})
        stage,_=send('K001','ETAP.TANIMLADIM',{'proje':'KONTROL-T1','ad':'Hazırlık','birim':'MEK_TASARIM','sorumlu':'K004','baslangic':today,'bitis':week,'hedef_saat':8})
        assignment,_=send('K004','GOREV.ATADIM',{'gorevler':[{'ad':'Teslim Denemesi','nereye':'PROJE','proje':'KONTROL-T1','etap':stage,'kisi':'K041','teslim_tarihi':week,'zaman_degeri':1,'zorluk':1,'onay_gerekli':True,'onaylayan':'K004','dosya_gerekli':False}]})
        task=assignment+'/1'
        notifications=read('K041','BILDIRIMLER','K041')
        assert any(b.get('hedef')==task and b.get('is_akisi')=='ATAMA' and not b.get('gorulme_ani') for b in notifications)
        send('K041','GOREV.KABUL_ETTIM',{},[('GOREV',task)])
        assert any(b.get('hedef')==task and b.get('gorulme_ani') for b in read('K041','BILDIRIMLER','K041'))
        send('K041','GOREV.TAMAMLADIM',{},[('GOREV',task)])
        assert any(b.get('hedef')==task and b.get('is_akisi')=='TESLIM' for b in read('K004','BILDIRIMLER','K004'))
        send('K004','GOREV.ONAYLADIM',{},[('GOREV',task)])
        assert read('K041','GOREV',task)['durum']=='BITTI'
        assert any(b.get('hedef')==task and b.get('is_akisi')=='ONAY' for b in read('K041','BILDIRIMLER','K041'))
        leave={'kisi':'K041','tur':'SAATLIK','baslangic':tomorrow+'T10:00:00+03:00','bitis':tomorrow+'T11:00:00+03:00','gerekce':'Teknik kabul'}
        _,result=send('K004','IZIN.TALEP_ETTIM',leave,expected='REDDEDILDI');assert result['kod']=='YETKI'
        leave_id,_=send('K041','IZIN.TALEP_ETTIM',leave)
        send('K004','IZIN.ONAYLADIM',{'hedef':leave_id})
        assert next(x for x in read('K041','IZIN','K041') if x['kimlik']==leave_id)['durum']=='ONAYLI'
        overtime,_=send('K004','EK_MESAI.PLANLADIM',{'kisi':'K041','tarih':tomorrow,'baslangic':'21:00','bitis':'22:00','aciklama':'Teknik kabul'},[('GOREV',task)])
        send('K004','EK_MESAI.IPTAL_ETTIM',{'hedef':overtime,'gerekce':'Deneme tamamlandı'})
        # İki diğer tür, kendi iptali, yönetici reddi ve izin çakışması.
        yearly={**leave,'tur':'YILLIK','baslangic':tomorrow+'T00:00:00+03:00','bitis':week+'T00:00:00+03:00'}
        yearly_id,_=send('K041','IZIN.TALEP_ETTIM',yearly)
        _,rejected=send('K004','IZIN.ONAYLADIM',{'hedef':yearly_id},expected='REDDEDILDI')
        assert rejected['kod']=='DURUM'
        send('K041','IZIN.IPTAL_ETTIM',{'hedef':yearly_id})
        excuse_id,_=send('K041','IZIN.TALEP_ETTIM',{**leave,'tur':'MAZERET'})
        send('K004','IZIN.REDDETTIM',{'hedef':excuse_id,'gerekce':'Aynı gün izniniz var.'})
        statuses={x['kimlik']:x['durum'] for x in read('K041','IZIN','K041')}
        assert statuses[yearly_id]=='IPTAL' and statuses[excuse_id] in ('RET','REDDEDILDI')
        # Gerçekleşen mesai: bitmiş son yedi gün; tekrar/gelecek/normal mesai reddi.
        yesterday=(now.date()-timedelta(days=1)).isoformat()
        past={'kisi':'K041','tarih':yesterday,'baslangic':'21:00','bitis':'22:00','aciklama':'Gerçekleşen'}
        send('K004','EK_MESAI.ONAYLADIM',past,[('GOREV',task)])
        for code,values in [('EK_MESAI.ONAYLADIM',past),('EK_MESAI.ONAYLADIM',{**past,'tarih':tomorrow}),('EK_MESAI.PLANLADIM',{**past,'tarih':tomorrow,'baslangic':'10:00','bitis':'11:00'})]:
            _,rejected=send('K004',code,values,[('GOREV',task)],expected='REDDEDILDI');assert rejected['kod']=='DURUM'
        print('Tur 1 SQL: üç izin türü, onay/ret/iptal/çakışma, ek mesai geçmiş/gelecek/tekrar geçti.',flush=True)
        phone=read('K017','TELEFON','K017');assert phone['calisma_penceresi']['gun']==today
        # Atölye: onay bekleten/bekletmeyen ve onaysız teslim yolları.
        send('K017','MESAI.GIRDIM',{})
        for approval, hold in [(True,True),(True,False),(False,False)]:
            created,_=send('K004','IS.TANIMLADIM',{'isler':[{'islem':'Atölye Kabul','birim':'IMALAT','nereye':'PROJE','proje':'KONTROL-T1','tur':'SURELI','tahmini_sure_dk':30,'teslim_tarihi':week,'onay_gerekli':approval,'onay_beklet':hold}]})
            job=created
            send('K009','IS.ATADIM',{'kisi':'K017','sira':1},[('IS',job),('LISTE','K017')])
            assert any(b.get('hedef')==job and b.get('is_akisi')=='ATAMA' for b in read('K017','BILDIRIMLER','K017'))
            send('K017','IS.BASLADIM',{},[('IS',job)])
            send('K017','IS.TAMAMLADIM',{},[('IS',job)])
            if approval:
                state=read('K009','IS',job);assert state['durum']=='ONAY_BEKLIYOR'
                owner=state['atayan']
                notifications=[b for b in read(owner,'BILDIRIMLER',owner) if b.get('hedef')==job and b.get('is_akisi')=='TESLIM']
                assert len(notifications)==1
                if not hold:
                    send(owner,'IS.REDDETTIM',{'not':'Düzeltme denemesi'},[('IS',job)])
                    assert any(b.get('hedef')==job and b.get('is_akisi')=='RET' for b in read('K017','BILDIRIMLER','K017'))
                    send('K017','IS.BASLADIM',{},[('IS',job)])
                    send('K017','IS.TAMAMLADIM',{},[('IS',job)])
                send(owner,'IS.ONAYLADIM',{},[('IS',job)])
                assert any(b.get('hedef')==job and b.get('is_akisi')=='ONAY' for b in read('K017','BILDIRIMLER','K017'))
            assert read('K009','IS',job)['durum']=='BITTI'
        print('Tur 1 SQL: atölye onaylı/bekletmeli/bekletmesiz/onaysız, ret/yeniden teslim ve bildirim zinciri geçti.',flush=True)
        # Takvim aralıklarının gerçekten sunucudan geldiğini başka günlerde doğrula.
        day=now.date()+timedelta(days=1)
        while day.weekday()!=0:day+=timedelta(days=1)
        driver=db.driver()
        try:
            for weekday in (day,day+timedelta(days=6)):
                moment=weekday.isoformat()+'T09:00:00+03:00'
                driver._cagir('SELECT test.saat(%s,%s,true)',(moment,moment),kontrol=True)
                db.tick()
                window=read('K017','TELEFON','K017')['calisma_penceresi']
                assert window['gun']==weekday.isoformat()
                if weekday.weekday()==0:
                    assert len(window['mesai'])==1 and len(window['calisma'])>1,window
                else:assert not window['mesai'] and not window['calisma'],window
        finally:driver.kapat()
        print('Tur 1 SQL: telefon hafta içi/sabit mola ve pazar pencereleri geçti.',flush=True)
        print('Tur 1 SQL: ana veri, atama/kabul/teslim/onay bildirimleri, kendi izni ve yetkisiz talep, ek mesai plan/iptal, telefon penceresi geçti.')
    finally:
        db.close()

if __name__=='__main__':
    run()
