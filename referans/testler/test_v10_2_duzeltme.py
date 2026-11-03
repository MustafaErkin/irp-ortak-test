"""Karar 112–113: Y113/Y113b/Y114 ve takvim sınırları."""
import unittest
from copy import deepcopy
from irp import an
from irp.gorunum_v7 import oku, tezgah_gostergesi, tezgah_uygun_mu
from irp.gorunum_v9 import gecikme_raporu
from .ortak import Duzenek, t, is_id
from .test_v7 import kur, gonder
from .test_v10_1 import ek_yetki, tarih, plan


def gorev_duzenegi(teslim=None):
    f=ek_yetki(Duzenek()); d=kur(f,t(22,'08:50'))
    g=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),dict(gorevler=[f.gorev_satiri(
        ad='Ölçü listesi',kisi='K041',teslim_tarihi='2026-10-23',zaman_degeri=2,onay_gerekli=False)]))+'/1'
    gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'09:10'),h=g)
    if teslim: gonder(f,d,'K041','GOREV.TAMAMLADIM',teslim,h=g)
    return f,d,g


def tezgah_duzenegi(ikinci=True):
    f=ek_yetki(Duzenek()); f.ata(8,'K017'); f.ata(7,'K023'); d=kur(f,t(23,'08:00'))
    tarih(f,d,[plan(8,t(24,'09:00'),t(24,'15:00'))],t(23,'08:30'))
    ids=[]
    for kisi,n,saat in [('K017',8,'09:00')]+([('K023',7,'09:01')] if ikinci else []):
        ids.append(gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(23,saat),dict(kisi=kisi,tarih='2026-10-24',
            baslangic=t(24,'09:00'),bitis=t(24,'15:00'),aciklama='Cumartesi imalat'),n,'IS'))
    return f,d,ids


def gantt_satiri(d,kimlik):
    return next(x for x in oku(d,'K001','GANTT','2509084',bas='2026-10-22',bit='2026-10-31') if x['kimlik']==kimlik)


class SenaryolarV10_2Duzeltme(unittest.TestCase):
    def test_Y113(self):
        _,d,g=gorev_duzenegi(t(26,'12:30'))
        # Oku çağrısı burada da görünür: cevap anahtarı dış kapı sözleşmesini kaydeder.
        row=next(x for x in oku(d,'K001','GANTT','2509084',bas='2026-10-22',bit='2026-10-26') if x['kimlik']==g)
        self.assertEqual((row['gecikme_takvim_dk'],row['gecikme_mesai_dk']),(3990,225))
        r=gecikme_raporu(d,'2026-10-22','2026-10-26',cagiran='K001')[0]
        self.assertEqual((r['gecikme_takvim_dk'],r['gecikme_mesai_dk']),(3990,225))
        self.assertEqual((r['gec_teslim'],r['zaman_degeri']),(1,2))

    def test_Y113b(self):
        _,d,g=gorev_duzenegi(t(26,'08:00'))
        row=next(x for x in oku(d,'K001','GANTT','2509084',bas='2026-10-22',bit='2026-10-26') if x['kimlik']==g)
        self.assertEqual((row['gecikme_takvim_dk'],row['gecikme_mesai_dk']),(3720,0))
        r=gecikme_raporu(d,'2026-10-22','2026-10-26',cagiran='K001')[0]
        self.assertEqual((r['gecikme_takvim_dk'],r['gecikme_mesai_dk']),(3720,0))

    def test_Y114(self):
        _,d,_=tezgah_duzenegi()
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],6)
        self.assertTrue(oku(d,'K001','TEZGAH_UYGUNLUK','CNC-02',bas=t(24,'10:00'),bit=t(24,'11:00'))['uygun'])
        self.assertEqual(oku(d,'K001','TEZGAH_GOSTERGESI','CNC-02',bas='2026-10-25')['planli_kullanilabilir'],0)
        r=oku(d,'K006','KAYNAK_YUKU','CNC-02',tur='TEZGAH',bas='2026-10-24',kapasite_dahil=True)
        self.assertEqual(r['planli_kullanilabilir'],6)
        self.assertEqual(r['satirlar'],oku(d,'K006','KAYNAK_YUKU','CNC-02',tur='TEZGAH',bas='2026-10-24'))
        self.assertEqual(oku(d,'K006','TAKVIM','CNC-02',tur='TEZGAH',bas='2026-10-24')['calisma'],[dict(bas=an(t(24,'09:00')),bit=an(t(24,'15:00')))])


class TakvimSinirlariV10_2(unittest.TestCase):
    def test_gecikme_acik_gorev_ve_okuma_saklanan_hali_degistirmez(self):
        _,d,g=gorev_duzenegi(); d.ilerlet(t(26,'12:30'))
        once=deepcopy(d.son_hal())
        row=gantt_satiri(d,g)
        self.assertEqual((row['gecikme_takvim_dk'],row['gecikme_mesai_dk']),(3990,225))
        self.assertEqual(d.son_hal(),once)

    def test_gecikme_erken_teslim_ve_iptal(self):
        _,d,g=gorev_duzenegi(t(23,'12:00'))
        self.assertEqual((gantt_satiri(d,g)['gecikme_takvim_dk'],gantt_satiri(d,g)['gecikme_mesai_dk']),(0,0))
        f,d,g=gorev_duzenegi(); gonder(f,d,'K012','GOREV.IPTAL_ETTIM',t(23,'12:00'),h=g)
        d.ilerlet(t(26,'12:30'))
        self.assertIsNone(gantt_satiri(d,g)['gecikme_mesai_dk'])

    def test_gecikme_izin_ve_ek_mesai(self):
        f,d,g=gorev_duzenegi()
        gonder(f,d,'K012','EK_MESAI.PLANLADIM',t(22,'10:00'),dict(kisi='K041',tarih='2026-10-24',baslangic=t(24,'09:00'),bitis=t(24,'10:00'),aciklama='Ek çizim'),g,'GOREV')
        izin=gonder(f,d,'K041','IZIN.TALEP_ETTIM',t(22,'10:10'),dict(kisi='K041',tur='YILLIK',baslangic=t(26),bitis=t(26,'09:00'),gerekce='İzin'))
        gonder(f,d,'K012','IZIN.ONAYLADIM',t(22,'10:11'),dict(hedef=izin))
        gonder(f,d,'K041','GOREV.TAMAMLADIM',t(26,'12:30'),h=g)
        self.assertEqual(gantt_satiri(d,g)['gecikme_mesai_dk'],225)  # 225 - 60 izin + 60 ek mesai.

    def test_gecikme_tatil_ve_havuz_birim_takvimi(self):
        f,d,g=gorev_duzenegi()
        gonder(f,d,'K001','GUN.TANIMLADIM',t(22,'10:00'),dict(tarih='2026-10-26',tur='TATIL',ad='Tatil'))
        gonder(f,d,'K041','GOREV.TAMAMLADIM',t(26,'12:30'),h=g)
        self.assertEqual(gantt_satiri(d,g)['gecikme_mesai_dk'],0)
        f=ek_yetki(Duzenek()); d=kur(f,t(23,'08:00'))
        tarih(f,d,[plan(1,t(23,'08:00'),t(23,'18:00'))],t(23,'08:10'))
        d.ilerlet(t(26,'12:30'))
        self.assertIsNone(d.isler[is_id(1)]['kisi'])
        self.assertEqual(gantt_satiri(d,is_id(1))['gecikme_mesai_dk'],225)

    def test_tezgah_bakim_ve_plansiz_durus(self):
        f,d,_=tezgah_duzenegi()
        gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(23,'10:00'),dict(tezgah='CNC-02',baslangic=t(24,'11:00'),bitis=t(24,'12:00'),aciklama='Yağlama'))
        gonder(f,d,'K017','TEZGAH.DURUS_BILDIRDIM',t(24,'09:00'),dict(tezgah='CNC-02',neden='ARIZA'))
        gonder(f,d,'K017','TEZGAH.DURUS_BITTI',t(24,'10:00'),dict(tezgah='CNC-02'))
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],5)
        self.assertEqual(tezgah_uygun_mu(d,'CNC-02',t(24,'11:00'),t(24,'12:00')),dict(uygun=False,neden='bakim'))
        self.assertEqual(tezgah_uygun_mu(d,'CNC-02',t(24,'09:00'),t(24,'10:00')),dict(uygun=False,neden='durus'))

    def test_tezgah_iptal_ve_an_penceresi(self):
        f,d,ids=tezgah_duzenegi()
        self.assertEqual(oku(d,'K006','TEZGAH_GOSTERGESI','CNC-02',bas=t(24,'10:00'),bit=t(24,'11:00'))['planli_kullanilabilir'],1)
        for i,hedef in enumerate(ids):
            gonder(f,d,'K009','EK_MESAI.IPTAL_ETTIM',t(23,'10:0'+str(i)),dict(hedef=hedef))
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],0)
        self.assertFalse(tezgah_uygun_mu(d,'CNC-02',t(24,'10:00'),t(24,'11:00'))['uygun'])

    def test_tezgah_vardiya_ortusmesi_ve_gece_yarisi(self):
        f,d,_=tezgah_duzenegi(False)
        gonder(f,d,'K009','TEZGAH.TAKVIM_TANIMLADIM',t(23,'10:00'),dict(tezgah='CNC-02',gecerli_baslangic='2026-10-24',vardiyalar=[dict(gunler=[6],bas='08:00',bit='12:00')]))
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],7)
        gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(23,'10:10'),dict(kisi='K017',tarih='2026-10-24',baslangic=t(24,'22:00'),bitis=t(25,'02:00'),aciklama='Gece'),8,'IS')
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-25')['planli_kullanilabilir'],11)
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-25','2026-10-25')['planli_kullanilabilir'],2)

    def test_tezgah_bos_yuk_ve_kapasite_okumasi_salt_okunur(self):
        _,d,_=tezgah_duzenegi()
        once=deepcopy(d.son_hal())
        r=oku(d,'K006','KAYNAK_YUKU','CNC-02',tur='TEZGAH',bas='2026-10-25',kapasite_dahil=True)
        self.assertEqual(r,dict(satirlar=[],planli_kullanilabilir=0))
        with self.assertRaisesRegex(ValueError,'TEZGAH'):
            oku(d,'K006','KAYNAK_YUKU','K017',tur='KISI',bas='2026-10-24',kapasite_dahil=True)
        self.assertEqual(d.son_hal(),once)

    def test_atanmis_is_gecikmesinde_kisinin_izni_dusulur(self):
        f=ek_yetki(Duzenek()); f.ata(1); d=kur(f,t(23,'08:00'))
        tarih(f,d,[plan(1,t(23,'08:00'),t(23,'18:00'))],t(23,'08:10'))
        izin=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(23,'09:00'),dict(kisi='K017',tur='YILLIK',baslangic=t(26),bitis=t(26,'09:00'),gerekce='İzin'))
        gonder(f,d,'K009','IZIN.ONAYLADIM',t(23,'09:01'),dict(hedef=izin))
        d.ilerlet(t(26,'12:30'))
        self.assertEqual(gantt_satiri(d,is_id(1))['gecikme_mesai_dk'],165)

    def test_tezgah_gerceklesen_damgasi_ve_tezgahsiz_is(self):
        f=Duzenek(); f.ata(8); f.ata(1,'K023'); d=kur(f,t(23,'08:00'))
        gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(23,'09:00'),dict(kisi='K023',tarih='2026-10-24',baslangic=t(24,'09:00'),bitis=t(24,'15:00'),aciklama='Elle iş'),1,'IS')
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],0)
        gonder(f,d,'K009','EK_MESAI.ONAYLADIM',t(26,'09:00'),dict(kisi='K017',tarih='2026-10-24',baslangic=t(24,'09:00'),bitis=t(24,'15:00'),aciklama='Gerçekleşen'),8,'IS')
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],6)

    def test_atama_icindeki_ek_mesai_tezgah_kapasitesine_girer(self):
        f=Duzenek(); f.ata(8)
        f.olaylar[-1]['girdiler']['ek_mesai']=dict(tarih='2026-10-24',baslangic=t(24,'09:00'),bitis=t(24,'15:00'),aciklama='Atamayla plan')
        d=kur(f,t(23,'08:00'))
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-24','2026-10-24')['planli_kullanilabilir'],6)
