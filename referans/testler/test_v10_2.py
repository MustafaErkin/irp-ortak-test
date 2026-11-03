"""Y103–Y112: T11'in bağımsız beklenenleri; girişler gerçek kabul kapısından."""
import unittest
from decimal import Decimal
from irp import an
from irp.gorunum_v7 import oku, fazla_mesai_kayitlari
from irp.varsayilanlar_v10_2 import parca_turu
from .ortak import Duzenek, t, is_id, yaz
from .test_v7 import kur, gonder, parca_turu as eski_parca
from .test_v10 import proje_duzenegi
from .test_v10_1 import ek_yetki, belge_turu, surum_olayi


def nesneli(uyeler=True):
    f = ek_yetki(proje_duzenegi() if uyeler else Duzenek())
    f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:00'),girdiler=eski_parca())
    return f, kur(f,t(22,'13:50'))


def ac(f,d,ad,zaman,sorumlu='K006',kim='K004',bek='BASARILI',**g):
    return gonder(f,d,kim,'NESNE.ACTIM',zaman,dict(tur='PARCA',ad=ad,sorumlu=sorumlu,**g),bek=bek)


def gec(f,d,n,asama,zaman,kim='K006',bek='BASARILI'):
    return gonder(f,d,kim,'NESNE.ASAMA_GECIRDIM',zaman,dict(hedef=n,yeni_asama=asama,gerekce='Akış'),n,'NESNE',bek)


class SenaryolarV10_2(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        from irp import Depo
        self.depolar=[]; original=Depo.__init__
        def init(d,*a,**kw):
            original(d,*a,**kw);self.depolar.append(d)
        p=patch.object(Depo,'__init__',init);p.start();self.addCleanup(p.stop)

    def tearDown(self):
        from irp.degismezler_v10_2 import denetle
        for d in self.depolar:
            s=denetle(d,True);self.assertTrue(all(s.values()),s)

    def test_Y103(self):
        f,d=nesneli(); p='2509084'; q='2509091'
        a=ac(f,d,'Rulman 6204',t(22,'14:00'),proje=p,baglar=[dict(tur='PROJE',kimlik=p)])
        b=ac(f,d,'Mil',t(22,'14:05'),baglar=[dict(tur='PROJE',kimlik=p)])
        ac(f,d,'Flanş',t(22,'14:10'),kim='K006',baglar=[dict(tur='PROJE',kimlik=p)],bek='YETKI')
        ac(f,d,'Kapak',t(22,'14:15'),proje=q,baglar=[dict(tur='PROJE',kimlik=p)],bek='BICIM')
        ac(f,d,'Pim',t(22,'14:20'),baglar=[dict(tur='PROJE',kimlik=p),dict(tur='PROJE',kimlik=q)],bek='BICIM')
        gonder(f,d,'K004','NESNE.GUNCELLEDIM',t(22,'14:25'),dict(hedef=b,degisenler=dict(baglar=[dict(tur='PROJE',kimlik=q)])),b,'NESNE',bek='BICIM')
        self.assertEqual(d.nesneler[b]['proje'],p)
        self.assertEqual({x['kimlik'] for x in oku(d,'K012','NESNELER',proje=p)},{a,b})

    def test_Y104(self):
        f=Duzenek(); d=kur(f,t(23,'07:55'))
        izin=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(23),dict(kisi='K017',tur='YILLIK',baslangic=t(26),bitis=t(26,'18:00'),gerekce='İzin'))
        f.olay('K009','IZIN.ONAYLADIM',t(23),girdiler=dict(hedef=izin))
        self.assertEqual(yaz(d,f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))
        gonder(f,d,'K009','IZIN.ONAYLADIM',t(23,'08:00').replace('08:00:00','08:00:30'),dict(hedef=izin))
        self.assertEqual(d.izinler[izin]['durum'],'ONAYLI')
        g=gonder(f,d,'K004','GOREV.ATADIM',t(23,'10:00'),dict(gorevler=[f.gorev_satiri(ad='Teklif karşılaştırması',kisi='K006',etap=None,onay_gerekli=True,onaylayan='K004',teslim_tarihi='2026-10-23',teslim_saati='17:00')]))+'/1'
        gonder(f,d,'K006','GOREV.KABUL_ETTIM',t(23,'10:05'),h=g)
        gonder(f,d,'K006','GOREV.TAMAMLADIM',t(23,'11:00'),h=g)
        gonder(f,d,'K004','GOREV.ONAYLADIM',t(23,'11:00'),h=g,bek='BAYAT')
        gonder(f,d,'K004','GOREV.ONAYLADIM',t(23,'11:00').replace('11:00:00','11:00:20'),h=g)
        self.assertEqual(d.gorevler[g]['durum'],'BITTI')
        g2=gonder(f,d,'K004','GOREV.ATADIM',t(23,'11:30'),dict(gorevler=[f.gorev_satiri(ad='Fiyat listesi',kisi='K006',etap=None,teslim_tarihi='2026-10-24')]))+'/1'
        gonder(f,d,'K004','GOREV.IPTAL_ETTIM',t(23,'11:40'),h=g2)
        d.ilerlet(t(23,'11:45')); f.olay('K006','GOREV.KABUL_ETTIM',t(23,'11:35'),g2)
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[g2]['durum'],'IPTAL'); self.assertNotIn(f.olaylar[-1]['olay_kimligi'],d.supheliler)

    def test_Y105(self):
        f,d=nesneli(); p='2509084'
        a=ac(f,d,'Rulman 6204',t(22,'14:00'),sorumlu='K045',proje=p)
        b=ac(f,d,'Mil',t(22,'14:01'),proje=p)
        gec(f,d,a,'SIPARISTE',t(22,'14:05'),'K045','YETKI')
        gonder(f,d,'K004','GOREV.ATADIM',t(22,'14:10'),dict(gorevler=[f.gorev_satiri(ad='Rulman siparişini takip et',kisi='K045',etap=f.etap['E-SAT'],teslim_tarihi='2026-10-25')]))
        gec(f,d,a,'SIPARISTE',t(22,'14:15'),'K045'); gec(f,d,a,'GELDI',t(22,'14:20'),'K045')
        gec(f,d,b,'SIPARISTE',t(22,'14:25'),'K045','YETKI')
        gonder(f,d,'K045','NESNE.GUNCELLEDIM',t(22,'14:30'),dict(hedef=a,degisenler=dict(ad='Rulman 6204-2RS')),a,'NESNE','YETKI')
        d.ilerlet(t(22,'14:40')); r=oku(d,'K045','TOP_KIMDE',a)
        self.assertEqual((r['asama'],r['sorumlu'],r['asama_ani']),('GELDI','K045',an(t(22,'14:20'))))

    def test_Y106(self):
        f=Duzenek(); d=kur(f,t(26,'08:50'))
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'09:00'),parca_turu())
        a=ac(f,d,'Ana mil',t(26,'10:00'),kim='K006',proje='2509084')
        gec(f,d,a,'ISLEMDE',t(26,'10:10'),'K009'); gec(f,d,a,'FASONDA',t(26,'10:20'),'K009')
        gec(f,d,a,'ISLEMDE',t(26,'10:25'),'K017','YETKI')
        b=ac(f,d,'Şase profili',t(26,'10:30'),kim='K006',proje='2509084')
        gec(f,d,b,'FASONDA',t(26,'10:40')); gec(f,d,b,'MONTAJDA',t(26,'10:45'),bek='DURUM')
        gec(f,d,a,'ISLEMDE',t(27,'09:00')); d.ilerlet(t(27,'10:00'))
        r=oku(d,'K006','TOP_KIMDE',a)
        self.assertEqual(r['asama_dakikalari'],dict(SIPARIS_VERILMELI=10,ISLEMDE=70,FASONDA=1360))
        self.assertEqual([(x['asama'],(x['bitis']-x['baslangic']).total_seconds()/60) for x in d.nesneler[a]['asama_gecmisi']], [('SIPARIS_VERILMELI',10),('ISLEMDE',10),('FASONDA',1360)])
        gec(f,d,b,'GELDI',t(28,'09:00'))

    def test_Y107(self):
        f=Duzenek(); d=kur(f,t(22,'07:50'))
        gonder(f,d,'K001','KOD.TANIMLADIM',t(22),dict(liste='ROL',kod='MALIYET',ad='Maliyet',aktif=True))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'08:05'),dict(kisi='K004',degisenler=dict(roller=['YONETICI','MALIYET']),gecerli_baslangic=t(22,'08:05')))
        for k in ('K004','K001'): self.assertEqual(oku(d,k,'TEZGAH_UCRETI','CNC-02',gun='2026-10-22'),Decimal(200))
        self.assertEqual(oku(d,'K001','SAAT_MALIYETI','CNC-02',gun='2026-10-22'),Decimal(200))
        for k,veri,hedef,kw in [('K006','TEZGAH_UCRETI','CNC-02',dict(gun='2026-10-22')),('K004','SAAT_MALIYETI','K017',dict(gun='2026-10-22')),('K004','MAAS','K017',dict(ay='2026-10'))]:
            with self.assertRaises(PermissionError): oku(d,k,veri,hedef,**kw)

    def test_Y108(self):
        f=Duzenek(); f.olay('K001','YETKI.TANIMLADIM',t(1,'07:10'),girdiler=dict(eylem_kodu='KISI.YETKINLIK_TANIMLADIM',kimler=['BIRIM_YONETICISI','YETKILI'],kapsam='BIRIM'))
        d=kur(f,t(22,'07:55'))
        for k in ('CNC_5_EKSEN','KAYNAK'): gonder(f,d,'K001','KOD.TANIMLADIM',t(22),dict(liste='YETKINLIK',kod=k,ad=k,aktif=True))
        for saat,kim,ys,gun,bek in [('08:05','K009',['CNC_5_EKSEN'],'2026-10-22','BASARILI'),('08:06','K006',['KAYNAK'],'2026-10-22','YETKI'),('08:07','K009',['TORNA'],'2026-10-22','DURUM'),('08:08','K009',['CNC_5_EKSEN'],'2026-10-21','DURUM')]:
            gonder(f,d,kim,'KISI.YETKINLIK_TANIMLADIM',t(22,saat),dict(kisi='K017',yetkinlikler=ys,gecerli_baslangic=gun),bek=bek)
        i=gonder(f,d,'K009','IS.TANIMLADIM',t(22,'08:10'),dict(isler=[dict(birim='IMALAT',proje='2509084',nereye='PROJE',islem='5 eksen frezeleme',tur='SURELI',tahmini_sure_dk=120,yetkinlik='CNC_5_EKSEN',onay_gerekli=False)]))
        gonder(f,d,'K009','IS.ATADIM',t(22,'08:15'),dict(kisi='K023',sira=1),i,'IS')
        rows={x['kimlik']:x for x in oku(d,'K006','KISILER',birim='IMALAT')}
        self.assertEqual(rows['K017']['yetkinlikler'],['CNC_5_EKSEN']); self.assertEqual(rows['K023']['yetkinlikler'],[])
        self.assertEqual(d.isler[i]['yetkinlik'],'CNC_5_EKSEN')

    def test_Y109(self):
        f=ek_yetki(proje_duzenegi()); d=kur(f,t(22,'13:50'))
        for m in ('M3','M8'): gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'13:51'),dict(kod=m,ad=m,servis_kimligi='SRV-'+m,aktif=True))
        et=gonder(f,d,'K001','ETAP.TANIMLADIM',t(22,'13:55'),dict(proje='2509091',ad='E-IML2',birim='IMALAT',baslangic='2026-10-26',bitis='2026-11-30',hedef_saat=40))
        ids=[]
        for saat,p,etap,ad,dak,bas,bit in [('14:00','2509091',et,'Pres plakası frezeleme',180,'08:00','11:00'),('14:10','2509084',f.etap['E-IML'],'Mil frezeleme',120,'10:00','12:00')]:
            i=gonder(f,d,'K004','IS.TANIMLADIM',t(22,saat),dict(isler=[dict(nereye='PROJE',proje=p,etap=etap,birim='IMALAT',islem=ad,tur='SURELI',tahmini_sure_dk=dak,tezgah='CNC-02',onay_gerekli=False)])); ids.append(i)
            gonder(f,d,'K004','PLAN.TARIHLEDIM',t(22,saat[:-1]+'5'),dict(hedefler=[dict(tur='IS',kimlik=i,planlanan_baslangic=t(3,bas,11),planlanan_bitis=t(3,bit,11))]),i,'IS')
        izin=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(22,'14:20'),dict(kisi='K017',tur='YILLIK',baslangic=t(23),bitis=t(23,'18:00'),gerekce='İzin'))
        gonder(f,d,'K009','IZIN.ONAYLADIM',t(22,'14:21'),dict(hedef=izin))
        c=oku(d,'K012','PLAN_CAKISMALARI','CNC-02',bas='2026-11-03',bit='2026-11-04')
        self.assertEqual(len(c),1); self.assertEqual(c[0]['hedefler'],[dict(tur='ERISIM_DISI'),dict(tur='IS',kimlik=ids[1])])
        self.assertEqual(len(oku(d,'K004','PLAN_CAKISMALARI','CNC-02',bas='2026-11-03')),1)
        ys=oku(d,'K012','KAYNAK_YUKU',tur='TEZGAH',kimlik='CNC-02',bas='2026-11-03')
        self.assertEqual(ys[0],dict(proje='ERISIM_DISI',planlanan_baslangic=an(t(3,'08:00',11)),planlanan_bitis=an(t(3,'11:00',11))))
        self.assertNotIn(ids[0],str(c)+str(ys)); self.assertNotIn('2509091',str(c)+str(ys))
        b=next(x for x in oku(d,'K012','GANTT','2509084',bas='2026-11-03') if x['kimlik']==ids[1])
        self.assertEqual((b['tezgah'],b['kisi']),('CNC-02',None))
        for kim,neden in [('K012','MUSAIT_DEGIL'),('K009','IZIN')]:
            cal=oku(d,kim,'TAKVIM',tur='KISI',kimlik='K017',bas='2026-10-22',bit='2026-10-24')
            self.assertIn(dict(bas=an(t(23)),bit=an(t(23,'18:00')),neden=neden),cal['kapali'])
        with self.assertRaisesRegex(ValueError,'TANIMSIZ_VERI'): oku(d,'K012','KISI')
        self.assertTrue({'K009','K017','K023'} <= {x['kimlik'] for x in oku(d,'K012','KISILER',birim='IMALAT')})
        self.assertTrue(oku(d,'K012','TEZGAH_UYGUNLUK','CNC-02',bas=t(3,'08:00',11),bit=t(3,'09:00',11))['uygun'])
        self.assertEqual(oku(d,'K012','KAPASITE','K017',bas='2026-10-23'),0)
        r=d.modul_bildirimi_birak('SRV-M3','M3','GECIKTI',dict(tur='PROJE',kimlik='2509091'),[dict(tur='KISI',kimlik=k) for k in ('K012','K004')],'Geç','UYARI',d.saat.simdi())
        self.assertEqual(r['alicilar'],['K004']); self.assertEqual(r['suzulenler'],[dict(kisi='K012',neden='PROJEYI_GOREMEZ')])

    def test_Y110(self):
        f,d=nesneli(False)
        bt=belge_turu(); bt['baglanabilir_turler']=['PROJE','NESNE']
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'08:55'),bt)
        p=ac(f,d,'Ana mil',t(26,'09:00'),kim='K006',proje='2509084')
        r=gonder(f,d,'K012','NESNE.ACTIM',t(26,'09:05'),dict(tur='BELGE',ad='Ana mil resmi',proje='2509084',sorumlu='K041',baglar=[dict(tur='NESNE',kimlik=p)]))
        q=ac(f,d,'Mil burcu',t(26,'09:06'),kim='K006',proje='2509084',baglar=[dict(tur='NESNE',kimlik=p)])
        for n,k,saat,atanan in [(p,'K023','09:10','09:12'),(q,'K017','09:13','09:14')]:
            i=gonder(f,d,'K009','IS.TANIMLADIM',t(26,saat),dict(isler=[dict(nereye='PROJE',proje='2509084',birim='IMALAT',islem='Tornalama',tur='SURELI',tahmini_sure_dk=60,onay_gerekli=False)]),n,'NESNE')
            gonder(f,d,'K009','IS.ATADIM',t(26,atanan),dict(kisi=k,sira=1),i,'IS')
        gonder(f,d,'K012','GOREV.ATADIM',t(26,'09:15'),dict(gorevler=[f.gorev_satiri(ad='Resim kontrolü',kisi='K044',teslim_tarihi='2026-10-27')]),r,'NESNE')
        surum_olayi(f,d,r,'EKLEDIM',t(26,'09:20'),kim='K041',ad='Rev02'); surum_olayi(f,d,r,'ONAYLADIM',t(26,'09:25'))
        self.assertEqual(sorted(x['alici'] for x in d.bildirimler.values() if x['kural']=='R43' and x['gecerli']),['K023','K044'])
        gonder(f,d,'K009','AYAR.YONLENDIRDIM',t(26,'09:26'),dict(birim='IMALAT',kisiler=['K009']))
        n=gonder(f,d,'K006','NOT.YAZDIM',t(26,'09:30'),dict(metin='Malzeme 42CrMo4 geldi',etiketler=['IMALAT']),p,'NESNE')
        self.assertEqual(d.gorevler[n+'/1']['kisi'],'K009')

    def test_Y111(self):
        f=Duzenek(); d=kur(f,t(22,'07:55'))
        g=dict(kod='M3',ad='İmalat hazırlık',servis_kimligi='SRV-M3',aktif=True,cihaz_harfi='P')
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22),g)
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'08:01'),dict(g,kod='M8',servis_kimligi='SRV-M8'),bek='DURUM')
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'08:02'),dict(g,kod='M8',servis_kimligi='SRV-M8',cihaz_harfi='PP'),bek='BICIM')
        for harf,cihaz,metin in [('M','MAS-K006','Teklif istendi'),('P','MODUL-M3','Sipariş verildi')]:
            gonder(f,d,'K006','NOT.YAZDIM',t(22,'09:00'),dict(metin=metin),'2509084','PROJE',harf=harf,cihaz=cihaz)
        self.assertEqual(len(d.notlar),2)
        self.assertNotEqual(d.cihaz_kaydol('K006','YENI'),'P')

    def test_Y112(self):
        f=Duzenek(); f.ata(1); d=kur(f,t(23,'10:00'))
        gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(23,'11:00'),dict(kisi='K017',tarih='2026-10-24',baslangic=t(24,'20:00'),bitis=t(25,'02:00'),aciklama='Sevkiyat'),1,'IS')
        for kim,kod,zaman,n in [('K017','MESAI.GIRDIM',t(24,'20:00'),None),('K017','IS.BASLADIM',t(24,'20:00'),1),('K017','IS.TAMAMLADIM',t(25,'02:00'),1),('K017','MESAI.CIKTIM',t(25,'02:00'),None)]:
            gonder(f,d,kim,kod,zaman,h=n)
        rows=[x for x in fazla_mesai_kayitlari(d) if x['kisi']=='K017']
        self.assertEqual(sum(x['prim'] for x in rows),Decimal('444.44'))
        gunler={}
        for a in d.araliklar:
            if a['kisi']=='K017' and a['kova']=='CALISMA': gunler[str(a['gun'])]=gunler.get(str(a['gun']),0)+(a['bitis']-a['baslangic']).total_seconds()/3600
        self.assertEqual(gunler,{'2026-10-24':4,'2026-10-25':2})
