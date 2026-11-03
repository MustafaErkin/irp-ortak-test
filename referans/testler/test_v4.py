"""V4: yalniz istenen duzeltmeler, Y44-Y49 ve pay korunumu."""
import unittest
from copy import deepcopy
from datetime import timedelta
from irp import Depo, Saat, an
from irp.cihaz import Cihaz
from irp.kisi_gunu import kapi
from irp.gorunumler import gorev_payi, gorev_gunluk_paylar, kapasite, kisinin_gunu, maas_dagilimi
from irp.is_ import emek
from irp.surum import is_alanlari, ozet, liste_surumu, META
from irp.zaman import ay_kapanisi
from .ortak import Duzenek, t, is_id, yaz
from .test_v3 import gonder, elle_ornegi


def kapanan_gorev():
    f = Duzenek()
    g = f.gorev_ata(t(28, '09:00'), ad='Kontrol listesi', zaman_degeri=30,
                   zorluk=2, teslim_tarihi='2026-11-05')
    f.gorev_olay('KABUL_ETTIM', t(28, '09:30'), g)
    d = f.calistir(t(1, '00:30', 11))
    ay_kapanisi(d, '2026-10-01')
    return f, d, g


class SenaryolarV4(unittest.TestCase):
    def test_Y44(self):
        f = Duzenek(); f.ata(9); f.ata(2, sira=2)
        f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 9)
        d = f.calistir(t(22, '10:05'))
        e, s = gonder(f, d, 'K017', 'IS.TAMAMLADIM', t(22, '10:05'), 9)
        self.assertEqual(s['sonuc'], 'BASARILI'); self.assertIn(e, d.supheliler)
        self.assertEqual(d.isler[is_id(9)]['durum'], 'ONAY_BEKLIYOR')
        self.assertTrue(any(b['doguran_olay']==e and b['kural']=='R05' and b['alici']=='K009' for b in d.bildirimler.values()))
        d.ilerlet(t(22, '10:20'))
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'ONAY_BEKLIYOR')
        self.assertFalse(kapi(d.kisi_durumu['K017'], 'IS.BASLADIM', d.isler[is_id(2)], is_id(9)))
        _, s = gonder(f, d, 'K009', 'IS.ONAYLADIM', t(22, '10:30'), 9)
        self.assertEqual(s['sonuc'], 'BASARILI'); d.ilerlet(t(22, '10:40'))
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'],
                         {'CALISMA':120, 'SABIT_MOLA':15, 'BEKLEME_ONAY':15, 'TANIMSIZ':10})
        self.assertEqual(d.listeler['K017'][0], is_id(2))
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')

    def test_Y45a(self):
        f=Duzenek(); g=f.gorev_ata(t(26,'09:00'), ad='Montaj resmi seti', zaman_degeri=20, zorluk=3, teslim_tarihi='2026-10-30')
        f.gorev_olay('KABUL_ETTIM',t(26,'09:30'),g); d=f.calistir(t(27,'08:00'))
        for gun in (26,27,28,30):
            self.assertEqual(gorev_payi(d,d.gorevler[g],f'2026-10-{gun}',f'2026-10-{gun}'),5)
        _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(27,'09:00'),girdiler={'tarih':'2026-10-30','ad':'Kopru'})
        self.assertEqual(s['sonuc'],'BASARILI'); d.ilerlet(t(27,'10:00'))
        for gun in (26,27,28):
            self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],f'2026-10-{gun}',f'2026-10-{gun}'),20/3)
        self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-30'),20)
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-30'),27)

    def test_Y45b(self):
        f,d,g=kapanan_gorev(); once=deepcopy(d.ay_kapanislari)
        self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-01','2026-10-31'),10)
        _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(2,'09:00',11),girdiler={'tarih':'2026-11-04','ad':'Tatil'})
        self.assertEqual(s['sonuc'],'BASARILI'); d.ilerlet(t(2,'10:00',11))
        for gun in (2,3,5):
            self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],f'2026-11-{gun:02}',f'2026-11-{gun:02}'),20/3)
        self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-11-04','2026-11-04'),0)
        self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-01','2026-11-30'),30)
        self.assertEqual(maas_dagilimi(d,'K041','2026-10-01')['toplam_saat'],10)
        self.assertEqual(d.ay_kapanislari,once)

    def test_Y46(self):
        c=Cihaz('K017','T',Saat('2026-08-22T09:00:00+03:00'))
        once=[c.olay_kimligi_uret() for _ in range(3)]
        c.saat.ilerlet(t(22,'09:00')); c.sayaci_esitle(Depo(c.saat))
        c.veri['fark_saniye']=-61*86400
        kimlik=c.olay_kimligi_uret()
        self.assertEqual(kimlik,'K017-2608220004-T'); self.assertNotIn(kimlik,once)

    def test_Y47(self):
        f,d,e,s,h=elle_ornegi(onay=True)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(emek(d,is_id(9)),480)
        self.assertEqual(d.listeler['K017'][0],is_id(9))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'ONAY_BEKLIYOR')
        self.assertFalse(kapi(d.kisi_durumu['K017'],'IS.BASLADIM',d.isler[is_id(5)],is_id(9)))
        once=kisinin_gunu(d,'K017','2026-10-22')
        self.assertEqual(once['kovalar'],{'CALISMA':480,'SABIT_MOLA':60,'BEKLEME_ONAY':60})
        self.assertTrue(once['araliklar'][-1]['sistem_kapatti'])
        _,s=gonder(f,d,'K009','IS.ONAYLADIM',t(23,'08:45'),9)
        self.assertEqual(s['sonuc'],'BASARILI'); d.ilerlet(t(23,'08:50'))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'],{'BEKLEME_ONAY':45,'TANIMSIZ':5})
        self.assertEqual(d.listeler['K017'][0],is_id(5))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'CALISMIYOR')

    def test_Y48(self):
        f=Duzenek(); d=f.calistir(t(26,'10:00'))
        for tarih,bek in [('2026-10-26','DURUM'),('2026-10-27','BASARILI')]:
            _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(26,'10:00'),girdiler={'tarih':tarih,'ad':'Tatil'})
            self.assertEqual(s.get('kod',s['sonuc']),bek)
        tak=deepcopy(d.varsayilan_takvim); tak['mesai_baslangic']='09:00'
        _,s=gonder(f,d,'K001','TAKVIM.TANIMLADIM',t(26,'10:00'),girdiler=dict(tak,gecerli_baslangic=t(26,'12:00')))
        self.assertEqual(s.get('kod'),'DURUM')
        _,s=gonder(f,d,'K001','TAKVIM.TANIMLADIM',t(26,'10:00'),girdiler=tak)
        self.assertEqual(s['sonuc'],'BASARILI')
        self.assertEqual(d.takvim('2026-10-26')['mesai_baslangic'],'08:00')
        self.assertEqual(d.takvim('2026-10-27')['gecerli_baslangic'],t(27,'00:00'))
        self.assertEqual(d.takvim('2026-10-27')['mesai_baslangic'],'09:00')

    def test_Y49(self):
        f=Duzenek(); f.ata(1); f.ata(2,sira=2); d=f.calistir(t(22,'07:30'))
        eski=liste_surumu(d,'K017')
        _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'07:30'),5,{'kisi':'K017','sira':1})
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertNotEqual(liste_surumu(d,'K017'),eski)
        f.olay('K009','IS.ATADIM','2026-10-22T07:30:01+03:00',6,{'kisi':'K017','sira':1},harf='T')
        e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=d.isler[is_id(6)]['surum']
        e['neyin_ustunde'].append({'tur':'LISTE','kimlik':'K017','surum':eski})
        self.assertEqual(yaz(d,e,taze=False)['kod'],'BAYAT')
        self.assertEqual(d.listeler['K017'],[is_id(5),is_id(1),is_id(2)])
        self.assertEqual(d.isler[is_id(6)]['durum'],'HAVUZDA')


class DegismezlerV4(unittest.TestCase):
    def test_B30_maas_ve_yuk_ilk_kabulden(self):
        f=Duzenek(); g=f.gorev_ata(t(26,'09:00'),zaman_degeri=30,teslim_tarihi='2026-10-30')
        f.gorev_olay('KABUL_ETTIM',t(27,'09:00'),g); d=f.calistir(t(28,'09:00'))
        _,s=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(28,'09:00'),g,{'degisenler':{'kisi':'K044'}})
        self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K044','GOREV.KABUL_ETTIM',t(28,'10:00'),g)
        self.assertEqual(s['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[g]['ilk_kabul_ani'],t(27,'09:00'))
        for yuk in (False,True):
            self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-26',yuk=yuk),0)
            self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-27','2026-10-27',yuk=yuk),10)
            self.assertEqual(gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-30',yuk=yuk),30)

    def test_I57_takvim_tatil_toplam_payi_korur(self):
        f,d,g=kapanan_gorev()
        for kod,gi in [('TATIL.EKLEDIM',{'tarih':'2026-11-04','ad':'Tatil'}),
                       ('TAKVIM.TANIMLADIM',dict(d.varsayilan_takvim,calisma_gunleri=[1,3,4,5]))]:
            _,s=gonder(f,d,'K001',kod,t(2,'09:00',11),girdiler=gi)
            self.assertEqual(s['sonuc'],'BASARILI')
            for yuk in (False,True):
                self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],'2026-10-01','2026-11-30',yuk=yuk),30)
        d.yeniden_kur()
        self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],'2026-11-01','2026-11-30'),20)

    def test_I58_kapanmis_gorev_payi_hic_degismez(self):
        f,d,g=kapanan_gorev(); once=deepcopy(d.ay_kapanislari)
        _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(2,'09:00',11),girdiler={'tarih':'2026-11-04','ad':'Tatil'})
        self.assertEqual(s['sonuc'],'BASARILI')
        d.yeniden_kur(); ay_kapanisi(d,'2026-10-01')
        self.assertEqual(d.ay_kapanislari,once)
        yeni=Depo(Saat(d.saat.simdi())); yeni._kayitlar=deepcopy(d._kayitlar)
        yeni.hassas_ekler=deepcopy(d.hassas_ekler); yeni.ay_kapanislari=deepcopy(d.ay_kapanislari); yeni.yeniden_kur()
        self.assertEqual(gorev_gunluk_paylar(d,d.gorevler[g]),gorev_gunluk_paylar(yeni,yeni.gorevler[g]))
        self.assertEqual(gorev_payi(yeni,yeni.gorevler[g],'2026-10-01','2026-10-31'),10)

    def test_B36_bes_isletim_alani_haric(self):
        f=Duzenek(); g=f.gorev_ata(); d=f.calistir(t(22,'09:00'))
        once=ozet(is_alanlari(d.gorevler[g]))
        for alan in META:
            yeni=deepcopy(d.gorevler[g]); yeni[alan]='degisti'
            self.assertEqual(ozet(is_alanlari(yeni)),once)
        yeni=deepcopy(d.gorevler[g]); yeni['ad']='Baska'
        self.assertNotEqual(ozet(is_alanlari(yeni)),once)
