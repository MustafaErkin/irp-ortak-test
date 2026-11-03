"""Y68-Y73: belgedeki sayilar ve normal kabul yolu."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo, Saat, an
from irp.gorunumler import (kapasite, maas_dagilimi, iscilik_maliyeti, etap_gostergesi,
    kisinin_gunu, onay_listesi, adil_performans, gorev_isaretleri, gorev_payi)
from irp.gorunum_v6 import iptal_edilenler
from irp.gorev import son_teslim_ani
from irp.zaman import ay_kapanisi
from irp.is_ import emek
from .ortak import Duzenek, t, is_id, s1
from .v5_destek import gonder, kurulum_paketi, sifirdan, is_satiri
from .tur2_ornekler import iki_kisi


def bitmis():
    f = Duzenek(); f.ata(1)
    for kod, saat, h in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 1), ('TAMAMLADIM', '09:00', 1)]: f.is_olay(kod, saat, h)
    return f, f.calistir(t(22, '09:00'))


def baglanti(**alanlar):
    s = dict(proje='2509091', etap=None, parca_kodu='2509091_01_01-17')
    s.update(alanlar)
    return dict(degisenler=s, gerekce='Yanlis projeye acilmis')


def gorev_onayi():
    f = Duzenek(); g = f.gorev_ata(t(22, '09:00'), ad='Kontrol', teslim_tarihi='2026-10-30', zaman_degeri=10, zorluk=1, onay_gerekli=True, onaylayan='K012')
    f.gorev_olay('KABUL_ETTIM', t(22, '10:00'), g)
    o = f.gorev_olay('TAMAMLADIM', t(22, '11:00'), g)
    return f, f.calistir(t(22, '11:05')), g, o


class SenaryolarV6(unittest.TestCase):
    def test_Y68a(self):
        f, d = bitmis()
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '09:30'), 1, baglanti())
        self.assertEqual(d.isler[is_id(1)]['durum'], 'BITTI')
        self.assertEqual(emek(d, is_id(1)), 60)
        self.assertEqual({a['proje'] for a in d.araliklar if a['is'] == is_id(1)}, {'2509091'})
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 0)
        self.assertEqual(iscilik_maliyeti(d, '2509091', '2026-10-01', '2026-10-31')['iscilik'], Decimal('111.11'))
        self.assertEqual(iscilik_maliyeti(d, '2509084', '2026-10-01', '2026-10-31')['iscilik'], 0)

    def test_Y68b(self):
        for kim, bek in [('K009', 'YETKI'), ('K001', 'BASARILI'), ('K012', 'YETKI')]:
            f, d = bitmis(); gonder(f, d, kim, 'IS.BAGLANTI_DUZELTTIM', t(22, '09:30'), 1, baglanti(), bek=bek)
        f, d = bitmis()
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '09:30'), 1, baglanti(proje='9999999'), bek='DURUM')
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '09:31'), 1, dict(baglanti(), gerekce=''), bek='BICIM')
        gonder(f, d, 'K004', 'IS.DEGISTIRDIM', t(22, '09:32'), 1, {'degisenler': {'proje': '2509091'}}, bek='BICIM')

    def test_Y68c(self):
        f = Duzenek(); f.ata(4)
        for kod, saat, h in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 4), ('DEVAM_ETTIM', '10:15', 4), ('MESAI.CIKTIM', '11:00', None)]: f.is_olay(kod, saat, h, gun=30)
        d = f.calistir(t(30, '11:00')); d.ilerlet(t(1, '00:30', 11)); ay_kapanisi(d, '2026-10-01')
        donmus = deepcopy(d.ay_kapanislari)
        gonder(f, d, 'K017', 'MESAI.GIRDIM', t(2, '07:58', 11))
        gonder(f, d, 'K017', 'IS.BASLADIM', t(2, '08:00', 11), 4)
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(2, '09:00', 11), 4, baglanti(parca_kodu='2509091_01_01-58'))
        d.ilerlet(t(2, '09:30', 11))
        self.assertEqual(d.ay_kapanislari, donmus)
        self.assertEqual(iscilik_maliyeti(d, '2509084', '2026-10-01', '2026-10-31')['iscilik'], Decimal('305.56'))
        self.assertEqual(iscilik_maliyeti(d, '2509091', '2026-11-01', '2026-11-30')['iscilik'], Decimal('166.67'))
        self.assertEqual(emek(d, is_id(4)), 255)

    def test_Y69a(self):
        f = s1(); d = f.calistir(t(22, '11:45'))
        once = deepcopy(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'])
        karne = adil_performans(d, 'K017', '2026-10-01', '2026-10-22')
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(23, '10:00'), 1, {'gerekce': 'Musteri istemiyor'})
        self.assertEqual(d.isler[is_id(1)]['iptal_oncesi_durum'], 'BITTI')
        self.assertEqual(d.isler[is_id(1)]['iptal_eden'], 'K009')
        self.assertEqual(emek(d, is_id(1)), 186)
        iptal = iptal_edilenler(d, '2509084')
        self.assertEqual(iptal['sayi'], 1); self.assertAlmostEqual(iptal['emek_saat'], 186/60)
        self.assertEqual(iptal['maliyet']['iscilik'], Decimal('344.44'))
        self.assertEqual(adil_performans(d, 'K017', '2026-10-01', '2026-10-22'), karne)
        # Acik S1 araligi saatin ilerlemesiyle uzar; iptal edilen isin kapali araligi aynidir.
        self.assertTrue(all(a['is_iptal'] for a in d.araliklar if a['is'] == is_id(1)))

    def test_Y69b(self):
        f, i = iki_kisi()
        f.olaylar = [e for e in f.olaylar if e['oldugu_an'] not in (t(22, '12:45'), t(22, '12:55'))]
        d = f.calistir(t(22, '12:51'))
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '12:52'), i + '/k2', {'gerekce': 'Tek kisi yeterli'})
        d.ilerlet(t(22, '13:00'))
        self.assertEqual(d.isler[i]['durum'], 'BITTI'); self.assertEqual(d.isler[i]['bitis_ani'], an(t(22, '12:52')))
        self.assertEqual(emek(d, i + '/k1'), 195); self.assertEqual(emek(d, i + '/k2'), 234)
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 3)
        self.assertEqual(iptal_edilenler(d, '2509084')['emek_saat'], 234/60)
        self.assertEqual(d.kisi_durumu['K023']['durum'], 'CALISMIYOR')

    def test_Y69c(self):
        f, i = iki_kisi(); f.olaylar = [e for e in f.olaylar if e['oldugu_an'] not in (t(22, '12:45'), t(22, '12:55'))]
        d = f.calistir(t(22, '12:51')); gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '12:52'), i, {'gerekce': 'Ana iptal'})
        self.assertTrue(all(d.isler[k]['durum'] == 'IPTAL' for k in (i, i + '/k1', i + '/k2')))
        self.assertEqual(d.isler[i + '/k1']['iptal_oncesi_durum'], 'BITTI')
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 0)
        self.assertEqual(iptal_edilenler(d, '2509084')['emek_saat'], 429/60)

    def test_Y70a(self):
        f = Duzenek(); d = f.calistir(t(15, '10:00'))
        e, _ = gonder(f, d, 'K001', 'KISI.AYRILDI', t(15, '10:00'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-16'})
        m = maas_dagilimi(d, 'K060', '2026-10-01')
        self.assertEqual(m['maas'], Decimal('11428.57')); self.assertAlmostEqual(m['payda'], 180*12/21)
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['doguran_olay'] == e}, {'K001', 'K012'})
        self.assertEqual(kapasite(d, 'K060', '2026-10-12', '2026-10-16'), 45)
        self.assertEqual(kapasite(d, 'K060', '2026-10-19', '2026-10-23'), 0)
        gonder(f, d, 'K060', 'NOT.YAZDIM', t(19, '10:00'), '2509084', {'metin': 'Not'}, tur='PROJE', bek='YETKI')

    def test_Y70b(self):
        f = Duzenek(); d = f.calistir(t(15, '10:00'))
        e, _ = gonder(f, d, 'K001', 'KISI.EKLEDIM', t(15, '10:05'), girdiler={'kod': 'K061', 'ad': 'Yeni', 'birim': 'MEK_TASARIM', 'yaka': 'BEYAZ', 'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-10-19'})
        gonder(f, d, 'K001', 'MAAS.GUNCELLEDIM', t(15, '10:06'), girdiler={'kisi': 'K061', 'gecerli_baslangic': '2026-10-19'}, hassas_ek={'nesne_kimlik': 'K061', 'tur': 'MAAS_AYLIK', 'tutar': 20000, 'gecerli_baslangic': '2026-10-19'})
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['doguran_olay'] == e}, {'K012'})
        self.assertEqual(kapasite(d, 'K061', '2026-10-12', '2026-10-16'), 0)
        self.assertEqual(kapasite(d, 'K061', '2026-10-19', '2026-10-23'), 45)
        m = maas_dagilimi(d, 'K061', '2026-10-01'); self.assertEqual(m['maas'], Decimal('8571.43')); self.assertAlmostEqual(m['payda'], 180*9/21)
        gonder(f, d, 'K061', 'NOT.YAZDIM', t(16, '10:00'), '2509084', {'metin': 'Not'}, tur='PROJE', bek='YETKI')
        gonder(f, d, 'K061', 'NOT.YAZDIM', t(19, '10:00'), '2509084', {'metin': 'Not'}, tur='PROJE')

    def test_Y70c(self):
        f = Duzenek(); d = f.calistir(t(15, '10:00'))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(15, '10:00'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-16'})
        gonder(f, d, 'K001', 'KISI.EKLEDIM', t(26, '10:00'), girdiler={'kod': 'K060', 'ad': 'Geri donen', 'birim': 'MEK_TASARIM', 'yaka': 'BEYAZ', 'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-11-02'})
        self.assertEqual(len(d.kisiler['K060']['istihdam_donemleri']), 2)
        self.assertEqual(kapasite(d, 'K060', '2026-10-26', '2026-10-30'), 0)
        self.assertEqual(kapasite(d, 'K060', '2026-11-02', '2026-11-06'), 45)
        self.assertEqual(maas_dagilimi(d, 'K060', '2026-11-01')['payda'], 180)

    def test_Y70d(self):
        f = Duzenek(); d = f.calistir(t(22, '10:00'))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, '10:00'), girdiler={'kisi': 'K017', 'ayrilis_tarihi': '2026-10-30'})
        gonder(f, d, 'K009', 'IS.ATADIM', t(22, '10:05'), 5, {'kisi': 'K017', 'sira': 1}, bek='DURUM')
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(23, '10:00'), girdiler={'kisi': 'K017', 'ayrilis_tarihi': '2026-11-06'})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(26, '10:00'), girdiler={'kisi': 'K017', 'iptal': True})
        gonder(f, d, 'K009', 'IS.ATADIM', t(26, '10:05'), 5, {'kisi': 'K017', 'sira': 1})
        self.assertIsNone(d.kisiler['K017']['ayrilis_tarihi'])
        f = Duzenek(); d = f.calistir(t(15, '10:00'))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(15, '10:00'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-16'})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(20, '10:00'), girdiler={'kisi': 'K060', 'iptal': True}, bek='DURUM')

    def test_Y70e(self):
        f = Duzenek(); d = f.calistir(t(22, '10:00'))
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(22, '10:00'), girdiler={'kisi': 'K001', 'degisenler': {'roller': ['YONETICI']}, 'gecerli_baslangic': t(22, '10:00')}, bek='DURUM')
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, '10:01'), girdiler={'kisi': 'K001', 'ayrilis_tarihi': '2026-10-23'}, bek='DURUM')

    def test_Y71a(self):
        for kim, kod, bek in [('K001', 'IS.ONAYLADIM', 'BASARILI'), ('K004', 'IS.REDDETTIM', 'BASARILI'), ('K012', 'IS.ONAYLADIM', 'YETKI'), ('K023', 'IS.ONAYLADIM', 'YETKI')]:
            f = Duzenek(); f.ata(9)
            for k, s, h in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 9), ('DEVAM_ETTIM', '10:15', 9), ('TAMAMLADIM', '11:00', 9)]: f.is_olay(k, s, h)
            d = f.calistir(t(22, '11:05'))
            self.assertIn(is_id(9), [x['kimlik'] for x in onay_listesi(d, 'K004')])
            gonder(f, d, kim, kod, t(22, '11:10'), 9, {'not': 'Duzelt'} if kod.endswith('REDDETTIM') else {}, bek=bek)
            gonder(f, d, 'K004', 'IS.ATADIM', t(22, '11:11'), 5, {'kisi': 'K023', 'sira': 1})

    def test_Y71b(self):
        f = Duzenek(); f.ata(9, kisi='K009')
        for k, s, h in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 9), ('TAMAMLADIM', '09:00', 9)]: f.is_olay(k, s, h, kisi='K009')
        d = f.calistir(t(22, '09:05'))
        gonder(f, d, 'K009', 'IS.ONAYLADIM', t(22, '09:10'), 9, bek='YETKI')
        gonder(f, d, 'K004', 'IS.ONAYLADIM', t(22, '09:11'), 9)

    def test_Y71c(self):
        for kim, bek in [('K001', 'BASARILI'), ('K004', 'YETKI'), ('K041', 'YETKI'), ('K012', 'BASARILI')]:
            f, d, g, o = gorev_onayi()
            gonder(f, d, kim, 'GOREV.ONAYLADIM', t(22, '11:10'), g, bek=bek)
            if kim == 'K001':
                self.assertEqual(d.gorevler[g]['durum'], 'BITTI'); self.assertEqual(d.gorevler[o]['durum'], 'IPTAL')
                self.assertIsNone(d.gorevler[o]['is_puani']); self.assertEqual(gorev_payi(d, d.gorevler[o], '2026-10-01', '2026-10-31'), 0)
            if kim == 'K012': self.assertEqual(d.gorevler[o]['is_puani'], 1)

    def test_Y72(self):
        f = Duzenek(); d = f.calistir(t(26, '09:00'))
        gonder(f, d, 'K009', 'IS.BAGLANTI_DUZELTTIM', t(26, '09:00'), 2, baglanti(), bek='YETKI')
        g = {'eylem_kodu': 'IS.BAGLANTI_DUZELTTIM', 'kimler': ['YONETICI', 'BIRIM_YONETICISI'], 'kapsam': 'BIRIM'}
        gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(26, '10:00'), girdiler=g)
        gonder(f, d, 'K009', 'IS.BAGLANTI_DUZELTTIM', t(26, '10:05'), 2, baglanti())
        gonder(f, d, 'K004', 'YETKI.TANIMLADIM', t(26, '10:06'), girdiler=g, bek='YETKI')
        gonder(f, d, 'K001', 'KOD.TANIMLADIM', t(26, '10:10'), girdiler={'liste': 'ROL', 'kod': 'KALITE', 'ad': 'Kalite sorumlusu', 'aktif': True})
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(26, '10:11'), girdiler={'kisi': 'K052', 'degisenler': {'roller': ['BEYAZ_YAKA', 'KALITE']}, 'gecerli_baslangic': t(26, '10:11')})
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(26, '10:12'), girdiler={'kisi': 'K006', 'degisenler': {'roller': ['UYDURMA']}, 'gecerli_baslangic': t(26, '10:12')}, bek='DURUM')

    def test_Y73_tatil(self):
        f = Duzenek(); d = f.calistir(t(26, '09:00'))
        gonder(f, d, 'K001', 'TATIL.EKLEDIM', t(26, '09:00'), girdiler={'tarih': '2026-11-06', 'ad': 'Yanlis'})
        gonder(f, d, 'K001', 'TATIL.KALDIRDIM', t(26, '09:01'), girdiler={'tarih': '2026-11-06'})
        self.assertEqual(kapasite(d, 'K041', '2026-11-02', '2026-11-06'), 45)
        gonder(f, d, 'K001', 'TATIL.KALDIRDIM', t(30, '09:00'), girdiler={'tarih': '2026-10-29'}, bek='DURUM')

    def test_Y73_kodlar(self):
        f = Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '13:00', 4)
        d = f.calistir(t(22, '13:00'))
        gonder(f, d, 'K001', 'KOD.TANIMLADIM', t(22, '13:00'), girdiler={'liste': 'ARIZA', 'kod': 'ARIZA.MAKINE', 'ad': 'Makine', 'aktif': False})
        gonder(f, d, 'K017', 'IS.ARIZA_BILDIRDIM', t(22, '13:20'), 4, {'neden': 'ARIZA.MAKINE'})
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'ARIZADA')
        for aktif, saat in [(True, '14:00'), (False, '14:02')]:
            gonder(f, d, 'K001', 'KOD.TANIMLADIM', t(22, saat), girdiler={'liste': 'PD', 'kod': 'PD.YENI', 'ad': 'Yeni', 'aktif': aktif})
            gonder(f, d, 'K012', 'GOREV.ATADIM', t(22, saat), girdiler={'gorevler': [f.gorev_satiri(nereye='PROJE_DISI', proje=None, etap=None, kategori='PD.YENI')]}, bek='BASARILI' if aktif else 'DURUM')

    def test_Y73_ileri_rol(self):
        f = Duzenek(); d = f.calistir(t(26, '09:00'))
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(26, '09:00'), girdiler={'kisi': 'K023', 'degisenler': {'roller': ['EKIP_LIDERI']}, 'gecerli_baslangic': t(2, '00:00', 11)})
        gonder(f, d, 'K023', 'IS.ATADIM', t(26, '09:01'), 5, {'kisi': 'K017', 'sira': 1}, bek='YETKI')
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(26, '09:02'), girdiler={'kisi': 'K023', 'degisenler': {'roller': ['CALISAN']}, 'gecerli_baslangic': t(20, '00:00')}, bek='DURUM')
        gonder(f, d, 'K023', 'IS.ATADIM', t(2, '09:00', 11), 5, {'kisi': 'K017', 'sira': 1})

    def test_Y73_teslim(self):
        f = Duzenek(); d = f.calistir(t(26, '10:00'))
        gonder(f, d, 'K001', 'TAKVIM.TANIMLADIM', t(26, '10:00'), girdiler=dict(d.varsayilan_takvim, mesai_bitis='17:00'))
        g, _ = gonder(f, d, 'K012', 'GOREV.ATADIM', t(26, '10:01'), girdiler={'gorevler': [f.gorev_satiri(teslim_tarihi='2026-10-28')]})
        g += '/1'; gonder(f, d, 'K041', 'GOREV.KABUL_ETTIM', t(26, '11:00'), g)
        self.assertEqual(son_teslim_ani(d.gorevler[g]), an(t(28, '17:00')))
        gonder(f, d, 'K041', 'GOREV.TAMAMLADIM', t(28, '17:30'), g)
        self.assertIn('GEC_TESLIM', gorev_isaretleri(d, g))

    def test_Y73_yonlendirme(self):
        f = Duzenek(); d = f.calistir(t(26, '09:00'))
        gonder(f, d, 'K012', 'AYAR.YONLENDIRDIM', t(26, '09:00'), girdiler={'birim': 'MEK_TASARIM', 'kisiler': ['K012', 'K060']})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(26, '09:01'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-26'}, bek='DURUM')
        gonder(f, d, 'K012', 'AYAR.YONLENDIRDIM', t(26, '09:02'), girdiler={'birim': 'MEK_TASARIM', 'kisiler': ['K012']})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(26, '09:03'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-26'})

    def test_Y73_kurulum(self):
        f, d, i, g = sifirdan()
        self.assertEqual(d.olay_ekle(f.olaylar[0], servis=True)['kod'], 'YETKI')
        f = Duzenek(False); olaylar = kurulum_paketi(f); d = Depo(Saat(t(1, '07:00')))
        olaylar = [e for e in olaylar if e['eylem_kodu'] != 'KISI.EKLEDIM']
        self.assertNotEqual(d.kurulum(olaylar, {}, servis=True)['sonuc'], 'BASARILI'); self.assertFalse(d.olaylar)
