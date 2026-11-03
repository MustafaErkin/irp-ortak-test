"""Kapsam eki 10.1.1. Beklenenler T8/T9/T10 ve karar 70/92/99'dan.

Bu dosyada model çıktısından öğrenilmiş beklenen değer yoktur.
"""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo, Saat, an
from irp.gorunum_v7 import oku, saat_maliyeti
from irp.gorunum_v9 import gorebilir_mi
from irp.gorunum_v10_1 import pencere, sapma, bildirim_kutusu
from irp.gorunumler import para
from irp.kurallar_v10 import etkin_pay
from .ortak import Duzenek, t, is_id, yaz
from .test_v7 import kur, gonder
from .test_v10 import gecikme_duzenegi
from .test_v10_1 import modul_duzenegi, belge_duzenegi, belge_turu, surum_olayi, birak


class DegismezDenetimi(unittest.TestCase):
    """C58: Karar 99 istisnası tarihsel I106/I107 denetiminde de geçerlidir."""
    def test_I106_I107_belge_sorumlusu_istisnasi(self):
        from .test_karar99 import ek_erisim_duzenegi
        from irp.degismezler_v10 import denetle
        f,d,n=ek_erisim_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        results=denetle(d,True)
        self.assertTrue(results['I106']); self.assertTrue(results['I107'])

    def test_I106_I107_baska_proje_istisna_degildir(self):
        from .test_karar99 import ek_erisim_duzenegi
        from irp.degismezler_v10 import denetle
        f,d,n=ek_erisim_duzenegi()
        oid=surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        # Denetleyicinin hatalı saklanmış kaydı da bulduğunu sınar.
        d._kayitlar[oid]['neyin_ustunde'].append(dict(tur='PROJE',kimlik='2509084',surum=1))
        results=denetle(d,True)
        self.assertFalse(results['I106']); self.assertFalse(results['I107'])

    def test_I106_I107_baska_sorumlu_istisna_degildir(self):
        from .test_karar99 import ek_erisim_duzenegi
        from irp.degismezler_v10 import denetle
        f,d,n=ek_erisim_duzenegi()
        oid=surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        d._kayitlar[oid]['kim']='K044'
        results=denetle(d,True)
        self.assertFalse(results['I106']); self.assertFalse(results['I107'])


class OnayGoreviMaliyeti(unittest.TestCase):
    """C59: Karar 12, T4 A14 ve T9 §8; onay saati yalnız onaylayana aittir."""
    def setUp(self):
        self.f=Duzenek(); self.d=kur(self.f,t(22,'08:00'))
        gonder(self.f,self.d,'K001','GUN_ONAYI.AYARLADIM',t(22,'08:01'),dict(birim='IMALAT',gerekli=True,gecerli_baslangic='2026-10-22'))
        self.g=gonder(self.f,self.d,'K012','GOREV.ATADIM',t(22,'08:02'),dict(gorevler=[self.f.gorev_satiri(zaman_degeri=10,onay_gerekli=True,onaylayan='K012',teslim_tarihi='2026-10-22')]))+'/1'
        gonder(self.f,self.d,'K041','GOREV.KABUL_ETTIM',t(22,'08:03'),h=self.g)
        gonder(self.f,self.d,'K041','GOREV.TAMAMLADIM',t(22,'09:00'),h=self.g)
        gonder(self.f,self.d,'K012','GOREV.ONAYLADIM',t(22,'09:01'),h=self.g)
        self.o=next(g for g in self.d.gorevler.values() if g['tur']=='ONAY')

    def test_onay_payi_baska_kisiye_yazilmaz(self):
        from irp.gorunumler import gorev_payi
        for yuk in (False,True):
            self.assertEqual(gorev_payi(self.d,self.o,'2026-10-22','2026-10-22',yuk=yuk,kisi='K009'),0)
            self.assertEqual(gorev_payi(self.d,self.o,'2026-10-22','2026-10-22',yuk=yuk,kisi='K012'),1)

    def test_gorevsiz_kiside_onay_bekleyen_tutar_sifir(self):
        from irp.gorunumler import maas_dagilimi
        v=maas_dagilimi(self.d,'K009','2026-10-01')
        self.assertEqual(v['tutarlar'],{})
        self.assertEqual(v['onay_bekleyen'],Decimal('0.00'))

class ModulGirdiKapilari(unittest.TestCase):
    """T10 §3.2: geçersiz istek tabloya ve günlüğe dokunmaz."""
    def setUp(self): self.f,self.d=modul_duzenegi()
    def reddet(self, expected='BICIM', **changes):
        self.d.ilerlet(t(22,'10:00')); before=deepcopy((dict(self.d.olaylar),self.d.modul_bildirimleri))
        args=dict(servis_kimligi='SRV-M3',modul='M3',kural='SATINALMA',kayit=dict(tur='IS',kimlik=is_id(4)),
                  alicilar=[dict(tur='KISI',kimlik='K017')],metin='Gecikme',onem='UYARI',an=t(22,'10:00'))
        args.update(changes); r=self.d.modul_bildirimi_birak(**args)
        self.assertEqual(r.get('kod'),expected)
        self.assertEqual((dict(self.d.olaylar),self.d.modul_bildirimleri),before)
        self.assertFalse(self.d.isleme_hatalari)

    def test_kayit_yok_durum(self): self.reddet('DURUM',kayit=dict(tur='IS',kimlik='yok'))
    def test_zaman_gelecekte_bicim(self): self.reddet(an='2026-10-22T10:00:01+03:00')
    def test_bos_cozum_kayit_uretmez(self):
        r=birak(self.d,t(22,'10:00'),alicilar=[dict(tur='KISI',kimlik='K999')])
        self.assertEqual((r['alicilar'],r['yeni'],r['guncellenen'],r['alici_kalmadi']),([],0,0,True))
        self.assertEqual(self.d.modul_bildirimleri,{})
    def test_farkli_kural_ayri_tekillik(self):
        a=birak(self.d,t(22,'10:00'),kural='A'); b=birak(self.d,t(22,'10:00'),kural='B')
        self.assertEqual((a['yeni'],b['yeni'],len(self.d.modul_bildirimleri)),(2,2,4))
    def test_olmayan_kurali_kaldirmak_digerini_korur(self):
        birak(self.d,t(22,'10:00')); before=deepcopy(self.d.modul_bildirimleri)
        r=self.d.modul_bildirimi_kaldir('SRV-M3','M3','BASKA',dict(tur='IS',kimlik=is_id(4)),t(22,'10:00'))
        self.assertEqual(r['kaldirilan'],0); self.assertEqual(self.d.modul_bildirimleri,before)
    def test_kutu_kopyasi_kalici_kaydi_degistirmez(self):
        birak(self.d,t(22,'10:00')); rows=bildirim_kutusu(self.d,'K009',cagiran='K009')
        rows[0]['metin']='değiştirildi'; self.assertNotEqual(bildirim_kutusu(self.d,'K009')[0]['metin'],'değiştirildi')
    def test_kutu_baskasina_kapali(self):
        with self.assertRaises(PermissionError): bildirim_kutusu(self.d,'K009',cagiran='K001')


def bad_module_case(changes):
    def test(self): self.reddet(**changes)
    return test


for name, changes in {
    'bos_kural':dict(kural=' '), 'kayit_dizi':dict(kayit=[]),
    'kayit_turu':dict(kayit=dict(tur='DOSYA',kimlik='F1')),
    'kayit_kimligi_bos':dict(kayit=dict(tur='IS',kimlik=' ')),
    'modul_kaydi_sayi':dict(kayit=dict(tur='IS',kimlik=is_id(4),modul_kaydi=12)),
    'zaman_gecersiz':dict(an='tarih-degil'), 'bos_metin':dict(metin=' \t'),
    'onem_gecersiz':dict(onem='ACIL'), 'alicilar_bos':dict(alicilar=[]),
    'alicilar_nesne':dict(alicilar={}), 'alici_metin':dict(alicilar=['K017']),
    'alici_kimlik_yok':dict(alicilar=[dict(tur='KISI')]),
    'alici_turu_yanlis':dict(alicilar=[dict(tur='FIRMA',kimlik='K017')]),
}.items(): setattr(ModulGirdiKapilari,'test_bicim_'+name,bad_module_case(changes))


class Sinirlar(unittest.TestCase):
    def test_mesai_damgasi_yedi_gun_tam_sinir_ve_bir_saniye(self):
        """T8 §3.1: en çok yedi gün; eşitlik kabul, bir saniye fazlası ret."""
        from .test_v7 import mesai_f
        for saat,bek in [('18:00:00','BASARILI'),('18:00:01','DURUM')]:
            with self.subTest(saat=saat):
                f=mesai_f(False); d=kur(f,t(22,'20:30'))
                gonder(f,d,'K009','EK_MESAI.ONAYLADIM',t(29,saat),
                       dict(kisi='K017',tarih='2026-10-22',baslangic='18:00',bitis='19:00',aciklama='Sevkiyat'),4,bek=bek)

    def test_ay_sinirlari_subat_artik_yil_ve_aralik(self):
        """T4 ay kapanışı: takvim ayının ilk ve son günü, ikisi de dahil."""
        from irp.gorunumler import ay_sinirlari
        for bas,bit in [('2024-02-01','2024-02-29'),('2026-02-01','2026-02-28'),('2026-12-01','2026-12-31')]:
            self.assertEqual(tuple(str(x) for x in ay_sinirlari(bas)),(bas,bit))

    def test_para_yarim_kurus_yukari(self):
        """T4 para: iki ondalık; yarım kuruş yukarı."""
        self.assertEqual(para(Decimal('1.005')),Decimal('1.01'))
        self.assertEqual(para(Decimal('1.004999')),Decimal('1.00'))
        self.assertEqual(para(Decimal('1.015')),Decimal('1.02'))
    def test_sapma_tam_plan_sinirinda_yok(self):
        d=Depo(Saat(t(22,'11:00'))); p,q=an(t(22,'10:00')),an(t(22,'11:00'))
        self.assertIsNone(sapma(d,'ACIK',p,q,p,None))
        d.ilerlet('2026-10-22T11:00:00.000001+03:00')
        self.assertEqual(sapma(d,'ACIK',p,q,p,None),dict(tur='GERIDE'))
    def test_pencere_esit_ve_ters_uc_reddedilir(self):
        for a,b in [(t(22),t(22)),(t(23),t(22))]:
            with self.assertRaises(ValueError): pencere(a,b)
        self.assertEqual(pencere('2026-10-22'),(an(t(22,'00:00')),an(t(23,'00:00'))))
    def test_sessiz_kabul_tatil_atlar_saat_esigi_dahil(self):
        """Karar 92: 26 Pazartesi 11:00 + üç iş günü = 30 Cuma 11:00 (29 tatil)."""
        f,d,g,e=gecikme_duzenegi(); x=d.sorumluluklar[e+'/1']
        d.ilerlet('2026-10-30T10:59:59+03:00'); self.assertFalse(etkin_pay(d,x))
        d.ilerlet(t(30,'11:00')); self.assertTrue(etkin_pay(d,x))
        self.assertFalse(x['dogrulandi']); self.assertFalse(x.get('gecmis'))


class SartnameKopru(unittest.TestCase):
    def test_modul_kullanici_oturumu_ve_aktarim_kapisi(self):
        """Karar 72/87, T8 §12: modül aynı olay kapısını kullanır."""
        from irp.gorunum_v7 import modul_yaz
        f,d,n,g=belge_duzenegi(); d.ilerlet(t(22,'10:00'))
        f.olay('K041','NOT.YAZDIM',t(22,'10:00'),[dict(tur='GOREV',kimlik=g)],dict(metin='Modül notu'))
        e=deepcopy(f.olaylar[-1]); count=len(d.olaylar)
        self.assertEqual(modul_yaz(d,'K044',e)['kod'],'YETKI')
        self.assertEqual(modul_yaz(d,'K041',dict(e,giris_sekli='AKTARIM'))['kod'],'YETKI')
        self.assertEqual(len(d.olaylar),count)
        self.assertEqual(modul_yaz(d,'K041',e)['sonuc'],'BASARILI')
        self.assertEqual(d.notlar[e['olay_kimligi']]['metin'],'Modül notu')

    def test_ortak_proje_kodu_degisse_nesne_bagi_kalir(self):
        """N:P0076, karar 72/77: modüller arası bağ değişmez kimliktedir."""
        f,d,n,g=belge_duzenegi()
        gonder(f,d,'K001','PROJE.KOD_DEGISTIRDIM',t(22,'10:00'),dict(kod='2610123',gerekce='Yeni kod'),'2509084','PROJE')
        self.assertEqual(oku(d,'K012','NESNE',n)['proje'],'2509084')
        self.assertEqual(oku(d,'K012','PROJE','2509084')['kod'],'2610123')
        self.assertEqual(d.gorevler[g]['proje'],'2509084')
    def test_kanitlar_nesne_olay_ve_dosyaya_baglanir(self):
        """T2 §2/4: kanıt biçimden bağımsız kimlik ve parmak izi taşır."""
        f,d,n,g=belge_duzenegi()
        fs=[dict(dosya_kimligi='KP-'+suffix,parmak_izi='sha-'+suffix) for suffix in ('foto','pdf','xlsx','cad','video')]
        e=gonder(f,d,'K041','NOT.YAZDIM',t(22,'10:00'),dict(metin='Ölçüm kanıtı'),[dict(tur='GOREV',kimlik=g),dict(tur='NESNE',kimlik=n)],kanit=fs)
        self.assertEqual(d.notlar[e]['kanit'],fs)
        for x in fs:
            self.assertEqual(d.dosyalar[x['dosya_kimligi']]['doguran_olay'],e)
            self.assertEqual(d.dosyalar[x['dosya_kimligi']]['parmak_izi'],x['parmak_izi'])
        self.assertEqual(d.olay_nesneleri[e],[('GOREV',g),('NESNE',n)])
    def test_calisan_ust_ve_yabanci_kisisel_erisimi(self):
        """Karar 63/T8 §1: kendi kişi kaydı ve üst zinciri, parasalda YETKILI."""
        d=kur(Duzenek(),t(22,'10:00'))
        for kim,expected in [('K041',True),('K012',True),('K001',True),('K044',False),('K007',False)]:
            self.assertEqual(gorebilir_mi(d,kim,'PERFORMANS','K041'),expected)
        for kim in ('K041','K012','K044','K007'):
            with self.assertRaises(PermissionError): oku(d,kim,'SAAT_MALIYETI','K041',gun='2026-10-22')
        self.assertEqual(oku(d,'K001','SAAT_MALIYETI','K041',gun='2026-10-22'),Decimal('111.1111111111111111111111111'))
