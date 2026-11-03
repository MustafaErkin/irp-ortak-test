import unittest,random
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from irp import Saat
from irp.cihaz import Cihaz
from irp.kabul import MATRIS,nesne
from irp.kisi_gunu import CALISAN,kapi
from irp.gorunumler import *
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from .ortak import Duzenek,t,is_id,s1,yaz
from .tur2_ornekler import isaret,iki_kisi,iptal_gorev

def onay_bekleyen():
    f=Duzenek(); f.ata(9); f.ata(2,sira=2); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
    return f,f.calistir(t(22,'09:10'))

class DegismezlerV2(unittest.TestCase):
    def test_I37(self):
        f,d=onay_bekleyen()
        for kod in sorted(CALISAN):
            f.olay('K017',kod,t(22,'09:11'),None if kod.startswith('MESAI') else 9,{'neden':'ARIZA.MAKINE'} if kod=='IS.ARIZA_BILDIRDIM' else {})
            e=f.olaylar[-1]
            for x in e['neyin_ustunde']: x['surum']=-999
            self.assertEqual(yaz(d,e,taze=False)['sonuc'],'BASARILI')
        f.ata(5,zaman=t(22,'09:12')); e=f.olaylar[-1]; e['neyin_ustunde'][0]['surum']=-1
        self.assertEqual(yaz(d,e,taze=False)['kod'],'BAYAT'); self.assertNotIn(e['olay_kimligi'],d.olaylar)
        f.is_olay('ONAYLADIM','09:13',5,'K009'); e=f.olaylar[-1]
        self.assertEqual(yaz(d,e)['kod'],'DURUM'); self.assertNotIn(e['olay_kimligi'],d.olaylar)

    def test_I38(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); s=d.isler[is_id(5)]['surum']
        olaylar=[]
        for kisi in ('K017','K023'):
            f.ata(5,kisi,zaman=t(22,'09:00')); e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=s; olaylar.append(e)
        engel=Barrier(2)
        def gonder(e): engel.wait(); return yaz(d,e,taze=False)
        with ThreadPoolExecutor(max_workers=2) as havuz: sonuclar=list(havuz.map(gonder,olaylar))
        self.assertEqual(sorted(x['sonuc'] for x in sonuclar),['BASARILI','REDDEDILDI'])
        self.assertEqual(sum(is_id(5) in l for l in d.listeler.values()),1)

    def test_I39(self):
        f=s1(); hedef=[e['olay_kimligi'] for e in f.olaylar if e['oldugu_an'] in (t(22,'10:40'),t(22,'10:52'))]
        d=f.calistir(t(22,'11:45'))
        for n,h in enumerate(hedef): isaret(f,h,zaman=t(22,'11:{:02d}'.format(43+n))); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        hic=[e for e in f.olaylar if e['olay_kimligi'] not in hedef and e['eylem_kodu']!='KAYIT.GECERSIZ_SAYDIM']
        self.assertEqual(d.son_hal(),f.calistir(t(22,'11:45'),hic).son_hal())

    def test_I40(self):
        f,g=iki_kisi()
        for saat,beklenen in [('12:40','CALISILIYOR'),('12:52','ONAY_BEKLIYOR'),('13:00','BITTI')]:
            d=f.calistir(t(22,saat)); self.assertEqual(d.isler[g]['durum'],beklenen)
            self.assertEqual(emek(d,g),emek(d,g+'/k1')+emek(d,g+'/k2')); self.assertFalse(any(g in l for l in d.listeler.values()))

    def test_I41(self):
        f=Duzenek(); f.ata(2,'K023'); f.is_olay('MESAI.GIRDIM','07:58',kisi='K023'); f.is_olay('TAMAMLADIM','09:00',2,'K023'); f.ata(5,'K023',2,zaman=t(22,'08:59'))
        beklenen=None
        for tohum in (1,7,42,2026):
            olaylar=list(f.olaylar); random.Random(tohum).shuffle(olaylar); d=f.yeniden_hesapla(t(22,'09:05'),olaylar)
            kume={(v['doguran_olay'],v['kural'],v['alici']) for v in d.bildirimler.values() if v['gecerli']}
            if beklenen is None: beklenen=kume
            self.assertEqual(kume,beklenen)

    def test_I42(self):
        f,g,o=iptal_gorev(); d=f.calistir(t(28,'12:00'))
        self.assertFalse(d.isleme_hatalari); self.assertTrue(d.olcumler); self.assertLessEqual(max(x['tur'] for x in d.olcumler),50)

    def test_I43(self):
        f,g,o=iptal_gorev(); d=f.calistir(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01'); once=deepcopy((d.hassas_ekler,d.ay_kapanislari))
        d.yeniden_kur(); self.assertEqual((d.hassas_ekler,d.ay_kapanislari),once)

    def test_I45_C26(self):
        """C26 TASARIM: A5/T3 ATADIM kapısı hedefteki onaylı başı korumuyor."""
        f,d=onay_bekleyen(); f.ata(5,zaman=t(22,'09:10')); sonuc=yaz(d,f.olaylar[-1])
        self.assertEqual(sonuc.get('kod'),'DURUM')
        self.assertEqual(d.listeler['K017'][0],is_id(9))

    def test_I46(self):
        f=s1(); d=f.calistir(t(22,'11:45')); i=d.isler[is_id(1)]
        for durum in ('CALISMIYOR','MOLADA','ARIZADA','DEVAM_BEKLIYOR','SABIT_MOLADA'):
            self.assertFalse(kapi(dict(durum=durum,acik_is=is_id(1),devam_izni=True),'IS.DEVAM_ETTIM',i,is_id(1)))

    def test_I47(self):
        f=s1(); d=f.calistir(t(22,'14:05')); kayitli=[deepcopy(a) for a in d.araliklar if a['kova'] not in ('TANIMSIZ','GECIS')]
        for saat in ('14:00','14:01'):
            f.olay('K009','IS.SURE_EKLEDIM',t(22,saat),1,{'baslangic':t(22,'08:00'),'bitis':t(22,'11:42'),'aciklama':saat,'is_bitti':False},adina='K017',giris_sekli='ELLE')
            self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual([a for a in d.araliklar if not a['elle'] and a['kova'] not in ('TANIMSIZ','GECIS')],kayitli)
        self.assertTrue(all(a['aciklama']=='14:00' for a in d.araliklar if a['elle']))

    def test_I48_C21(self):
        """C21 TASARIM: silinen çevrimdışı depoda sunucuya ulaşmamış sayaç yeniden üretilir."""
        c=Cihaz('K017','T',Saat(t(22,'09:00'))); ilk=c.olay_kimligi_uret()
        c.depo_kayboldu()
        with self.assertRaises(ConnectionError): c.olay_kimligi_uret()
        c.yeniden_kaydol({'T'})
        self.assertNotEqual(c.olay_kimligi_uret(),ilk)

    def test_I49_kapsam_disina_dokunma(self):
        f=Duzenek(); a=f.gorev_ata(); b=f.gorev_ata(t(21,'17:41'),kisi='K044'); d=f.calistir(t(22,'08:00')); once=d.gorevler[b]
        f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),a); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertIs(d.gorevler[b],once); self.assertLess(d.olcumler[-1]['olay'],len(d.olaylar))
        hal=d.son_hal(); d.yeniden_kur(); self.assertEqual(d.son_hal(),hal)

    def test_I50_kaynaklar_degismez(self):
        d=s1().calistir(t(22,'11:45')); once=deepcopy(dict(d.olaylar)); d.yeniden_kur(); self.assertEqual(dict(d.olaylar),once)


def matris_deneyi(satir,kod):
    def test(self):
        f=Duzenek(); g=f.gorev_ata(onay_gerekli=True,onaylayan='K012'); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); d=f.calistir(t(22,'09:00'))
        kim='K017'; hedef=None; girdiler={}; alan={}
        if satir=='is_duzenle':
            hedef=4; girdiler={'degisenler':{'islem':'Yeni'},'gerekce':'Iptal'}
        elif satir=='etap_duzenle':
            hedef=f.etap['E-IML']; alan={'tur':'ETAP'}; girdiler={'degisenler':{'ad':'Yeni'}}
        elif satir=='yasam_ana':
            if kod.startswith('PROJE.'):
                hedef='2509084'; alan={'tur':'PROJE'}; girdiler={'degisenler':{'ad':'Yeni'}}
            elif kod=='AYAR.MAAS_PAYDASI': girdiler={'deger':160,'gecerli_baslangic':'2026-11-01'}
            else: girdiler={'deger':''}
        if satir=='saat': alan={'adina':'K023'}; hedef=None if kod.startswith('MESAI') else 4; girdiler={'neden':'ARIZA.MAKINE'} if kod=='IS.ARIZA_BILDIRDIM' else {}
        elif satir=='havuz': girdiler={'isler':[{'birim':'IMALAT'}]}
        elif satir=='lider':
            hedef=4; girdiler={'kisi':'K017','sira':1,'yeni_sira':1,'kimden':'K017','kime':'K023','not':'Ret','is_tanimi':'Plansiz','tur':'SURELI','onay_gerekli':False,'nereye':'PROJE','proje':'2509084','birim':'IMALAT','baslangic':t(22,'08:00'),'bitis':t(22,'08:05'),'aciklama':'Elle','is_bitti':False}
            if kod=='IS.SURE_EKLEDIM': alan={'adina':'K023','giris_sekli':'ELLE'}
        elif satir=='isaret':
            hedef_olay=next(e for e in f.olaylar if e['eylem_kodu']=='MESAI.GIRDIM')['olay_kimligi']; kim='K044'; girdiler={'hedef':hedef_olay,'gerekce':'Yanlis'}; alan={'duzelttigi_olay':hedef_olay}
        elif satir=='gorev_ata': girdiler={'gorevler':[f.gorev_satiri()]}
        elif satir.startswith('gorev_'):
            hedef=g; kim='K044'; girdiler={'not':'Ret','sebep_olan':'K041','revizyon_ver':False,'degisenler':{'ad':'Yeni'}}
        elif satir=='not': kim='K999'; hedef=[{'tur':'PROJE','kimlik':'2509084'}]; girdiler={'metin':'Not'}
        elif satir=='yonlendirme': girdiler={'birim':'MEK_TASARIM','kisiler':['K041']}
        elif satir=='etap': girdiler={'proje':'2509084','ad':'Yeni','birim':'MEK_TASARIM','baslangic':'2026-10-22','bitis':'2026-11-22','hedef_saat':20}
        elif satir=='ana':
            # Ortak veriden geçerli biçimi al; yetkisiz oturumla dene.
            aday=next((e for e in f.olaylar if e['eylem_kodu']==kod),None)
            if aday: girdiler=deepcopy(aday['girdiler'])
            else: girdiler={'kisi':'K041','degisenler':{'ad':'Yeni'},'gecerli_baslangic':'2026-10-22','ayrilis_tarihi':'2026-10-22','hedef':t(22,'10:00')}
        if satir=='aktarim': kod_='NOT.YAZDIM'; kim='K017'; hedef=[{'tur':'PROJE','kimlik':'2509084'}]; girdiler={'metin':'Not'}; alan={'giris_sekli':'AKTARIM'}
        else: kod_=kod
        f.olay(kim,kod_,t(22,'09:00'),hedef,girdiler,**alan); e=f.olaylar[-1]
        sonuc=d.olay_ekle(e) if satir=='aktarim' else yaz(d,e)
        self.assertEqual(sonuc.get('kod'),'YETKI',(kod,sonuc)); self.assertNotIn(e['olay_kimligi'],d.olaylar)
    return test

for satir,kodlar,_ in MATRIS:
    for kod in kodlar: setattr(DegismezlerV2,'test_I44_'+satir+'_'+kod.replace('.','_'),matris_deneyi(satir,kod))
