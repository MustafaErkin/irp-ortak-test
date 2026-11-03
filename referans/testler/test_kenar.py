"""Kenar/saldırı testleri ve bulgu numaralı beklenen tasarım başarısızlıkları.

unittest.expectedFailure pytest tarafından da XFAIL olarak toplanır.
Karşı örneklerde yalnız son bağımsız beklenen assertion başarısız olmalıdır.
"""
import itertools
import random
import unittest
from copy import deepcopy
from irp import Depo, Saat, an
from irp.cihaz import Cihaz
from irp.demo import Demo
from irp.kisi_gunu import kapi
from irp.gorunumler import *
from irp.zaman import ay_kapanisi
from .ortak import Duzenek, t, is_id, s1, s13, yaz
from .kenarlar_v2 import KenarlarV2
from .test_senaryolar import revizyon_ornegi, dakika, dilimler, habersiz_ornegi


class Kenarlar(unittest.TestCase):
    def test_diger_ariza_notu_ve_performans_gorunurlugu(self):
        f = s1(); d = f.calistir(t(22, '11:45'))
        f.is_olay('ARIZA_BILDIRDIM', '11:44', 2, neden='ARIZA.DIGER')
        self.assertEqual(d.olay_ekle(f.olaylar[-1])['sonuc'], 'REDDEDILDI')
        with self.assertRaises(PermissionError): adil_performans(d, 'K041', '2026-10-01', '2026-10-31', cagiran='K044')
        self.assertIsInstance(adil_performans(d, 'K041', '2026-10-01', '2026-10-31', cagiran='K041'), dict)
        self.assertIsInstance(adil_performans(d, 'K041', '2026-10-01', '2026-10-31', cagiran='K001'), dict)

    def test_iscilik_ise_yazilan_beklemeyi_icerir(self):
        f = Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 4); f.is_olay('ARIZA_BILDIRDIM', '08:30', 4, neden='ARIZA.MAKINE')
        d = f.calistir(t(22, '09:00'))
        self.assertEqual(emek(d, is_id(4)), 30)
        self.assertEqual(iscilik_maliyeti(d, '2509084', '2026-10-22', '2026-10-22')['iscilik'], Decimal('111.11'))

    def test_demo_yeni_girdi_yok_saat_ayari_var(self):
        f = s1(); d = f.calistir(t(22, '09:00'), demo=True)
        f.olay('K001', 'AYAR.SAAT_KAYDIRDIM', t(22, '09:00'), girdiler={'hedef': t(22, '10:05')})
        self.assertEqual(d.olay_ekle(f.olaylar[-1])['sonuc'], 'BASARILI')
        self.assertEqual(d.saat.simdi(), an(t(22, '10:05')))
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'SABIT_MOLADA')
        e = deepcopy(f.olaylar[-1]); e['olay_kimligi'] = 'K001-2610229999-M'; e['girdiler']['hedef'] = t(22, '08:00')
        self.assertEqual(d.olay_ekle(e)['sonuc'], 'REDDEDILDI')
        e = deepcopy(next(e for e in f.olaylar if e['eylem_kodu'] == 'IS.BASLADIM')); e['olay_kimligi'] = 'K017-2610229999-T'
        self.assertEqual(d.olay_ekle(e)['sonuc'], 'REDDEDILDI')

    def test_R24_uyari_ve_sonraki_is_hazir_alanlari(self):
        from irp.cihaz import atama_uyarilari, sonraki_is_hazirla
        f, ids = s13(); d = f.calistir(t(26, '12:00'))
        satir = f.gorev_satiri(teslim_tarihi='2026-11-23', zaman_degeri=1000)
        uyarilar = atama_uyarilari(d, [satir])
        self.assertEqual({u['kural'] for u in uyarilar}, {'R23', 'R24'})
        hazir = sonraki_is_hazirla(d, ids['a'])
        self.assertEqual(hazir['kaynak'], ids['a']); self.assertEqual(hazir['on_kosul'], [ids['a']])
        self.assertEqual(hazir['proje'], '2509084'); self.assertEqual(hazir['etap'], f.etap['E-TAS'])

    def test_gun_akisinda_lider_ve_takvim_var(self):
        from irp.kisi_gunu import gun_akisi
        f, _ = habersiz_ornegi(); d = f.calistir(t(22, '13:10'))
        akis = gun_akisi(d, 'K017', '2026-10-22')
        self.assertTrue(any(x['olay'] and x['olay']['eylem_kodu'] == 'IS.SIRALADIM' for x in akis))
        self.assertTrue(any(x['kimlik'] == 'MOLA_BASI' for x in akis))
        self.assertTrue(all(x['an'] <= d.saat.simdi() for x in akis))

    def test_bekleyen_olaylar_cihaz_kapilarini_acar(self):
        f = Duzenek(); f.ata(4); d = f.calistir(t(22, '07:58'))
        h = dict(d.kisi_durumu['K017']); cihaz = Cihaz('K017', 'T', Saat(t(22, '07:58')))
        cihaz.olay_yaz('MESAI.GIRDIM', h)
        cihaz.saat.ilerlet(t(22, '08:00'))
        cihaz.olay_yaz('IS.BASLADIM', h, d.isler, d.listeler['K017'], is_id(4))
        cihaz.saat.ilerlet(t(22, '08:10'))
        cihaz.olay_yaz('IS.MOLA_VERDIM', h, d.isler, d.listeler['K017'], is_id(4))
        self.assertEqual(cihaz.bekleyen_sayisi(), 3)
        self.assertEqual(cihaz.ekran_hali(h, d.isler, d.listeler['K017'])['son_hal']['durum'], 'MOLADA')

    def test_farkli_saat_dilimleri_gercek_anla_siralanir(self):
        f = s1(); normal = f.calistir(t(22, '11:45')).son_hal()
        from datetime import timezone
        karisik = deepcopy(f.olaylar)
        for e in karisik[::2]: e['oldugu_an'] = an(e['oldugu_an']).astimezone(timezone.utc).isoformat()
        d = f.calistir(t(22, '11:45'), karisik)
        # Kaynak zaman gösterimi değişebilir; gerçekleşen aralık ve iş durumları değişmez.
        beklenen = f.calistir(t(22, '11:45'))
        self.assertEqual(d.araliklar, beklenen.araliklar)
        self.assertEqual(d.listeler, beklenen.listeler)
        self.assertEqual(d.supheliler, beklenen.supheliler)

    def test_kucultulmus_cift_atama_uc_olay(self):
        f=Duzenek(); f.ata(4); f.ata(4,'K023',zaman=t(22,'08:00'))
        d=f.calistir(t(22,'08:30'))
        self.assertEqual(sum(is_id(4) in l for l in d.listeler.values()),1)

    def test_bozuk_tipler_bicim_hatasidir(self):
        f = s1(); d = f.calistir(t(22, '11:45')); e = deepcopy(next(e for e in f.olaylar if e['eylem_kodu'] == 'IS.ATADIM'))
        e['olay_kimligi'] = 'K009-2610229988-M'; e['girdiler']['sira'] = 'bir'
        self.assertEqual(d.olay_ekle(e)['sonuc'], 'REDDEDILDI')
        self.assertNotIn(e['olay_kimligi'], d.olaylar)
    def test_tum_gelis_permutasyonlari(self):
        f = Duzenek(); f.ata(4)
        for kod, saat, n in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:00', 4), ('MOLA_VERDIM', '09:00', 4), ('DEVAM_ETTIM', '09:10', 4)]: f.is_olay(kod, saat, n)
        temel, akis = f.olaylar[:-4], f.olaylar[-4:]
        beklenen = f.calistir(t(22, '09:30')).son_hal()
        for perm in itertools.permutations(akis):
            self.assertEqual(f.calistir(t(22, '09:30'), temel + list(perm)).son_hal(), beklenen)

    def test_molada_calisan_ve_lider(self):
        f = Duzenek(); f.ata(9); f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 9); f.is_olay('TAMAMLADIM', '09:55', 9)
        f.is_olay('ONAYLADIM', '10:05', 9, 'K009')
        d = f.calistir(t(22, '10:10')); self.assertEqual(d.kisi_durumu['K017']['durum'], 'SABIT_MOLADA')
        d.ilerlet(t(22, '10:20')); self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')
        self.assertEqual(dilimler(d, 'SABIT_MOLA'), [('10:00', '10:15')])
        f2 = Duzenek(); f2.ata(4); f2.is_olay('MESAI.GIRDIM', '07:58'); f2.is_olay('BASLADIM', '08:00', 4)
        e = f2.is_olay('MOLA_VERDIM', '10:05', 4)
        d = f2.calistir(t(22, '10:20')); self.assertIn(e, d.supheliler)
        self.assertEqual(dakika(d, 'MOLA'), 0); self.assertEqual(dakika(d, 'SABIT_MOLA'), 15)

    def test_paydos_sonrasi_ve_tatil(self):
        f = s1(); f.is_olay('MESAI.CIKTIM', '18:05')
        d = f.calistir(t(22, '18:10'))
        self.assertTrue(all(a['bitis'] and a['bitis'] <= an(t(22, '18:00')) for a in d.araliklar))
        f.is_olay('MESAI.GIRDIM', '08:00', gun=29)
        d = f.calistir(t(29, '09:00')); self.assertFalse([a for a in d.araliklar if str(a['gun']) == '2026-10-29'])

    def test_elle_sure_eski_hafta_reddedilir(self):
        f=s1(); d=f.calistir(t(2,'10:00',11))
        f.olay('K009','IS.SURE_EKLEDIM',t(2,'09:00',11),1,{'baslangic':t(22,'08:00'),'bitis':t(22,'08:05'),'aciklama':'Eski hafta','is_bitti':False},adina='K017',giris_sekli='ELLE')
        self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'DURUM')

    def test_iki_cihaz_ayni_an(self):
        f = Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM', '07:58')
        f.olay('K017', 'IS.BASLADIM', t(22, '08:00'), 4, harf='T')
        f.olay('K017', 'IS.BASLADIM', t(22, '08:00'), 4, harf='U')
        a = f.calistir(t(22, '09:00')); b = f.yeniden_hesapla(t(22, '09:00'), list(reversed(f.olaylar)))
        self.assertEqual(a.son_hal(), b.son_hal()); self.assertEqual(len(a.supheliler), 1)
        self.assertEqual(dakika(a, 'CALISMA'), 60)

    def test_lider_adina_basla(self):
        f = Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM', '07:58')
        f.olay('K009', 'IS.BASLADIM', t(22, '08:00'), 4, adina='K017')
        d = f.calistir(t(22, '09:00')); self.assertEqual(dakika(d, 'CALISMA'), 60)
        self.assertFalse([a for a in d.araliklar if a['kisi'] == 'K009'])
        self.assertEqual(d.kisi_durumu['K017']['acik_is'], is_id(4))

    def test_on_is_baska_kisiye_devredilir(self):
        f = Duzenek(); f.ata(3); f.ata(8, 'K023'); f.ata(7, 'K023', 2)
        f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('MESAI.GIRDIM', '07:59', kisi='K023')
        f.is_olay('TAMAMLADIM', '08:00', 8, 'K023')
        f.is_olay('DEVRETTIM', '08:10', 7, 'K009', kimden='K023', kime='K009')
        f.is_olay('MESAI.GIRDIM', '08:11', kisi='K009')
        f.is_olay('TAMAMLADIM', '08:20', 7, 'K009')
        d = f.calistir(t(22, '08:30'))
        self.assertEqual(d.isler[is_id(7)]['durum'], 'BITTI')
        self.assertEqual(d.isler[is_id(3)]['durum'], 'SIRADA')

    def test_yerel_gunluk_baglanti_ve_sayac(self):
        f = s1(); d = f.calistir(t(22, '11:45')); cihaz = Cihaz('K017', 'T', Saat(t(22, '12:00')))
        f.is_olay('MESAI.CIKTIM','11:45'); e=f.olaylar[-1]
        cihaz.gunluk_ekle(e); cihaz.gonderim_dongusu(d, False); self.assertEqual(cihaz.bekleyen_sayisi(), 1)
        cihaz.gonderim_dongusu(d); self.assertEqual(cihaz.bekleyen_sayisi(), 0)
        cihaz.sayaci_esitle(d); self.assertNotIn(cihaz.olay_kimligi_uret(), d.olaylar)
        cihaz.saat_farki_olc(t(22, '12:00'), t(22, '12:02'), t(22, '12:00'))
        self.assertEqual(cihaz.simdi_duzeltilmis(), an(t(22, '12:02')))

    def test_demo_geri_saat_sifirlar(self):
        f = s1(); d = Depo(Saat(t(1, '00:00'), demo=True)); oynatici = Demo(d, f.olaylar, t(1, '00:00'))
        oynatici.oynat(t(22, '12:45')); oynatici.oynat(t(22, '09:00'))
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISIYOR')
        self.assertEqual(dakika(d, 'CALISMA'), 55)
        with self.assertRaises(ValueError): d.saat.ilerlet(t(22, '08:00'))

    def test_geri_al_ve_duzeltme(self):
        f = s1(); mola = next(e for e in f.olaylar if e['eylem_kodu'] == 'IS.MOLA_VERDIM')
        f.olay('K017','KAYIT.GECERSIZ_SAYDIM',t(22,'11:43'),girdiler={'hedef':mola['olay_kimligi'],'gerekce':'Yanlis'},duzelttigi_olay=mola['olay_kimligi'])
        d = f.calistir(t(22, '11:45')); self.assertIn(mola['olay_kimligi'], d.olaylar)
        self.assertEqual(dakika(d, 'MOLA'), 0); self.assertEqual(dakika(d, 'CALISMA', is_=is_id(1)), 198)

    def test_bicim_yetki_ayrimi(self):
        f = s1(); d = f.calistir(t(22, '11:45')); e = deepcopy(f.olaylar[-1]); e['olay_kimligi'] = 'yanlis'
        self.assertEqual(d.olay_ekle(e)['sonuc'], 'REDDEDILDI')
        e['olay_kimligi'] = 'K017-2610229999-T'; self.assertEqual(d.olay_ekle(e, oturum='K023')['sonuc'], 'REDDEDILDI')
        e['adina'] = 'K023'; self.assertEqual(d.olay_ekle(e)['sonuc'], 'REDDEDILDI')

    def test_rastgele_gorev_retleri(self):
        for tohum in (42, 73, 2026):
            rng = random.Random(tohum); f = Duzenek()
            for n in range(8):
                g = f.gorev_ata(t(21, '08:{:02d}'.format(n)), zaman_degeri=rng.randint(1, 60), onay_gerekli=True, onaylayan='K012')
                f.gorev_olay('KABUL_ETTIM', t(21, '09:{:02d}'.format(n)), g)
                f.gorev_olay('TAMAMLADIM', t(22, '09:{:02d}'.format(n)), g)
                if rng.choice([True, False]):
                    f.gorev_olay('REDDETTIM', t(22, '10:{:02d}'.format(n)), g, 'K012', **{'not': 'Duzelt', 'sebep_olan': 'K041', 'revizyon_ver': False})
                    f.gorev_olay('TAMAMLADIM', t(22, '11:{:02d}'.format(n)), g)
                f.gorev_olay('ONAYLADIM', t(22, '14:{:02d}'.format(n)), g, 'K012')
            d = f.calistir(t(22, '15:00'))
            self.assertFalse(d.supheliler); self.assertTrue(all(g['durum'] == 'BITTI' for g in d.gorevler.values()))
            karmasik = list(f.olaylar); rng.shuffle(karmasik)
            self.assertEqual(d.son_hal(), f.yeniden_hesapla(t(22, '15:00'), karmasik).son_hal())

