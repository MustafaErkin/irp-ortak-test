"""V5: servis kurulumu ve normal yol; ortak yukleyiciden bagimsiz."""
from copy import deepcopy
from irp import Depo, Saat, an
from irp.kabul import nesne, TANIKLIK
from irp.kapilar_v3 import liste_hedefleri
from .ortak import Duzenek, t, is_id


def gonder(f, d, kim, kod, zaman, hedef=None, girdiler=None, bek='BASARILI', hassas_ek=None, **alan):
    if an(zaman) > d.saat.simdi(): d.ilerlet(zaman)
    k = f.olay(kim, kod, zaman, hedef, girdiler, **alan)
    e = deepcopy(f.olaylar[-1])
    if kod not in TANIKLIK:
        for kisi in liste_hedefleri(e):
            e['neyin_ustunde'].append({'tur': 'LISTE', 'kimlik': kisi})
        for h in e['neyin_ustunde']: h['surum'] = nesne(d, h['tur'], h['kimlik']).get('surum')
    s = d.olay_ekle(e, oturum=kim, hassas_ek=hassas_ek)
    if bek is not None: assert s.get('kod', s['sonuc']) == bek, (kod, girdiler, s)
    assert not d.isleme_hatalari, d.isleme_hatalari
    return k, s


def is_satiri(f, **alan):
    s = {'islem': '063 Kaynak', 'birim': 'IMALAT', 'nereye': 'PROJE', 'proje': '2509084', 'etap': f.etap['E-IML'],
         'parca_kodu': '2509084_07_04-63', 'tur': 'SURELI', 'tahmini_sure_dk': 120, 'onay_gerekli': True, 'onay_beklet': False, 'on_isler': []}
    s.update(alan); return s


def onaysiz_bekleme(ikinci=True):
    f = Duzenek()
    i = f.olay('K004', 'IS.TANIMLADIM', t(21), girdiler={'isler': [is_satiri(f)]})
    f.ata(i, sira=1)
    if ikinci: f.ata(2, sira=2)
    f.is_olay('MESAI.GIRDIM', '07:58'); f.is_olay('BASLADIM', '08:00', i)
    d = f.calistir(t(22, '08:01'))
    return f, d, i


def kurulum_paketi(f):
    zaman = t(1, '07:00')
    for kod, g in [('AYAR.ONAY_ORANI', {'deger': .1}),
                   ('AYAR.MAAS_PAYDASI', {'deger': 180, 'gecerli_baslangic': t(1, '00:00')}),
                   ('AYAR.PARCA_KODU_DESENI', {'deger': r'^\d{7}_\d{2}_\d{2}-\d{2}$'}),
                   ('TAKVIM.TANIMLADIM', dict(Depo(Saat(zaman)).varsayilan_takvim, gecerli_baslangic=t(1, '00:00'))),
                   ('TATIL.EKLEDIM', {'tarih': '2026-10-29', 'ad': 'Cumhuriyet'}),
                   ('BIRIM.TANIMLADIM', {'kod': 'YONETIM', 'ad': 'Yonetim', 'tur': 'MASA_BASI', 'basi': None}),
                   ('KISI.EKLEDIM', {'kod': 'K001', 'ad': 'Yetkili', 'birim': 'YONETIM', 'yaka': 'BEYAZ', 'roller': ['YETKILI', 'YONETICI'], 'giris_tarihi': '2026-10-01'}),
                   ('BIRIM.TANIMLADIM', {'kod': 'YONETIM', 'ad': 'Yonetim', 'tur': 'MASA_BASI', 'basi': 'K001'})]:
        f.olay('K001', kod, zaman, girdiler=g, giris_sekli='AKTARIM')
    from irp.yetki_v6 import varsayilan_kodlar, varsayilan_yetkiler
    for g in varsayilan_kodlar().values():
        f.olay('K001', 'KOD.TANIMLADIM', zaman, girdiler=g, giris_sekli='AKTARIM')
    for g in varsayilan_yetkiler(surum=9):
        f.olay('K001', 'YETKI.TANIMLADIM', zaman, girdiler=g, giris_sekli='AKTARIM')
    f.olay('K001', 'KURULUM.TAMAMLADIM', zaman, giris_sekli='AKTARIM')
    return deepcopy(f.olaylar)


def sifirdan():
    f = Duzenek(ortak=False); d = Depo(Saat(t(1, '07:00')))
    s = d.kurulum(kurulum_paketi(f), {'ariza': ['ARIZA.DIGER'], 'mola': ['KISISEL'], 'pd': ['PD.IDARI_MALI']}, servis=True)
    assert s['sonuc'] == 'BASARILI', s
    adimlar = []
    def birim(k, tur, ust, basi=None):
        adimlar.append(('BIRIM.TANIMLADIM', {'kod': k, 'ad': k, 'tur': tur, 'ust_birim': ust, 'basi': basi}))
    def kisi(k, b, yaka, rol):
        adimlar.append(('KISI.EKLEDIM', {'kod': k, 'ad': k, 'birim': b, 'yaka': yaka, 'roller': [rol], 'giris_tarihi': '2026-10-01'}))
    birim('PLANLAMA', 'MASA_BASI', 'YONETIM'); kisi('K004', 'PLANLAMA', 'BEYAZ', 'YONETICI'); birim('PLANLAMA', 'MASA_BASI', 'YONETIM', 'K004')
    birim('IMALAT', 'ATOLYE', 'PLANLAMA'); kisi('K009', 'IMALAT', 'MAVI', 'EKIP_LIDERI'); birim('IMALAT', 'ATOLYE', 'PLANLAMA', 'K009')
    kisi('K017', 'IMALAT', 'MAVI', 'CALISAN')
    birim('MEK_TASARIM', 'MASA_BASI', 'YONETIM'); kisi('K012', 'MEK_TASARIM', 'BEYAZ', 'YONETICI'); birim('MEK_TASARIM', 'MASA_BASI', 'YONETIM', 'K012')
    kisi('K041', 'MEK_TASARIM', 'BEYAZ', 'BEYAZ_YAKA')
    adimlar += [('TEZGAH.TANIMLADIM', {'kod': 'CNC-02', 'ad': 'CNC', 'birim': 'IMALAT'}),
                ('PROJE.ACTIM', {'kod': '2509084', 'ad': 'Rulman cakma', 'teslim_tarihi': '2027-01-29'})]
    for n, (kod, g) in enumerate(adimlar): gonder(f, d, 'K001', kod, t(1, '09:%02d' % n), girdiler=g)
    for n, (ad, b, bit, saat) in enumerate([('E-TAS', 'MEK_TASARIM', '2026-11-20', 400), ('E-IML', 'IMALAT', '2026-12-25', 1200)]):
        f.etap[ad], _ = gonder(f, d, 'K004', 'ETAP.TANIMLADIM', t(1, '09:%02d' % (13+n)), girdiler={'proje': '2509084', 'ad': ad, 'birim': b, 'baslangic': '2026-10-01', 'bitis': bit, 'hedef_saat': saat})
    i, _ = gonder(f, d, 'K004', 'IS.TANIMLADIM', t(1, '09:15'), girdiler={'isler': [is_satiri(f, onay_gerekli=False, tahmini_sure_dk=180)]})
    gonder(f, d, 'K009', 'IS.ATADIM', t(1, '16:00'), i, {'kisi': 'K017', 'sira': 1})
    g, _ = gonder(f, d, 'K012', 'GOREV.ATADIM', t(1, '16:10'), girdiler={'gorevler': [f.gorev_satiri(ad='Montaj resmi', teslim_tarihi='2026-10-09', zaman_degeri=20)]})
    g += '/1'
    for kim, kod, saat, h in [('K017', 'MESAI.GIRDIM', '07:58', None), ('K017', 'IS.BASLADIM', '08:00', i), ('K041', 'GOREV.KABUL_ETTIM', '09:00', g), ('K017', 'IS.DEVAM_ETTIM', '10:15', i), ('K017', 'IS.TAMAMLADIM', '11:00', i)]:
        gonder(f, d, kim, kod, t(2, saat), h)
    d.ilerlet(t(2, '11:05'))
    return f, d, i, g
