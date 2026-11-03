"""Y98–Y99: karar 91–92, belge beklentileri ve gerçek kabul yolu."""
import unittest
from copy import deepcopy
from irp import an
from irp.gorunumler import adil_performans
from irp.gorunum_v9 import proje_gorebilir_mi, proje_erisim_gecmisi
from irp.kurallar_v10 import projede_yetkili, etkin_pay
from irp.yetki_v6 import varsayilan_yetkiler
from .ortak import t, s1, is_id, yaz
from .test_v7 import kur, gonder, dakika
from .test_v9 import duzenek, gec_duzenegi, durus_duzenegi, degerlendir, pay


def proje_duzenegi(eski=False):
    f=s1()
    if not eski:
        for e in f.olaylar:
            if e['eylem_kodu']=='PROJE.ACTIM': e['girdiler']['sorumlu']='K012' if e['girdiler']['kod']=='2509084' else 'K004'
            if e['eylem_kodu']=='ETAP.TANIMLADIM': e['kim']='K001'
        for r in varsayilan_yetkiler(): f.olay('K001','YETKI.TANIMLADIM',t(1,'07:09'),girdiler=r)
        f.olay('K001','YETKI.TANIMLADIM',t(1,'07:09'),girdiler=dict(eylem_kodu='PROJE.HEPSINI_GORUR',kimler=[],kapsam='FIRMA'))
        f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='proje_gorunurlugu',deger='UYELER'))
    return f


def gecikme_duzenegi(kendi=False):
    f,g=gec_duzenegi(False)
    f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='sessiz_kabul_is_gunu',deger=3))
    next(e for e in f.olaylar if e['eylem_kodu']=='GOREV.TAMAMLADIM')['girdiler']['gecikme_aciklamasi']='Muhasebeden maliyet bilgisi gelmedi'
    d=kur(f,t(26,'10:05'))
    ev=degerlendir(f,d,g,[pay('K041' if kendi else 'K052')],neden='BEKLEME_BIRIM')
    return f,d,g,ev


def performans(d,k='K041'):
    return adil_performans(d,k,'2026-10-01','2026-10-31')


class SenaryolarV10(unittest.TestCase):
    def kredi(self,d,z,bekleyen,k052=0):
        p=performans(d)
        self.assertEqual((p['zaman_orani'],p['kesinlesmedi'],p['bekleyen_satir_sayisi']),(z,bool(bekleyen),bekleyen))
        self.assertEqual(performans(d,'K052')['sebep_olunan_gecikme'],k052)

    def proje_akisi(self,eski):
        f=proje_duzenegi(eski); d=kur(f,t(22,'12:00'))
        for k,a,b in [('K001',1,1),('K012',1,0),('K004',1,1),('K009',1,0),('K017',1,0),('K023',0,0),('K041',0,0),('K006',0,0),('K007',0,0),('K044',0,0)]:
            self.assertEqual((proje_gorebilir_mi(d,k,'2509084'),proje_gorebilir_mi(d,k,'2509091')),(True,True) if eski else (bool(a),bool(b)),k)
        def ata(k,saat,kisi='K041',p='2509084',bek='BASARILI'):
            return gonder(f,d,k,'GOREV.ATADIM',t(22,saat),dict(gorevler=[f.gorev_satiri(kisi=kisi,proje=p,etap=None,zaman_degeri=2,teslim_tarihi='2026-10-23')]),bek='BASARILI' if eski else bek)
        ata('K012','12:10')
        self.assertTrue(proje_gorebilir_mi(d,'K041','2509084'))
        ata('K012','12:15','K044',bek='YETKI')
        gonder(f,d,'K012','PROJE.ERISIM_VERDIM',t(22,'12:20'),dict(proje='2509084',kisi='K044',gerekce='Otomasyon destegi'))
        ata('K012','12:25','K044')
        ata('K007','12:30','K052',bek='YETKI')
        ata('K012','12:35',p='2509091',bek='YETKI')
        def etap(k,saat,b,ad,bek='BASARILI'):
            return gonder(f,d,k,'ETAP.TANIMLADIM',t(22,saat),dict(proje='2509091',ad=ad,birim=b,baslangic='2026-10-26',bitis='2026-11-30',hedef_saat=40),bek='BASARILI' if eski else bek)
        etap('K004','12:40','PLANLAMA','E-PLN','YETKI')
        e=etap('K001','12:45','OTO_TASARIM','E-OTO')
        self.assertIsNone(d.etaplar[e]['sorumlu'])
        self.assertTrue(proje_gorebilir_mi(d,'K012','2509091'))
        # Y98b eski tabloyu sabit tutar; 13:00 devir yeni senaryoya aittir.
        if not eski:
            gonder(f,d,'K001','YETKI.TANIMLADIM',t(22,'13:00'),dict(eylem_kodu='ETAP.TANIMLADIM',kimler=['YETKILI','PROJE_SORUMLUSU'],kapsam='FIRMA'))
        etap('K004','13:05','PLANLAMA','E-PLN')
        etap('K012','13:10','MEK_TASARIM','E-MEK','YETKI')
        gonder(f,d,'K012','PLAN.ONAYLADIM',t(22,'13:15'),dict(proje='2509084',gerekce='Baslangic plani'))
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(22,'13:20'),dict(proje='2509084',gerekce='Deneme'),bek='BASARILI' if eski else 'YETKI')
        gonder(f,d,'K012','PROJE.ERISIM_KALDIRDIM',t(22,'13:30'),dict(proje='2509084',kisi='K044',gerekce='Calisma bitti'))
        self.assertTrue(proje_gorebilir_mi(d,'K044','2509084'))
        self.assertEqual(len(proje_erisim_gecmisi(d,'2509084')),5)
        self.assertEqual(len([x for x in d.bildirimler.values() if x['kural']=='R42' and x['alici']=='K044']),2)

    def test_Y98(self): self.proje_akisi(False)
    def test_Y98b(self): self.proje_akisi(True)

    def test_Y99(self):
        f,d,g,ev=gecikme_duzenegi()
        self.assertEqual(d.gorevler[g]['gecikme_nedeni'],'BELIRTILMEDI')
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['kural']=='R38'},{'K007','K001'})
        self.assertTrue(any(x['kural']=='R40' and x['alici']=='K012' for x in d.bildirimler.values()))
        d.ilerlet(t(26,'11:05')); self.kredi(d,0,1)

    def test_Y99a(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K007','SORUMLULUK.DOGRULADIM',t(27,'09:00'),dict(hedef=ev,satir=1,karar='ONAY'))
        self.kredi(d,1,0,8)

    def test_Y99b(self):
        f,d,g,ev=gecikme_duzenegi(); ids=set(d.olaylar)
        d.ilerlet(t(30,'10:59')); self.kredi(d,0,1)
        d.ilerlet(t(30,'11:00')); self.kredi(d,1,0,8)
        self.assertEqual(set(d.olaylar),ids)
        self.assertFalse(d.sorumluluklar[ev+'/1']['dogrulandi'])  # Kaynak değişmez.
        self.assertTrue(etkin_pay(d,d.sorumluluklar[ev+'/1']))

    def test_Y99c(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),dict(hedef=ev,satir=1,gerekce='Bilgi 22.10 tarihinde verildi'))
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['kural']=='R39'},{'K007','K001'})
        gonder(f,d,'K007','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(27,'15:00'),dict(hedef=ev,satir=1,karar='KABUL',gerekce='Dogru'))
        self.kredi(d,0,0); d.ilerlet(t(30,'11:00')); self.kredi(d,0,0)

    def test_Y99d(self):
        f,d,g,ev=gecikme_duzenegi(True); self.kredi(d,0,0)
        gonder(f,d,'K041','SORUMLULUK.ITIRAZ_ETTIM',t(26,'12:00'),dict(hedef=ev,satir=1,gerekce='Gecikme benden degil'))
        self.kredi(d,0,1)
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['kural']=='R39'},{'K012','K001'})
        degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')],zaman=t(26,'14:00'))
        self.kredi(d,1,0)

    def test_Y99e(self):
        f,h=durus_duzenegi()
        # Olay sözleşmesinin alanı `not`; Python anahtar sözcüğü nedeniyle sözlükle.
        next(e for e in f.olaylar if e['olay_kimligi']==h)['girdiler']={'not':'Elektrot bitti'}
        d=kur(f,t(22,'13:50')); self.assertEqual(dakika(d,'BEKLEME_ARIZA'),26)
        self.assertTrue(all(x['neden']=='BELIRTILMEDI' for x in d.araliklar if x['kova']=='BEKLEME_ARIZA'))
        gonder(f,d,'K017','IS.ARIZA_BILDIRDIM',t(22,'13:51'),{},4,bek='BICIM')
