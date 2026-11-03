"""Y50-Y67: belge sayilariyla bagimsiz beklentiler, normal kabul kapisi."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp import Depo, Saat, an
from irp.gorunumler import kisinin_gunu, etap_gostergesi, kapasite, maas_dagilimi, yuk
from irp.is_ import emek
from irp.kisi_gunu import kapi
from .ortak import Duzenek, t, is_id
from .v5_destek import gonder, is_satiri, onaysiz_bekleme, sifirdan, kurulum_paketi
from .tur2_ornekler import iki_kisi


def bitir(f, d, i, saat='11:00'):
    if saat >= '10:15': gonder(f, d, 'K017', 'IS.DEVAM_ETTIM', t(22, '10:15'), i)
    gonder(f, d, 'K017', 'IS.TAMAMLADIM', t(22, saat), i)


class SenaryolarV5(unittest.TestCase):
    def test_Y50(self):
        f, d, i = onaysiz_bekleme(); bitir(f, d, i)
        self.assertEqual(d.listeler['K017'], [is_id(2)])
        self.assertEqual(d.isler[i]['tamamlayan'], 'K017')
        self.assertEqual(d.isler[i]['onay_bekleme_ani'], an(t(22, '11:00')))
        self.assertEqual(d.isler[i]['durum'], 'ONAY_BEKLIYOR')
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '11:02'), 2)
        gonder(f, d, 'K009', 'IS.ONAYLADIM', t(22, '11:30'), i)
        d.ilerlet(t(22, '11:35'))
        self.assertEqual(emek(d, i), 165)
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'CALISMA': 198, 'SABIT_MOLA': 15, 'TANIMSIZ': 2})
        self.assertEqual(d.isler[i]['bitis_ani'], an(t(22, '11:30')))
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 2)
        self.assertFalse(d.supheliler)
        self.assertFalse(any(x['kural'] == 'R08' for x in d.bildirimler.values()))

    def test_Y51(self):
        f, d, i = onaysiz_bekleme(); bitir(f, d, i)
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '11:02'), 2)
        gonder(f, d, 'K009', 'IS.REDDETTIM', t(22, '11:30'), i, {'not': 'Dikis eksik'})
        self.assertEqual(d.listeler['K017'], [is_id(2), i]); self.assertEqual(d.kisi_durumu['K017']['acik_is'], is_id(2))
        gonder(f, d, 'K017', 'IS.TAMAMLADIM', t(22, '11:50'), 2)
        gonder(f, d, 'K017', 'IS.DEVAM_ETTIM', t(22, '11:52'), i)
        d.ilerlet(t(22, '11:55'))
        self.assertEqual(emek(d, is_id(2)), 48)
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar']['YENIDEN_ISLEME'], 3)
        self.assertEqual(d.listeler['K017'], [i]); self.assertFalse(d.supheliler)

    def test_Y52(self):
        f, d, i = onaysiz_bekleme(False); bitir(f, d, i, '09:00')
        gonder(f, d, 'K009', 'IS.REDDETTIM', t(22, '09:30'), i, {'not': 'Dikis eksik'})
        self.assertEqual(d.listeler['K017'], [i]); self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')
        gonder(f, d, 'K017', 'IS.DEVAM_ETTIM', t(22, '09:40'), i); d.ilerlet(t(22, '09:45'))
        gun = kisinin_gunu(d, 'K017', '2026-10-22')
        self.assertEqual(gun['kovalar'], {'CALISMA': 60, 'TANIMSIZ': 40, 'YENIDEN_ISLEME': 5})
        self.assertEqual(len([a for a in gun['araliklar'] if a['kova'] == 'TANIMSIZ']), 1)

    def test_Y53(self):
        f, d, i = onaysiz_bekleme()
        e, _ = gonder(f, d, 'K017', 'IS.TAMAMLADIM', t(22, '10:05'), i)
        d.ilerlet(t(22, '10:40'))
        self.assertIn(e, d.supheliler); self.assertEqual(d.isler[i]['durum'], 'ONAY_BEKLIYOR')
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'CALISMA': 120, 'SABIT_MOLA': 15, 'TANIMSIZ': 25})
        self.assertTrue(kapi(d.kisi_durumu['K017'], 'IS.BASLADIM', d.isler[is_id(2)], is_id(2)))

    def test_Y54(self):
        f, i = iki_kisi()
        next(e for e in f.olaylar if e['olay_kimligi'] == i)['girdiler']['isler'][0]['onay_beklet'] = False
        d = f.calistir(t(22, '13:00'))
        self.assertEqual((emek(d, i+'/k1'), emek(d, i+'/k2')), (195, 227))
        self.assertEqual(d.isler[i]['durum'], 'BITTI')
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 6)
        self.assertFalse(any(a['kova'] == 'BEKLEME_ONAY' for a in d.araliklar))
        for k in ('K017', 'K023'): self.assertEqual(d.listeler[k], [])

    def test_Y55(self):
        f, d, i = onaysiz_bekleme()
        # Biçim eksikliginde eski fixture tamamlamasini kasitli atla.
        s = is_satiri(f); s.pop('onay_beklet')
        f.olay('K004', 'IS.TANIMLADIM', t(22, '08:01'), girdiler={'isler': [s]})
        e = deepcopy(f.olaylar[-1]); e['girdiler']['isler'][0].pop('onay_beklet')
        self.assertEqual(d.olay_ekle(e)['kod'], 'BICIM')
        bitir(f, d, i, '09:00')
        gonder(f, d, 'K009', 'IS.DEGISTIRDIM', t(22, '09:01'), i, {'degisenler': {'onay_beklet': True}}, bek='DURUM')
        gonder(f, d, 'K009', 'IS.ATADIM', t(22, '09:02'), 5, {'kisi': 'K017', 'sira': 1})
        f2 = Duzenek(); j = f2.olay('K004', 'IS.TANIMLADIM', t(21), girdiler={'isler': [is_satiri(f2)]}); f2.ata(j)
        d2 = f2.calistir(t(22, '07:50'))
        gonder(f2, d2, 'K009', 'IS.DEGISTIRDIM', t(22, '07:50'), j, {'degisenler': {'onay_beklet': True}})
        for kod, saat in [('MESAI.GIRDIM', '07:58'), ('IS.BASLADIM', '08:00'), ('IS.TAMAMLADIM', '09:00')]:
            gonder(f2, d2, 'K017', kod, t(22, saat), None if kod.startswith('MESAI') else j)
        self.assertEqual(d2.kisi_durumu['K017']['durum'], 'ONAY_BEKLIYOR')
        gonder(f2, d2, 'K009', 'IS.ATADIM', t(22, '09:01'), 5, {'kisi': 'K017', 'sira': 1}, bek='DURUM')

    def test_Y56(self):
        f = Duzenek(); f.ata(1); f.ata(2, sira=2); f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', 1)
        d = f.calistir(t(22, '08:01'))
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '09:00'), 1, {'gerekce': 'Musteri iptal etti'})
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '09:05'), 2); d.ilerlet(t(22, '09:10'))
        self.assertEqual(d.isler[is_id(1)]['durum'], 'IPTAL'); self.assertEqual(d.listeler['K017'], [is_id(2)])
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'CALISMA': 65, 'GECIS': 5})
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['tamamlanan'], 0)
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['harcanan_emek'], 5/60)  # karar 58: iptal ayri

    def test_Y57(self):
        f = Duzenek(); f.ata(3); f.is_olay('MESAI.GIRDIM', '07:58'); d = f.calistir(t(22, '08:01'))
        gonder(f, d, 'K009', 'IS.IPTAL_ETTIM', t(22, '09:00'), 7, {'gerekce': 'Disaridan alinacak'})
        self.assertFalse(d.isler[is_id(3)]['kilitli']); self.assertEqual(d.kisi_durumu['K017']['durum'], 'CALISMIYOR')
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '09:10'), 3); d.ilerlet(t(22, '09:15'))
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'BEKLEME_ON_IS': 70, 'CALISMA': 5})

    def test_Y58(self):
        f = Duzenek(); f.ata(5); f.ata(2, sira=2); f.is_olay('MESAI.GIRDIM', '07:58'); d = f.calistir(t(22, '08:01'))
        gonder(f, d, 'K009', 'IS.DEGISTIRDIM', t(22, '08:30'), 5, {'degisenler': {'on_isler': [is_id(8)]}})
        self.assertEqual(d.kisi_durumu['K017']['durum'], 'ON_IS_BEKLIYOR')
        gonder(f, d, 'K009', 'IS.SIRALADIM', t(22, '08:40'), 2, {'kisi': 'K017', 'yeni_sira': 1})
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '08:42'), 2)
        gonder(f, d, 'K009', 'IS.DEGISTIRDIM', t(22, '08:50'), 2, {'degisenler': {'on_isler': [is_id(8)]}}, bek='DURUM')
        d.ilerlet(t(22, '08:55'))
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'TANIMSIZ': 30, 'BEKLEME_ON_IS': 10, 'GECIS': 2, 'CALISMA': 13})

    def test_Y59(self):
        f = Duzenek(); d = f.calistir(t(26, '10:00'))
        for kim, p, bek in [('K001', '2509084', 'DURUM'), ('K009', '2509091', 'YETKI'), ('K001', '2509091', 'BASARILI')]:
            gonder(f, d, kim, 'PROJE.KAPATTIM', t(26, '10:00'), p, tur='PROJE', bek=bek)
        for kod, gi, kim in [('IS.TANIMLADIM', {'isler': [is_satiri(f, proje='2509091', etap=None)]}, 'K004'),
                              ('GOREV.ATADIM', {'gorevler': [f.gorev_satiri(proje='2509091', etap=None)]}, 'K012'),
                              ('ETAP.TANIMLADIM', {'proje': '2509091', 'ad': 'Yeni', 'birim': 'IMALAT', 'baslangic': '2026-10-26', 'bitis': '2026-11-01', 'hedef_saat': 10}, 'K004')]:
            gonder(f, d, kim, kod, t(26, '10:01'), girdiler=gi, bek='DURUM')
        for p, bek in [('2509091', 'DURUM'), ('2509084', 'BASARILI')]:
            gonder(f, d, 'K001', 'PROJE.DEGISTIRDIM', t(26, '10:02'), p, {'degisenler': {'teslim_tarihi': '2027-02-26'}}, tur='PROJE', bek=bek)
        gonder(f, d, 'K004', 'ETAP.DEGISTIRDIM', t(26, '10:03'), f.etap['E-IML'], {'degisenler': {'hedef_saat': 1000}}, tur='ETAP')
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['hedef'], 1000)
        gonder(f, d, 'K004', 'ETAP.DEGISTIRDIM', t(26, '10:04'), f.etap['E-IML'], {'degisenler': {'baslangic': '2026-12-25', 'bitis': '2026-11-02'}}, tur='ETAP', bek='DURUM')

    def test_Y60(self):
        f = Duzenek(); f.ata(1); f.gorev_ata(t(22, '09:00'), ad='Kontrol', teslim_tarihi='2026-10-30', zaman_degeri=10); d = f.calistir(t(22, '10:30'))
        def ayril(k, tarih, saat, bek): gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, saat), girdiler={'kisi': k, 'ayrilis_tarihi': tarih}, bek=bek)
        ayril('K017', '2026-10-22', '10:30', 'DURUM')
        gonder(f, d, 'K009', 'IS.DEVRETTIM', t(22, '10:31'), 1, {'kimden': 'K017', 'kime': 'K023', 'kime_sira': 1})
        ayril('K017', '2026-10-21', '10:32', 'DURUM'); ayril('K017', '2026-10-22', '10:33', 'BASARILI')
        gonder(f, d, 'K009', 'IS.ATADIM', t(22, '10:34'), 5, {'kisi': 'K017', 'sira': 1}, bek='DURUM')
        ayril('K009', '2026-10-22', '10:40', 'DURUM'); ayril('K041', '2026-10-22', '10:41', 'DURUM')
        d.ilerlet(t(23, '09:00'))
        gonder(f, d, 'K017', 'NOT.YAZDIM', t(22, '16:00'), '2509084', {'metin': 'Son gun'}, tur='PROJE')
        gonder(f, d, 'K017', 'NOT.YAZDIM', t(23, '08:00'), '2509084', {'metin': 'Ertesi gun'}, tur='PROJE', bek='YETKI')

    def test_Y61(self):
        f, d, i = onaysiz_bekleme(False); bitir(f, d, i, '09:00')
        gonder(f, d, 'K017', 'MESAI.CIKTIM', t(22, '16:00'))
        gonder(f, d, 'K001', 'KISI.AYRILDI', t(22, '16:05'), girdiler={'kisi': 'K017', 'ayrilis_tarihi': '2026-10-22'})
        gonder(f, d, 'K023', 'MESAI.GIRDIM', t(23, '07:58'))
        gonder(f, d, 'K009', 'IS.REDDETTIM', t(23, '09:00'), i, {'not': 'Dikis eksik'})
        self.assertFalse(any(i in l for l in d.listeler.values())); self.assertEqual(d.isler[i]['durum'], 'REDDEDILDI')
        gonder(f, d, 'K009', 'IS.ATADIM', t(23, '09:05'), i, {'kisi': 'K023', 'sira': 1})
        gonder(f, d, 'K023', 'IS.DEVAM_ETTIM', t(23, '09:10'), i); d.ilerlet(t(23, '09:15'))
        self.assertEqual(kisinin_gunu(d, 'K023', '2026-10-23')['kovalar'], {'TANIMSIZ': 70, 'YENIDEN_ISLEME': 5})
        self.assertEqual(emek(d, i), 65)

    def test_Y62(self):
        f = Duzenek(); f.ata(1); d = f.calistir(t(22, '12:00'))
        for k, rol, saat in [('K009', 'CALISAN', '12:00'), ('K023', 'EKIP_LIDERI', '12:01')]:
            gonder(f, d, 'K001', 'KISI.DEGISTIRDIM', t(22, saat), girdiler={'kisi': k, 'degisenler': {'roller': [rol]}, 'gecerli_baslangic': t(22, saat)})
        gonder(f, d, 'K001', 'BIRIM.TANIMLADIM', t(22, '12:02'), girdiler=dict(d.birimler['IMALAT'], basi='K023'))
        d.ilerlet(t(22, '13:00'))
        for kod, saat, h in [('MESAI.GIRDIM', '07:58', None), ('IS.BASLADIM', '08:00', 1)]:
            gonder(f, d, 'K009', kod, t(22, saat), h, adina='K017', harf='T')
        gonder(f, d, 'K009', 'IS.MOLA_VERDIM', t(22, '13:05'), 1, adina='K017', bek='YETKI')
        gonder(f, d, 'K009', 'IS.ATADIM', t(22, '13:06'), 2, {'kisi': 'K017', 'sira': 2}, bek='YETKI')
        gonder(f, d, 'K023', 'IS.ATADIM', t(22, '13:07'), 2, {'kisi': 'K017', 'sira': 2})
        d.ilerlet(t(22, '13:10'))
        self.assertEqual(d.listeler['K017'], [is_id(1), is_id(2)])
        self.assertEqual(kisinin_gunu(d, 'K017', '2026-10-22')['kovalar'], {'CALISMA': 120, 'SABIT_MOLA': 45, 'TANIMSIZ': 145})

    def test_Y63(self):
        f = Duzenek(); d = f.calistir(t(21, '09:00'))
        gonder(f, d, 'K001', 'TEZGAH.TANIMLADIM', t(21, '09:00'), girdiler={'kod': 'CNC-02', 'ad': 'CNC', 'birim': 'IMALAT', 'aktif': False})
        gonder(f, d, 'K004', 'IS.TANIMLADIM', t(21, '09:01'), girdiler={'isler': [is_satiri(f, tezgah='CNC-02', tezgah_rolu='BASLAT')]}, bek='DURUM')
        gonder(f, d, 'K001', 'TEZGAH.TANIMLADIM', t(21, '09:02'), girdiler={'kod': 'CNC-03', 'ad': 'CNC', 'birim': 'PLANLAMA'}, bek='DURUM')
        gonder(f, d, 'K009', 'IS.ATADIM', t(21, '16:00'), 8, {'kisi': 'K023', 'sira': 1})
        gonder(f, d, 'K009', 'IS.ATADIM', t(21, '16:01'), 7, {'kisi': 'K023', 'sira': 2})
        gonder(f, d, 'K009', 'IS.ATADIM', t(21, '16:02'), 3, {'kisi': 'K017', 'sira': 1})
        for k in ('K017', 'K023'): gonder(f, d, k, 'MESAI.GIRDIM', t(22, '07:58'))
        gonder(f, d, 'K023', 'IS.TAMAMLADIM', t(22, '08:30'), 8)
        gonder(f, d, 'K023', 'IS.TAMAMLADIM', t(22, '13:00'), 7)
        gonder(f, d, 'K017', 'IS.BASLADIM', t(22, '13:05'), 3); d.ilerlet(t(22, '13:10'))
        self.assertEqual(sum((a['bitis']-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['kova']=='TEZGAH'), 270)

    def test_Y64(self):
        f, d, i, g = sifirdan()
        self.assertFalse(d.supheliler); self.assertEqual(emek(d, i), 165)
        self.assertEqual(d.listeler['K017'], [])
        self.assertEqual(etap_gostergesi(d, f.etap['E-IML'])['yuzde'], .25)
        self.assertEqual(d.gorevler[g]['durum'], 'ACIK')
        self.assertAlmostEqual(yuk(d, 'K041', '2026-10-02', '2026-10-02'), 20/6)
        self.assertEqual(kapasite(d, 'K041', '2026-10-05', '2026-10-09'), 45)
        self.assertTrue(d.kurulum_tamamlandi)

    def test_Y65(self):
        f, d, i, g = sifirdan()
        birim = dict(d.birimler['IMALAT']); birim.pop('surum')
        kisi = {'kod': 'K050', 'ad': 'Yeni', 'birim': 'YOK', 'yaka': 'BEYAZ', 'roller': ['CALISAN'], 'giris_tarihi': '2026-10-02'}
        etap = {'proje': '2509084', 'ad': 'Yeni', 'birim': 'IMALAT', 'baslangic': '2026-10-01', 'bitis': '2026-11-01', 'hedef_saat': 10}
        denemeler = [('K001', 'KISI.EKLEDIM', kisi, 'DURUM'),
          ('K001', 'BIRIM.TANIMLADIM', dict(birim, kod='SATIS', ust_birim='YOK'), 'DURUM'),
          ('K001', 'BIRIM.TANIMLADIM', {'kod':'YONETIM','ad':'Yonetim','tur':'MASA_BASI','basi':'K001','ust_birim':'IMALAT'}, 'DURUM'),
          ('K001', 'BIRIM.TANIMLADIM', dict(birim, tur='MASA_BASI'), 'DURUM'),
          ('K001', 'BIRIM.TANIMLADIM', dict(birim, basi='K999'), 'DURUM'),
          ('K001', 'TEZGAH.TANIMLADIM', {'kod':'CNC-03','ad':'Yeni','birim':'PLANLAMA'}, 'DURUM'),
          ('K004', 'ETAP.TANIMLADIM', dict(etap, proje='9999999'), 'DURUM'),
          ('K004', 'ETAP.TANIMLADIM', dict(etap, baslangic='2026-11-20'), 'DURUM')]
        for alan in ({'birim':'PLANLAMA'}, {'etap':'E-YOK'}, {'tezgah':'CNC-09'}, {'parca_kodu':'ABC-1'}):
            denemeler.append(('K004', 'IS.TANIMLADIM', {'isler':[is_satiri(f, **alan)]}, 'BICIM' if 'parca_kodu' in alan else 'DURUM'))
        denemeler += [('K012', 'GOREV.ATADIM', {'gorevler':[f.gorev_satiri(kisi='K999')]}, 'DURUM'),
          ('K001','PROJE.ACTIM',{'kod':'2509084','ad':'Tekrar','teslim_tarihi':'2027-01-01'},'DURUM'),
          ('K004','KISI.EKLEDIM',dict(kisi,birim='PLANLAMA'),'YETKI'),
          ('K001','AYAR.MAAS_PAYDASI',{'deger':160,'gecerli_baslangic':t(2,'00:00')},'DURUM'),
          ('K001','AYAR.MAAS_PAYDASI',{'deger':160,'gecerli_baslangic':t(1,'00:00',11)},'BASARILI'),
          ('K001','BIRIM.TANIMLADIM',dict(birim,ad='Imalat ve Kaynak'),'BASARILI')]
        for kim, kod, gi, bek in denemeler: gonder(f,d,kim,kod,t(2,'11:06'),girdiler=gi,bek=bek)
        j,_=gonder(f,d,'K004','IS.TANIMLADIM',t(2,'11:07'),girdiler={'isler':[is_satiri(f)]})
        gonder(f,d,'K009','IS.ATADIM',t(2,'11:08'),j,{'kisi':'K999','sira':1},bek='DURUM')
        self.assertEqual(d.birimler['IMALAT']['basi'],'K009')

    def test_Y66(self):
        f = Duzenek(); d = f.calistir(t(26, '10:00'))
        gonder(f,d,'K001','AYAR.MAAS_PAYDASI',t(26,'10:00'),girdiler={'deger':160,'gecerli_baslangic':t(1,'00:00',11)})
        g,_=gonder(f,d,'K012','GOREV.ATADIM',t(2,'09:00',11),girdiler={'gorevler':[f.gorev_satiri(proje='2509091',etap=None,zaman_degeri=100,teslim_tarihi='2026-11-27')]})
        gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(2,'09:30',11),g+'/1'); d.ilerlet(t(27,'18:00',11))
        maas=maas_dagilimi(d,'K041','2026-11-01')
        self.assertEqual(maas['payda'],160); self.assertEqual(maas['tutarlar']['2509091'],Decimal('12500.00'))
        self.assertEqual(maas['dagitilamayan'],Decimal('7500.00')); self.assertEqual(maas_dagilimi(d,'K041','2026-10-01')['payda'],180)

    def test_Y67(self):
        f=Duzenek(); d=f.calistir(t(26,'10:00'))
        gonder(f,d,'K001','TAKVIM.TANIMLADIM',t(26,'10:00'),girdiler=dict(d.varsayilan_takvim,mesai_bitis='17:00'))
        self.assertEqual(kapasite(d,'K041','2026-10-26','2026-10-30'),33)
        self.assertEqual(kapasite(d,'K041','2026-11-02','2026-11-06'),40)
        gonder(f,d,'K017','MESAI.GIRDIM',t(27,'07:58')); d.ilerlet(t(27,'17:01'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'MESAI_DISI')
        self.assertEqual(d.araliklar[-1]['bitis'],an(t(27,'17:00')))
