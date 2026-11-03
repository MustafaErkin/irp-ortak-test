"""I1–I33 ve ek değişmezler; sabit tohumlu geçerli olay üretimi."""
from .degismezler_v2 import DegismezlerV2
import itertools
import random
import unittest
from copy import deepcopy
from datetime import timedelta
from irp import Depo, Saat, an
from irp.olay import kodla
from irp.kisi_gunu import kapi, bos_hal
from irp.cihaz import Cihaz
from irp.demo import Demo
from irp.gorunumler import *
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from .ortak import Duzenek, t, is_id, s1, s13
from .test_senaryolar import revizyon_ornegi, demo_ornegi

TOHUMLAR = [0, 1, 7, 42, 73, 211, 2026, 261026]


def gecerli_dizi(tohum):
    rng = random.Random(tohum); f = Duzenek(); f.ata(4); f.ata(5, sira=2)
    f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:0' + str(rng.randrange(5)), 4)
    f.is_olay('MOLA_VERDIM', '09:{:02d}'.format(rng.randrange(0, 20)), 4)
    f.is_olay('DEVAM_ETTIM', '09:{:02d}'.format(rng.randrange(25, 45)), 4)
    f.is_olay('DEVAM_ETTIM', '10:{:02d}'.format(rng.randrange(15, 25)), 4)
    f.is_olay('DEVAM_ETTIM', '12:{:02d}'.format(rng.randrange(30, 40)), 4)
    f.is_olay('DEVAM_ETTIM', '15:{:02d}'.format(rng.randrange(15, 25)), 4)
    f.is_olay('TAMAMLADIM', '16:{:02d}'.format(rng.randrange(0, 20)), 4)
    f.is_olay('BASLADIM', '16:30', 5)
    f.is_olay('MESAI.CIKTIM', '17:{:02d}'.format(rng.randrange(30, 60)))
    return f


def gun_degismezleri(d):
    """Simülasyonda da aynı bağımsız aralık muhasebesi kullanılır."""
    hatalar = []
    gruplar = defaultdict(list)
    for a in d.araliklar:
        if a['kisi']: gruplar[(a['kisi'], a['gun'])].append(a)
    for (kisi, tarih), araliklar in gruplar.items():
        araliklar.sort(key=lambda a: a['baslangic'])
        for n, a in enumerate(araliklar):
            son = a['bitis'] or d.saat.simdi()
            if n and (araliklar[n-1]['bitis'] or d.saat.simdi()) > a['baslangic']: hatalar.append(('I1', kisi, tarih))
            if not gun_ani(tarih, '08:00') <= a['baslangic'] < son <= min(gun_ani(tarih, '18:00'), d.saat.simdi()): hatalar.append(('I3', kisi, tarih))
            if a['kova'] in ('CALISMA', 'YENIDEN_ISLEME') and not a['is']: hatalar.append(('I5', kisi, tarih))
            if a['kova'] in ('MOLA', 'GECIS', 'TANIMSIZ', 'SABIT_MOLA') and a['is']: hatalar.append(('I5', kisi, tarih))
        if sum(a['bitis'] is None for a in araliklar) > 1: hatalar.append(('I6', kisi, tarih))
        if tarih != d.saat.simdi().date() and any(a['bitis'] is None for a in araliklar): hatalar.append(('I6', kisi, tarih))
    return hatalar


class Degismezler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uretimler = [gecerli_dizi(s) for s in TOHUMLAR]
        cls.depolar = [f.calistir(t(22, '18:01')) for f in cls.uretimler]
        cls.fg, cls.ids = s13(); cls.gd = cls.fg.calistir(t(26, '12:00'))

    def test_I1(self):
        for d in self.depolar: self.assertFalse([h for h in gun_degismezleri(d) if h[0] == 'I1'])

    def test_I2(self):
        for f, d in zip(self.uretimler, self.depolar):
            cikis = next(an(e['oldugu_an']) for e in f.olaylar if e['eylem_kodu'] == 'MESAI.CIKTIM')
            self.assertEqual(sum(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'].values()), (cikis - an(t(22, '08:00'))).total_seconds() / 60)

    def test_I3(self):
        for d in self.depolar: self.assertFalse([h for h in gun_degismezleri(d) if h[0] == 'I3'])

    def test_I4(self):
        for d in self.depolar:
            molalar = [(a['baslangic'], a['bitis']) for a in d.araliklar if a['kova'] == 'SABIT_MOLA']
            self.assertEqual(molalar, [(an(t(22, '10:00')), an(t(22, '10:15'))), (an(t(22, '12:00')), an(t(22, '12:30'))), (an(t(22, '15:00')), an(t(22, '15:15')))])

    def test_I5(self):
        for d in self.depolar: self.assertFalse([h for h in gun_degismezleri(d) if h[0] == 'I5'])

    def test_I6(self):
        for d in self.depolar + [s1().calistir(t(22, '11:45'))]: self.assertFalse([h for h in gun_degismezleri(d) if h[0] == 'I6'])

    def test_I7(self):
        f = s1(); kovalar = {'CALISIYOR': {'CALISMA', 'YENIDEN_ISLEME'}, 'MOLADA': {'MOLA'}, 'SABIT_MOLADA': {'SABIT_MOLA'}, 'DEVAM_BEKLIYOR': {'TANIMSIZ'}, 'CALISMIYOR': {'TANIMSIZ', 'GECIS', 'BEKLEME_ON_IS'}}
        for saat in ['08:03', '09:00', '10:05', '10:16', '10:45', '11:45']:
            d = f.calistir(t(22, saat)); h = d.kisi_durumu['K017']
            self.assertIn(h['kova'], kovalar[h['durum']])

    def test_I8(self):
        for d in self.depolar:
            liste = [i for l in d.listeler.values() for i in l]
            self.assertEqual(len(liste), len(set(liste)))
            self.assertTrue(all(d.isler[i]['durum'] != 'BITTI' for i in liste))

    def test_I9(self):
        f = Duzenek(); f.ata(3)
        d = f.calistir(t(22, '09:00'))
        for liste in d.listeler.values():
            for kimlik in liste:
                i = d.isler[kimlik]
                self.assertEqual(i['durum'] == 'ON_IS_BEKLIYOR', any(d.isler[x]['durum'] != 'BITTI' for x in i['on_isler']))

    def test_I10(self):
        oklar = {('HAVUZDA', 'SIRADA'), ('HAVUZDA', 'ON_IS_BEKLIYOR'), ('ON_IS_BEKLIYOR', 'SIRADA'), ('SIRADA', 'CALISILIYOR'), ('YARIM', 'CALISILIYOR'), ('CALISILIYOR', 'YARIM'), ('CALISILIYOR', 'BITTI'), ('CALISILIYOR', 'ONAY_BEKLIYOR'), ('SIRADA', 'BITTI'), ('SIRADA', 'ONAY_BEKLIYOR'), ('ONAY_BEKLIYOR', 'BITTI'), ('ONAY_BEKLIYOR', 'REDDEDILDI'), ('REDDEDILDI', 'CALISILIYOR')}
        f = self.uretimler[0]; once = {}
        for e in sorted(f.olaylar, key=lambda e: (e['oldugu_an'], e['olay_kimligi'])):
            if an(e['oldugu_an']) < an(t(20)): continue
            d = f.calistir(e['oldugu_an'])
            for k, i in d.isler.items():
                if k in once and once[k] != i['durum']: self.assertIn((once[k], i['durum']), oklar)
                once[k] = i['durum']

    def test_I11(self):
        for d in self.depolar:
            toplam = sum(v for k, v in kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'].items() if k in ('CALISMA', 'YENIDEN_ISLEME'))
            self.assertEqual(sum(emek(d, i) for i in d.isler), toplam)

    def test_I12(self):
        f, _, _, _ = revizyon_ornegi(False); d = f.calistir(t(19, '17:00'))
        for g in d.gorevler.values():
            if g['durum'] != 'BITTI': self.assertIsNone(g['is_puani'])
            elif g['tur'] == 'ONAY': self.assertEqual(g['is_puani'], g['zaman_degeri'])
            else: self.assertEqual(g['is_puani'], g['zaman_degeri'] * g['zorluk'])

    def test_I13(self):
        for g in self.gd.gorevler.values():
            if g['tur'] == 'ONAY': self.assertEqual(g['zaman_degeri'], int(self.gd.gorevler[g['kaynak']]['zaman_degeri'] * .1))

    def test_I14(self):
        for g in self.gd.gorevler.values():
            if g['tur'] == 'NORMAL' and g['onay_gerekli']:
                acik = [o for o in self.gd.gorevler.values() if o['tur'] == 'ONAY' and o.get('kaynak') == g['kimlik'] and o['durum'] != 'BITTI']
                self.assertEqual(len(acik), int(g['durum'] == 'ONAY_BEKLIYOR'))

    def test_I15(self):
        f, g, r, _ = revizyon_ornegi(); d = f.calistir(t(3, '12:00', 11))
        self.assertEqual(d.gorevler[g]['durum'], 'REVIZYONDA'); self.assertNotEqual(d.gorevler[r]['durum'], 'BITTI')
        d = f.calistir(t(4, '17:00', 11)); self.assertEqual(d.gorevler[r]['durum'], 'BITTI'); self.assertEqual(d.gorevler[g]['durum'], 'BITTI')

    def test_I16(self):
        from irp.gorev import kapi as gorev_kapi
        g = self.gd.gorevler[self.ids['h']]
        self.assertEqual(g['durum'], 'ON_IS_BEKLIYOR')
        self.assertFalse(gorev_kapi(self.gd, g, {'eylem_kodu': 'GOREV.TAMAMLADIM', 'kim': 'K044', 'kanit': []}))

    def test_I17(self):
        d = self.depolar[0]; once = d.son_hal()
        for islem in ('GUNCELLE', 'SIL', 'TRUNCATE'):
            with self.assertRaises(PermissionError): d.olay_koru(islem)
        k = next(iter(d.olaylar)); e = d.olaylar[k]; e['girdiler']['boz'] = 1
        self.assertNotIn('boz', d.olaylar[k]['girdiler']); self.assertEqual(d.son_hal(), once)

    def test_I18(self):
        f = s1(); beklenen = f.calistir(t(22, '11:45')).son_hal()
        for tohum in TOHUMLAR:
            sirali = list(f.olaylar); random.Random(tohum).shuffle(sirali)
            self.assertEqual(f.yeniden_hesapla(t(22, '11:45'), sirali).son_hal(), beklenen)

    def test_I19(self):
        for f, d in zip(self.uretimler, self.depolar):
            once = d.son_hal()
            for e in f.olaylar[::3]: d.olay_ekle(e, servis=True)
            self.assertEqual(d.son_hal(), once)

    def test_I20(self):
        for d in self.depolar + [self.gd]:
            once = d.son_hal(); d.yeniden_kur(); self.assertEqual(d.son_hal(), once)

    def test_I21(self):
        f = Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 4); f.is_olay('ARIZA_BILDIRDIM', '09:00', 4, neden='ARIZA.MAKINE')
        d = f.calistir(t(22, '09:30'))
        once = deepcopy(d.bildirimler)
        for _ in range(3): d.yeniden_kur()
        self.assertEqual(d.bildirimler, once); self.assertEqual(len(once), 1)

    def test_I22(self):
        f = Duzenek(); f.ata(3); f.is_olay('MESAI.GIRDIM', '07:58'); e = f.is_olay('BASLADIM', '08:00', 3)
        d = f.calistir(t(22, '09:00'))
        self.assertIn(e, d.olaylar); self.assertIn(e, d.supheliler); self.assertEqual(emek(d, is_id(3)), 0)

    def test_I23(self):
        d = s1().calistir(t(22, '11:45')); e = deepcopy(next(iter(d.olaylar.values())))
        e['girdiler']['degisen'] = True
        self.assertEqual(d.olay_ekle(e, servis=True)['sonuc'], 'CAKISMA'); self.assertTrue(d.isleme_hatalari)

    def test_I24(self):
        for kisi in self.gd.kisiler:
            m = maas_dagilimi(self.gd, kisi, '2026-10-01')
            self.assertGreaterEqual(m['payda'], 180)
            self.assertLessEqual(abs(sum(m['tutarlar'].values()) + m['dagitilamayan'] - m['maas']), Decimal('.02'))

    def test_I25(self):
        f = s1(); d = f.calistir(t(1, '00:30', 11)); ay_kapanisi(d, '2026-10-01')
        once = deepcopy(d.ay_kapanislari); maliyet = iscilik_maliyeti(d, '2509084', '2026-10-01', '2026-10-31')
        f.olay('K009', 'IS.SURE_EKLEDIM', t(2, '10:00', 11), 4, {'baslangic': t(22, '08:00'), 'bitis': t(22, '08:05'), 'aciklama': 'Gec', 'is_bitti': False}, adina='K017', giris_sekli='ELLE')
        d.ilerlet(t(2, '11:00', 11)); d.olay_ekle(f.olaylar[-1]); ay_kapanisi(d, '2026-10-01')
        self.assertEqual(d.ay_kapanislari, once)
        self.assertEqual(iscilik_maliyeti(d, '2509084', '2026-10-01', '2026-10-31'), maliyet)

    def test_I26(self):
        for k in self.gd.etaplar:
            e = etap_gostergesi(self.gd, k)
            self.assertLessEqual(e['tamamlanan'], e['planli_toplam'])
            if not e['hedef']: self.assertEqual(e['yuzde'], 'Hesaplanamaz')

    def test_I27(self):
        self.assertEqual(kapasite(self.gd, 'K041', '2026-10-26', '2026-10-30'), 36)
        for kisi in self.gd.kisiler: self.assertGreaterEqual(yuk(self.gd, kisi, '2026-10-26', '2026-10-30'), 0)

    def test_I28(self):
        e = etap_gostergesi(self.gd, self.fg.etap['E-TAS'])
        vadesi_gelen = [g for g in self.gd.gorevler.values() if g['tur'] == 'NORMAL' and son_teslim_ani(g) <= self.gd.saat.simdi()]
        self.assertEqual(sum(e['dort_kategori'].values()), sum(g['zaman_degeri'] for g in vadesi_gelen))

    def test_I29(self):
        f = demo_ornegi(); d = Depo(Saat(t(1, '00:00'), demo=True)); oynatici = Demo(d, f.olaylar, t(1, '00:00'))
        oynatici.oynat(t(22, '10:05')); oynatici.oynat(t(22, '12:45')); once = d.son_hal()
        oynatici.demo_sifirla(); oynatici.oynat(t(22, '12:45')); self.assertEqual(d.son_hal(), once)

    def test_I30(self):
        f = s1(); d = f.calistir(t(22, '09:00'))
        self.assertTrue(all(a['baslangic'] <= d.saat.simdi() and (a['bitis'] is None or a['bitis'] <= d.saat.simdi()) for a in d.araliklar))
        self.assertEqual(d.isler[is_id(1)]['durum'], 'CALISILIYOR')
        self.assertFalse(d.bildirimler)

    def test_I31(self):
        f = self.fg; d = f.calistir(t(26, '12:00')); once = {k: g['zaman_degeri'] for k, g in d.gorevler.items() if g['tur'] == 'ONAY'}
        e = deepcopy(next(x for x in f.olaylar if x['eylem_kodu'] == 'AYAR.ONAY_ORANI'))
        e.update(olay_kimligi='K001-2610269999-M', oldugu_an=t(26, '11:59')); e['girdiler'] = {'deger': .2, 'gecerli_baslangic': t(26, '11:59')}
        d.olay_ekle(e)
        self.assertEqual({k: d.gorevler[k]['zaman_degeri'] for k in once}, once)

    def test_I32(self):
        cihaz = Cihaz('K017', 'T', Saat(t(22)))
        ids = [cihaz.olay_kimligi_uret() for _ in range(200)]
        self.assertEqual(len(ids), len(set(ids)))
        d = s1().calistir(t(22, '11:45')); yeni = Cihaz('K017', 'T', Saat(t(22, '12:00'))); yeni.sayaci_esitle(d)
        self.assertNotIn(yeni.olay_kimligi_uret(), d.olaylar)

    def test_I33(self):
        cihaz = Cihaz('K017', 'T', Saat(t(23, '07:55')))
        ekran = cihaz.ekran_hali({'durum': 'CALISIYOR', 'son_hesap_ani': t(22, '17:00')})
        self.assertTrue(kapi(ekran['son_hal'], 'MESAI.GIRDIM', None, None))

    def test_I34_uretec_kapilara_uyar(self):
        for f in self.uretimler:
            d = Depo(Saat(t(1, '00:00')))
            for e in sorted(f.olaylar, key=lambda e: (e['oldugu_an'], e['olay_kimligi'])):
                d.ilerlet(e['oldugu_an'])
                if e['kim'] == 'K017':
                    hedef = e['neyin_ustunde'][0]['kimlik'] if e['neyin_ustunde'] else None
                    liste = d.listeler.get('K017', [])
                    self.assertTrue(kapi(d.kisi_durumu.get('K017', bos_hal()), e['eylem_kodu'], d.isler.get(hedef), liste[0] if liste else None, d.sabit_molada(an(e['oldugu_an']))), e)
                d.olay_ekle(e, servis=True)

    def test_I35_saat_olay_uretmez(self):
        d = s1().calistir(t(22, '09:00')); once = len(d.olaylar)
        d.ilerlet(t(22, '18:01')); self.assertEqual(len(d.olaylar), once)

    def test_I36_kanit_gunlugu_degistirmez(self):
        d = s1().calistir(t(22, '11:45')); once = kodla(dict(d.olaylar))
        d.yeniden_kur(); self.assertEqual(kodla(dict(d.olaylar)), once)
