"""Başlangıç haritasında kabul örneği olmayan olaylar ve sorgular."""
import unittest
from irp.gorunum_v7 import kapasite,gun_sonu_raporu
from .ortak import Duzenek,t
from .test_v7 import kur,gonder


class KabulBosluklari(unittest.TestCase):
    def test_gelecek_gun_tanimi_kaldirilinca_takvime_doner(self):
        """T8 §2: ileri tarihli gün istisnası kaldırılabilir."""
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        gonder(f,d,'K001','GUN.TANIMLADIM',t(22,'08:01'),dict(tarih='2026-10-26',tur='TATIL',ad='Özel tatil'))
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-26'),0)
        gonder(f,d,'K001','GUN.KALDIRDIM',t(22,'08:02'),dict(tarih='2026-10-26'))
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-26'),9)

    def test_bakim_baslamadan_iptal_edilir(self):
        """T8 §6: bakımın ileri tarihli planı başlamadan geri alınabilir."""
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        oid=gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(22,'08:01'),dict(tezgah='CNC-02',baslangic=t(23,'09:00'),bitis=t(23,'10:00'),aciklama='Bakım'))
        self.assertFalse(d.bakimlar[oid]['iptal'])
        gonder(f,d,'K009','TEZGAH.BAKIM_IPTAL_ETTIM',t(22,'08:02'),dict(hedef=oid))
        self.assertTrue(d.bakimlar[oid]['iptal'])

    def test_beyaz_yakanin_gunu_iade_ve_tekrar_gonderim(self):
        """T8 §8/T9 §8: beyaz yaka iade edilen günü yeniden gönderir."""
        from irp.gorunum_v9 import gun_isleri
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        gonder(f,d,'K001','GUN_ONAYI.AYARLADIM',t(22,'08:01'),dict(birim=d.kisiler['K041']['birim'],gerekli=True,gecerli_baslangic='2026-10-22'))
        gonder(f,d,'K041','GUN_SONU.GONDERDIM',t(22,'18:01'),dict(gun='2026-10-22',aciklama='Gün tamam',tanimsiz_aciklama=''))
        gonder(f,d,'K012','GUN_SONU.IADE_ETTIM',t(22,'18:02'),dict(kisi='K041',gun='2026-10-22',gerekce='Açıklama'))
        self.assertEqual(gun_sonu_raporu(d,'K041','2026-10-22')['durum'],'IADE')
        self.assertTrue(any(x['tur']=='MESAI_SONU' and x['gun']=='2026-10-22' for x in gun_isleri(d,'K041')))
        gonder(f,d,'K041','GUN_SONU.GONDERDIM',t(22,'18:03'),dict(gun='2026-10-22',aciklama='Açıklama eklendi',tanimsiz_aciklama=''))
        self.assertEqual(gun_sonu_raporu(d,'K041','2026-10-22')['durum'],'GONDERILDI')
