"""Yeni bolgede kesisimler ve I59-I66 degismezleri."""
import unittest
from copy import deepcopy
from irp import Depo, Saat, an
from irp.degismezler_v5 import denetle
from irp.gorunumler import kisinin_gunu, yuk, kapasite, etap_gostergesi
from irp.is_ import emek
from .ortak import Duzenek, t, is_id
from .v5_destek import gonder, onaysiz_bekleme, kurulum_paketi, sifirdan, is_satiri
from .test_v5 import bitir
from .tur2_ornekler import iki_kisi


class KenarlarV5(unittest.TestCase):
    def test_ayrilmis_aliciya_not_gorevi_dogmaz(self):
        f,d,i,g=sifirdan()
        gonder(f,d,'K009','AYAR.YONLENDIRDIM',t(2,'11:10'),girdiler={'birim':'IMALAT','kisiler':['K017']})
        gonder(f,d,'K017','MESAI.CIKTIM',t(2,'11:11'))
        gonder(f,d,'K001','KISI.AYRILDI',t(2,'11:12'),girdiler={'kisi':'K017','ayrilis_tarihi':'2026-10-02'},bek='DURUM')
        gonder(f,d,'K009','AYAR.YONLENDIRDIM',t(2,'11:13'),girdiler={'birim':'IMALAT','kisiler':[]})
        gonder(f,d,'K001','KISI.AYRILDI',t(2,'11:14'),girdiler={'kisi':'K017','ayrilis_tarihi':'2026-10-02'})
        e,_=gonder(f,d,'K004','NOT.YAZDIM',t(5,'09:00'),'2509084',{'metin':'Olcu sorusu','etiketler':['IMALAT']},tur='PROJE')
        self.assertNotIn(e+'/1',d.gorevler)
        self.assertNotIn('atlanan_alicilar',d.notlar[e])

    def test_is_degistirme_yeni_etap_ve_tezgah_kapilari(self):
        f,d,i=onaysiz_bekleme()
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(22,'08:02'),i,{'degisenler':{'etap':'YOK'}},bek='BICIM')
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(22,'08:03'),i,{'degisenler':{'tezgah':'YOK'}},bek='DURUM')
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(22,'08:04'),i,{'degisenler':{'tezgah':'CNC-02','tezgah_rolu':'BASLAT'}})
        self.assertEqual(d.isler[i]['tezgah'],'CNC-02')

    def test_yeni_alanlarda_bozuk_bicim_red(self):
        f,d,i=onaysiz_bekleme()
        for degisiklik in ([], {'tahmini_sure_dk':-1}, {'onay_beklet':1}):
            gonder(f,d,'K009','IS.DEGISTIRDIM',t(22,'08:02'),i,{'degisenler':degisiklik},bek='BICIM')
        gonder(f,d,'K001','AYAR.MAAS_PAYDASI',t(22,'08:03'),girdiler={'deger':0,'gecerli_baslangic':'2026-11-01'},bek='BICIM')
        gonder(f,d,'K001','AYAR.PARCA_KODU_DESENI',t(22,'08:04'),girdiler={'deger':'['},bek='BICIM')

    def test_onay_ertesi_gun_kisiyi_bekletmez(self):
        f,d,i=onaysiz_bekleme(); bitir(f,d,i,'09:00')
        gonder(f,d,'K017','MESAI.CIKTIM',t(22,'17:00'))
        gonder(f,d,'K017','MESAI.GIRDIM',t(23,'07:58'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'CALISMIYOR')
        gonder(f,d,'K017','IS.BASLADIM',t(23,'08:00'),2)
        gonder(f,d,'K009','IS.ONAYLADIM',t(23,'08:10'),i)
        self.assertEqual(d.kisi_durumu['K017']['acik_is'],is_id(2))

    def test_beklemesiz_elle_bitis_aktif_isi_kapatir(self):
        f,d,i=onaysiz_bekleme()
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(22,'11:00'),i,{'baslangic':t(22,'08:00'),'bitis':t(22,'09:00'),'aciklama':'Saha teyidi','is_bitti':True},adina='K017',giris_sekli='ELLE')
        self.assertEqual(d.isler[i]['tamamlayan'],'K017')
        self.assertEqual(d.isler[i]['onay_bekleme_ani'],an(t(22,'09:00')))
        self.assertEqual(d.listeler['K017'],[is_id(2)])
        self.assertEqual(emek(d,i),60)
        self.assertNotIn('BEKLEME_ONAY',kisinin_gunu(d,'K017','2026-10-22')['kovalar'])

    def test_elle_bitis_baska_aktif_isi_durdurmaz(self):
        f,d,i=onaysiz_bekleme()
        gonder(f,d,'K009','IS.SIRALADIM',t(22,'08:30'),2,{'kisi':'K017','yeni_sira':1})
        gonder(f,d,'K017','IS.BASLADIM',t(22,'08:35'),2)
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(22,'09:30'),i,{'baslangic':t(22,'08:00'),'bitis':t(22,'09:00'),'aciklama':'Eski is fiziksel bitti','is_bitti':True},adina='K017',giris_sekli='ELLE')
        self.assertEqual(d.kisi_durumu['K017']['acik_is'],is_id(2))
        self.assertEqual(d.isler[i]['durum'],'ONAY_BEKLIYOR')

    def test_ret_sabit_molada_baska_isi_bolmez(self):
        f,d,i=onaysiz_bekleme(); bitir(f,d,i,'09:00')
        gonder(f,d,'K017','IS.BASLADIM',t(22,'09:02'),2)
        gonder(f,d,'K009','IS.REDDETTIM',t(22,'10:05'),i,{'not':'Duzelt'})
        self.assertEqual(d.kisi_durumu['K017']['durum'],'SABIT_MOLADA')
        self.assertEqual(d.listeler['K017'],[is_id(2),i])
        d.ilerlet(t(22,'10:16'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'DEVAM_BEKLIYOR')
        self.assertEqual(d.kisi_durumu['K017']['acik_is'],is_id(2))

    def test_beklemesiz_onayda_devir_kapali(self):
        f,d,i=onaysiz_bekleme(); bitir(f,d,i,'09:00')
        gonder(f,d,'K009','IS.DEVRETTIM',t(22,'09:05'),i,{'kimden':'K017','kime':'K023'},bek='DURUM')
        self.assertEqual(d.isler[i]['tamamlayan'],'K017')

    def test_iptal_sabit_mola_sonunda_aktif_isi_acmaz(self):
        f,d,i=onaysiz_bekleme()
        gonder(f,d,'K009','IS.IPTAL_ETTIM',t(22,'10:05'),i,{'gerekce':'Iptal'})
        d.ilerlet(t(22,'10:20'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'CALISMIYOR')
        self.assertIsNone(d.kisi_durumu['K017']['acik_is'])
        self.assertEqual(emek(d,i),120)

    def test_iptal_onay_bekleyen_kisiyi_acar(self):
        f=Duzenek(); f.ata(9); f.ata(2,sira=2); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=f.calistir(t(22,'09:01'))
        gonder(f,d,'K009','IS.IPTAL_ETTIM',t(22,'09:10'),9,{'gerekce':'Iptal'})
        self.assertEqual(d.kisi_durumu['K017']['durum'],'CALISMIYOR')
        self.assertEqual(d.listeler['K017'],[is_id(2)])

    def test_ana_iptali_acik_alt_isleri_kapatir(self):
        f,i=iki_kisi(); f.olaylar=[e for e in f.olaylar if an(e['oldugu_an'])<=an(t(22,'09:00'))]
        d=f.calistir(t(22,'09:00'))
        gonder(f,d,'K009','IS.IPTAL_ETTIM',t(22,'09:00'),i,{'gerekce':'Ana is iptal'})
        for h in (i,i+'/k1',i+'/k2'): self.assertEqual(d.isler[h]['durum'],'IPTAL')
        for k in ('K017','K023'): self.assertFalse(d.listeler[k]); self.assertEqual(d.kisi_durumu[k]['durum'],'CALISMIYOR')

    def test_iptal_onkosul_gorevi_acar(self):
        f=Duzenek(); p=f.gorev_ata(t(21,'09:00')); q=f.gorev_ata(t(21,'09:01'),kisi='K044',on_kosul=[p]); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),q,'K044'); d=f.calistir(t(22,'08:10'))
        self.assertEqual(d.gorevler[q]['durum'],'ON_IS_BEKLIYOR')
        gonder(f,d,'K012','GOREV.IPTAL_ETTIM',t(22,'08:20'),p)
        self.assertEqual(d.gorevler[q]['durum'],'ACIK')

    def test_iptal_isi_taniklik_acamaz(self):
        f,d,i=onaysiz_bekleme(); gonder(f,d,'K009','IS.IPTAL_ETTIM',t(22,'08:20'),i,{'gerekce':'Iptal'})
        e,_=gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'08:30'),i)
        self.assertEqual(d.isler[i]['durum'],'IPTAL'); self.assertIn(e,d.supheliler)

    def test_ayrilisi_kayitli_kisiye_devir_ve_gorev_yok(self):
        f=Duzenek(); f.ata(1); d=f.calistir(t(22,'08:00'))
        gonder(f,d,'K001','KISI.AYRILDI',t(22,'08:00'),girdiler={'kisi':'K023','ayrilis_tarihi':'2026-10-30'})
        gonder(f,d,'K009','IS.DEVRETTIM',t(22,'08:01'),1,{'kimden':'K017','kime':'K023'},bek='DURUM')
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'08:02'),girdiler={'gorevler':[f.gorev_satiri(kisi='K023')]},bek='DURUM')
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'08:03'),girdiler={'gorevler':[f.gorev_satiri(onay_gerekli=True,onaylayan='K023')]},bek='DURUM')

    def test_kurulum_atomik_tek_sefer_ve_aktarim_kapali(self):
        f=Duzenek(False); paket=kurulum_paketi(f); d=Depo(Saat(t(1,'07:00')))
        bozuk=deepcopy(paket)
        [e for e in bozuk if e['eylem_kodu']=='BIRIM.TANIMLADIM'][-1]['girdiler']['basi']='K999'
        self.assertEqual(d.kurulum(bozuk,{},servis=True)['kod'],'DURUM'); self.assertFalse(d.olaylar)
        self.assertEqual(d.kurulum(paket,{},servis=False)['kod'],'YETKI')
        self.assertEqual(d.kurulum(paket,{},servis=True)['sonuc'],'BASARILI')
        self.assertEqual(d.kurulum(paket,{},servis=True)['kod'],'DURUM')
        self.assertEqual(d.olay_ekle(paket[0],servis=True)['kod'],'YETKI')

    def test_ana_veri_guncelleme_baglantiyi_korur(self):
        f,d,i,g=sifirdan()
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(2,'11:10'),girdiler={'kisi':'K017','gecerli_baslangic':t(2,'11:10'),'degisenler':{'birim':'YOK'}},bek='DURUM')
        gonder(f,d,'K004','ETAP.DEGISTIRDIM',t(2,'11:11'),f.etap['E-IML'],{'degisenler':{'birim':'MEK_TASARIM'}},tur='ETAP',bek='DURUM')
        self.assertEqual(d.kisiler['K017']['birim'],'IMALAT')

    def test_teslimsiz_yuk_yeni_takvime_sigar(self):
        f=Duzenek(); f.ata(4); d=f.calistir(t(26,'09:00'))
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(26,'09:00'),4,{'degisenler':{'tahmini_sure_dk':1200}})
        gonder(f,d,'K001','TAKVIM.TANIMLADIM',t(26,'09:01'),girdiler=dict(d.varsayilan_takvim,mesai_bitis='17:00'))
        self.assertEqual([yuk(d,'K017','2026-10-%02d'%n,'2026-10-%02d'%n) for n in (26,27,28)],[9,8,3])

    def test_I59_beklemesiz_onay(self):
        f,d,i=onaysiz_bekleme(); bitir(f,d,i,'09:00'); self.assertTrue(denetle(d)['I59'])
        d.araliklar.append({'kova':'BEKLEME_ONAY','is':i,'baslangic':an(t(22,'09:00'))})
        self.assertFalse(denetle(d)['I59'])

    def test_I60_iptal_listede_degil(self):
        f,d,i=onaysiz_bekleme(); gonder(f,d,'K009','IS.IPTAL_ETTIM',t(22,'09:00'),i,{'gerekce':'Iptal'})
        self.assertTrue(denetle(d)['I60']); d.listeler['K017'].append(i); self.assertFalse(denetle(d)['I60'])

    def test_I61_ayrilis_sonrasi_olay_yok(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); gonder(f,d,'K001','KISI.AYRILDI',t(22,'09:00'),girdiler={'kisi':'K023','ayrilis_tarihi':'2026-10-22'})
        e,_=gonder(f,d,'K023','MESAI.GIRDIM',t(23,'08:00'),bek='YETKI')
        self.assertNotIn(e,d.olaylar); self.assertTrue(denetle(d)['I61'])

    def test_I62_normal_yol_basvurulari(self):
        f,d,i,g=sifirdan(); self.assertTrue(denetle(d)['I62'])
        d.birimler['YONETIM']['ust_birim']='IMALAT'; self.assertFalse(denetle(d)['I62'])

    def test_I63_onay_listeden_ayri(self):
        f,d,i=onaysiz_bekleme(); bitir(f,d,i,'09:00'); self.assertTrue(denetle(d)['I63'])
        d.listeler['K017'].append(i); self.assertFalse(denetle(d)['I63'])

    def test_I64_kapali_projede_acik_nesne_yok(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); gonder(f,d,'K001','PROJE.KAPATTIM',t(22,'09:00'),'2509091',tur='PROJE')
        self.assertTrue(denetle(d)['I64']); d.projeler['2509084']['aktif']=False; self.assertFalse(denetle(d)['I64'])

    def test_I65_tek_liste_sahipligi(self):
        f,d,i=onaysiz_bekleme(); self.assertTrue(denetle(d)['I65'])
        d.listeler['K023']=[i]; self.assertFalse(denetle(d)['I65'])

    def test_I66_kurulum_sonrasi_aktarim_yok(self):
        f,d,i,g=sifirdan(); self.assertTrue(denetle(d)['I66'])
        e=deepcopy(next(iter(d.olaylar.values()))); e['olay_kimligi']='K001-2610029999-M'; e['oldugu_an']=t(2,'12:00')
        self.assertEqual(d.olay_ekle(e,servis=True)['kod'],'YETKI'); self.assertNotIn(e['olay_kimligi'],d.olaylar)
