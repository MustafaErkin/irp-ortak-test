"""Y8–Y28; tarihsel izdüşüm ve canlı kabul testleri ayrı, beklenenler elle."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Saat,an
from irp.cihaz import Cihaz
from irp.kisi_gunu import kapi
from irp.gorunumler import *
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from .ortak import Duzenek,t,is_id,s1,s13,yaz
from .tur2_ornekler import isaret,iki_kisi,iptal_gorev,kisi_degisim,s12_veri

class SenaryolarV2(unittest.TestCase):
    def test_Y8(self):
        f=Duzenek(); f.ata(1); f.is_olay('MESAI.GIRDIM','07:58'); f.ata(3,zaman=t(22,'08:05'))
        ara=f.calistir(t(22,'08:07')); self.assertEqual(ara.kisi_durumu['K017']['durum'],'ON_IS_BEKLIYOR')
        self.assertFalse(kapi(ara.kisi_durumu['K017'],'IS.BASLADIM',ara.isler[is_id(3)],is_id(3)))
        f.olay('K009','IS.SIRALADIM',t(22,'08:10'),1,{'kisi':'K017','yeni_sira':1})
        d=f.calistir(t(22,'08:20')); a=kisinin_gunu(d,'K017','2026-10-22')
        self.assertEqual(a['kovalar'],{'TANIMSIZ':5,'BEKLEME_ON_IS':5,'GECIS':10})
        self.assertEqual(d.listeler['K017'][0],is_id(1))
        self.assertTrue(any(x['kural']=='R04' and x['gecerli'] for x in d.bildirimler.values()))

    def test_Y9a(self):
        f=Duzenek(); f.ata(9); f.ata(2,sira=2)
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','16:00',9); f.is_olay('TAMAMLADIM','17:30',9)
        f.is_olay('MESAI.GIRDIM','07:57',gun=23)
        ara=f.calistir(t(23,'08:10')); self.assertEqual(ara.kisi_durumu['K017']['durum'],'ONAY_BEKLIYOR')
        self.assertFalse(kapi(ara.kisi_durumu['K017'],'IS.BASLADIM',ara.isler[is_id(2)],is_id(9)))
        f.is_olay('ONAYLADIM','08:20',9,'K009',gun=23); f.is_olay('BASLADIM','08:22',2,gun=23)
        d=f.calistir(t(23,'08:30'))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'],{'BEKLEME_ONAY':20,'TANIMSIZ':2,'CALISMA':8})
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar']['BEKLEME_ONAY'],30)

    def test_Y9b(self):
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',4)
        for saat in ('10:15','12:30','15:15'): f.is_olay('DEVAM_ETTIM',saat,4)
        f.is_olay('ARIZA_BILDIRDIM','17:40',4,neden='ARIZA.MAKINE'); f.is_olay('DEVAM_ONAYLADIM','17:50',4,'K009')
        f.is_olay('MESAI.GIRDIM','07:58',gun=23)
        d=f.calistir(t(23,'08:01')); self.assertEqual(d.kisi_durumu['K017']['durum'],'ARIZADA'); self.assertTrue(d.kisi_durumu['K017']['devam_izni'])
        f.is_olay('DEVAM_ETTIM','08:03',4,gun=23); d=f.calistir(t(23,'08:10'))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'],{'BEKLEME_ARIZA':3,'CALISMA':7})

    def test_Y10(self):
        f,g,o=iptal_gorev(); ara=f.calistir(t(28,'10:30')); self.assertEqual(ara.gorevler[o]['zaman_degeri'],2)
        d=f.calistir(t(28,'12:00')); self.assertEqual(d.gorevler[g]['durum'],'IPTAL'); self.assertEqual(d.gorevler[o]['durum'],'IPTAL')
        self.assertFalse(onay_listesi(d,'K012')); self.assertEqual(yuk(d,'K012','2026-10-26','2026-10-30'),0)
        self.assertEqual(maas_dagilimi(d,'K041','2026-10-01')['paylar'],{'iptal:2509084':15})
        self.assertEqual(maas_dagilimi(d,'K012','2026-10-01')['paylar'],{})

    def test_Y11(self):
        f=Duzenek(); f.ata(3)
        for k in ('K017','K023'): f.is_olay('MESAI.GIRDIM','07:58',kisi=k)
        f.is_olay('DEVRETTIM','08:30',3,'K009',kimden='K017',kime='K023')
        d=f.calistir(t(22,'08:40'))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar'],{'BEKLEME_ON_IS':30,'TANIMSIZ':10})
        self.assertEqual(kisinin_gunu(d,'K023','2026-10-22')['kovalar'],{'TANIMSIZ':30,'BEKLEME_ON_IS':10})
        self.assertEqual(d.isler[is_id(3)]['durum'],'ON_IS_BEKLIYOR'); self.assertEqual(emek(d,is_id(3)),0)
        self.assertEqual({x['kural'] for x in d.bildirimler.values() if x['gecerli']},{'R04','R08'})

    def test_Y12(self):
        f=Duzenek(); f.ata(1); f.ata(2,sira=2); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',1)
        e=f.is_olay('TAMAMLADIM','10:05',1); f.is_olay('BASLADIM','10:20',2)
        d=f.calistir(t(22,'10:30')); self.assertIn(e,d.supheliler); self.assertEqual(emek(d,is_id(1)),120); self.assertEqual(emek(d,is_id(2)),10)
        ara=f.calistir(t(22,'10:16')); self.assertEqual(ara.kisi_durumu['K017']['durum'],'CALISMIYOR')
        self.assertFalse(kapi(ara.kisi_durumu['K017'],'IS.DEVAM_ETTIM',ara.isler[is_id(1)],is_id(2)))

    def test_Y13(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); surum=d.isler[is_id(5)]['surum']
        f.ata(5,zaman=t(22,'09:00')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        f.ata(5,'K023',zaman=t(22,'09:01')); e=f.olaylar[-1]; e['neyin_ustunde'][0]['surum']=surum
        self.assertEqual(yaz(d,e,taze=False)['kod'],'BAYAT'); self.assertNotIn(e['olay_kimligi'],d.olaylar)
        f.is_olay('ONAYLADIM','09:05',5,'K009'); self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'DURUM')
        self.assertEqual(d.listeler['K017'],[is_id(5)]); self.assertFalse(d.listeler.get('K023'))
        c=Cihaz('K009','M',Saat(t(22,'09:01')))
        self.assertFalse(c.tazelik(False,t(22,'09:01'))); self.assertFalse(c.tazelik(True,t(22,'09:00'))); self.assertTrue(c.tazelik(True,t(22,'09:01')))

    def test_Y14(self):
        f=Duzenek(); g=f.gorev_ata(onay_gerekli=True,onaylayan='K012'); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58')
        d=f.calistir(t(22,'09:00'))
        denemeler=[('K017','AYAR.ONAY_ORANI',None,{'deger':.9,'gecerli_baslangic':t(22,'09:00')},{}),('K001','AYAR.ONAY_ORANI',None,{'deger':.2,'gecerli_baslangic':t(22,'09:00')},{}),('K041','GOREV.ONAYLADIM',g,{},{}),('K044','GOREV.TAMAMLADIM',g,{},{}),('K009','IS.BASLADIM',4,{},dict(adina='K017')),('K012','IS.BASLADIM',4,{},dict(adina='K017')),('K052','KISI.EKLEDIM',None,dict(kod='K099',ad='Yeni',birim='IMALAT',yaka='MAVI',roller=['CALISAN'],giris_tarihi='2026-10-22'),{}),('K041','GOREV.ATADIM',None,{'gorevler':[f.gorev_satiri(kisi='K044')]},{})]
        for n,(kim,kod,h,girdiler,alan) in enumerate(denemeler):
            with self.subTest(kod=kod,kim=kim):
                f.olay(kim,kod,t(22,'08:{:02d}'.format(10+n)),h,girdiler,**alan); sonuc=yaz(d,f.olaylar[-1])
                self.assertEqual(sonuc['sonuc'] if n in (1,4) else sonuc['kod'],'BASARILI' if n in (1,4) else 'YETKI')
        e=deepcopy(f.olaylar[0]); e.update(kim='K017',giris_sekli='AKTARIM',olay_kimligi='K017-2610229999-T')
        self.assertEqual(d.olay_ekle(e)['kod'],'YETKI')

    def test_Y15a(self):
        f=s1(); hedefler=[e['olay_kimligi'] for e in f.olaylar if e['oldugu_an'] in (t(22,'10:40'),t(22,'10:52'))]; d=f.calistir(t(22,'11:45'))
        for n,h in enumerate(hedefler):
            isaret(f,h,zaman='2026-10-22T11:44:{:02d}+03:00'.format(n*30)); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar'].get('MOLA',0),0); self.assertEqual(emek(d,is_id(1)),198); self.assertFalse(d.supheliler)
        self.assertTrue(all(h in d.olaylar for h in hedefler))

    def test_Y15b(self):
        f=s1(); mola=next(e for e in f.olaylar if e['eylem_kodu']=='IS.MOLA_VERDIM')['olay_kimligi']; devam=next(e for e in f.olaylar if e['oldugu_an']==t(22,'10:52'))['olay_kimligi']
        d=f.calistir(t(22,'11:45')); isaret(f,mola); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(emek(d,is_id(1)),198); self.assertEqual(set(d.supheliler),{devam})

    def test_Y15c(self):
        f=s1(); h=next(e for e in f.olaylar if e['eylem_kodu']=='IS.MOLA_VERDIM')['olay_kimligi']; d=f.calistir(t(22,'11:45')); isaret(f,h,kim='K017')
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')

    def test_Y15d(self):
        f=s1(); h=next(e for e in f.olaylar if e['eylem_kodu']=='IS.MOLA_VERDIM')['olay_kimligi']; d=f.calistir(t(22,'11:45')); m=isaret(f,h); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        for hedef,kim,zaman,gerekce,beklenen in [(m,'K009',t(22,'11:45'),'Yanlis','DURUM'),(h,'K009',t(30,'11:00'),'Yanlis','DURUM'),(h,'K009',t(22,'11:45'),'','BICIM'),(h,'K012',t(22,'11:45'),'Yanlis','YETKI')]:
            isaret(f,hedef,kim,zaman,gerekce); self.assertEqual(yaz(d,f.olaylar[-1])['kod'],beklenen)
        f=Duzenek(); g=f.gorev_ata(t(22,'08:00')); d=f.calistir(t(22,'11:45')); isaret(f,g.rsplit('/',1)[0],kim='K012')
        self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'DURUM')

    def test_Y16(self):
        f,g=iki_kisi(); d=f.calistir(t(22,'13:00'))
        self.assertEqual(emek(d,g+'/k1'),195); self.assertEqual(emek(d,g+'/k2'),227); self.assertEqual(emek(d,g),422)
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar']['BEKLEME_ONAY'],40)
        self.assertEqual(kisinin_gunu(d,'K023','2026-10-22')['kovalar']['BEKLEME_ONAY'],10)
        self.assertEqual(d.isler[g]['durum'],'BITTI'); self.assertEqual(d.isler[g]['tahmini_sure_dk'],360); self.assertFalse(any(g in l for l in d.listeler.values()))
        self.assertEqual(etap_gostergesi(d,f.etap['E-IML'])['tamamlanan'],6)

    def test_Y16_canli_E8(self):
        """E8 TASARIM: Y16 K004'ün IMALAT havuzuna iş tanımlaması T3 matrisiyle reddediliyor."""
        f=Duzenek(); d=f.calistir(t(22,'08:00'))
        f.olay('K004','IS.TANIMLADIM',t(22,'08:00'),girdiler={'isler':[{'birim':'IMALAT','islem':'Govde kaynagi','tur':'SURELI','kisi_sayisi':2,'tahmini_sure_dk':180,'onay_gerekli':True}]})
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')

    def test_Y17(self):
        for gun_son,beklenen in [(17,1),(12,0)]:
            f=Duzenek(); ilk=f.gorev_ata(t(26,'09:14'),satirlar=[f.gorev_satiri(zaman_degeri=8,teslim_tarihi='2026-11-13')]+[f.gorev_satiri(teslim_tarihi='2026-11-13') for _ in range(12)]+[f.gorev_satiri(kisi='K044',teslim_tarihi='2026-11-23',zaman_degeri=3,on_kosul=[{'satir':1}])])
            bek=ilk.rsplit('/',1)[0]+'/14'; f.gorev_olay('KABUL_ETTIM',t(26,'10:00'),ilk); f.gorev_olay('KABUL_ETTIM',t(26,'10:00'),bek,'K044'); f.gorev_olay('TAMAMLADIM',t(gun_son,'10:00',11),ilk)
            d=f.calistir(t(17,'11:00',11)); self.assertEqual(adil_performans(d,'K041','2026-11-01','2026-11-30')['bekletme'],beklenen); self.assertEqual(d.gorevler[bek]['durum'],'ACIK')

    def test_Y18(self):
        f=Duzenek(); f.ata(2,'K023'); f.is_olay('MESAI.GIRDIM','07:58',kisi='K023'); f.is_olay('BASLADIM','08:00',2,'K023'); f.is_olay('DEVAM_ETTIM','10:15',2,'K023'); bit=f.is_olay('TAMAMLADIM','11:00',2,'K023')
        d=f.calistir(t(22,'11:05')); eski=bit+':R08:K009'; self.assertTrue(d.bildirimler[eski]['gecerli'])
        f.ata(5,'K023',2,zaman='2026-10-22T10:59:30+03:00'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertFalse(d.bildirimler[eski]['gecerli']); self.assertEqual(d.listeler['K023'],[is_id(5)])
        self.assertEqual(d.son_hal(),f.calistir(t(22,'11:05')).son_hal())

    def test_Y19(self):
        d=s1().calistir(t(22,'11:45')); acik=[a for a in d.araliklar if a['bitis'] is None]
        self.assertEqual(len(acik),1); self.assertEqual(acik[0]['is'],is_id(2)); self.assertEqual(acik[0]['baslangic'],an(t(22,'11:42')))

    def test_Y20(self):
        f=Duzenek(); f.olay('K017','MESAI.GIRDIM',t(22,'08:00'),olay_kimligi='K017-2610220007-T'); d=f.calistir(t(22,'09:00'))
        c=Cihaz('K017','T',Saat(t(22,'09:00'))); c.sayaci_esitle(d); self.assertEqual(c.olay_kimligi_uret(),'K017-2610220008-T')
        c.saat.ilerlet(t(23,'08:00')); self.assertEqual(c.olay_kimligi_uret(),'K017-2610230001-T')

    def test_Y21(self):
        f=Duzenek(); f.ata(5); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',5); d=f.calistir(t(22,'10:00'))
        self.assertEqual(emek(d,is_id(5)),120); self.assertEqual(yuk(d,'K017','2026-10-22','2026-10-22'),0)

    def test_Y22(self):
        f=Duzenek(); g=f.gorev_ata(teslim_tarihi='2026-10-23'); f.gorev_olay('IPTAL_ETTIM',t(22,'09:00'),g,'K012'); d=f.calistir(t(26,'09:00')); e=etap_gostergesi(d,f.etap['E-TAS'])
        self.assertEqual(sum(e['dort_kategori'].values()),0); self.assertEqual(e['planli_toplam'],0)

    def test_Y23(self):
        f=Duzenek(); d=f.calistir(t(26,'09:00')); f.olay('K001','AYAR.ONAY_ORANI',t(26,'09:00'),girdiler={'deger':.2,'gecerli_baslangic':'2026-10-21'})
        self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'DURUM'); self.assertNotIn(f.olaylar[-1]['olay_kimligi'],d.olaylar)

    def test_Y24(self):
        from .test_senaryolar import revizyon_ornegi
        f,g,r,o=revizyon_ornegi(ikinci_ret=True); r2=f.gorev_olay('REDDETTIM',t(4,'15:30',11),r,'K012',**{'not':'Ikinci','sebep_olan':'K041','revizyon_ver':True,'yeni_teslim_tarihi':'2026-11-06','zaman_degeri':2,'kime':'K041'})+'/1'
        f.gorev_olay('KABUL_ETTIM',t(5,'09:00',11),r2); f.gorev_olay('TAMAMLADIM',t(6,'15:00',11),r2); f.gorev_olay('ONAYLADIM',t(6,'16:00',11),r2,'K012')
        d=f.calistir(t(6,'17:00',11)); once=d.son_hal(); d.yeniden_kur(); self.assertEqual(d.son_hal(),once); self.assertEqual(d.gorevler[g]['durum'],'BITTI')
        self.assertIsNone(d.gorevler[r]['is_puani']); self.assertIsNone(d.gorevler[r2]['is_puani'])

    def test_Y25(self):
        f,ids=s13(); f.gorev_olay('DEGISTIRDIM',t(23,'11:00'),ids['i'],'K012',degisenler={'teslim_tarihi':'2026-11-06'})
        d=f.calistir(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01'); kaynak=deepcopy((d.hassas_ekler,d.ay_kapanislari))
        self.assertAlmostEqual(gorev_payi(d,d.gorevler[ids['i']],'2026-10-01','2026-10-31'),19.384615384615383)
        d.yeniden_kur(); self.assertEqual((d.hassas_ekler,d.ay_kapanislari),kaynak)

    def test_Y26(self):
        f=Duzenek(); g=f.gorev_ata(onay_gerekli=True,onaylayan='K012',dosya_gerekli=True); f.gorev_olay('KABUL_ETTIM',t(22,'08:05'),g); o=f.gorev_olay('TAMAMLADIM',t(22,'09:10'),g,kanit=2)
        a=f.calistir(t(22,'09:20')); b=f.yeniden_hesapla(t(22,'09:20'),list(reversed(f.olaylar)))
        self.assertEqual(a.son_hal(),b.son_hal()); self.assertEqual(b.gorevler[o]['durum'],'ACIK')

    def test_Y27(self):
        f,g=kisi_degisim(); d=f.calistir(t(28,'09:30')); self.assertEqual(d.gorevler[g]['durum'],'ATANDI'); d=f.calistir(t(28,'10:30')); self.assertEqual(d.gorevler[g]['durum'],'ACIK')
        self.assertEqual(maas_dagilimi(d,'K041','2026-10-01')['paylar']['2509091'],24)
        self.assertEqual(maas_dagilimi(d,'K044','2026-10-01')['paylar']['2509091'],12)
        self.assertEqual(maas_dagilimi(d,'K044','2026-11-01')['paylar']['2509091'],24)

    def test_Y28(self):
        f=s12_veri(); e=f.olay('K001','MAAS.GUNCELLEDIM',t(16,'09:00'),girdiler={'kisi':'K041','gecerli_baslangic':'2026-10-16'})
        f.hassas[e]={'nesne_tur':'KISI','nesne_kimlik':'K041','tur':'MAAS_AYLIK','tutar':26000,'gecerli_baslangic':'2026-10-16'}
        d=f.calistir(t(30,'18:00')); m=maas_dagilimi(d,'K041','2026-10-01')
        self.assertEqual(m['maas'],Decimal('22857.14')); self.assertEqual(m['tutarlar'],{'2509084':Decimal('10285.71'),'2509091':Decimal('6533.33'),'PD.IDARI_MALI':Decimal('1884.44')}); self.assertEqual(m['dagitilamayan'],Decimal('4153.66'))

    def test_Y6_guncellemesi(self):
        f=s1(); d=f.calistir(t(22,'14:05'))
        for zaman,aciklama,kod in [(t(2,'14:00',11),'Eski','DURUM'),(t(22,'14:00'),'','BICIM')]:
            f.olay('K009','IS.SURE_EKLEDIM',zaman,1,{'baslangic':t(22,'08:00'),'bitis':t(22,'11:42'),'aciklama':aciklama,'is_bitti':False},adina='K017',giris_sekli='ELLE')
            self.assertEqual(yaz(d,f.olaylar[-1])['kod'],kod)
