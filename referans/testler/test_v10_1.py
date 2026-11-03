"""Y100–Y102: belgedeki saatler ve bağımsız sayısal beklentiler."""
import unittest
from copy import deepcopy
from irp import an
from irp.gorunum_v10_1 import gantt, plan_cakismalari, gecerli_surum, surumler, bildirim_kutusu
from irp.gorunum_v9 import okunmamis_bildirimler
from irp.yetki_v6 import varsayilan_yetkiler
from .ortak import Duzenek, s1, t, is_id, yaz
from .test_v7 import kur, gonder
from .test_v10 import proje_duzenegi


def ek_yetki(f):
    for r in varsayilan_yetkiler():
        if r['eylem_kodu'] in ('PLAN.TARIHLEDIM', 'MODUL.TANIMLADIM'):
            f.olay('K001', 'YETKI.TANIMLADIM', t(1, '07:10'), girdiler=r)
    return f


def plan(n, bas, bit, tur='IS'):
    return dict(tur=tur, kimlik=is_id(n) if isinstance(n,int) else n, planlanan_baslangic=bas, planlanan_bitis=bit)


def tarih(f, d, hedefler, zaman, kim='K004', bek='BASARILI'):
    return gonder(f,d,kim,'PLAN.TARIHLEDIM',zaman,dict(hedefler=hedefler,kaynak='Planlama'),
        [dict(tur=s['tur'],kimlik=s['kimlik']) for s in hedefler],bek=bek)


def belge_turu(**kw):
    return dict(kod='BELGE',ad='Belge',asamalar=['CALISILIYOR',dict(kod='TAMAM',son=True)],baslangic_asamasi='CALISILIYOR',
        gecisler=[dict(den='CALISILIYOR',e='TAMAM',kimler=['YONETICI'])],baglanabilir_turler=['IS','GOREV','PROJE'],
        acabilenler=dict(kimler=['YONETICI'],kapsam='FIRMA'),**kw)


def belge_duzenegi():
    f=ek_yetki(Duzenek())
    f.olay('K001','NESNE_TURU.TANIMLADIM',t(20,'09:00'),girdiler=belge_turu(surum_onaylayanlar=None))
    n=f.olay('K012','NESNE.ACTIM',t(22,'09:00'),girdiler=dict(tur='BELGE',ad='Konveyör montaj resmi',proje='2509084',sorumlu='K041'))
    oid=f.olay('K012','GOREV.ATADIM',t(22,'09:30'),[dict(tur='NESNE',kimlik=n)],dict(gorevler=[f.gorev_satiri(ad='PLC yerleşimi',kisi='K044',teslim_tarihi='2026-10-24',zaman_degeri=4,zorluk=1)]))
    g=oid+'/1'; f.gorev_olay('KABUL_ETTIM',t(22,'09:45'),g,'K044')
    return f,kur(f,t(22,'09:50')),n,g


def surum_olayi(f,d,n,kod,zaman,kim='K012',no=1,ad=None,dosyalar=None,bek='BASARILI',gerekce='Yanlış dosya'):
    g=dict(hedef=n)
    if kod=='EKLEDIM': g.update(dosyalar=dosyalar if dosyalar is not None else ['F-'+str(no)],surum_adi=ad,aciklama='Çizim')
    else: g['surum_no']=no
    if kod=='GERI_CEKTIM': g['gerekce']=gerekce
    return gonder(f,d,kim,'NESNE.SURUM_'+kod,zaman,g,n,'NESNE',bek,
        kanit=[dict(dosya_kimligi=k,parmak_izi='sha-'+k) for k in g.get('dosyalar',[])])


def modul_duzenegi(uyeler=False):
    f=ek_yetki(proje_duzenegi() if uyeler else Duzenek())
    for m in ('M3','M8'):
        f.olay('K001','MODUL.TANIMLADIM',t(22,'08:00'),girdiler=dict(kod=m,ad=m,servis_kimligi='SRV-'+m,aktif=True))
    return f,kur(f,t(22,'09:00'))


def birak(d,zaman,**kw):
    d.ilerlet(zaman)
    args=dict(servis_kimligi='SRV-M3',modul='M3',kural='SIPARIS_GECIKTI',kayit=dict(tur='IS',kimlik=is_id(4)),
        alicilar=[dict(tur='BIRIM_YONETICILERI',kimlik='IMALAT'),dict(tur='KISI',kimlik='K006')],
        metin='Rulman siparişi 3 gün gecikecek',onem='UYARI',an=zaman)
    args.update(kw)
    return d.modul_bildirimi_birak(**args)


class SenaryolarV10_1(unittest.TestCase):
    def test_Y100(self):
        f=ek_yetki(s1())
        for e in f.olaylar:
            if e['eylem_kodu']=='IS.ATADIM': e['oldugu_an']=e['bildigi_son_hal_ani']=t(21,'16:00' if e['girdiler']['sira']==1 else '16:01')
        f.ata(4,sira=3,zaman=t(21,'16:02'))
        hs=[plan(1,t(22),t(22,'11:00')),plan(2,t(22,'11:00'),t(22,'13:00')),plan(4,t(22,'10:00'),t(22,'15:00'))]
        f.olay('K004','PLAN.TARIHLEDIM',t(21,'10:00'),[dict(tur='IS',kimlik=s['kimlik']) for s in hs],dict(hedefler=hs,kaynak='Planlama'))
        g=f.gorev_ata(t(22,'09:00'),ad='Montaj resmi',teslim_tarihi='2026-10-23',zaman_degeri=8,planlanan_baslangic=t(22,'13:00'))
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g)
        d=kur(f,t(21,'17:00'))
        c=plan_cakismalari(d,'K017','2026-10-22')
        self.assertEqual([(x['baslangic'],x['bitis']) for x in c],[(an(t(22,'10:00')),an(t(22,'11:00'))),(an(t(22,'11:00')),an(t(22,'13:00')))])
        for e in sorted([e for e in f.olaylar if an(e['oldugu_an'])>d.saat.simdi()],key=lambda x:(x['oldugu_an'],x['olay_kimligi'])):
            d.ilerlet(e['oldugu_an']); self.assertEqual(yaz(d,e)['sonuc'],'BASARILI')
        d.ilerlet(t(22,'12:00')); rows={s['kimlik']:s for s in gantt(d,'2509084','2026-10-22')}
        self.assertEqual((rows[is_id(1)]['gerceklesen_baslangic'],rows[is_id(1)]['gerceklesen_bitis'],rows[is_id(1)]['sapma']),
            (an(t(22,'08:05')),an(t(22,'11:40')),dict(tur='BITIS',dakika=40)))
        self.assertEqual((rows[is_id(2)]['durum'],rows[is_id(2)]['sapma']),('CALISILIYOR',None))
        self.assertEqual(rows[is_id(4)]['sapma'],dict(tur='BASLAMADI'))
        self.assertEqual((rows[g]['planlanan_bitis'],rows[g]['gerceklesen_baslangic'],rows[g]['durum'],rows[g]['sapma']),
            (an(t(23,'18:00')),an(t(22,'09:30')),'ACIK',None))
        self.assertEqual(len(plan_cakismalari(d,'K017','2026-10-22')),1)
        tarih(f,d,[plan(4,t(22,'13:00'),t(22,'18:00'))],t(22,'12:05'))
        tarih(f,d,[plan(1,t(22,'13:00'),t(22,'14:00'))],t(22,'12:06'),bek='DURUM')
        tarih(f,d,[plan(2,t(22,'14:00'),t(22,'13:00'))],t(22,'12:07'),bek='BICIM')
        tarih(f,d,[plan(2,t(22,'13:00'),t(22,'14:00')),plan(1,t(22,'13:00'),t(22,'14:00'))],t(22,'12:08'),bek='DURUM')
        tarih(f,d,[plan(2,t(22,'13:00'),t(22,'14:00'))],t(22,'12:09'),kim='K017',bek='YETKI')
        d.ilerlet(t(22,'12:10')); self.assertEqual(plan_cakismalari(d,'K017','2026-10-22'),[])
        self.assertEqual(d.isler[is_id(2)]['planlanan_baslangic'],an(t(22,'11:00')))

    def test_Y101(self):
        f,d,n,g=belge_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041',ad='R0')
        d.ilerlet(t(22,'10:05')); self.assertIsNone(gecerli_surum(d,n))
        self.assertEqual(surumler(d,n,cagiran='K044'),[]); self.assertEqual(len(surumler(d,n,cagiran='K012')),1)
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:30'),kim='K041',bek='YETKI')
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'11:00'))
        self.assertEqual(gecerli_surum(d,n)['surum_no'],1)
        surum_olayi(f,d,n,'EKLEDIM',t(23,'09:00'),kim='K041',no=2,ad='R1')
        self.assertEqual(gecerli_surum(d,n)['surum_no'],1)
        surum_olayi(f,d,n,'ONAYLADIM',t(23,'10:00'),no=2)
        self.assertEqual(gecerli_surum(d,n)['surum_no'],2)
        surum_olayi(f,d,n,'GERI_CEKTIM',t(23,'11:00'),no=2)
        self.assertEqual(gecerli_surum(d,n)['surum_no'],1)
        self.assertEqual([(s['surum_no'],s['durum'],s['surum_adi']) for s in surumler(d,n)],[(1,'ONAYLI','R0'),(2,'GERI_CEKILDI','R1')])
        self.assertEqual([(x['alici'],x['an']) for x in d.bildirimler.values() if x['kural']=='R43'],
            [('K044',an(t(22,'11:00'))),('K044',an(t(23,'10:00'))),('K044',an(t(23,'11:00')))])

    def test_Y101b(self):
        f,d,n,g=belge_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041',ad='R0')
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:01'),kim='K041',dosyalar=[],bek='BICIM')
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:02'),kim='K041',no=2,ad='R0',bek='DURUM')
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'10:03'),no=3,bek='DURUM')
        surum_olayi(f,d,n,'GERI_CEKTIM',t(22,'10:04'),gerekce='',bek='BICIM')
        self.assertEqual(len(d.nesne_surumleri),1)

    def test_Y102(self):
        f,d=modul_duzenegi(); kaynak=deepcopy(d._kayitlar); indeks=deepcopy(d.olay_nesneleri)
        r=birak(d,t(22,'10:00')); self.assertEqual((r['yeni'],r['alicilar']),(2,['K006','K009']))
        self.assertEqual(d._kayitlar,kaynak); self.assertEqual(d.olay_nesneleri,indeks)
        self.assertEqual(len([x for x in okunmamis_bildirimler(d,'K006') if x.get('kaynak')=='M3']),1)
        r=birak(d,t(22,'10:05'),metin='Rulman siparişi 4 gün gecikecek'); self.assertEqual((r['yeni'],r['guncellenen']),(0,2))
        key=next(k for k,x in d.modul_bildirimleri.items() if x['alici']=='K009')
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'10:10'),dict(bildirimler=[key]))
        self.assertEqual(d.modul_bildirimleri[key]['gorulme_ani'],an(t(22,'10:10')))
        d.ilerlet(t(22,'10:20')); r=d.modul_bildirimi_kaldir('SRV-M3','M3','SIPARIS_GECIKTI',dict(tur='IS',kimlik=is_id(4)),t(22,'10:20'))
        self.assertEqual(r['kaldirilan'],2); self.assertFalse(any(x['gecerli'] for x in d.modul_bildirimleri.values()))
        self.assertFalse(any(x.get('kaynak')=='M3' for x in okunmamis_bildirimler(d,'K006')))
        once=deepcopy(d.modul_bildirimleri); d.ilerlet(t(22,'10:25')); d.yeniden_kur(); self.assertEqual(d.modul_bildirimleri,once)
        self.assertEqual(len(d.olaylar)-len(kaynak),1)
        self.assertEqual(birak(d,t(22,'10:30'),modul='M8')['kod'],'YETKI')
        self.assertEqual(birak(d,t(22,'10:31'),servis_kimligi='SRV-M9',modul='M9')['kod'],'YETKI')
        self.assertEqual(birak(d,t(22,'10:32'),metin='')['kod'],'BICIM')

    def test_Y102b(self):
        f,d=modul_duzenegi(True); h=dict(tur='PROJE',kimlik='2509091')
        r=birak(d,t(22,'11:00'),kayit=h,alicilar=[dict(tur='KISI',kimlik=k) for k in ('K006','K004')])
        self.assertEqual(r['alicilar'],['K004'])
        r=birak(d,t(22,'11:05'),kayit=h,alicilar=[dict(tur='KISI',kimlik='K006')])
        self.assertTrue(r['alici_kalmadi']); self.assertEqual(len(d.modul_bildirimleri),1)
