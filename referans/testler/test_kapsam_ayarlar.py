"""Ayar değerlerinin gerçek kabul ve görünüm yolları; B58 açık davranış kilidi."""
import unittest
from irp.gorunum_v9 import hatirlatmalar
from .ortak import Duzenek,t
from .test_v7 import kur,gonder


class AyarDegerleri(unittest.TestCase):
    def rapor_duzenegi(self,value):
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'08:01'),dict(anahtar='gun_sonu_raporu_zorunlu',deger=True))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'08:02'),dict(anahtar='gun_sonu_hatirlatma',deger=value))
        return f,d

    def rows(self,d):
        return [x for x in hatirlatmalar(d) if x['kural']=='R32' and x['kisi']=='K041' and x['gun']=='2026-10-22']

    def test_ertesi_is_gunu_mesaisi_ve_zorunluluk_kapali(self):
        """T8 §8, T9 §8: ertesi mesai; zorunluluk kapalıysa R32 yok."""
        f,d=self.rapor_duzenegi('ERTESI_IS_GUNU')
        d.ilerlet(t(23,'07:59:59')); self.assertEqual(self.rows(d),[])
        d.ilerlet(t(23,'08:00')); self.assertTrue(self.rows(d))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(23,'08:01'),dict(anahtar='gun_sonu_raporu_zorunlu',deger=False))
        self.assertEqual(self.rows(d),[])

    def test_B58_davranis_kilidi_sayisal_hatirlatma_saat(self):
        """DAVRANIS_KILIDI: birim tasarımda yazılı değil; bugünkü saat yorumunu korur."""
        for value,once,esik in [(0,'07:59:59','08:00:00'),(3,'10:59:59','11:00:00')]:
            with self.subTest(value=value):
                _,d=self.rapor_duzenegi(value)
                d.ilerlet(t(23,once)); self.assertEqual(self.rows(d),[])
                d.ilerlet(t(23,esik)); self.assertTrue(self.rows(d))

    def test_izin_ik_ayarinda_acik_false_ust_onayiyla_biter(self):
        """T9 §9.1: tür için İK gerekmiyorsa üst onayı ONAYLI yapar."""
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'08:01'),dict(anahtar='izin_ik_onayi',deger={'YILLIK':False}))
        oid=gonder(f,d,'K041','IZIN.TALEP_ETTIM',t(22,'08:02'),dict(kisi='K041',tur='YILLIK',baslangic=t(26,'08:00'),bitis=t(26,'18:00'),gerekce='Yıllık izin'))
        gonder(f,d,'K012','IZIN.ONAYLADIM',t(22,'08:03'),dict(hedef=oid))
        self.assertEqual(d.izinler[oid]['durum'],'ONAYLI')
