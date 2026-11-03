"""Tarihsel ana veri ve takvim korumalarının kalan sınırları."""
import unittest
from decimal import Decimal
from .ortak import Duzenek,t,is_id
from .test_v7 import kur,gonder


class TarihselMutasyonlar(unittest.TestCase):
    def test_M180_onay_bekleyen_basi_ayni_sirada_tutmak_gecerlidir(self):
        """T3 liste kilidi: başın yerini değiştirmek yasaktır; 1 → 1 yeri değiştirmez."""
        f=Duzenek(); f.ata(9); f.is_olay('MESAI.GIRDIM','07:58')
        f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=kur(f,t(22,'09:01'))
        gonder(f,d,'K009','IS.SIRALADIM',t(22,'09:02'),dict(kisi='K017',yeni_sira=1),9)
        self.assertEqual(d.listeler['K017'],[is_id(9)])

    def test_M242_henuz_gonderilmemis_beyaz_yaka_gunu_iade_edilemez(self):
        """T8 §8: iade yalnız gönderilmiş veya değişmiş rapora uygulanır."""
        f=Duzenek(); d=kur(f,t(22,'18:01'))
        gonder(f,d,'K012','GUN_SONU.IADE_ETTIM',t(22,'18:02'),dict(kisi='K041',gun='2026-10-22',gerekce='Henüz gönderilmedi'),bek='DURUM')

    def test_M235_ekip_lideri_rolu_olmayan_atayan_kendi_isini_onaylar(self):
        """T3/T4: atayan ilişkisi ekip lideri rolünden bağımsız onay yetkisidir."""
        f=Duzenek()
        f.olay('K001','IS.ATADIM',t(21,'16:00'),9,dict(kisi='K017',sira=1))
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=kur(f,t(22,'09:01'))
        oid=gonder(f,d,'K001','IS.ONAYLADIM',t(22,'09:02'),{},9)
        self.assertNotIn(oid,d.supheliler); self.assertEqual(d.isler[is_id(9)]['durum'],'BITTI')

    def test_M171_gecmis_gorunum_yalniz_o_anda_bilinen_hassas_eki_kullanir(self):
        """Karar 15/74: maaş eki bağlı kaynak olayıyla birlikte tarihsel görünüme girer."""
        from irp.gorunum_v7 import durum,saat_maliyeti
        f=Duzenek()
        oid=f.olay('K001','MAAS.GUNCELLEDIM',t(26,'09:00'),girdiler=dict(kisi='K017',gecerli_baslangic='2026-10-26'))
        f.hassas[oid]=dict(nesne_tur='KISI',nesne_kimlik='K017',tur='MAAS_AYLIK',tutar=36000,gecerli_baslangic='2026-10-26')
        d=kur(f,t(26,'09:01')); old=durum(d,t(22,'09:00'))
        self.assertEqual(saat_maliyeti(old,'K017','2026-10-22'),Decimal(20000)/Decimal(180))
        self.assertEqual(saat_maliyeti(d,'K017','2026-10-26'),Decimal(200))

    def test_M213_aktarimdaki_istihdam_disi_taniklik_emek_uretmez(self):
        """Karar 59/T8: istihdam dışında kapasite ve ücretli emek yoktur.

        Servis aktarımı yetki kapısını geçse de hesap bu korumayı sürdürür.
        """
        f=Duzenek(); f.ata(4)
        f.olay('K001','KISI.AYRILDI',t(21,'17:00'),girdiler=dict(kisi='K017',ayrilis_tarihi='2026-10-21'))
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',4); f.is_olay('TAMAMLADIM','09:00',4)
        d=f.calistir(t(22,'09:01'))
        self.assertFalse(any(a['kisi']=='K017' and a['is']==is_id(4) for a in d.araliklar))

    def test_M260_baslamis_gunun_tatili_kaldirilamaz(self):
        """Karar 56/T4: tatil ve gün istisnası yalnız ileri gün için kaldırılır."""
        f=Duzenek(); d=kur(f,t(29,'09:00'))
        gonder(f,d,'K001','TATIL.KALDIRDIM',t(29,'09:01'),dict(tarih='2026-10-29'),bek='DURUM')
