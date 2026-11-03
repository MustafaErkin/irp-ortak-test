"""senaryolar.md: beklenenler değiştirilmeden bağımsız doğrulamalar."""
from .senaryolar_v2 import SenaryolarV2
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo, Saat, an
from irp.gorunumler import *
from irp.is_ import emek
from irp.gorev import son_teslim_ani
from irp.zaman import ay_kapanisi
from irp.demo import Demo, uret
from irp.cihaz import Cihaz
from .ortak import Duzenek, t, is_id, s1, s13, yaz


def dakika(d, kova, kisi='K017', is_=None):
    return sum(((a['bitis'] or d.saat.simdi()) - a['baslangic']).total_seconds() / 60 for a in d.araliklar if a['kisi'] == kisi and a['kova'] == kova and (is_ is None or a['is'] == is_))


def dilimler(d, kova, kisi='K017', is_=None):
    return [(a['baslangic'].strftime('%H:%M'), a['bitis'].strftime('%H:%M') if a['bitis'] else None) for a in d.araliklar if a['kisi'] == kisi and a['kova'] == kova and (is_ is None or a['is'] == is_)]


def bildirim(d, kural): return [b for b in d.bildirimler.values() if b['kural'] == kural]


class Senaryolar(unittest.TestCase):
    def test_S1(self):
        d = s1().calistir(t(22, '11:45'))
        self.assertEqual(emek(d, is_id(1)), 186)
        self.assertEqual(dilimler(d, 'CALISMA', is_=is_id(1)), [('08:05', '10:00'), ('10:17', '10:40'), ('10:52', '11:40')])
        self.assertEqual(dilimler(d, 'TANIMSIZ'), [('08:00', '08:05'), ('10:15', '10:17'), ('11:40', '11:42')])
        self.assertEqual(dilimler(d, 'MOLA'), [('10:40', '10:52')])
        self.assertEqual(dilimler(d, 'SABIT_MOLA'), [('10:00', '10:15')])
        self.assertEqual(dilimler(d, 'CALISMA', is_=is_id(2)), [('11:42', None)])
        self.assertEqual(emek(d, is_id(2)), 3)
        self.assertEqual(d.isler[is_id(1)]['durum'], 'BITTI')
        self.assertEqual(d.isler[is_id(1)]['bitis_ani'], an(t(22, '11:40')))
        self.assertEqual(d.isler[is_id(2)]['durum'], 'CALISILIYOR')
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISIYOR')
        self.assertEqual(d.kisi_durumu['K017']['acik_is'], is_id(2))
        self.assertFalse(d.bildirimler); self.assertFalse(d.supheliler)

    def test_S2(self):
        f = Duzenek(); f.ata(4)
        for kod, saat in [('MESAI.GIRDIM', '07:55'), ('BASLADIM', '08:00'), ('DEVAM_ETTIM', '10:15'), ('DEVAM_ETTIM', '12:30')]: f.is_olay(kod, saat, None if kod.startswith('MESAI') else 4)
        f.is_olay('ARIZA_BILDIRDIM', '13:20', 4, neden='ARIZA.MAKINE', not_='Kaynak makinesi akim vermiyor')
        f.is_olay('DEVAM_ONAYLADIM', '13:45', 4, kisi='K009')
        ara = f.calistir(t(22, '13:45'))
        self.assertEqual(ara.kisi_durumu['K017']['durum'], 'ARIZADA')
        self.assertTrue(ara.kisi_durumu['K017']['devam_izni'])
        f.is_olay('DEVAM_ETTIM', '13:46', 4)
        d = f.calistir(t(22, '13:50'))
        self.assertEqual(dakika(d, 'BEKLEME_ARIZA'), 26)
        self.assertEqual(dilimler(d, 'CALISMA'), [('08:00', '10:00'), ('10:15', '12:00'), ('12:30', '13:20'), ('13:46', None)])
        self.assertEqual(len(bildirim(d, 'R07')), 1)
        self.assertEqual(bildirim(d, 'R07')[0]['alici'], 'K009')
        self.assertFalse(dilimler(d, 'TANIMSIZ'))

    def test_S3(self):
        f = Duzenek()
        for n, k, s in [(4, 'K017', 1), (3, 'K017', 2), (8, 'K023', 1), (7, 'K023', 2)]: f.ata(n, k, s)
        for kod, saat, n, kisi in [('MESAI.GIRDIM', '07:58', None, 'K017'), ('BASLADIM', '08:00', 4, 'K017'), ('DEVAM_ETTIM', '10:15', 4, 'K017'), ('TAMAMLADIM', '11:50', 4, 'K017'), ('BASLADIM', '12:41', 3, 'K017'), ('MESAI.GIRDIM', '07:59', None, 'K023'), ('TAMAMLADIM', '08:10', 8, 'K023'), ('TAMAMLADIM', '12:40', 7, 'K023')]: f.is_olay(kod, saat, n, kisi)
        d = f.calistir(t(22, '12:45'))
        self.assertEqual(dakika(d, 'BEKLEME_ON_IS'), 21)
        self.assertEqual(dilimler(d, 'BEKLEME_ON_IS'), [('11:50', '12:00'), ('12:30', '12:41')])
        self.assertEqual(d.isler[is_id(3)]['durum'], 'CALISILIYOR')
        self.assertEqual(dakika(d, 'TEZGAH', None), 270)
        self.assertEqual(d.kisi_durumu['K023']['durum'], 'CALISMIYOR')
        self.assertEqual(dilimler(d, 'TANIMSIZ', 'K023'), [('08:00', '10:00'), ('10:15', '12:00'), ('12:30', None)])
        self.assertEqual(len(bildirim(d, 'R04')), 1)
        self.assertEqual(bildirim(d, 'R08')[0]['an'], an(t(22, '12:40')))
        ara = f.calistir(t(22, '12:40'))
        self.assertEqual(ara.isler[is_id(3)]['durum'], 'SIRADA')

    def test_S4(self):
        f = Duzenek(); f.ata(1); f.ata(2, sira=2); f.ata(3, sira=3, zaman=t(22, '07:42'))
        d = f.calistir(t(22, '07:45'))
        self.assertEqual(d.listeler['K017'], [is_id(1), is_id(2), is_id(3)])
        self.assertEqual(d.isler[is_id(3)]['durum'], 'ON_IS_BEKLIYOR')
        self.assertEqual(d.isler[is_id(3)]['atayan'], 'K009')
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'MESAI_DISI')
        self.assertFalse(d.araliklar)

    def test_S5(self):
        f = Duzenek(); f.ata(4); f.ata(5, sira=2)
        for kod, saat, n in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 4), ('DEVAM_ETTIM', '10:16', 4)]: f.is_olay(kod, saat, n)
        f.is_olay('SIRALADIM', '10:30', 5, kisi='K009', **{'kisi_hedef': 'K017', 'yeni_sira': 1})
        f.olaylar[-1]['girdiler']['kisi'] = f.olaylar[-1]['girdiler'].pop('kisi_hedef')
        f.is_olay('BASLADIM', '10:33', 5)
        d = f.calistir(t(22, '10:35'))
        self.assertEqual(dilimler(d, 'CALISMA', is_=is_id(4)), [('08:00', '10:00'), ('10:16', '10:30')])
        self.assertEqual(dilimler(d, 'GECIS'), [('10:30', '10:33')])
        self.assertEqual(d.isler[is_id(4)]['durum'], 'YARIM')
        self.assertEqual(d.listeler['K017'], [is_id(5), is_id(4)])

    def test_S6(self):
        f = Duzenek(); f.ata(4); f.ata(6, sira=2); f.ata(2, 'K023')
        for kisi, n in [('K017', 4), ('K023', 2)]:
            for kod, saat in [('MESAI.GIRDIM', '07:58'), ('BASLADIM', '08:00'), ('DEVAM_ETTIM', '10:15'), ('DEVAM_ETTIM', '12:30')]: f.is_olay(kod, saat, None if kod.startswith('MESAI') else n, kisi)
        f.is_olay('DEVRETTIM', '14:00', 4, kisi='K009', kimden='K017', kime='K023', kimden_yeni_is=is_id(6))
        for kod, saat in [('BASLADIM', '14:05'), ('DEVAM_ETTIM', '15:15'), ('TAMAMLADIM', '16:30')]: f.is_olay(kod, saat, 4, 'K023')
        d = f.calistir(t(22, '16:35'))
        self.assertEqual(dakika(d, 'CALISMA', 'K017', is_id(4)), 315)
        self.assertEqual(dakika(d, 'CALISMA', 'K023', is_id(4)), 130)
        self.assertEqual(emek(d, is_id(4)), 445)
        self.assertEqual(dilimler(d, 'GECIS'), [('14:00', '15:00'), ('15:15', None)])
        self.assertEqual(dilimler(d, 'GECIS', 'K023'), [('14:00', '14:05')])
        self.assertEqual(d.isler[is_id(2)]['durum'], 'YARIM')
        self.assertEqual(d.listeler['K017'][0], is_id(6))
        self.assertEqual(d.isler[is_id(4)]['bitis_ani'], an(t(22, '16:30')))

    def test_S7(self):
        f = Duzenek(); f.ata(5)
        for kod, saat, n in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 5), ('DEVAM_ETTIM', '10:15', 5)]: f.is_olay(kod, saat, n)
        yeni = f.olay('K009', 'IS.PLANSIZ_TANIMLADIM', t(22, '11:20'), [{'tur': 'PROJE', 'kimlik': '2509084'}], {'nereye': 'PROJE', 'proje': '2509084', 'is_tanimi': 'Kaynak catlagi tamiri', 'tur': 'SURELI', 'onay_gerekli': False, 'kisi': 'K017', 'sira': 1})
        for kod, saat in [('BASLADIM', '11:22'), ('DEVAM_ETTIM', '12:31'), ('TAMAMLADIM', '12:42')]: f.is_olay(kod, saat, yeni)
        d = f.calistir(t(22, '12:45'))
        self.assertTrue(d.isler[yeni]['plansiz']); self.assertEqual(emek(d, yeni), 49)
        self.assertEqual(d.isler[yeni]['durum'], 'BITTI'); self.assertEqual(d.isler[is_id(5)]['durum'], 'YARIM')
        self.assertEqual(d.listeler['K017'], [is_id(5)])
        self.assertEqual(dilimler(d, 'GECIS'), [('11:20', '11:22')])
        self.assertTrue(all(a['plansiz'] and a['proje'] == '2509084' for a in d.araliklar if a['is'] == yeni))

    def test_S8(self):
        f = Duzenek(); f.ata(9)
        for kod, saat, kisi in [('MESAI.GIRDIM', '07:58', 'K017'), ('BASLADIM', '11:25', 'K017'), ('DEVAM_ETTIM', '12:30', 'K017'), ('TAMAMLADIM', '14:55', 'K017'), ('REDDETTIM', '15:20', 'K009'), ('DEVAM_ETTIM', '15:22', 'K017'), ('TAMAMLADIM', '16:52', 'K017'), ('ONAYLADIM', '16:57', 'K009')]:
            f.is_olay(kod, saat, None if kod.startswith('MESAI') else 9, kisi, **({'not': 'Dikis eksik'} if kod == 'REDDETTIM' else {}))
        d = f.calistir(t(22, '17:00'))
        self.assertEqual(dakika(d, 'CALISMA'), 180); self.assertEqual(dakika(d, 'YENIDEN_ISLEME'), 90)
        self.assertEqual(dakika(d, 'BEKLEME_ONAY'), 15)
        self.assertEqual(dilimler(d, 'BEKLEME_ONAY'), [('14:55', '15:00'), ('15:15', '15:20'), ('16:52', '16:57')])
        self.assertEqual(dilimler(d, 'GECIS'), [('15:20', '15:22')])
        self.assertEqual(len(bildirim(d, 'R05')), 2); self.assertEqual(len(bildirim(d, 'R08')), 1)
        self.assertEqual(d.isler[is_id(9)]['durum'], 'BITTI')

    def test_S9(self):
        f = Duzenek()
        ilk = f.gorev_ata(satirlar=[f.gorev_satiri(ad='Teknik resim ' + str(n + 13), onay_gerekli=n == 0, onaylayan='K012', dosya_gerekli=n == 0, teslim_tarihi='2026-10-22' if n == 0 else '2026-10-23') for n in range(8)])
        ids = [ilk.rsplit('/', 1)[0] + '/' + str(n) for n in range(1, 9)]
        self.assertTrue(all(g['durum'] == 'ATANDI' for g in f.calistir(t(21, '18:00')).gorevler.values()))
        f.gorev_olay('KABUL_ETTIM', t(22, '08:05'), ids)
        self.assertTrue(all(g['durum'] == 'ACIK' for g in f.calistir(t(22, '08:06')).gorevler.values()))
        onay = f.gorev_olay('TAMAMLADIM', t(22, '09:10'), ilk, kanit=2)
        ara = f.calistir(t(22, '09:20'))
        self.assertEqual(ara.gorevler[ilk]['durum'], 'ONAY_BEKLIYOR'); self.assertEqual(ara.gorevler[onay]['durum'], 'ACIK')
        self.assertEqual(ara.gorevler[onay]['zaman_degeri'], 0); self.assertIsNone(ara.gorevler[onay]['teslim_tarihi'])
        self.assertEqual(ara.gorevler[onay]['tur'], 'ONAY'); self.assertEqual(ara.gorevler[onay]['kisi'], 'K012')
        f.gorev_olay('ONAYLADIM', t(22, '09:40'), ilk, 'K012')
        d = f.calistir(t(22, '10:00'))
        self.assertEqual(d.gorevler[ilk]['is_puani'], 2); self.assertEqual(d.gorevler[onay]['durum'], 'BITTI')
        self.assertEqual(d.gorevler[ilk]['ilk_teslim_ani'], t(22, '09:10'))
        self.assertEqual(d.gorevler[ilk]['onay_ani'], t(22, '09:40'))
        self.assertEqual(gorev_payi(d, d.gorevler[ilk], '2026-10-01', '2026-10-31'), 1)

    def test_S10(self):
        f = Duzenek(); g = f.gorev_ata(t(15, '09:00'), teslim_tarihi='2026-10-16', onay_gerekli=True, onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM', t(15, '14:00'), g)
        onay1 = f.gorev_olay('TAMAMLADIM', t(16, '10:00'), g)
        f.gorev_olay('REDDETTIM', t(16, '11:30'), g, 'K012', **{'not': 'Olcu eksik', 'sebep_olan': 'K041', 'revizyon_ver': False})
        ara = f.calistir(t(16, '12:00'))
        self.assertEqual(ara.gorevler[g]['durum'], 'REDDEDILDI'); self.assertEqual(ara.gorevler[onay1]['durum'], 'BITTI')
        onay2 = f.gorev_olay('TAMAMLADIM', t(16, '15:00'), g)
        f.gorev_olay('ONAYLADIM', t(16, '15:20'), g, 'K012')
        d = f.calistir(t(16, '16:00')); p = adil_performans(d, 'K041', '2026-10-01', '2026-10-31')
        self.assertEqual(d.gorevler[g]['is_puani'], 2); self.assertEqual(d.gorevler[onay2]['durum'], 'BITTI')
        self.assertEqual(p['kalite_ret'], 1); self.assertEqual(p['sebep_olunan_gecikme'], 0); self.assertEqual(p['zamaninda'], 1)

    def test_S10b(self):
        f, g, r, o = revizyon_ornegi(False)
        ara = f.calistir(t(16, '12:00'))
        self.assertEqual(ara.gorevler[g]['durum'], 'REVIZYONDA'); self.assertEqual(ara.gorevler[r]['durum'], 'ATANDI')
        self.assertEqual(ara.gorevler[r]['zorluk'], 2); self.assertTrue(ara.gorevler[r]['onay_gerekli'])
        d = f.calistir(t(19, '17:00'))
        self.assertEqual(d.gorevler[g]['durum'], 'BITTI'); self.assertEqual(d.gorevler[r]['durum'], 'BITTI')
        self.assertEqual(d.gorevler[g]['is_puani'], 2); self.assertEqual(d.gorevler[r]['is_puani'], 4)
        self.assertEqual(d.gorevler[r]['kisi'], 'K044'); self.assertEqual(d.gorevler[r]['onaylayan'], 'K012')
        self.assertEqual(adil_performans(d, 'K041', '2026-10-01', '2026-10-31')['sebep_olunan_gecikme'], 2)
        self.assertEqual(maas_dagilimi(d, 'K044', '2026-10-01')['paylar']['revizyon:2509084'], 2)

    def test_S11(self):
        f = Duzenek(); g = f.gorev_ata(proje='2509091', teslim_tarihi='2026-11-05', zaman_degeri=60, zorluk=5)
        f.gorev_olay('KABUL_ETTIM', t(22, '08:05'), g)
        d = f.calistir(t(22, '09:00'))
        self.assertEqual(len(is_gunleri(d, '2026-10-22', '2026-11-05')), 10)
        self.assertEqual(maas_dagilimi(d, 'K041', '2026-10-01')['paylar']['2509091'], 36)
        self.assertEqual(maas_dagilimi(d, 'K041', '2026-11-01')['paylar']['2509091'], 24)
        self.assertIsNone(d.gorevler[g]['is_puani'])

    def test_S12(self):
        f = Duzenek()
        for n, saat, kabul, teslim, proje, kat in [(1, 81, 1, '2026-10-30', '2509084', None), (2, 12, 5, '2026-10-09', '2509091', None), (3, 60, 22, '2026-11-05', '2509091', None), (4, 16, 12, '2026-10-16', None, 'PD.IDARI_MALI')]:
            g = f.gorev_ata(t(kabul, '08:00'), zaman_degeri=saat, teslim_tarihi=teslim, proje=proje, kategori=kat, nereye='PROJE' if proje else 'PROJE_DISI')
            f.gorev_olay('KABUL_ETTIM', t(kabul, '09:00'), g)
        d = f.calistir(t(30, '18:00')); m = maas_dagilimi(d, 'K041', '2026-10-01')
        self.assertEqual(m['paylar'], {'2509084': 81, '2509091': 48, 'PD.IDARI_MALI': 16})
        self.assertEqual(m['payda'], 180)
        self.assertEqual(m['tutarlar'], {'2509084': Decimal('9000.00'), '2509091': Decimal('5333.33'), 'PD.IDARI_MALI': Decimal('1777.78')})
        self.assertEqual(m['dagitilamayan'], Decimal('3888.89'))
        self.assertEqual(sum(m['tutarlar'].values()) + m['dagitilamayan'], m['maas'])

    def test_S13(self):
        f, ids = s13(); d = f.calistir(t(26, '12:00')); g = etap_gostergesi(d, f.etap['E-TAS'])
        self.assertEqual(g['planli_toplam'], 153); self.assertEqual(g['tamamlanan'], 78)
        self.assertEqual(g['dort_kategori'], {'tamamlandi': 78, 'onay_bekliyor': 16, 'revizyonda': 0, 'geride': 11})
        self.assertEqual(g['yuzde'], 19.5)
        self.assertEqual(d.gorevler[ids['h']]['durum'], 'ON_IS_BEKLIYOR')
        self.assertIn('GEC_TESLIM', gorev_isaretleri(d, ids['c']))
        self.assertNotIn('GECIKTI', gorev_isaretleri(d, ids['c']))
        self.assertIn('GECIKTI', gorev_isaretleri(d, ids['f'])); self.assertIn('GECIKTI', gorev_isaretleri(d, ids['g']))
        self.assertEqual(son_teslim_ani(d.gorevler[ids['g']]), an(t(26, '10:00')))
        self.assertEqual((an(d.gorevler[ids['c']]['ilk_teslim_ani']).date() - son_teslim_ani(d.gorevler[ids['c']]).date()).days, 3)
        self.assertEqual(sorted(x['zaman_degeri'] for x in d.gorevler.values() if x['tur'] == 'ONAY'), [0, 1, 1, 2, 4])
        self.assertGreater(g['butce_tuketimi'], g['yuzde'])

    def test_S14(self):
        f, ids = s13(); f.gorev_olay('DEGISTIRDIM', t(23, '11:00'), ids['i'], 'K012', degisenler={'teslim_tarihi': '2026-11-06'}, gerekce='Musteri I/O degisikligi')
        d = f.calistir(t(26, '12:00'))
        self.assertEqual(son_teslim_ani(d.gorevler[ids['i']]), an(t(6, '18:00', 11)))
        self.assertAlmostEqual(gorev_payi(d, d.gorevler[ids['i']], '2026-10-01', '2026-10-31'), 24 * 21 / 26)
        self.assertIn('2026-10-30', d._olaylar[ids['i'].rsplit('/', 1)[0]])

    def test_S14b(self):
        f, ids = s13(); f.gorev_olay('DEGISTIRDIM', t(23, '11:00'), ids['i'], 'K012', degisenler={'teslim_tarihi': '2026-11-06'})
        d = f.calistir(t(1, '00:30', 11)); ay_kapanisi(d, '2026-10-01')
        once = deepcopy(maas_dagilimi(d, 'K044', '2026-10-01'))
        f.gorev_olay('DEGISTIRDIM', t(3, '10:00', 11), ids['i'], 'K012', degisenler={'teslim_tarihi': '2026-11-13'})
        d.ilerlet(t(3, '11:00', 11)); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(maas_dagilimi(d, 'K044', '2026-10-01'), once)
        # Karar 50: gorev duzeyindeki kapanmis pay da sabittir.
        self.assertAlmostEqual(gorev_payi(d, d.gorevler[ids['i']], '2026-10-01', '2026-10-31'), 24 * 21 / 26)
        d.yeniden_kur(); self.assertEqual(maas_dagilimi(d, 'K044', '2026-10-01'), once)

    def test_S15(self):
        f = Duzenek(); g = f.gorev_ata(t(26, '09:00'), veren='K007', kisi='K052', proje=None, nereye='PROJE_DISI', kategori='PD.IDARI_MALI', teslim_tarihi='2026-10-28', zaman_degeri=6, zorluk=3, dosya_gerekli=True)
        f.gorev_olay('KABUL_ETTIM', t(26, '10:00'), g, 'K052'); f.gorev_olay('TAMAMLADIM', t(28, '10:00'), g, 'K052', kanit=1)
        d = f.calistir(t(28, '11:00'))
        self.assertEqual(d.gorevler[g]['durum'], 'BITTI'); self.assertEqual(d.gorevler[g]['is_puani'], 18)
        self.assertEqual(maas_dagilimi(d, 'K052', '2026-10-01')['paylar']['PD.IDARI_MALI'], 6)

    def test_S16(self):
        f = Duzenek()
        satirlar = [f.gorev_satiri(ad='Montaj', teslim_tarihi='2026-11-13', zaman_degeri=8)] + [f.gorev_satiri(ad='Teknik ' + str(n), teslim_tarihi='2026-11-13') for n in range(12)] + [f.gorev_satiri(ad='BOM', kisi='K044', teslim_tarihi='2026-11-23', zaman_degeri=3, on_kosul=[{'satir': 1}], uyarilar=['Etap bitisi asiliyor']), f.gorev_satiri(kisi='K060', zaman_degeri=4, teslim_tarihi='2026-11-12')]
        g = f.gorev_ata(t(26, '09:14'), satirlar=satirlar); bom = g.rsplit('/', 1)[0] + '/14'
        f.gorev_olay('KABUL_ETTIM', t(26, '10:00'), bom, 'K044')
        d = f.calistir(t(26, '10:30'))
        self.assertEqual(len(d.gorevler), 15); self.assertEqual(d.gorevler[bom]['durum'], 'ON_IS_BEKLIYOR')
        self.assertEqual(d.gorevler[bom]['on_kosul'], [g]); self.assertTrue(d.gorevler[bom]['uyarilar'])
        self.assertTrue(all(x['durum'] == 'ATANDI' for k, x in d.gorevler.items() if k != bom))
        self.assertAlmostEqual(yuk(d, 'K041', '2026-11-09', '2026-11-13'), 20 * 5 / 14)

    def test_S17(self):
        f = Duzenek(); g = f.gorev_ata(t(23, '08:00'), satirlar=[f.gorev_satiri(ad=ad, onay_gerekli=True, onaylayan='K012') for ad in ['M', 'R', 'X', 'Y']])
        ids = [g.rsplit('/', 1)[0] + '/' + str(n) for n in range(1, 5)]
        f.gorev_olay('KABUL_ETTIM', t(23, '09:00'), ids)
        for n, kimlik in enumerate(ids): f.gorev_olay('TAMAMLADIM', t(23, '11:{:02d}'.format(n)), kimlik)
        f.gorev_olay('ONAYLADIM', t(26, '09:20'), ids, 'K012')
        yeni = f.gorev_ata(t(26, '09:31'), satirlar=[f.gorev_satiri(kisi='K006', zaman_degeri=2, teslim_tarihi='2026-10-30', kaynak=ids[0], on_kosul=[ids[0]]), f.gorev_satiri(zaman_degeri=3, teslim_tarihi='2026-10-30', kaynak=ids[1])])
        f.gorev_olay('KABUL_ETTIM', t(26, '10:00'), yeni, 'K006')
        d = f.calistir(t(26, '10:30'))
        self.assertTrue(all(d.gorevler[x]['durum'] == 'BITTI' for x in ids))
        self.assertTrue(all(x['durum'] == 'BITTI' for x in d.gorevler.values() if x['tur'] == 'ONAY'))
        self.assertEqual(d.gorevler[yeni]['durum'], 'ACIK'); self.assertEqual(d.gorevler[yeni]['kaynak'], ids[0])
        self.assertEqual(kapasite(d, 'K006', '2026-10-26', '2026-10-30'), 36)

    def test_S18(self):
        f = Duzenek(); not_ = f.olay('K045', 'NOT.YAZDIM', t(26, '11:05'), [{'tur': 'PARCA', 'kimlik': '2509084_07_04-14'}], {'metin': 'Tedarikci delik olcusunu soruyor', 'etiketler': ['MEK_TASARIM']}, kanit=[{'dosya_kimligi': 'F-not/1', 'parmak_izi': 'abc'}])
        f.gorev_olay('KABUL_ETTIM', t(26, '11:20'), not_ + '/1', 'K012')
        yeni = f.gorev_ata(t(26, '11:40'), ad='Delik toleransini netlestir', teslim_tarihi='2026-10-27', sorun_kaynakli=True, kaynak=not_)
        d = f.calistir(t(26, '12:00'))
        self.assertEqual(len(d.notlar), 1); self.assertEqual(d.notlar[not_]['neyin_ustunde'][0]['kimlik'], '2509084_07_04-14')
        self.assertEqual(d.gorevler[not_ + '/1']['durum'], 'BITTI'); self.assertEqual(d.gorevler[not_ + '/1']['zaman_degeri'], 0)
        self.assertEqual(d.gorevler[yeni]['durum'], 'ATANDI'); self.assertTrue(d.gorevler[yeni]['sorun_kaynakli'])

    def test_D1(self):
        f = s1(); d = f.calistir(t(22, '11:45'))
        e = next(e for e in f.olaylar if e['eylem_kodu'] == 'IS.BASLADIM')
        once = d.son_hal(); sayi = len(d.olaylar)
        self.assertTrue(d.olay_ekle(e,servis=True)['tekrar']); self.assertEqual(len(d.olaylar), sayi)
        degisik = deepcopy(e); degisik['girdiler']['not'] = 'Farkli'
        self.assertEqual(d.olay_ekle(degisik,servis=True)['sonuc'], 'CAKISMA')
        self.assertEqual(d.son_hal(), once); self.assertEqual(len(d.isleme_hatalari), 1)

    def test_D2(self):
        f, gec = habersiz_ornegi()
        temel = [e for e in f.olaylar if e['olay_kimligi'] not in gec]
        d = f.calistir(t(22, '13:10'), sorted(temel, key=lambda e: (e['oldugu_an'], e['olay_kimligi'])) + [e for e in f.olaylar if e['olay_kimligi'] in gec])
        self.assertEqual(emek(d, is_id(4)), 153)
        self.assertEqual(dakika(d, 'MOLA'), 12)
        self.assertEqual(dakika(d, 'SABIT_MOLA'), 45)
        self.assertEqual(dakika(d, 'GECIS'), 96)
        self.assertEqual(d.isler[is_id(4)]['durum'], 'BITTI')
        self.assertEqual(len(d.supheliler), 1)
        self.assertEqual(sum(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'].values()), 310)
        diger = f.calistir(t(22, '13:10'))
        self.assertEqual(d.son_hal(), diger.son_hal())

    def test_D2b(self):
        f, _ = habersiz_ornegi()
        f.olay('K009', 'IS.SURE_EKLEDIM', t(22, '14:00'), 4, {'baslangic': t(22, '11:00'), 'bitis': t(22, '11:40'), 'aciklama': 'Telefon kapaliydi, sozlu bildirildi', 'is_bitti': False}, adina='K017', giris_sekli='ELLE')
        d = f.calistir(t(22, '14:05'))
        self.assertEqual(emek(d, is_id(4)), 193)
        self.assertEqual(dilimler(d, 'GECIS'), [('11:40', '12:00'), ('12:30', '13:06')])
        elle = elle_sureler(d, 'IMALAT', '2026-10-22', '2026-10-22')
        self.assertEqual(len(elle), 1); self.assertEqual(elle[0]['yazan'], 'K009'); self.assertTrue(elle[0]['aciklama'])

    def test_D3(self):
        f = Duzenek(); f.ata(4)
        f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 4)
        once = f.calistir(t(22, '12:15'))
        self.assertEqual(once.kisi_durumu['K017']['durum'], 'SABIT_MOLADA')
        self.assertEqual(once.kisi_durumu['K017']['son_olay_ani'], an(t(22, '08:00')))
        f.is_olay('DEVAM_ETTIM', '10:15', 4); ariza = f.is_olay('ARIZA_BILDIRDIM', '10:30', 4, neden='ARIZA.MALZEME_YOK')
        once.ilerlet(t(22, '13:00'))
        for e in f.olaylar[-2:]: once.olay_ekle(e)
        once.ilerlet(t(22, '13:10'))
        self.assertEqual(once.kisi_durumu['K017']['durum'], 'ARIZADA')
        self.assertEqual(dilimler(once, 'BEKLEME_ARIZA'), [('10:30', '12:00'), ('12:30', None)])
        self.assertEqual(bildirim(once, 'R07')[0]['an'], an(t(22, '10:30')))
        self.assertEqual(once.olaylar[ariza]['bulut_ulasma_ani'], t(22, '13:00'))
        self.assertEqual(once.kisi_durumu['K017']['son_olay_ani'], an(t(22, '10:30')))

    def test_D4(self):
        f = Duzenek(); f.ata(4)
        for kod, saat in [('MESAI.GIRDIM', '07:58'), ('BASLADIM', '08:00'), ('DEVAM_ETTIM', '10:15'), ('DEVAM_ETTIM', '12:30'), ('DEVAM_ETTIM', '15:15')]: f.is_olay(kod, saat, None if kod.startswith('MESAI') else 4)
        ara = f.calistir(t(22, '18:01'))
        self.assertEqual(emek(ara, is_id(4)), 540); self.assertEqual(ara.isler[is_id(4)]['durum'], 'YARIM')
        self.assertEqual(ara.kisi_durumu['K017']['durum'], 'MESAI_DISI')
        self.assertTrue(ara.araliklar[-1]['sistem_kapatti'])
        cihaz = Cihaz('K017', 'T', Saat(t(23, '07:55')))
        self.assertEqual(cihaz.ekran_hali({'durum': 'CALISIYOR', 'son_hesap_ani': t(22, '17:00')})['son_hal']['durum'], 'MESAI_DISI')
        f.is_olay('MESAI.GIRDIM', '07:55', gun=23); f.is_olay('BASLADIM', '08:02', 4, gun=23)
        d = f.calistir(t(23, '08:10'))
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-23')['kovalar'], {'TANIMSIZ': 2, 'CALISMA': 8})
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar']['CALISMA'], 540)

    def test_Y1(self):
        f, g, r, o = revizyon_ornegi()
        ara = f.calistir(t(3, '12:00', 11))
        self.assertEqual(ara.gorevler[g]['durum'], 'REVIZYONDA'); self.assertEqual(ara.gorevler[o]['durum'], 'BITTI')
        d = f.calistir(t(4, '17:00', 11))
        self.assertEqual(d.gorevler[g]['durum'], 'BITTI'); self.assertEqual(d.gorevler[r]['durum'], 'BITTI')
        self.assertEqual(d.gorevler[g]['is_puani'], 2); self.assertIsNone(d.gorevler[r]['is_puani'])
        self.assertLessEqual(an(d.gorevler[r]['ilk_teslim_ani']), son_teslim_ani(d.gorevler[r]))
        p = adil_performans(d, 'K041', '2026-10-01', '2026-11-30')
        self.assertEqual(p['kalite_ret'], 1); self.assertEqual(p['sebep_olunan_gecikme'], 2); self.assertEqual(p['zamaninda'], 1)
        self.assertEqual(maas_dagilimi(d, 'K041', '2026-10-01')['paylar']['2509084'], 1)
        self.assertEqual(maas_dagilimi(d, 'K041', '2026-11-01')['paylar']['revizyon:2509084'], 2)

    def test_Y2(self):
        f = Duzenek(); g = f.gorev_ata(zaman_degeri=60, zorluk=5, teslim_tarihi='2026-11-05', onay_gerekli=True, onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM', t(22, '08:05'), g)
        o1 = f.gorev_olay('TAMAMLADIM', t(4, '10:00', 11), g)
        f.gorev_olay('ONAYLADIM', t(4, '15:00', 11), g, 'K012')
        # Karar 46 üstün: Y2'nin yalnız gün veren eski girdisi olay anına açıldı (E17).
        f.olay('K001', 'AYAR.ONAY_ORANI', t(5, '09:00', 11), girdiler={'deger': .2})
        g2 = f.gorev_ata(t(5, '10:00', 11), kisi='K044', zaman_degeri=60, onay_gerekli=True, onaylayan='K012', teslim_tarihi='2026-11-06')
        f.gorev_olay('KABUL_ETTIM', t(5, '10:01', 11), g2, 'K044')
        o2 = f.gorev_olay('TAMAMLADIM', t(6, '10:00', 11), g2, 'K044')
        d = f.calistir(t(6, '11:00', 11))
        self.assertEqual(d.gorevler[o1]['zaman_degeri'], 6); self.assertEqual(d.gorevler[o2]['zaman_degeri'], 12)
        self.assertEqual(gorev_payi(d, d.gorevler[o1], '2026-11-04', '2026-11-04'), 6)
        d.yeniden_kur(); self.assertEqual(d.gorevler[o1]['zaman_degeri'], 6)

    def test_Y3(self):
        f = Duzenek(); f.ata(1); f.ata(2, sira=2)
        f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '09:00', 1); f.is_olay('TAMAMLADIM', '10:16', 1)
        d = f.calistir(t(22, '10:20'))
        self.assertEqual(emek(d, is_id(1)), 60); self.assertEqual(dilimler(d, 'SABIT_MOLA'), [('10:00', '10:15')])
        self.assertEqual(dilimler(d, 'TANIMSIZ'), [('08:00', '09:00'), ('10:15', None)])
        self.assertEqual(d.listeler['K017'][0], is_id(2)); self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')

    def test_Y4(self):
        f, ids = s13(); atolye = s1()
        f.olaylar += [e for e in atolye.olaylar if e['eylem_kodu'] in ('IS.ATADIM', 'IS.BASLADIM', 'IS.DEVAM_ETTIM', 'IS.MOLA_VERDIM', 'IS.TAMAMLADIM', 'MESAI.GIRDIM') and (not e['neyin_ustunde'] or e['neyin_ustunde'][0]['kimlik'] != is_id(2))]
        d = f.calistir(t(26, '12:00'))
        self.assertEqual(etap_gostergesi(d, f.etap['E-TAS'])['yuzde'], 19.5)
        self.assertEqual(etap_gostergesi(d, f.etap['E-SAT'])['yuzde'], 'Hesaplanamaz')
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['yuzde'], .25)
        self.assertAlmostEqual(proje_gostergesi(d, '2509084')['yuzde'], (78 + 3) / 1600 * 100)

    def test_Y5(self):
        f = demo_ornegi()
        olaylar = uret([f.olaylar], 42)
        self.assertEqual(olaylar, uret([f.olaylar], 42))
        d = Depo(Saat(t(1, '00:00'), gercek=t(26, '12:00'), demo=True)); oynatici = Demo(d, olaylar, t(1, '00:00'))
        oynatici.oynat(t(22, '10:05'))
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'SABIT_MOLADA')
        self.assertEqual(d.saat.saat_kaydirma, an(t(22, '10:05')) - an(t(26, '12:00')))
        oynatici.oynat(t(22, '12:45')); once = d.son_hal()
        oynatici.demo_sifirla(); oynatici.oynat(t(22, '12:45'))
        self.assertEqual(d.son_hal(), once)
        kotu = deepcopy(olaylar[-1]); kotu['olay_kimligi'] = 'K017-2610229998-T'
        self.assertEqual(d.olay_ekle(kotu, oturum=kotu['kim'])['sonuc'], 'REDDEDILDI')
        with self.assertRaises(PermissionError): d.olay_koru('TRUNCATE')

    def test_Y6(self):
        f = s1()
        f.olay('K009', 'IS.SURE_EKLEDIM', t(22, '14:00'), 4, {'baslangic': t(22, '08:00'), 'bitis': t(22, '11:42'), 'aciklama': 'Eksik kayit', 'is_bitti': False}, adina='K017', giris_sekli='ELLE')
        d = f.calistir(t(22, '14:05'))
        self.assertEqual(dakika(d, 'MOLA'), 12); self.assertEqual(emek(d, is_id(4)), 9)
        self.assertEqual(dakika(d, 'SABIT_MOLA'), 45)
        bos = deepcopy(f.olaylar[-1]); bos['olay_kimligi'] = 'K009-2610229999-M'; bos['girdiler']['aciklama'] = ''
        self.assertEqual(d.olay_ekle(bos)['sonuc'], 'REDDEDILDI')

    def test_Y7(self):
        f, g, r, o = revizyon_ornegi(ikinci_ret=True)
        r2 = f.gorev_olay('REDDETTIM', t(4, '15:30', 11), r, 'K012', **{'not': 'Ikinci hata', 'sebep_olan': 'K041', 'revizyon_ver': True, 'yeni_teslim_tarihi': '2026-11-06', 'zaman_degeri': 2, 'kime': 'K041'}) + '/1'
        f.gorev_olay('KABUL_ETTIM', t(5, '09:00', 11), r2); f.gorev_olay('TAMAMLADIM', t(6, '15:00', 11), r2); f.gorev_olay('ONAYLADIM', t(6, '16:00', 11), r2, 'K012')
        d = f.calistir(t(6, '17:00', 11))
        self.assertTrue(all(d.gorevler[x]['durum'] == 'BITTI' for x in (g, r, r2)))
        self.assertEqual(d.gorevler[g]['is_puani'], 2); self.assertIsNone(d.gorevler[r]['is_puani']); self.assertIsNone(d.gorevler[r2]['is_puani'])
        self.assertEqual(adil_performans(d, 'K041', '2026-11-01', '2026-11-30')['kalite_ret'], 2)
        self.assertEqual(adil_performans(d, 'K041', '2026-11-01', '2026-11-30')['sebep_olunan_gecikme'], 4)


def revizyon_ornegi(ayni=True, ikinci_ret=False):
    f = Duzenek(); g = f.gorev_ata(t(26, '09:00') if ayni else t(15, '09:00'), teslim_tarihi='2026-10-30' if ayni else '2026-10-16', onay_gerekli=True, onaylayan='K012')
    f.gorev_olay('KABUL_ETTIM', t(26, '09:30') if ayni else t(15, '14:00'), g)
    o = f.gorev_olay('TAMAMLADIM', t(28, '10:00') if ayni else t(16, '10:00'), g)
    r = f.gorev_olay('REDDETTIM', t(2, '10:00', 11) if ayni else t(16, '11:30'), g, 'K012', **{'not': 'Olcu eksik', 'sebep_olan': 'K041', 'revizyon_ver': True, 'yeni_teslim_tarihi': '2026-11-04' if ayni else '2026-10-19', 'zaman_degeri': 2, 'kime': 'K041' if ayni else 'K044'}) + '/1'
    f.gorev_olay('KABUL_ETTIM', t(3, '09:00', 11) if ayni else t(19, '09:00'), r, 'K041' if ayni else 'K044')
    f.gorev_olay('TAMAMLADIM', t(4, '15:00', 11) if ayni else t(19, '16:00'), r, 'K041' if ayni else 'K044')
    if not ikinci_ret: f.gorev_olay('ONAYLADIM', t(4, '16:00', 11) if ayni else t(19, '16:30'), r, 'K012')
    return f, g, r, o


def habersiz_ornegi():
    f = Duzenek(); f.ata(4); f.ata(5, sira=2)
    f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 4)
    gec = []
    for kod, saat in [('DEVAM_ETTIM', '10:15'), ('MOLA_VERDIM', '10:40'), ('DEVAM_ETTIM', '10:52'), ('TAMAMLADIM', '11:40')]:
        gec.append(f.is_olay(kod, saat, 4)); f.olaylar[-1]['bildigi_son_hal_ani'] = t(22, '09:00')
    f.olay('K009', 'IS.SIRALADIM', t(22, '11:00'), 5, {'kisi': 'K017', 'yeni_sira': 1})
    f.is_olay('BASLADIM', '13:06', 5)
    return f, gec


def demo_ornegi():
    # S1, S3, S8 aynı kişi ve aynı gün için birbirini dışlar (B17).
    # S1 22 Ekim; S3 23 Ekim; S8 26 Ekim: her biri kendi akışını korur.
    f = s1()
    for n, kisi, sira in [(4, 'K017', 1), (3, 'K017', 2), (8, 'K023', 1), (7, 'K023', 2)]: f.ata(n, kisi, sira, t(22, '18:{:02d}'.format(sira)))
    for kod, saat, n, kisi in [('MESAI.GIRDIM', '07:58', None, 'K017'), ('BASLADIM', '08:00', 4, 'K017'), ('DEVAM_ETTIM', '10:15', 4, 'K017'), ('TAMAMLADIM', '11:50', 4, 'K017'), ('BASLADIM', '12:41', 3, 'K017'), ('MESAI.GIRDIM', '07:59', None, 'K023'), ('TAMAMLADIM', '08:10', 8, 'K023'), ('TAMAMLADIM', '12:40', 7, 'K023')]: f.is_olay(kod, saat, n, kisi, gun=23)
    f.ata(9, zaman=t(23, '18:05'))
    for kod, saat, kisi in [('MESAI.GIRDIM', '07:58', 'K017'), ('BASLADIM', '11:25', 'K017'), ('DEVAM_ETTIM', '12:30', 'K017'), ('TAMAMLADIM', '14:55', 'K017'), ('REDDETTIM', '15:20', 'K009'), ('DEVAM_ETTIM', '15:22', 'K017'), ('TAMAMLADIM', '16:52', 'K017'), ('ONAYLADIM', '16:57', 'K009')]: f.is_olay(kod, saat, None if kod.startswith('MESAI') else 9, kisi, gun=26, **({'not': 'Dikis eksik'} if kod == 'REDDETTIM' else {}))
    return f
