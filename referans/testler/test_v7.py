"""Y74-Y86: belge sayilari bagimsiz, yeni olaylar gercek kabul yolundan."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo,Saat,an
from irp.gorunumler import gorev_gunluk_paylar,iscilik_maliyeti,maas_dagilimi,adil_performans
from irp.gorunum_v7 import (gun_agirligi,kapasite,fazla_mesai_kayitlari,kisi_uygun_mu,tezgah_gostergesi,
    tezgah_uygun_mu,gun_sonu_raporu,hatirlatmalar,plan_karsilastir,top_kimde,gecmis_gorunumu,onceki_donem_duzeltmeleri,oku,gorebilir_mi)
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from .ortak import Duzenek,t,is_id,s1,yaz


def kur(f,simdi):
    d=Depo(Saat(t(1,'00:00')))
    for e in sorted(f.olaylar,key=lambda e:(e.get('gelis',e['oldugu_an']),e['olay_kimligi'])):
        zaman=e.get('gelis',e['oldugu_an'])
        if an(zaman)>an(simdi): continue
        d.ilerlet(zaman)
        if an(e['oldugu_an'])<an(t(21,'00:00')) and not e.get('canli'):
            x=deepcopy(e); x['giris_sekli']='AKTARIM'; r=d.olay_ekle(x,servis=True,hassas_ek=f.hassas.get(e['olay_kimligi']))
        else: r=yaz(d,e,hassas=f.hassas.get(e['olay_kimligi']))
        if r['sonuc']!='BASARILI': raise AssertionError((e['eylem_kodu'],e['oldugu_an'],r))
        if d.isleme_hatalari: raise AssertionError(d.isleme_hatalari)
    d.ilerlet(simdi); return d


def gonder(f,d,kim,kod,zaman,g=None,h=None,tur=None,bek='BASARILI',**kw):
    d.ilerlet(zaman)
    if kod.startswith('EK_MESAI.') and isinstance(h,int): tur='IS'
    oid=f.olay(kim,kod,zaman,h,g,tur=tur,**kw); r=yaz(d,f.olaylar[-1])
    if (r['sonuc'] if bek=='BASARILI' else r.get('kod'))!=bek: raise AssertionError((kod,r,bek))
    if d.isleme_hatalari: raise AssertionError(d.isleme_hatalari)
    return oid


def mesai_f(plan=True):
    f=Duzenek(); f.ata(4)
    if plan: f.olaylar[-1]['girdiler']['ek_mesai']=dict(tarih='2026-10-22',baslangic='18:00',bitis='20:00',aciklama='Sevkiyat')
    for kod,saat in [('MESAI.GIRDIM','07:58'),('BASLADIM','08:00'),('DEVAM_ETTIM','10:15'),('DEVAM_ETTIM','12:30'),('DEVAM_ETTIM','15:15'),('TAMAMLADIM','19:00')]:
        f.is_olay(kod,saat,None if kod.startswith('MESAI') else 4)
    return f


def durus_f():
    f=Duzenek(); f.ata(1); f.ata(2,'K023')
    for k,n in [('K017',1),('K023',2)]:
        f.is_olay('MESAI.GIRDIM','07:58',kisi=k); f.is_olay('BASLADIM','08:00',n,k)
    f.is_olay('MOLA_VERDIM','09:00',2,'K023')
    dur=f.olay('K009','DURUS.BASLADI',t(22,'09:30'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK'),gelis=t(22,'10:40'))
    f.olay('K009','DURUS.BITTI',t(22,'10:20'),girdiler=dict(hedef=dur),gelis=t(22,'10:40'))
    f.is_olay('DEVAM_ETTIM','10:25',1); f.is_olay('DEVAM_ETTIM','10:30',2,'K023')
    return f


def dakika(d,kova,k='K017'):
    return sum(((a['bitis'] or d.saat.simdi())-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['kisi']==k and a['kova']==kova)


def parca_turu():
    asamalar=['SIPARIS_VERILMELI','SIPARISTE','GELDI','ISLEMDE','KALITE_ONAYLI','MONTAJA_HAZIR','MONTAJDA']
    gecisler=[dict(den=a,e=b,kimler=roller,kapsam='FIRMA') for a,b,roller in [
        (asamalar[0],asamalar[1],['BEYAZ_YAKA','YONETICI']), (asamalar[1],asamalar[2],['BEYAZ_YAKA','YONETICI']),
        (asamalar[2],asamalar[3],['EKIP_LIDERI']), (asamalar[3],asamalar[4],['EKIP_LIDERI']),
        (asamalar[4],asamalar[5],['EKIP_LIDERI','YONETICI']), (asamalar[5],asamalar[6],['EKIP_LIDERI']),
        (asamalar[0],asamalar[5],['YONETICI'])]]
    return dict(kod='PARCA',ad='Parca',asamalar=[dict(kod=a,son=a==asamalar[-1]) for a in asamalar],baslangic_asamasi=asamalar[0],gecisler=gecisler,baglanabilir_turler=['PROJE','NESNE'],acabilenler=dict(kimler=['BEYAZ_YAKA','YONETICI'],kapsam='FIRMA'))


class SenaryolarV7(unittest.TestCase):
    def test_Y74a(self):
        f=s1(); d=kur(f,t(22,'11:40'))
        self.assertEqual(emek(d,is_id(1)),186)
        self.assertEqual(iscilik_maliyeti(d,'2509084','2026-10-22','2026-10-22')['iscilik'],Decimal('344.44'))

    def test_Y74b(self):
        f=Duzenek(); f.olay('K001','KISI.EKLEDIM',t(15),girdiler=dict(kod='K061',ad='Yeni',birim='IMALAT',yaka='MAVI',roller=['CALISAN'],giris_tarihi='2026-10-19'))
        f.ata(2,'K061')
        for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:00',2),('TAMAMLADIM','09:30',2)]: f.is_olay(kod,saat,n,'K061')
        d=kur(f,t(22,'09:30')); self.assertEqual(emek(d,is_id(2)),90)
        v=iscilik_maliyeti(d,'2509084','2026-10-01','2026-10-31')
        self.assertEqual(v['iscilik'],'VERI_EKSIK'); self.assertTrue(v['eksik_veri'])

    def test_Y74c(self):
        f=Duzenek(); g=f.gorev_ata(t(1,'09:00'),satirlar=[f.gorev_satiri(zaman_degeri=135,teslim_tarihi='2026-10-30'),f.gorev_satiri(proje='2509091',etap=None,zaman_degeri=90,teslim_tarihi='2026-10-30')])
        f.gorev_olay('KABUL_ETTIM',t(1,'10:00'),[g,g[:-1]+'2'])
        d=kur(f,t(30,'18:00')); v=maas_dagilimi(d,'K041','2026-10-01')
        self.assertEqual(v['tutarlar'],{'2509084':Decimal('15000'),'2509091':Decimal('10000')})
        self.assertEqual(v['dagitilamayan'],0); self.assertEqual(v['maasin_ustu'],5000)

    def test_Y75(self):
        f=Duzenek(); g=f.gorev_ata(t(26,'09:00'),zaman_degeri=20,teslim_tarihi='2026-10-30'); f.gorev_olay('KABUL_ETTIM',t(26,'09:30'),g)
        tanim=dict(tarih='2026-10-28',tur='YARIM_GUN',mesai_baslangic='08:00',mesai_bitis='13:00',sabit_molalar=[dict(ad='Cay',bas='10:00',bit='10:15')],ad='Yarim gun')
        f.olay('K001','GUN.TANIMLADIM',t(26,'10:00'),girdiler=tanim)
        f.olay('K001','GUN.TANIMLADIM',t(26,'10:01'),girdiler=dict(tanim,tarih='2026-10-31',tur='OZEL_MESAI',sabit_molalar=[]))
        d=kur(f,t(26,'11:00')); pay={x['gun']:x['saat'] for x in gorev_gunluk_paylar(d,d.gorevler[g])}
        self.assertAlmostEqual(gun_agirligi(d,'2026-10-28'),4.75/9)
        self.assertAlmostEqual(pay['2026-10-26'],5.669291,places=6); self.assertAlmostEqual(pay['2026-10-28'],2.992126,places=6)
        self.assertAlmostEqual(sum(pay.values()),20)
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-30'),31.75)
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-31'),36.75)
        gonder(f,d,'K001','GUN.TANIMLADIM',t(26,'11:01'),dict(tanim,tarih='2026-10-26'),bek='DURUM')
        gonder(f,d,'K017','MESAI.GIRDIM',t(28,'07:58')); d.ilerlet(t(28,'14:00'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'MESAI_DISI')
        self.assertEqual(max(a['bitis'] for a in d.araliklar if a['kisi']=='K017'),an(t(28,'13:00')))

    def test_Y76a(self):
        d=kur(mesai_f(),t(22,'20:30')); self.assertEqual(dakika(d,'CALISMA'),600)
        fm=fazla_mesai_kayitlari(d); self.assertEqual(len(fm),1); self.assertEqual(fm[0]['saat'],1); self.assertEqual(fm[0]['prim'],Decimal('55.56'))
        self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),11)
        self.assertEqual(dakika(d,'TANIMSIZ'),60); self.assertEqual(d.isler[is_id(4)]['bitis_ani'],an(t(22,'19:00')))
        self.assertFalse(d.supheliler)

    def test_Y76b(self):
        f=mesai_f(False); d=kur(f,t(22,'20:30')); oid=f.olaylar[-1]['olay_kimligi']
        self.assertIn(oid,d.supheliler); self.assertIn(oid,d.mesai_sonrasi_isaretleri); self.assertEqual(dakika(d,'CALISMA'),540)
        gonder(f,d,'K009','EK_MESAI.ONAYLADIM',t(23,'09:00'),dict(kisi='K017',tarih='2026-10-22',baslangic='18:00',bitis='19:00',aciklama='Sevkiyat'),4)
        self.assertNotIn(oid,d.supheliler); self.assertNotIn(oid,d.mesai_sonrasi_isaretleri)
        self.assertEqual(dakika(d,'CALISMA'),600); self.assertEqual(fazla_mesai_kayitlari(d)[0]['prim'],Decimal('55.56'))

    def test_Y76c(self):
        f=mesai_f(False); d=kur(f,t(22,'20:30')); g=dict(kisi='K017',tarih='2026-10-22',baslangic='18:00',bitis='19:00',aciklama='Mesai')
        gonder(f,d,'K023','EK_MESAI.ONAYLADIM',t(23,'09:00'),g,4,bek='YETKI')
        gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(23,'09:01'),dict(g,tarih='2026-10-23',baslangic='16:00'),4,bek='DURUM')
        gonder(f,d,'K009','EK_MESAI.ONAYLADIM',t(30,'09:00'),g,4,bek='DURUM')

    def test_Y77(self):
        f=Duzenek(); g=f.gorev_ata(t(22,'09:00'),zaman_degeri=10,teslim_tarihi='2026-10-26',ek_mesai=dict(tarih='2026-10-24',baslangic='09:00',bitis='13:00',aciklama='Musteri'))
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); f.gorev_olay('TAMAMLADIM',t(24,'12:00'),g)
        d=kur(f,t(24,'12:30')); self.assertEqual(fazla_mesai_kayitlari(d),[])
        damga=dict(kisi='K041',tarih='2026-10-24',baslangic='09:00',bitis='12:00')
        # Karar 75: hafta sonu mesaisi pazartesi damgalanabilir.
        gonder(f,d,'K012','EK_MESAI.ONAYLADIM',t(26,'09:00'),damga,g,tur='GOREV')
        self.assertEqual(fazla_mesai_kayitlari(d)[0]['prim'],Decimal('166.67'))
        self.assertEqual(kapasite(d,'K041','2026-10-24','2026-10-24'),4)
        self.assertEqual(len(gorev_gunluk_paylar(d,d.gorevler[g])),3)
        self.assertTrue(all(abs(x['saat']-10/3)<1e-9 for x in gorev_gunluk_paylar(d,d.gorevler[g])))
        gonder(f,d,'K012','EK_MESAI.ONAYLADIM',t(26,'09:01'),damga,g,tur='GOREV',bek='DURUM')

    def test_Y78a(self):
        d=kur(durus_f(),t(22,'10:45'))
        for k in ('K017','K023'):
            self.assertEqual(dakika(d,'BEKLEME_DURUS',k),35); self.assertEqual(dakika(d,'SABIT_MOLA',k),15)
        self.assertEqual(dakika(d,'CALISMA'),110); self.assertEqual(dakika(d,'MOLA','K023'),30)
        self.assertEqual(dakika(d,'TANIMSIZ'),5); self.assertEqual(dakika(d,'TANIMSIZ','K023'),10)
        self.assertTrue({'K004','K001'} <= {x['alici'] for x in d.bildirimler.values() if x['kural']=='R34'})

    def test_Y78b(self):
        f=Duzenek()
        for n,k,s in [(4,'K017',1),(3,'K017',2),(8,'K023',1),(7,'K023',2)]: f.ata(n,k,s)
        for kod,saat,n,k in [('MESAI.GIRDIM','07:58',None,'K017'),('BASLADIM','08:00',4,'K017'),('DEVAM_ETTIM','10:15',4,'K017'),('TAMAMLADIM','11:50',4,'K017'),('BASLADIM','12:41',3,'K017'),('MESAI.GIRDIM','07:59',None,'K023'),('TAMAMLADIM','08:10',8,'K023'),('TAMAMLADIM','12:40',7,'K023')]: f.is_olay(kod,saat,n,k)
        x=f.olay('K009','DURUS.BASLADI',t(22,'11:00'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK'))
        f.olay('K009','DURUS.BITTI',t(22,'11:30'),girdiler=dict(hedef=x))
        d=kur(f,t(22,'12:45')); self.assertEqual(dakika(d,'TEZGAH',None),240)
        self.assertEqual(sum((a['bitis']-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['is']==is_id(4)),165)

    def test_Y78c(self):
        f=Duzenek(); d=kur(f,t(22,'09:00')); g=dict(kapsam=['IMALAT'],neden='ELEKTRIK')
        gonder(f,d,'K023','DURUS.BASLADI',t(22,'09:01'),g,bek='YETKI'); gonder(f,d,'K012','DURUS.BASLADI',t(22,'09:02'),g,bek='YETKI')
        gonder(f,d,'K009','DURUS.BASLADI',t(22,'09:03'),g)
        oid=gonder(f,d,'K009','DURUS.BASLADI',t(22,'09:04'),g)
        self.assertIn(oid,d.supheliler); self.assertEqual(len(d.duruslar),1)

    def test_Y79(self):
        f=Duzenek(); f.ata(1); f.ata(2,sira=2)
        f.olay('K001','AYAR.DEGISTIRDIM',t(21,'09:00'),girdiler=dict(anahtar='gun_sonu_raporu_zorunlu',deger=True))
        for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:00',1),('DEVAM_ETTIM','10:15',1),('TAMAMLADIM','11:00',1),('BASLADIM','11:05',2),('DEVAM_ETTIM','12:30',2),('TAMAMLADIM','13:30',2),('MESAI.CIKTIM','17:55',None)]: f.is_olay(kod,saat,n)
        f.is_olay('MESAI.GIRDIM','07:58',kisi='K023'); f.is_olay('MESAI.CIKTIM','17:55',kisi='K023')
        f.olay('K017','GUN_SONU.GONDERDIM',t(22,'17:50'),girdiler=dict(gun='2026-10-22',aciklama='Kesim',tanimsiz_aciklama='Yeni is bekledim'))
        d=kur(f,t(22,'18:00'))
        # T9 8: mavi yaka gondermez; eski gonderim yalniz aciklama birakir.
        gonder(f,d,'K009','GUN_SONU.IADE_ETTIM',t(22,'18:10'),dict(kisi='K017',gun='2026-10-22',gerekce='Acikla'),bek='DURUM')
        gonder(f,d,'K017','GUN_SONU.GONDERDIM',t(22,'18:20'),dict(gun='2026-10-22',aciklama='Kesim',tanimsiz_aciklama='Lider toplantidaydi'))
        r=gun_sonu_raporu(d,'K017','2026-10-22')
        self.assertEqual(r['ozet']['kovalar'],dict(CALISMA=280,TANIMSIZ=255,SABIT_MOLA=60))
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'18:30'),dict(kisi='K017',gun='2026-10-22',ozet_surumu=r['ozet_surumu']))
        self.assertEqual(gun_sonu_raporu(d,'K017','2026-10-22')['durum'],'ONAYLANDI')
        d.ilerlet(t(23,'08:00')); self.assertFalse(any(x['kural']=='R32' and x['alici']=='K023' for x in hatirlatmalar(d)))
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(23,'09:00'),dict(baslangic=t(22,'13:30'),bitis=t(22,'15:00'),aciklama='Kontrol',is_bitti=False),2,adina='K017')
        r=gun_sonu_raporu(d,'K017','2026-10-22'); self.assertEqual(r['durum'],'DEGISTI')
        self.assertEqual(r['ozet']['isler'][is_id(2)],205); self.assertEqual(r['ozet']['kovalar']['TANIMSIZ'],165)
        self.assertEqual(r['onaylanan_ozet']['kovalar']['TANIMSIZ'],255)
        g=dict(kisi='K017',gun='2026-10-22',ozet_surumu=r['ozet_surumu'])
        gonder(f,d,'K017','GUN_SONU.ONAYLADIM',t(23,'09:05'),g,bek='YETKI'); gonder(f,d,'K004','GUN_SONU.ONAYLADIM',t(23,'09:10'),g)

    def test_Y80(self):
        f=Duzenek(); talep=f.olay('K041','IZIN.TALEP_ETTIM',t(21,'10:00'),girdiler=dict(kisi='K041',tur='YILLIK',baslangic=t(28),bitis=t(28,'18:00'),gerekce='Aile ziyareti'))
        f.olay('K012','IZIN.ONAYLADIM',t(21,'11:00'),girdiler=dict(hedef=talep))
        g=f.gorev_ata(t(26,'09:00'),satirlar=[f.gorev_satiri(zaman_degeri=20,teslim_tarihi='2026-10-30'),f.gorev_satiri(zaman_degeri=10,teslim_tarihi='2026-10-28')])
        f.gorev_olay('KABUL_ETTIM',t(26,'09:30'),[g,g[:-1]+'2']); d=kur(f,t(26,'10:00'))
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-30'),27)
        self.assertEqual([x['saat'] for x in gorev_gunluk_paylar(d,d.gorevler[g])],[20/3]*3)
        self.assertEqual([x['saat'] for x in gorev_gunluk_paylar(d,d.gorevler[g[:-1]+'2'])],[5,5])
        self.assertEqual(kisi_uygun_mu(d,'K041',t(28,'10:00'),t(28,'11:00'),'K044')['neden'],'musait degil')
        self.assertEqual(kisi_uygun_mu(d,'K041',t(28,'10:00'),t(28,'11:00'),'K012')['neden'],'izin (YILLIK)')
        self.assertTrue(any(x['kural']=='R37' and x['alici']=='K012' for x in d.bildirimler.values()))
        yeni=gonder(f,d,'K041','IZIN.TALEP_ETTIM',t(26,'11:00'),dict(kisi='K041',tur='SAATLIK',baslangic=t(28,'10:00'),bitis=t(28,'11:00'),gerekce='Tekrar'))
        gonder(f,d,'K044','IZIN.ONAYLADIM',t(26,'11:01'),dict(hedef=yeni),bek='YETKI')
        gonder(f,d,'K012','IZIN.ONAYLADIM',t(26,'11:02'),dict(hedef=yeni),bek='DURUM')

    def test_Y80_mavi(self):
        f=Duzenek(); x=f.olay('K017','IZIN.TALEP_ETTIM',t(21,'10:00'),girdiler=dict(kisi='K017',tur='YILLIK',baslangic=t(27),bitis=t(27,'18:00'),gerekce='Izin'))
        f.olay('K009','IZIN.ONAYLADIM',t(21,'11:00'),girdiler=dict(hedef=x))
        giris=f.is_olay('MESAI.GIRDIM','07:58',gun=27); d=kur(f,t(27,'19:00'))
        self.assertEqual(dakika(d,'IZIN'),600); self.assertEqual(dakika(d,'SABIT_MOLA'),0); self.assertIn(giris,d.supheliler)

    def test_Y81(self):
        f=Duzenek(); f.olay('K009','TEZGAH.TAKVIM_TANIMLADIM',t(21,'09:00'),girdiler=dict(tezgah='CNC-02',vardiyalar=[dict(gunler=[1,2,3,4,5],bas='00:00',bit='24:00')],gecerli_baslangic='2026-10-22'))
        f.olay('K009','TEZGAH.BAKIM_PLANLADIM',t(21,'09:01'),girdiler=dict(tezgah='CNC-02',baslangic=t(23),bitis=t(23,'12:00'),aciklama='Bakim'))
        f.olay('K017','TEZGAH.DURUS_BILDIRDIM',t(23,'14:00'),girdiler=dict(tezgah='CNC-02',neden='ARIZA'))
        f.olay('K017','TEZGAH.DURUS_BITTI',t(23,'15:00'),girdiler=dict(tezgah='CNC-02')); d=kur(f,t(23,'16:00'))
        v=tezgah_gostergesi(d,'CNC-02','2026-10-22','2026-10-23'); self.assertEqual(v['planli_kullanilabilir'],44); self.assertEqual(v['durus'],{'ARIZA':1})
        for a,b,bek in [(t(23,'09:00'),t(23,'10:00'),'bakim'),(t(23,'14:30'),t(23,'14:45'),'durus'),(t(22,'20:00'),t(22,'21:00'),None)]: self.assertEqual(tezgah_uygun_mu(d,'CNC-02',a,b)['neden'],bek)
        gonder(f,d,'K041','TEZGAH.DURUS_BILDIRDIM',t(23,'16:01'),dict(tezgah='CNC-02',neden='ARIZA'),bek='YETKI')
        gonder(f,d,'K023','TEZGAH.DURUS_BILDIRDIM',t(23,'16:02'),dict(tezgah='CNC-02',neden='ARIZA'))

    def test_Y82(self):
        f=Duzenek(); d=kur(f,t(26,'08:00'))
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(26,'09:00'),dict(proje='2509084'))
        b0=deepcopy(d.plan_surumleri['2509084'][0])
        gonder(f,d,'K004','ETAP.DEGISTIRDIM',t(27,'09:00'),dict(degisenler=dict(bitis='2027-01-08')),f.etap['E-IML'],'ETAP')
        self.assertTrue(plan_karsilastir(d,'2509084')['onaysiz_degisti'])
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(28,'09:00'),dict(proje='2509084',gerekce='Malzeme'))
        self.assertEqual(d.plan_surumleri['2509084'][0],b0)
        v=plan_karsilastir(d,'2509084'); self.assertFalse(v['onaysiz_degisti']); self.assertEqual(v['sapma'][f.etap['E-IML']]['bitis_gun'],14)
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(28,'09:01'),dict(proje='2509091'),bek='DURUM')
        gonder(f,d,'K017','PLAN.ONAYLADIM',t(28,'09:02'),dict(proje='2509084',gerekce='Yenile'),bek='YETKI')
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(28,'09:03'),dict(proje='2509084'),bek='BICIM')

    def test_Y83(self):
        f=Duzenek(); g=f.gorev_ata(t(22,'09:00'),zaman_degeri=8,teslim_tarihi='2026-10-23',onay_gerekli=True,onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); onay=f.gorev_olay('TAMAMLADIM',t(22,'14:00'),g)
        d=kur(f,t(22,'14:30')); sor=[dict(tur='KISI',kimlik=k,yuzde=y) for k,y in [('K041',60),('K044',40)]]
        ret=gonder(f,d,'K012','GOREV.REDDETTIM',t(22,'15:00'),dict(not_='Olculer',**{'not':'Olculer'},sorumlular=sor,revizyon_ver=False),g,'GOREV')
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['kalite_ret'],.6)
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['kalite_ret'],.4)
        self.assertTrue(all(x['dogrulandi'] for x in d.sorumluluklar.values()))
        self.assertFalse(any(x['kural']=='R38' for x in d.bildirimler.values()))
        gonder(f,d,'K041','SORUMLULUK.DOGRULADIM',t(22,'15:10'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Ben'),bek='YETKI')
        gonder(f,d,'K017','SORUMLULUK.DOGRULADIM',t(22,'15:11'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Ben'),bek='YETKI')
        gonder(f,d,'K012','SORUMLULUK.DOGRULADIM',t(22,'16:00'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Kanita gore'))
        it=gonder(f,d,'K044','SORUMLULUK.ITIRAZ_ETTIM',t(22,'16:05'),dict(hedef=ret+'/2',gerekce='Liste zamaninda'))
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['kalite_ret'],0)
        gonder(f,d,'K012','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(22,'16:30'),dict(hedef=it,karar='KABUL',gerekce='Dogru'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['kalite_ret'],.6)
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['kalite_ret'],0)
        self.assertEqual(d.gorevler[g]['durum'],'REDDEDILDI'); self.assertEqual(d.gorevler[onay]['durum'],'BITTI')
        gonder(f,d,'K012','GOREV.REDDETTIM',t(22,'16:31'),dict(**{'not':'Olcu'},revizyon_ver=False,sorumlular=[dict(sor[0],yuzde=70),sor[1]]),g,'GOREV',bek='BICIM')

    def test_Y83b(self):
        f=Duzenek(); g=f.gorev_ata(t(22,'09:00'),veren='K004',zaman_degeri=4,teslim_tarihi='2026-10-23',etap=f.etap['E-SAT'],onay_gerekli=True,onaylayan='K004')
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); f.gorev_olay('TAMAMLADIM',t(22,'13:00'),g)
        d=kur(f,t(22,'13:30'))
        self.assertTrue(any(x['kural']=='R30' and x['alici']=='K012' for x in d.bildirimler.values()))
        ret=gonder(f,d,'K004','GOREV.REDDETTIM',t(22,'14:00'),dict(**{'not':'Eksik kalem'},sorumlular=[dict(tur='KISI',kimlik='K041',yuzde=100)],revizyon_ver=False),g,'GOREV')
        self.assertFalse(d.sorumluluklar[ret+'/1']['dogrulandi'])
        self.assertEqual({x['alici'] for x in d.bildirimler.values() if x['kural']=='R38'},{'K012','K001'})
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['kalite_ret'],0)
        gonder(f,d,'K004','SORUMLULUK.DOGRULADIM',t(22,'14:30'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Ben'),bek='YETKI')
        gonder(f,d,'K012','SORUMLULUK.DOGRULADIM',t(22,'15:00'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Kontrol'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['kalite_ret'],1)

    def test_Y84(self):
        f=Duzenek(); f.gorev_ata(t(26,'09:00'),veren='K004',zaman_degeri=4,teslim_tarihi='2026-10-30',etap=f.etap['E-SAT'])
        d=kur(f,t(26,'10:00')); self.assertTrue(any(x['kural']=='R30' and x['alici']=='K012' for x in d.bildirimler.values()))
        d=kur(s1(),t(22,'11:45')); self.assertEqual(gecmis_gorunumu(d,t(22,'10:30'))['kisi_durumu']['K017']['durum'],'CALISIYOR')
        self.assertEqual(gecmis_gorunumu(d,t(22,'11:41'))['listeler']['K017'],[is_id(2)])
        d=kur(durus_f(),t(22,'10:45')); eski=gecmis_gorunumu(d,t(22,'10:35'))
        self.assertFalse(any(a['kova']=='BEKLEME_DURUS' for a in eski['araliklar']))
        eski=gecmis_gorunumu(d,t(22,'10:41'))
        self.assertEqual(sum((a['bitis']-a['baslangic']).total_seconds()/60 for a in eski['araliklar'] if a['kisi']=='K017' and a['kova']=='BEKLEME_DURUS'),35)

    def test_Y85(self):
        f=Duzenek(); f.ata(4); d=kur(f,t(29,'17:00')); d.cihaz_esitle('K017','TEL-K017')
        d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        kapali=deepcopy(d.ay_kapanislari)
        for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:00',4),('DEVAM_ETTIM','10:15',4),('MESAI.CIKTIM','11:00',None)]:
            f.is_olay(kod,saat,n,gun=30); d.ilerlet(t(2,'08:00',11)); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.ay_kapanislari,kapali)
        x=next(x for x in onceki_donem_duzeltmeleri(d) if x['kisi']=='K017')
        self.assertEqual(x['saat'],2.75); self.assertEqual(x['tutar'],Decimal('305.56')); self.assertEqual(x['ay'],'2026-11-01')
        self.assertIn('TEL-K017',d.ay_kapanislari['2026-10-01:CIHAZ_UYARILARI'])

    def test_Y86(self):
        f=Duzenek()
        next(e for e in f.olaylar if e['eylem_kodu']=='IS.TANIMLADIM')['girdiler']['isler'][2]['parca_kodu']='2509084_07_04-61'
        d=kur(f,t(26,'08:00'))
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'09:00'),parca_turu())
        x=gonder(f,d,'K006','NESNE.ACTIM',t(26,'10:00'),dict(tur='PARCA',ad='2509084_07_04-61',proje='2509084',sorumlu='K006',baglar=[]))
        for zaman,kim,asama,bek in [(t(26,'10:10'),'K006','SIPARISTE','BASARILI'),(t(27,'09:00'),'K006','GELDI','BASARILI'),(t(27,'09:30'),'K017','ISLEMDE','YETKI'),(t(27,'09:31'),'K009','ISLEMDE','BASARILI'),(t(27,'09:40'),'K009','MONTAJDA','DURUM')]:
            gonder(f,d,kim,'NESNE.ASAMA_GECIRDIM',zaman,dict(hedef=x,yeni_asama=asama,gerekce='Akis'),bek=bek)
        d.ilerlet(t(27,'10:00')); v=top_kimde(d,x)
        self.assertEqual(v['asama'],'ISLEMDE'); self.assertEqual(v['asama_dakikalari']['SIPARIS_VERILMELI'],10)
        self.assertEqual(v['asama_dakikalari']['SIPARISTE'],1370); self.assertEqual(v['asama_dakikalari']['GELDI'],31)
        self.assertEqual(d.isler[is_id(3)]['nesne'],x)

    def test_gorunurluk(self):
        d=kur(Duzenek(),t(22))
        self.assertTrue(gorebilir_mi(d,'K012','PERFORMANS','K041')); self.assertTrue(gorebilir_mi(d,'K001','PERFORMANS','K041'))
        self.assertFalse(gorebilir_mi(d,'K044','PERFORMANS','K041')); self.assertFalse(gorebilir_mi(d,'K012','MAAS','K041'))
        self.assertFalse(gorebilir_mi(d,'K001','BILINMEYEN','K041'))
        with self.assertRaises(PermissionError): oku(d,'K044','IZIN_DETAY','K041')
        self.assertTrue(gorebilir_mi(d,'K041','BIRIM_PERFORMANS','MEK_TASARIM'))

if __name__=='__main__': unittest.main()
