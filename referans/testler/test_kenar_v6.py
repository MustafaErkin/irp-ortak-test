"""Yeni kararlarin kesisimleri; guvenceleri bozan karsit girdiler."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo, Saat, an
from irp.gorunumler import kapasite, maas_dagilimi, onay_listesi, iscilik_maliyeti, gorev_payi
from irp.gorunum_v6 import iptal_edilenler
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from irp.degismezler_v6 import denetle, yetki_tarihcesi
from .ortak import Duzenek, t, is_id
from .v5_destek import gonder, onaysiz_bekleme, is_satiri
from .test_v6 import bitmis, baglanti, gorev_onayi
from .tur2_ornekler import iki_kisi, iptal_gorev


class KenarlarV6(unittest.TestCase):
    def test_gec_not_ayrilisla_ayni_bulut_aninda_gelis_sirasini_korur(self):
        f=Duzenek(); d=f.calistir(t(22,'08:00'))
        gonder(f,d,'K012','AYAR.YONLENDIRDIM',t(22,'08:00'),girdiler={'birim':'MEK_TASARIM','kisiler':['K060']})
        gonder(f,d,'K012','AYAR.YONLENDIRDIM',t(22,'10:00'),girdiler={'birim':'MEK_TASARIM','kisiler':['K012']})
        gonder(f,d,'K001','KISI.AYRILDI',t(23,'09:00'),girdiler={'kisi':'K060','ayrilis_tarihi':'2026-10-23'})
        e,_=gonder(f,d,'K041','NOT.YAZDIM',t(22,'09:00'),'2509084',{'metin':'Ayni bulut saniyesinde gec not','etiketler':['MEK_TASARIM']},tur='PROJE')
        self.assertEqual(d.kisiler['K060']['ayrilis_tarihi'],'2026-10-23')
        self.assertEqual(d.notlar[e]['atlanan_alicilar'],['K060'])
        self.assertNotIn(e+'/1',d.gorevler)

    def test_ileri_rol_ayrilik_boslugunda_yetki_acmaz_yeniden_giris_rolleri_alinir(self):
        f=Duzenek(); d=f.calistir(t(15,'09:00'))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(15,'09:00'),girdiler={'kisi':'K060','gecerli_baslangic':t(20,'00:00'),'degisenler':{'roller':['YONETICI']}})
        gonder(f,d,'K001','KISI.AYRILDI',t(15,'09:01'),girdiler={'kisi':'K060','ayrilis_tarihi':'2026-10-16'})
        d.ilerlet(t(20,'09:00'))
        gonder(f,d,'K060','NOT.YAZDIM',t(20,'09:01'),'2509084',{'metin':'Ayrilik boslugu'},tur='PROJE',bek='YETKI')
        gonder(f,d,'K001','KISI.EKLEDIM',t(26,'09:00'),girdiler={'kod':'K060','ad':'Donen','birim':'MEK_TASARIM','yaka':'BEYAZ','roller':['BEYAZ_YAKA'],'giris_tarihi':'2026-10-26'})
        self.assertEqual(d.kisiler['K060']['roller'],['BEYAZ_YAKA'])
        self.assertEqual(kapasite(d,'K060','2026-10-19','2026-10-23'),0)
        self.assertTrue(all(denetle(d,True).values()))

    def test_baglanti_sonrasi_iptalde_donuk_maliyet_eski_projede(self):
        f,d=bitmis(); d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        gonder(f,d,'K004','IS.BAGLANTI_DUZELTTIM',t(2,'09:00',11),1,baglanti())
        gonder(f,d,'K009','IS.IPTAL_ETTIM',t(2,'09:01',11),1,{'gerekce':'Iptal'})
        self.assertEqual(iptal_edilenler(d,'2509084')['maliyet']['iscilik'],Decimal('111.11'))
        self.assertEqual(iptal_edilenler(d,'2509091')['maliyet']['iscilik'],0)
        self.assertEqual(iptal_edilenler(d,'2509084', '2026-10-23','2026-10-31')['maliyet']['iscilik'],0)

    def test_ust_giris_oncesi_gorev_kabuluyle_maas_payi_acamaz(self):
        f=Duzenek(); d=f.calistir(t(15,'09:00'))
        gonder(f,d,'K001','KISI.EKLEDIM',t(15,'09:00'),girdiler={'kod':'K061','ad':'Yeni','birim':'MEK_TASARIM','yaka':'BEYAZ','roller':['BEYAZ_YAKA'],'giris_tarihi':'2026-10-19'})
        g,_=gonder(f,d,'K012','GOREV.ATADIM',t(15,'09:01'),girdiler={'gorevler':[f.gorev_satiri(kisi='K061',teslim_tarihi='2026-10-23')]})
        gonder(f,d,'K012','GOREV.KABUL_ETTIM',t(15,'09:02'),g+'/1',bek='YETKI')
        self.assertEqual(maas_dagilimi(d,'K061','2026-10-01')['toplam_saat'],0)

    def test_gec_not_ayrilisi_geri_almaz_alici_atlanir(self):
        f = Duzenek(); d = f.calistir(t(22, '08:00'))
        gonder(f, d, 'K012', 'AYAR.YONLENDIRDIM', t(22, '08:00'), girdiler={'birim':'MEK_TASARIM','kisiler':['K060']})
        gonder(f, d, 'K012', 'AYAR.YONLENDIRDIM', t(22, '10:00'), girdiler={'birim':'MEK_TASARIM','kisiler':['K012']})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, '10:01'), girdiler={'kisi':'K060','ayrilis_tarihi':'2026-10-22'})
        d.ilerlet(t(23, '09:00'))
        e, _ = gonder(f, d, 'K041', 'NOT.YAZDIM', t(22, '09:00'), '2509084', {'metin':'Gec not','etiketler':['MEK_TASARIM']}, tur='PROJE')
        self.assertEqual(d.kisiler['K060']['ayrilis_tarihi'], '2026-10-22')
        self.assertNotIn(e+'/1', d.gorevler); self.assertEqual(d.notlar[e]['atlanan_alicilar'], ['K060'])
        self.assertEqual(kapasite(d, 'K060', '2026-10-23', '2026-10-23'), 0)

    def test_giris_oncesi_ayrilis_istihdami_ters_cevirmez(self):
        f=Duzenek(); d=f.calistir(t(15,'09:00'))
        gonder(f,d,'K001','KISI.EKLEDIM',t(15,'09:00'),girdiler={'kod':'K061','ad':'Yeni','birim':'MEK_TASARIM','yaka':'BEYAZ','roller':['BEYAZ_YAKA'],'giris_tarihi':'2026-10-19'})
        gonder(f,d,'K001','KISI.AYRILDI',t(15,'09:01'),girdiler={'kisi':'K061','ayrilis_tarihi':'2026-10-16'},bek='DURUM')

    def test_kurulum_son_olayi_tek_basina_kilit_koyamaz(self):
        f=Duzenek(False); f.olay('K001','KURULUM.TAMAMLADIM',t(1,'07:00'),giris_sekli='AKTARIM')
        d=Depo(Saat(t(1,'07:00')))
        self.assertEqual(d.olay_ekle(f.olaylar[-1],servis=True)['kod'],'DURUM')
        self.assertFalse(d.olaylar); self.assertFalse(d.kurulum_tamamlandi)

    def test_I72_yetkisiz_kaynak_enjeksiyonu_yakalanir(self):
        f, d = bitmis()
        e=f.olay('K017','IS.BAGLANTI_DUZELTTIM',t(22,'09:00'),1,baglanti())
        ham=deepcopy(f.olaylar[-1]); ham['bulut_ulasma_ani']=t(22,'09:00'); d._kayitlar[e]=ham
        self.assertIn(e,yetki_tarihcesi(d)['yetkisiz_kararlar'])

    def test_I73_kapanis_tutari_bozulmasi_yakalanir(self):
        f,d=bitmis(); d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        self.assertTrue(denetle(d,True)['I73'])
        d.ay_kapanislari['2026-10-01:MALIYET']['2509084']['iscilik'] += Decimal('1')
        self.assertFalse(denetle(d,True)['I73'])

    def test_baska_firma_alti_satir_yeni_roller(self):
        from simulasyon.farkli_firma_v6 import calistir
        _, d, m = calistir()
        self.assertEqual(m['yetki_satiri'], 6)
        self.assertNotIn('ROL:EKIP_LIDERI', d.kod_listesi)

    def test_ust_verenin_gorevini_degistirir_iptal_eder(self):
        f = Duzenek(); g = f.gorev_ata(); d = f.calistir(t(22, '08:00'))
        gonder(f, d, 'K004', 'GOREV.DEGISTIRDIM', t(22, '08:01'), g, {'degisenler': {'ad': 'Duzeltme'}}, bek='YETKI')
        gonder(f, d, 'K001', 'GOREV.DEGISTIRDIM', t(22, '08:02'), g, {'degisenler': {'ad': 'Duzeltme'}})
        gonder(f, d, 'K001', 'GOREV.IPTAL_ETTIM', t(22, '08:03'), g)
        self.assertEqual(d.gorevler[g]['durum'], 'IPTAL')

    def test_ust_gorev_tanikligini_yazar(self):
        f = Duzenek(); g = f.gorev_ata(); d = f.calistir(t(22, '08:00'))
        gonder(f, d, 'K012', 'GOREV.KABUL_ETTIM', t(22, '08:01'), g)
        gonder(f, d, 'K001', 'GOREV.TAMAMLADIM', t(22, '08:02'), g)
        self.assertEqual(d.gorevler[g]['durum'], 'BITTI')

    def test_ust_ret_onay_gorevine_pay_yazmaz(self):
        f, d, g, o = gorev_onayi()
        gonder(f, d, 'K001', 'GOREV.REDDETTIM', t(22, '11:10'), g, {'not': 'Duzelt', 'sebep_olan': 'K041', 'revizyon_ver': False})
        self.assertEqual(d.gorevler[o]['durum'], 'IPTAL'); self.assertIsNone(d.gorevler[o]['is_puani'])
        self.assertEqual(maas_dagilimi(d, 'K012', '2026-10-01')['toplam_saat'], 0)

    def test_yetki_tablosu_kendi_onayini_acamaz(self):
        f, d, g, o = gorev_onayi()
        gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, '11:06'), girdiler={'eylem_kodu': 'GOREV.ONAYLADIM', 'kimler': ['BEYAZ_YAKA'], 'kapsam': 'FIRMA'})
        gonder(f, d, 'K041', 'GOREV.ONAYLADIM', t(22, '11:07'), g, bek='YETKI')

    def test_toplu_onayda_kendi_hedefi_tum_olayi_reddeder(self):
        f = Duzenek(); f.ata(9, 'K009'); f.ata(3, 'K017')
        for k, kisi, saat in [(9, 'K009', '09:00'), (3, 'K017', '09:01')]:
            f.is_olay('MESAI.GIRDIM', '07:58', kisi=kisi); f.is_olay('TAMAMLADIM', saat, k, kisi=kisi)
        next(e for e in f.olaylar if e['eylem_kodu'] == 'IS.TANIMLADIM')['girdiler']['isler'][2]['on_isler'] = []
        d = f.calistir(t(22, '09:02'))
        gonder(f, d, 'K009', 'IS.ONAYLADIM', t(22, '09:03'), [is_id(3), is_id(9)], bek='YETKI')
        self.assertEqual(d.isler[is_id(3)]['durum'], 'ONAY_BEKLIYOR')

    def test_hassas_yetki_tablosuyla_devredilemez(self):
        f = Duzenek(); d = f.calistir(t(22, '09:00'))
        for kod in ('YETKI.TANIMLADIM', 'MAAS.GUNCELLEDIM'):
            gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, '09:01'), girdiler={'eylem_kodu': kod, 'kimler': ['YONETICI'], 'kapsam': 'FIRMA'})
        gonder(f, d, 'K004', 'YETKI.TANIMLADIM', t(22, '09:02'), girdiler={'eylem_kodu': 'IS.ATADIM', 'kimler': [], 'kapsam': 'BIRIM'}, bek='YETKI')
        gonder(f, d, 'K004', 'MAAS.GUNCELLEDIM', t(22, '09:03'), girdiler={'kisi': 'K017', 'gecerli_baslangic': '2026-10-01'}, bek='YETKI')

    def test_gec_taniklik_eski_yetki_satiriyla(self):
        f = Duzenek(); f.ata(1); d = f.calistir(t(22, '07:30'))
        # Isin birimindeki CALISAN'a adina yazma yetkisi verilir, sonra kaldirilir.
        for saat, kimler in [('07:30', ['CALISAN']), ('09:00', [])]:
            for kod in ('MESAI.GIRDIM', 'IS.BASLADIM'):
                gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, saat), girdiler={'eylem_kodu': kod, 'kimler': kimler, 'kapsam': 'BIRIM'})
        gonder(f, d, 'K023', 'MESAI.GIRDIM', t(22, '07:58'), adina='K017')
        gonder(f, d, 'K023', 'IS.BASLADIM', t(22, '08:00'), 1, adina='K017')
        gonder(f, d, 'K023', 'IS.BASLADIM', t(22, '09:01'), 1, adina='K017', bek='YETKI')
        self.assertEqual(emek(d, is_id(1)), 61)

    def test_gec_taniklik_yeni_yetki_gecmisi_acmaz(self):
        f = Duzenek(); f.ata(1); d = f.calistir(t(22, '09:00'))
        gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, '09:00'), girdiler={'eylem_kodu': 'IS.BASLADIM', 'kimler': ['CALISAN'], 'kapsam': 'BIRIM'})
        gonder(f, d, 'K023', 'IS.BASLADIM', t(22, '08:00'), 1, adina='K017', bek='YETKI')

    def test_silinen_satir_sabit_iliskiyi_silmez(self):
        f, d, g, o = gorev_onayi()
        gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, '11:06'), girdiler={'eylem_kodu': 'GOREV.ONAYLADIM', 'kimler': [], 'kapsam': 'BIRIM'})
        gonder(f, d, 'K012', 'GOREV.ONAYLADIM', t(22, '11:07'), g)
        self.assertEqual(d.gorevler[g]['durum'], 'BITTI')

    def test_ayrilan_atayanin_onayi_ustte_kalir(self):
        f, d, i = onaysiz_bekleme(False)
        gonder(f, d, 'K017', 'IS.TAMAMLADIM', t(22, '09:00'), i)
        gonder(f, d, 'K001', 'BIRIM.TANIMLADIM', t(22, '09:01'), girdiler=dict(d.birimler['IMALAT'], basi=None))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, '09:02'), girdiler={'kisi': 'K009', 'ayrilis_tarihi': '2026-10-22'})
        d.ilerlet(t(23, '09:00')); self.assertIn(i, [x['kimlik'] for x in onay_listesi(d, 'K001')])
        gonder(f, d, 'K004', 'IS.ONAYLADIM', t(23, '09:01'), i)

    def test_iki_kisi_baglanti_altlara_yayilir(self):
        f, i = iki_kisi(); d = f.calistir(t(22, '13:00'))
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '13:01'), i, baglanti())
        self.assertEqual({d.isler[k]['proje'] for k in (i, i+'/k1', i+'/k2')}, {'2509091'})
        self.assertEqual(emek(d, i), 422)
        gonder(f, d, 'K009', 'IS.DEGISTIRDIM', t(22, '13:02'), i, {'degisenler': {'tahmini_sure_dk': 240}}, bek='DURUM')

    def test_iptal_isin_baglantisi_kapali(self):
        f, d = bitmis(); gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '09:01'), 1, {'gerekce': 'Iptal'})
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '09:02'), 1, baglanti(), bek='DURUM')
        self.assertEqual(iptal_edilenler(d, '2509084')['emek_saat'], 1)

    def test_tezgah_cevrimi_baglanti_ve_iptalde_korunur(self):
        f = Duzenek(); f.ata(8); f.ata(7, sira=2)
        f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('TAMAMLADIM', '08:30', 8); f.is_olay('TAMAMLADIM', '13:00', 7)
        d = f.calistir(t(22, '13:01'))
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '13:02'), 7, baglanti())
        self.assertEqual(iscilik_maliyeti(d, '2509091', '2026-10-01', '2026-10-31')['tezgah'], 900)
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '13:03'), 7, {'gerekce': 'Iptal'})
        self.assertEqual(iscilik_maliyeti(d, '2509091', '2026-10-01', '2026-10-31', iptal=True)['tezgah'], 900)
        self.assertEqual(sum((a['bitis']-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['kova']=='TEZGAH'), 270)

    def test_kapanmis_aydan_sonra_iptal_tutari_degistirmez(self):
        f, d = bitmis(); d.ilerlet(t(1, '00:30', 11)); ay_kapanisi(d, '2026-10-01'); once = deepcopy(d.ay_kapanislari)
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(2, '09:00', 11), 1, {'gerekce': 'Yeni ay iptali'})
        self.assertEqual(d.ay_kapanislari, once)
        self.assertEqual(iscilik_maliyeti(d, '2509084', '2026-10-01', '2026-10-31')['iscilik'], Decimal('111.11'))
        self.assertEqual(iptal_edilenler(d, '2509084')['maliyet']['iscilik'], Decimal('111.11'))
        self.assertTrue(denetle(d, True)['I73'])

    def test_iptal_gorevin_kisisel_payi_korunur(self):
        f, g, o = iptal_gorev(); d = f.calistir(t(28, '12:00'))
        self.assertEqual(gorev_payi(d, d.gorevler[g], '2026-10-01', '2026-10-31'), 15)
        self.assertEqual(maas_dagilimi(d, 'K041', '2026-10-01')['paylar'], {'iptal:2509084': 15})
        self.assertEqual(iptal_edilenler(d, '2509084')['emek_saat'], 15)

    def test_istihdam_ay_ortasi_zam_birlesimi(self):
        f = Duzenek(); d = f.calistir(t(15, '09:00'))
        gonder(f, d, 'K001', 'MAAS.GUNCELLEDIM', t(15, '09:00'), girdiler={'kisi': 'K060', 'gecerli_baslangic': '2026-10-12'}, hassas_ek={'nesne_kimlik': 'K060', 'tur': 'MAAS_AYLIK', 'tutar': 30000, 'gecerli_baslangic': '2026-10-12'})
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(15, '09:01'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-16'})
        self.assertEqual(maas_dagilimi(d, 'K060', '2026-10-01')['maas'], Decimal('13809.52'))

    def test_yeniden_giriste_bosluk_ve_gec_taniklik(self):
        f = Duzenek(); d = f.calistir(t(15, '09:00'))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(15, '09:00'), girdiler={'kisi': 'K060', 'ayrilis_tarihi': '2026-10-16'})
        gonder(f, d, 'K001', 'KISI.EKLEDIM', t(26, '09:00'), girdiler={'kod': 'K060', 'ad': 'Donen', 'birim': 'MEK_TASARIM', 'yaka': 'BEYAZ', 'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-10-26'})
        gonder(f, d, 'K060', 'NOT.YAZDIM', t(16, '16:00'), '2509084', {'metin': 'Eski donem'}, tur='PROJE')
        gonder(f, d, 'K060', 'NOT.YAZDIM', t(20, '16:00'), '2509084', {'metin': 'Bosluk'}, tur='PROJE', bek='YETKI')
        gonder(f, d, 'K060', 'NOT.YAZDIM', t(26, '16:00'), '2509084', {'metin': 'Yeni donem'}, tur='PROJE')
        self.assertEqual(maas_dagilimi(d, 'K060', '2026-10-01')['maas'], Decimal('15238.10'))
        self.assertTrue(all(denetle(d, True).values()))

    def test_iki_yetkilinin_ileri_rol_planlari_birlikte_denetlenir(self):
        f = Duzenek(); d = f.calistir(t(22, '09:00'))
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(22, '09:00'), girdiler={'kisi': 'K060', 'gecerli_baslangic': t(22, '09:00'), 'degisenler': {'roller': ['YETKILI']}})
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(22, '09:01'), girdiler={'kisi': 'K001', 'gecerli_baslangic': t(2, '00:00', 11), 'degisenler': {'roller': ['YONETICI']}})
        gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(22, '09:02'), girdiler={'kisi': 'K060', 'gecerli_baslangic': t(3, '00:00', 11), 'degisenler': {'roller': ['BEYAZ_YAKA']}}, bek='DURUM')
        d.ilerlet(t(2, '09:00', 11)); self.assertTrue(denetle(d, True)['I70'])

    def test_yonetim_yetki_gecmisi_son_tabloyla_karistirilmaz(self):
        f, d = bitmis()
        gonder(f, d, 'K004', 'IS.BAGLANTI_DUZELTTIM', t(22, '09:30'), 1, baglanti())
        gonder(f, d, 'K001', 'YETKI.TANIMLADIM', t(22, '09:31'), girdiler={'eylem_kodu': 'IS.BAGLANTI_DUZELTTIM', 'kimler': [], 'kapsam': 'BIRIM'})
        self.assertFalse(yetki_tarihcesi(d)['yetkisiz_kararlar'])
        self.assertTrue(all(denetle(d, True).values()))
