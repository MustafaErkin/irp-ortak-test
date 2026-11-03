"""Karar 99: Y101c–d ve dar yetki istisnasının kabul/ret sınırları."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from irp.gorunum_v7 import oku
from irp.gorunum_v9 import proje_gorebilir_mi
from irp.gorunum_v10_1 import surumler, gecerli_surum, surum_olayi_gorebilir
from irp.kurallar_v10 import projede_yetkili
from irp.degismezler_v10_1 import denetle
from .ortak import Duzenek, t
from .test_v7 import kur, gonder
from .test_v10 import proje_duzenegi
from .test_v10_1 import ek_yetki, belge_turu, surum_olayi, plan, tarih


def ozel_belge_duzenegi():
    f=ek_yetki(Duzenek())
    f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:00'),girdiler=belge_turu(surum_onaylayanlar=None))
    tur=belge_turu(surum_onaylayanlar=dict(kimler=['YETKILI'],kapsam='FIRMA'))
    tur.update(kod='BELGE2',ad='Belge 2')
    f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:01'),girdiler=tur)
    n=f.olay('K012','NESNE.ACTIM',t(22,'09:00'),girdiler=dict(tur='BELGE2',ad='Elektrik şeması',proje='2509084',sorumlu='K041'))
    return f,kur(f,t(22,'09:05')),n


def ek_erisim_duzenegi():
    f=ek_yetki(proje_duzenegi())
    f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:00'),girdiler=belge_turu(surum_onaylayanlar=None))
    n=f.olay('K004','NESNE.ACTIM',t(22,'09:00'),girdiler=dict(tur='BELGE',ad='Elektro-pres resmi',proje='2509091',sorumlu='K041'))
    f.olay('K004','PROJE.ERISIM_VERDIM',t(22,'09:01'),girdiler=dict(proje='2509091',kisi='K041',gerekce='Belge'))
    return f,kur(f,t(22,'09:05')),n


class SenaryolarKarar99(unittest.TestCase):
    def test_Y101c(self):
        f=ek_yetki(proje_duzenegi())
        f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:00'),girdiler=belge_turu(surum_onaylayanlar=None))
        d=kur(f,t(22,'08:55'))
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),dict(gorevler=[
            f.gorev_satiri(ad='Montaj resmi',teslim_tarihi='2026-10-24',zaman_degeri=8,zorluk=2)]))
        n=gonder(f,d,'K012','NESNE.ACTIM',t(22,'09:10'),dict(tur='BELGE',ad='Konveyör montaj resmi',proje='2509084',sorumlu='K041'))
        n3=gonder(f,d,'K012','NESNE.ACTIM',t(22,'09:20'),dict(tur='BELGE',ad='PLC şeması',proje='2509084',sorumlu='K044'))
        self.assertTrue(proje_gorebilir_mi(d,'K041','2509084'))
        self.assertFalse(projede_yetkili(d,'K041','2509084'))
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041',ad='R0')
        self.assertEqual([(s['surum_no'],s['durum']) for s in surumler(d,n,cagiran='K041')],[(1,'TASLAK')])
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:10'),kim='K041',bek='YETKI')
        gonder(f,d,'K041','GOREV.ATADIM',t(22,'10:20'),dict(gorevler=[
            f.gorev_satiri(ad='Ölçü kontrolü',kisi='K006',etap=None,teslim_tarihi='2026-10-24',zaman_degeri=1)]),bek='YETKI')
        self.assertFalse(proje_gorebilir_mi(d,'K044','2509084'))
        surum_olayi(f,d,n3,'EKLEDIM',t(22,'10:30'),kim='K044',ad='R0',dosyalar=['F-N3'],bek='YETKI')
        self.assertEqual(len(d.nesne_surumleri),1)
        self.assertIsNone(gecerli_surum(d,n))

    def test_Y101d(self):
        f,d,n=ozel_belge_duzenegi()
        oid=surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041',ad='R0')
        d.ilerlet(t(22,'10:05'))
        for k in ('K012','K001'):
            self.assertEqual([s['surum_no'] for s in oku(d,k,'SURUMLER',n)],[1])
            self.assertEqual(oku(d,k,'DOSYA','F-1')['dosya_kimligi'],'F-1')
        self.assertEqual(oku(d,'K044','SURUMLER',n),[])
        with self.assertRaises(PermissionError): oku(d,'K044','DOSYA','F-1')
        self.assertIn(oid,[e['olay_kimligi'] for e in oku(d,'K001','HAM_OLAY','K001')])
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:30'),kim='K012',bek='YETKI')
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'11:00'),kim='K001')
        self.assertEqual(gecerli_surum(d,n)['surum_no'],1)
        self.assertEqual([s['durum'] for s in surumler(d,n,cagiran='K044')],['ONAYLI'])


class Karar99Kenarlari(unittest.TestCase):
    def test_ek_erisim_sorumluya_yalniz_taslak_yazdirir(self):
        f,d,n=ek_erisim_duzenegi()
        self.assertTrue(proje_gorebilir_mi(d,'K041','2509091'))
        self.assertFalse(projede_yetkili(d,'K041','2509091'))
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        for kod,z in [('ONAYLADIM','10:01'),('GERI_CEKTIM','10:02')]:
            surum_olayi(f,d,n,kod,t(22,z),kim='K041',bek='YETKI')
        gonder(f,d,'K041','NESNE.GUNCELLEDIM',t(22,'10:03'),dict(hedef=n,degisenler=dict(ad='Başka ad')),n,'NESNE',bek='YETKI')
        tarih(f,d,[plan(1,t(23),t(23,'10:00'))],t(22,'10:04'),kim='K041',bek='YETKI')
        self.assertEqual(d.nesneler[n]['ad'],'Elektro-pres resmi')
        self.assertEqual(len(d.nesne_surumleri),1)

    def test_ustun_yazmasinda_t9_proje_kapisi_kalir(self):
        f,d,n=ek_erisim_duzenegi()
        self.assertTrue(proje_gorebilir_mi(d,'K012','2509091'))
        self.assertFalse(projede_yetkili(d,'K012','2509091'))
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        for kod,z in [('EKLEDIM','10:01'),('ONAYLADIM','10:02'),('GERI_CEKTIM','10:03')]:
            surum_olayi(f,d,n,kod,t(22,z),kim='K012',bek='YETKI')
        self.assertEqual(len(surumler(d,n,cagiran='K012')),1)
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:04'),kim='K001')
        self.assertEqual(gecerli_surum(d,n)['surum_no'],1)

    def test_erisim_kaybi_sorumlu_ve_ustun_okumasini_kapatir(self):
        f,d,n=ek_erisim_duzenegi()
        oid=surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        for k in ('K041','K012'):
            self.assertEqual(len(surumler(d,n,cagiran=k)),1)
            self.assertTrue(surum_olayi_gorebilir(d,k,d.olaylar[oid]))
        gonder(f,d,'K004','PROJE.ERISIM_KALDIRDIM',t(22,'10:01'),dict(proje='2509091',kisi='K041',gerekce='Bitti'))
        for k in ('K041','K012'):
            self.assertFalse(proje_gorebilir_mi(d,k,'2509091'))
            self.assertEqual(surumler(d,n,cagiran=k),[])
            self.assertFalse(surum_olayi_gorebilir(d,k,d.olaylar[oid]))
            with self.assertRaises(PermissionError): oku(d,k,'DOSYA','F-1')
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:02'),kim='K041',no=2,bek='YETKI')
        self.assertTrue(denetle(d,True)['I119'])

    def test_sorumlu_olmayan_uye_taslak_ekleyemez(self):
        f,d,n=ek_erisim_duzenegi()
        gonder(f,d,'K004','PROJE.ERISIM_VERDIM',t(22,'09:06'),dict(proje='2509091',kisi='K044',gerekce='İnceleme'))
        self.assertTrue(proje_gorebilir_mi(d,'K044','2509091'))
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K044',bek='YETKI')
        self.assertFalse(d.nesne_surumleri)

    def test_istisna_eklenen_baska_proje_hedefine_tasinmaz(self):
        f,d,n=ek_erisim_duzenegi()
        gonder(f,d,'K012','PROJE.ERISIM_VERDIM',t(22,'09:06'),dict(proje='2509084',kisi='K041',gerekce='İnceleme'))
        self.assertTrue(proje_gorebilir_mi(d,'K041','2509084'))
        self.assertFalse(projede_yetkili(d,'K041','2509084'))
        gonder(f,d,'K041','NESNE.SURUM_EKLEDIM',t(22,'10:00'),dict(hedef=n,dosyalar=['F-1']),
            [dict(tur='NESNE',kimlik=n),dict(tur='PROJE',kimlik='2509084')],bek='YETKI',
            kanit=[dict(dosya_kimligi='F-1',parmak_izi='abc')])
        self.assertFalse(d.nesne_surumleri)

    def test_guncel_hiyerarsi_okutur_onay_yetkisi_vermez(self):
        f,d,n=ozel_belge_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'10:01'),dict(kisi='K041',gecerli_baslangic=t(22,'10:01'),degisenler=dict(birim='MUHASEBE')))
        self.assertEqual(surumler(d,n,cagiran='K012'),[])
        self.assertEqual(len(surumler(d,n,cagiran='K007')),1)
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:02'),kim='K007',bek='YETKI')
        self.assertTrue(denetle(d,True)['I119'])


class Karar99Degismezleri(unittest.TestCase):
    def test_I119_onaylayamayan_ust_ve_diger_okuyucular(self):
        f,d,n=ozel_belge_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        gorunen={k for k in d.kisiler if surumler(d,n,cagiran=k)}
        self.assertEqual(gorunen,{'K041','K012','K001'})
        self.assertTrue(denetle(d,True)['I119'])

    def test_I119_eksik_ust_ve_yetkisiz_okumayi_yakalar(self):
        f,d,n=ozel_belge_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        for bozuk_kisi,ekle in [('K012',False),('K044',True)]:
            def bozuk(depo,nesne,cagiran=None):
                if cagiran==bozuk_kisi:
                    return deepcopy(list(depo.nesne_surumleri.values())) if ekle else []
                return surumler(depo,nesne,cagiran=cagiran)
            with self.subTest(kisi=bozuk_kisi), patch('irp.gorunum_v10_1.surumler',bozuk):
                self.assertFalse(denetle(d,True)['I119'])
