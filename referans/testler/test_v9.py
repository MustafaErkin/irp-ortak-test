"""Y87-Y97: T9'un elle hesaplanmis beklentileri gercek kabul yolundan."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import an
from irp.gorunumler import adil_performans,iscilik_maliyeti,maas_dagilimi,proje_gostergesi,gorev_gunluk_paylar
from irp.gorunum_v7 import kapasite,gun_agirligi,kisi_uygun_mu,gun_sonu_raporu,durum,tezgah_gostergesi,oku
from irp.gorunum_v9 import (gecikme_raporu,degisiklik_gecmisi,proje_degisiklikleri,proje_gorebilir_mi,
    gorebilir_mi,proje_erisim_gecmisi,gun_isleri,okunmamis_bildirimler,gorev_listesi,sorumluluk_ekleri,proje_kaydi)
from irp.kurallar_v9 import DURUS_NEDENLERI
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from .ortak import Duzenek,t,is_id,s1
from .test_v7 import kur,gonder,dakika


def duzenek():
    f=Duzenek()
    for baslik,altlar in DURUS_NEDENLERI.items():
        f.olay('K001','KOD.TANIMLADIM',t(1,'07:10'),girdiler=dict(liste='DURUS_NEDENI',kod=baslik,ad=baslik,aktif=True,ust=None))
        for alt in altlar:
            kod=baslik+'_'+alt
            f.olay('K001','KOD.TANIMLADIM',t(1,'07:11'),girdiler=dict(liste='DURUS_NEDENI',kod=kod,ad=kod,aktif=True,ust=baslik))
    return f


def durus_duzenegi():
    f=duzenek(); f.ata(4)
    for kod,saat in [('MESAI.GIRDIM','07:55'),('BASLADIM','08:00'),('DEVAM_ETTIM','10:15'),('DEVAM_ETTIM','12:30')]: f.is_olay(kod,saat,None if kod.startswith('MESAI') else 4)
    oid=f.is_olay('ARIZA_BILDIRDIM','13:20',4,neden='DURUS_NEDENI.MALZEME_EKSIK',not_='Elektrot bitti')
    f.is_olay('DEVAM_ONAYLADIM','13:45',4,kisi='K009'); f.is_olay('DEVAM_ETTIM','13:46',4)
    return f,oid


def gec_duzenegi(neden=True):
    f=duzenek(); g=f.gorev_ata(t(22,'09:00'),ad='Montaj resmi',teslim_tarihi='2026-10-23',zaman_degeri=8)
    f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g)
    f.gorev_olay('TAMAMLADIM',t(26,'10:00'),g,**(dict(gecikme_nedeni='DURUS_NEDENI.BEKLEME_MUSTERI',gecikme_aciklamasi='Musteri olcu onayi gec') if neden else {}))
    return f,g


def degerlendir(f,d,hedef,ss,kim='K012',zaman=None,bek='BASARILI',neden='BEKLEME_MUSTERI'):
    return gonder(f,d,kim,'GECIKME.DEGERLENDIRDIM',zaman or t(26,'11:00'),dict(hedef=hedef,neden='DURUS_NEDENI.'+neden,sorumlular=ss,gerekce='Kayit incelendi'),bek=bek)


def pay(k,y=100,tur='KISI'): return dict(tur=tur,kimlik=k,yuzde=y)


class SenaryolarV9(unittest.TestCase):
    def test_Y87(self):
        f=duzenek(); d=kur(f,t(22,'08:50'))
        gonder(f,d,'K001','PROJE.KOD_DEGISTIRDIM',t(22,'09:00'),dict(kod='2509099',gerekce='Yanlis girilmis'),'2509091','PROJE')
        g=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:10'),dict(gorevler=[f.gorev_satiri(proje='2509091',etap=None,zaman_degeri=4,teslim_tarihi='2026-10-23')]))+'/1'
        self.assertEqual(d.gorevler[g]['proje'],'2509091'); self.assertEqual(d.projeler['2509091']['kod'],'2509099')
        h=d.projeler['2509091']['kod_gecmisi']; self.assertEqual([x['kod'] for x in h],['2509091','2509099']); self.assertEqual(h[0]['bitis'],an(t(22,'09:00')))
        for saat,kimlik,kod in [('09:20','P-Y87-1','2509091'),('09:21','P-Y87-2','2509099'),('09:22','2509084','2509100')]:
            gonder(f,d,'K001','PROJE.ACTIM',t(22,saat),dict(kimlik=kimlik,kod=kod,ad='Deneme'),bek='DURUM')
        gonder(f,d,'K012','PROJE.KOD_DEGISTIRDIM',t(22,'09:30'),dict(kod='2509101',gerekce='Deneme'),'2509084','PROJE',bek='YETKI')
        gonder(f,d,'K001','PROJE.KOD_DEGISTIRDIM',t(22,'09:31'),dict(kod='2509102',gerekce=''),'2509084','PROJE',bek='BICIM')
        self.assertEqual(proje_kaydi(d,'2509091',t(22,'08:59'))['kod'],'2509091')

    def test_Y88(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:50'))
        ev=degerlendir(f,d,h,[pay('PLANLAMA',tur='BIRIM')],'K009',t(22,'14:00'),neden='MALZEME_GECIKTI')
        self.assertEqual(dakika(d,'BEKLEME_ARIZA'),26)
        self.assertTrue(all(x['neden']=='DURUS_NEDENI.MALZEME_EKSIK' for x in d.araliklar if x['kova']=='BEKLEME_ARIZA'))
        self.assertFalse(d.sorumluluklar[ev+'/1']['dogrulandi'])
        ss=gecikme_raporu(d,'2026-10-01','2026-10-31'); self.assertEqual(ss[0]['durus_dk'],26)
        self.assertTrue(any(x['kural']=='R38' and x['alici']=='K001' for x in d.bildirimler.values()))
        gonder(f,d,'K001','SORUMLULUK.DOGRULADIM',t(22,'14:10'),dict(hedef=ev,satir=1,karar='ONAY',gerekce='Dogru'))
        ss=gecikme_raporu(d,'2026-10-01','2026-10-31'); self.assertEqual(ss[0]['sebep_olunan_bekleme_dk'],26)
        self.assertEqual(sorumluluk_ekleri(d,'K017','2026-10-01','2026-10-31')['sebep_olunan_bekleme_dk'],0)

    def test_Y88b(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:19'))
        for saat,neden in [('13:20','MALZEME'),('13:21','MALZEME_DIGER')]:
            gonder(f,d,'K017','IS.ARIZA_BILDIRDIM',t(22,saat),dict(neden='DURUS_NEDENI.'+neden),4,bek='BICIM')
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:50'))
        degerlendir(f,d,h,[pay('PLANLAMA',90,'BIRIM')],'K009',t(22,'14:00'),bek='BICIM')
        degerlendir(f,d,h,[pay('PLANLAMA',tur='BIRIM')],'K017',t(22,'14:01'),bek='YETKI')

    def test_Y89(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],0)
        self.assertTrue(any(x['kural']=='R40' and x['alici']=='K012' for x in d.bildirimler.values()))
        degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')])
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],1)
        ss=gecikme_raporu(d,'2026-10-01','2026-10-31'); self.assertEqual((ss[0]['kimlik'],ss[0]['gec_teslim'],ss[0]['zaman_degeri']),('DIS:MUSTERI',1,8))

    def test_Y89b(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05')); ev=degerlendir(f,d,g,[pay('K041',50),pay('K044',50)])
        self.assertTrue(all(s['dogrulandi'] for s in d.sorumluluklar.values()))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],.5)
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['sebep_olunan_gecikme'],4)
        gonder(f,d,'K044','SORUMLULUK.ITIRAZ_ETTIM',t(26,'11:30'),dict(hedef=ev,satir=2,gerekce='Benim payim degil'))
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['sebep_olunan_gecikme'],0)
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],0)
        self.assertTrue(adil_performans(d,'K041','2026-10-01','2026-10-31')['kesinlesmedi'])

    def test_Y89c(self):
        f,g=gec_duzenegi(False); d=kur(f,t(26,'10:05'))
        self.assertEqual(d.gorevler[g]['gecikme_nedeni'],'GIRILMEDI'); self.assertEqual(d.gorevler[g]['durum'],'BITTI')
        self.assertTrue(any(x['kural']=='R40' for x in d.bildirimler.values()))

    def test_Y89d(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05'))
        for k,saat in [('K041','11:00'),('K044','11:01')]: degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')],k,t(26,saat),bek='YETKI')
        f.olaylar=[e for e in f.olaylar if e['eylem_kodu']!='GECIKME.DEGERLENDIRDIM']
        next(e for e in f.olaylar if e['eylem_kodu']=='GOREV.TAMAMLADIM')['oldugu_an']=t(23,'14:00')
        d=kur(f,t(26,'10:05')); degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')],bek='DURUM')

    def test_Y90(self):
        f=duzenek(); g=f.gorev_ata(t(22,'09:00'),teslim_tarihi='2026-10-23',zaman_degeri=8)
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); f.gorev_olay('TAMAMLADIM',t(22,'14:00'),g)
        d=kur(f,t(26,'08:50')); once=deepcopy(d.gorevler[g])
        h=gonder(f,d,'K012','GOREV.ATADIM',t(26,'09:00'),dict(gorevler=[f.gorev_satiri(zaman_degeri=4,teslim_tarihi='2026-10-27',degisiklik=dict(kaynak=g,neden='MUSTERI'))]))+'/1'
        self.assertEqual(d.gorevler[g],once)
        self.assertEqual((d.gorevler[h]['tur'],d.gorevler[h]['degisiklik_kaynagi'],d.gorevler[h]['durum']),('DEGISIKLIK',g,'ATANDI'))
        self.assertEqual(degisiklik_gecmisi(d,g),[g,h]); self.assertEqual(proje_degisiklikleri(d,'2509084','2026-10-01','2026-10-31')['MUSTERI']['zaman_degeri'],4)

    def test_Y90b(self):
        f=duzenek(); g=f.gorev_ata(t(22,'09:00'),teslim_tarihi='2026-10-23',zaman_degeri=8)
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); f.gorev_olay('TAMAMLADIM',t(22,'14:00'),g)
        d=kur(f,t(26,'08:50'))
        h=gonder(f,d,'K012','GOREV.ATADIM',t(26,'09:00'),dict(gorevler=[f.gorev_satiri(zaman_degeri=4,teslim_tarihi='2026-10-27',degisiklik=dict(kaynak=g,neden='HATA',sorumlular=[pay('K041')]))]))+'/1'
        gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(26,'09:30'),h=h)
        gonder(f,d,'K041','GOREV.TAMAMLADIM',t(26,'15:00'),h=h)
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['kalite_ret'],1)
        self.assertEqual(d.gorevler[h]['durum'],'BITTI'); self.assertIsNone(d.gorevler[h]['is_puani'])

    def test_Y90c(self):
        f=duzenek(); g=f.gorev_ata(t(22,'09:00'),onay_gerekli=True,onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); onay=f.gorev_olay('TAMAMLADIM',t(22,'14:00'),g)
        iptal=f.gorev_ata(t(22,'09:01')); f.gorev_olay('IPTAL_ETTIM',t(22,'09:05'),iptal,'K012')
        d=kur(f,t(26,'08:50'))
        for n,(kaynak,proje,neden,ss,bek) in enumerate([(iptal,'2509084','MUSTERI',[],'DURUM'),(onay,'2509084','MUSTERI',[],'DURUM'),(g,'2509091','MUSTERI',[],'DURUM'),(g,'2509084','MUSTERI',[pay('K041')],'BICIM')]):
            s=f.gorev_satiri(proje=proje,etap=None,zaman_degeri=4,teslim_tarihi='2026-10-27',degisiklik=dict(kaynak=kaynak,neden=neden,sorumlular=ss))
            gonder(f,d,'K012','GOREV.ATADIM',t(26,'09:0'+str(n)),dict(gorevler=[s]),bek=bek)

    def test_Y90d(self):
        f=duzenek(); g=f.gorev_ata(t(22,'09:00')); f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g)
        d=kur(f,t(22,'11:50')); once=deepcopy(d.gorevler[g])
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:00'),dict(gorevler=[f.gorev_satiri(degisiklik=dict(kaynak=g,neden='IYILESTIRME'))]))
        self.assertEqual(d.gorevler[g],once); self.assertEqual(d.gorevler[g]['durum'],'ACIK')

    def test_Y90e(self):
        f=s1(); d=kur(f,t(22,'11:45')); once=deepcopy(d.isler[is_id(1)])
        s=dict(nereye='PROJE',proje='2509084',etap=f.etap['E-IML'],birim='IMALAT',islem='Degisiklik: Kaynak',tur='SURELI',tahmini_sure_dk=60,onay_gerekli=False,degisiklik=dict(kaynak=is_id(1),neden='IYILESTIRME'))
        h=gonder(f,d,'K004','IS.TANIMLADIM',t(22,'12:00'),dict(isler=[s]))
        self.assertEqual(d.isler[is_id(1)],once); self.assertEqual(degisiklik_gecmisi(d,is_id(1)),[is_id(1),h])

    def test_Y91(self):
        f=duzenek(); d=kur(f,t(30,'09:50'))
        gonder(f,d,'K001','PROJE.KAPATTIM',t(30,'10:00'),h='2509091',tur='PROJE')
        p=dict(kimlik='P-SRV-1',kod='2509091',ek='Servis',ad='Elektro-pres servis',ana_proje='2509091')
        gonder(f,d,'K001','PROJE.ACTIM',t(2,'09:00',11),p)
        self.assertEqual(d.projeler['P-SRV-1']['kod']+' · '+d.projeler['P-SRV-1']['ek'],'2509091 · Servis')
        gonder(f,d,'K001','PROJE.ACTIM',t(2,'09:10',11),dict(p,kimlik='P-SRV-2'),bek='DURUM')
        gonder(f,d,'K001','PROJE.ACTIM',t(2,'09:11',11),dict(p,kimlik='P-SRV-3',ek='Servis 2',ana_proje='P-SRV-1'),bek='DURUM')
        s=f.gorev_satiri(proje='P-SRV-1',etap=None,zaman_degeri=6,teslim_tarihi='2026-11-04')
        h=gonder(f,d,'K012','GOREV.ATADIM',t(2,'09:30',11),dict(gorevler=[s]))+'/1'
        gonder(f,d,'K012','GOREV.ATADIM',t(2,'09:31',11),dict(gorevler=[dict(s,proje='2509091')]),bek='DURUM')
        gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(2,'09:40',11),h=h); gonder(f,d,'K041','GOREV.TAMAMLADIM',t(4,'16:00',11),h=h)
        v=proje_gostergesi(d,'2509091',cagiran='K001'); self.assertEqual(v['bagli_projeler'],['P-SRV-1']); self.assertEqual(v['bitis_sonrasi'],dict(emek_saat=6,maliyet=Decimal('666.67')))
        self.assertNotIn('maliyet',proje_gostergesi(d,'2509091',cagiran='K012')['bitis_sonrasi'])

    def test_Y92(self):
        from .test_v10 import proje_duzenegi
        f=proje_duzenegi()
        d=kur(f,t(22,'12:00'))
        for k,ilk,ikinci in [('K017',True,False),('K023',False,False),('K009',True,False),('K006',False,False),('K041',False,False),('K004',True,True),('K012',True,False),('K001',True,True)]:
            self.assertEqual((gorebilir_mi(d,k,'PROJE','2509084'),gorebilir_mi(d,k,'PROJE','2509091')),(ilk,ikinci),k)
        self.assertTrue(gorebilir_mi(d,'K017','IS',is_id(1))); self.assertFalse(gorebilir_mi(d,'K023','IS',is_id(1)))
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:10'),dict(gorevler=[f.gorev_satiri(zaman_degeri=2,teslim_tarihi='2026-10-23')]))
        self.assertTrue(proje_gorebilir_mi(d,'K041','2509084'))
        gonder(f,d,'K004','PROJE.ERISIM_VERDIM',t(22,'12:20'),dict(proje='2509091',kisi='K006',gerekce='Satin alma'))
        self.assertTrue(proje_gorebilir_mi(d,'K006','2509091'))
        gonder(f,d,'K006','PROJE.ERISIM_VERDIM',t(22,'12:30'),dict(proje='2509091',kisi='K045',gerekce='Deneme'),bek='YETKI')
        gonder(f,d,'K004','PROJE.ERISIM_KALDIRDIM',t(22,'12:40'),dict(proje='2509091',kisi='K006',gerekce='Bitti'))
        self.assertFalse(proje_gorebilir_mi(d,'K006','2509091')); self.assertEqual(len(proje_erisim_gecmisi(d,'2509091')),2)
        self.assertFalse(gorebilir_mi(d,'K017','ADIL_PERFORMANS','K023')); self.assertFalse(gorebilir_mi(d,'K017','MAAS','K017'))
        self.assertEqual(len([x for x in d.bildirimler.values() if x['kural']=='R42' and x['alici']=='K006']),2)

    def test_Y92b(self):
        d=kur(s1(),t(22,'12:00'))
        for k in d.kisiler:
            for p in d.projeler: self.assertTrue(gorebilir_mi(d,k,'PROJE',p))

    def test_Y93(self):
        f=duzenek(); b=next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='BIRIM.TANIMLADIM' and e['girdiler']['kod']=='IMALAT')
        tak=dict(mesai_baslangic='07:00',mesai_bitis='16:00',gunler=[1,2,3,4,5],sabit_molalar=[dict(ad='Cay',bas='09:00',bit='09:15'),dict(ad='Yemek',bas='12:00',bit='12:30')])
        f.olay('K001','BIRIM.TANIMLADIM',t(21,'10:00'),girdiler=dict(b,takvim=tak,takvim_gecerli='2026-10-22')); f.ata(1)
        for kod,saat,n in [('MESAI.GIRDIM','06:58',None),('BASLADIM','07:00',1),('DEVAM_ETTIM','09:15',1),('TAMAMLADIM','10:30',1)]: f.is_olay(kod,saat,n)
        d=kur(f,t(22,'10:35')); self.assertEqual(emek(d,is_id(1)),195); self.assertEqual(dakika(d,'SABIT_MOLA'),15)
        self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),8.25); self.assertEqual(gun_agirligi(d,'K017','2026-10-22'),1)
        self.assertEqual(kapasite(d,'K017','2026-10-21','2026-10-21'),9); self.assertEqual(kapasite(d,'K041','2026-10-22','2026-10-22'),9)
        self.assertFalse(kisi_uygun_mu(d,'K017',t(22,'16:30'),t(22,'17:00'),'K001')['uygun']); self.assertTrue(kisi_uygun_mu(d,'K041',t(22,'16:30'),t(22,'17:00'),'K001')['uygun'])
        self.assertEqual(min(x['baslangic'] for x in d.araliklar if x['kisi']=='K017'),an(t(22,'07:00')))
        self.assertEqual(d.kisi_durumu['K017']['kova'],'TANIMSIZ')

    def test_Y93b(self):
        f=duzenek(); d=kur(f,t(21,'09:50')); b=dict(d.birimler['IMALAT']); b.pop('surum',None)
        tak=dict(mesai_baslangic='07:00',mesai_bitis='16:00',gunler=[1,2,3,4,5],sabit_molalar=[])
        gonder(f,d,'K001','BIRIM.TANIMLADIM',t(21,'10:00'),dict(b,takvim=tak,takvim_gecerli='2026-10-21'),bek='DURUM')

    def test_Y94(self):
        f,d=gun_duzenegi(); once=iscilik_maliyeti(d,'2509084','2026-10-01','2026-10-31')
        self.assertEqual(emek(d,is_id(1)),200); self.assertEqual((once['iscilik'],once['onay_bekleyen']),(Decimal('370.37'),Decimal('370.37')))
        isler=gun_isleri(d,'K009'); self.assertIn(dict(tur='GUN_ONAYI',birim='IMALAT',gun='2026-10-22',kisiler=['K017','K023']),isler)
        self.assertFalse(any(x['gun']=='2026-10-22' and x['tur']=='MESAI_SONU' for x in gun_isleri(d,'K041')))
        self.assertTrue(any(x['gun']=='2026-10-22' for x in gun_isleri(d,'K041',t(22,'17:49'))))
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'18:10'),dict(gunler=onaylar(d),not_='Tamam'))
        for k in ('K017','K023'): self.assertEqual(gun_sonu_raporu(d,k,'2026-10-22')['durum'],'ONAYLANDI')
        self.assertFalse(gun_isleri(d,'K009')); self.assertEqual(iscilik_maliyeti(d,'2509084','2026-10-01','2026-10-31')['onay_bekleyen'],0)
        gonder(f,d,'K009','GUN_SONU.IADE_ETTIM',t(22,'18:12'),dict(kisi='K017',gun='2026-10-22',gerekce='Deneme'),bek='DURUM')
        self.assertEqual(gun_sonu_raporu(d,'K041','2026-10-22')['durum'],'GONDERILDI'); self.assertFalse(any(x['kural']=='R32' for x in d.bildirimler.values()))

    def test_Y94b(self):
        f,d=gun_duzenegi(); d.ilerlet(t(23,'08:00'))
        self.assertTrue({'K009','K004','K001'}<={x['alici'] for x in d.bildirimler.values() if x['kural']=='R33' and x['gun']=='2026-10-22'})
        self.assertTrue(any(x['tur']=='GUN_ONAYI' and x['gun']=='2026-10-22' for x in gun_isleri(d,'K009')))
        d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        u=next(x for x in d.ay_kapanislari['2026-10-01:ONAY_UYARILARI'] if x['birim']=='IMALAT' and x['gun']=='2026-10-22')
        self.assertTrue({'K017','K023'}<=set(u['kisiler']))

    def test_Y94c(self):
        f,d=gun_duzenegi(); ss=onaylar(d)
        gonder(f,d,'K023','GUN_SONU.ONAYLADIM',t(22,'18:10'),dict(gunler=ss),bek='YETKI')
        ss.append(dict(kisi='K009',gun='2026-10-22',ozet_surumu=gun_sonu_raporu(d,'K009','2026-10-22')['ozet_surumu']))
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'18:11'),dict(gunler=ss),bek='YETKI')
        self.assertFalse(any(x['durum']=='ONAYLANDI' for x in d.gun_sonu_raporlari.values()))
        gonder(f,d,'K009','GUN_ONAYI.AYARLADIM',t(22,'18:12'),dict(birim='IMALAT',gerekli=True,gecerli_baslangic='2026-10-23'),bek='YETKI')

    def test_Y95(self):
        f,d,h=izin_duzenegi()
        self.assertEqual(d.izinler[h]['durum'],'TALEP')
        gonder(f,d,'K012','IZIN.ONAYLADIM',t(22,'10:00'),dict(hedef=h))
        self.assertEqual(d.izinler[h]['durum'],'IK_BEKLIYOR'); self.assertTrue(kisi_uygun_mu(d,'K041',t(2,'09:00',11),t(2,'10:00',11),'K001')['uygun'])
        self.assertTrue(any(x['kural']=='R41' and x['alici']=='K007' for x in d.bildirimler.values()))
        for k,saat in [('K012','10:30'),('K052','10:31')]: gonder(f,d,k,'IZIN.IK_ONAYLADIM',t(22,saat),dict(hedef=h),bek='YETKI')
        gonder(f,d,'K007','IZIN.IK_ONAYLADIM',t(22,'11:00'),dict(hedef=h))
        self.assertEqual(d.izinler[h]['durum'],'ONAYLI'); self.assertFalse(kisi_uygun_mu(d,'K041',t(2,'09:00',11),t(2,'10:00',11),'K001')['uygun'])

    def test_Y95b(self):
        f,d,h=izin_duzenegi('K007')
        gonder(f,d,'K001','IZIN.ONAYLADIM',t(22,'09:30'),dict(hedef=h))
        gonder(f,d,'K007','IZIN.IK_ONAYLADIM',t(22,'09:40'),dict(hedef=h),bek='YETKI')
        gonder(f,d,'K001','IZIN.IK_ONAYLADIM',t(22,'09:50'),dict(hedef=h))
        self.assertEqual(d.izinler[h]['durum'],'ONAYLI')

    def test_Y95c(self):
        f,d,h=izin_duzenegi(); gonder(f,d,'K012','IZIN.ONAYLADIM',t(22,'10:00'),dict(hedef=h))
        gonder(f,d,'K007','IZIN.REDDETTIM',t(22,'11:00'),dict(hedef=h,gerekce='Bakiye yetersiz'))
        self.assertEqual(d.izinler[h]['durum'],'RET'); self.assertTrue(any(x['kural']=='R36' and x['alici']=='K041' for x in d.bildirimler.values()))

    def test_Y95d(self):
        f,d,h=izin_duzenegi()
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'12:00'),dict(kisi='K007',degisenler=dict(roller=['YONETICI']),gecerli_baslangic=t(22,'12:00')),bek='DURUM')
        f=duzenek(); d=kur(f,t(22,'08:50'))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:00'),dict(anahtar='izin_ik_onayi',deger={'YILLIK':True}),bek='DURUM')

    def test_Y96(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:29')); b=h+'/R07/K009'
        self.assertTrue(any(x['kural']=='R07' for x in okunmamis_bildirimler(d,'K009')))
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'13:30'),dict(bildirimler=[b]))
        self.assertFalse(any(x['kural']=='R07' for x in okunmamis_bildirimler(d,'K009')))
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'13:35'),dict(bildirimler=[b]))
        self.assertEqual(next(x['gorulme_ani'] for x in d.bildirimler.values() if x['kural']=='R07'),an(t(22,'13:30')))
        for k,saat in [('K017','13:36'),('K001','13:37')]: gonder(f,d,k,'BILDIRIM.GORDUM',t(22,saat),dict(bildirimler=[b]),bek='YETKI')
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'13:38'),dict(bildirimler=['olmayan']),bek='DURUM')

    def test_Y97(self):
        f=duzenek(); d=kur(f,t(22,'08:50'))
        p=dict(kimlik='P-Y97',kod='2510001',ad='Kaynak hucresi',baslangic_tarihi='2026-11-01',kesin_kabul_tarihi='2027-06-30',sorumlu='K012')
        gonder(f,d,'K001','PROJE.ACTIM',t(22,'09:00'),p)
        for a in ('baslangic_tarihi','kesin_kabul_tarihi','sorumlu'): self.assertEqual(d.projeler['P-Y97'][a],p[a])
        gonder(f,d,'K001','PROJE.ACTIM',t(22,'09:01'),dict(p,kimlik='P-Y97-B',kod='2510002',sorumlu='K099'),bek='DURUM')
        ss=[f.gorev_satiri(ad=ad,oncelik=o,teslim_tarihi='2026-10-'+tarih,etap=None,zaman_degeri=2) for ad,o,tarih in [('A','NORMAL','23'),('B','ACIL','30'),('C','YUKSEK','26')]]
        h=gonder(f,d,'K012','GOREV.ATADIM',t(22,'10:00'),dict(gorevler=ss))
        gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'10:30'),h=[h+'/'+str(n) for n in (1,2,3)])
        self.assertEqual([x['ad'] for x in gorev_listesi(d,'K041')],['B','C','A'])
        for x in gorev_listesi(d,'K041'):
            y=dict(x,oncelik='NORMAL'); self.assertEqual(gorev_gunluk_paylar(d,x),gorev_gunluk_paylar(d,y))

    def test_Y97_makine(self):
        f=makine_duzenegi(); d=kur(f,t(22,'12:39'))
        gonder(f,d,'K023','IS.TAMAMLADIM',t(22,'12:40'),dict(makine_bitis_ani=t(22,'11:30')),7)
        ss=[x for x in d.araliklar if x['kova']=='TEZGAH']; self.assertEqual((ss[0]['bitis']-ss[0]['baslangic']).total_seconds()/60,200)
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-22','2026-10-22')['bitti_alinmayi_bekledi_dk'],70)

    def test_Y97_makine_kapilar(self):
        f=makine_duzenegi(); d=kur(f,t(22,'12:39'))
        for n,bitis in enumerate(('12:50','08:00')): gonder(f,d,'K023','IS.TAMAMLADIM',t(22,'12:4'+str(n)),dict(makine_bitis_ani=t(22,bitis)),7,bek='BICIM')


def gun_duzenegi():
    f=duzenek(); f.ata(1)
    f.olay('K004','GUN_ONAYI.AYARLADIM',t(21,'17:00'),girdiler=dict(birim='IMALAT',gerekli=True,gecerli_baslangic='2026-10-22'))
    for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:05',1),('DEVAM_ETTIM','10:15',1),('TAMAMLADIM','11:40',1),('MESAI.CIKTIM','17:55',None)]: f.is_olay(kod,saat,n)
    f.is_olay('MESAI.GIRDIM','07:59',kisi='K023'); f.is_olay('MESAI.CIKTIM','17:55',kisi='K023')
    f.olay('K041','GUN_SONU.GONDERDIM',t(22,'17:50'),girdiler=dict(gun='2026-10-22',aciklama='Montaj resmi bitti'))
    return f,kur(f,t(22,'18:05'))


def onaylar(d):
    return [dict(kisi=k,gun='2026-10-22',ozet_surumu=gun_sonu_raporu(d,k,'2026-10-22')['ozet_surumu']) for k in ('K017','K023')]


def izin_duzenegi(kisi='K041'):
    f=duzenek()
    next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='KISI.EKLEDIM' and e['girdiler']['kod']=='K007')['roller']=['YONETICI','IK']
    f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='izin_ik_onayi',deger={'YILLIK':True},gecerli_baslangic='2026-10-01'))
    d=kur(f,t(22,'08:50')); h=gonder(f,d,kisi,'IZIN.TALEP_ETTIM',t(22,'09:00'),dict(kisi=kisi,tur='YILLIK',baslangic=t(2 if kisi=='K041' else 3,'08:00',11),bitis=t(2 if kisi=='K041' else 3,'18:00',11),gerekce='Aile'))
    return f,d,h


def makine_duzenegi():
    f=duzenek()
    for n,k,s in [(4,'K017',1),(3,'K017',2),(8,'K023',1),(7,'K023',2)]: f.ata(n,k,s)
    for kod,saat,n,k in [('MESAI.GIRDIM','07:58',None,'K017'),('BASLADIM','08:00',4,'K017'),('DEVAM_ETTIM','10:15',4,'K017'),('TAMAMLADIM','11:50',4,'K017'),('MESAI.GIRDIM','07:59',None,'K023'),('TAMAMLADIM','08:10',8,'K023')]: f.is_olay(kod,saat,n,k)
    return f
