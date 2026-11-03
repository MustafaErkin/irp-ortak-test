"""Sözleşme testlerinin ortak adımları."""

PO_DOSYASI = {'ad': 'PO1246789.pdf', 'konum': '\\\\sunucu\\satis\\2611001\\PO1246789.pdf'}
SOZLESME = {'ad': 'Sozlesme_imzali.pdf', 'konum': '\\\\sunucu\\satis\\2611001\\sozlesme.pdf'}


def govde(on: dict, **ek) -> dict:
    g = {k: on[k] for k in ('surum', 'proje_adi', 'sorumlu', 'siparis_tarihi', 'teslim_tarihi', 'kesin_kabul_tarihi')}
    g.update(ek)
    return g


def donustur(api, kisi='K050', surum=57, **ek):
    on = api('GET', kisi, f'/donustur/onizleme?surum={surum}')
    assert on.status_code == 200, on.json()
    return api('POST', kisi, '/donustur', json=govde(on.json(), **ek))


def ac(api, kisi='K050', surum=57, **ek) -> str:
    r = donustur(api, kisi, surum, **ek)
    assert r.status_code == 200, r.json()
    return r.json()['proje']


def _y(api, eylem, girdiler, kim='K001', neyin_ustunde=()):
    c = api.c.surucu.yetkili_olay(eylem, girdiler, kim=kim, neyin_ustunde=neyin_ustunde)
    assert c['sonuc'] == 'BASARILI', (eylem, c)
    return c


def erisim_ver(api, kisi, proje='2611001'):
    """Yetkili çekirdeğin Proje erişimi ekranından (M11A-01)."""
    _y(api, 'PROJE.ERISIM_VERDIM', {'proje': proje, 'kisi': kisi, 'gerekce': 'M1.1A sınaması'})


def etap_ve_gorev(api, proje='2611001'):
    """M11A04'ün zemini: MEK_TASARIM etabı (K012), K012 K041'e görev atar; K041 kabul eder, 05.11.2026 15:00'te
    tamamlar. Görev kabulü ve tamamlanması neyin_ustunde'de görevin sürümünü taşır."""
    _y(api, 'ETAP.TANIMLADIM', {'proje': proje, 'ad': 'Mekanik tasarım (3D/2D)', 'birim': 'MEK_TASARIM',
                                'sorumlu': 'K012', 'baslangic': '2026-11-02', 'bitis': '2026-12-13',
                                'hedef_saat': 120})
    k050 = api.c.giris('K050', 'deneme')
    etap = k050.oku('ETAPLAR', proje=proje).deger[0]['kimlik']
    _y(api, 'GOREV.ATADIM', {'gorevler': [{'kisi': 'K041', 'ad': 'Mekanik tasarım', 'nereye': 'PROJE',
                                           'proje': proje, 'etap': etap, 'teslim_tarihi': '2026-11-06',
                                           'zaman_degeri': 16, 'zorluk': 1, 'onay_gerekli': False,
                                           'dosya_gerekli': False}]}, kim='K012')
    k041 = api.c.giris('K041', 'deneme')
    g = k041.oku('GOREV', 'K041').deger[0]
    _y(api, 'GOREV.KABUL_ETTIM', {}, kim='K041', neyin_ustunde=[k041.hedef('GOREV', g)])
    g = k041.oku('GOREV', g['kimlik']).deger
    api.c.surucu.saat('2026-11-05T15:00:00+03:00')
    _y(api, 'GOREV.TAMAMLADIM', {}, kim='K041', neyin_ustunde=[k041.hedef('GOREV', g)])


def parcalar(api, hazir=1, toplam=4, proje='2611001'):
    for n in range(1, toplam + 1):
        _y(api, 'NESNE.ACTIM', {'tur': 'PARCA', 'ad': f'Fikstür parçası {n}', 'kod': f'FX-{n:03d}', 'proje': proje,
                                'sorumlu': 'K012', 'baglar': [{'tur': 'PROJE', 'kimlik': proje}]})
    k001 = api.c.giris('K001', 'deneme')
    for x in k001.oku('NESNELER', proje=proje).deger[:hazir]:
        _y(api, 'NESNE.ASAMA_GECIRDIM', {'hedef': x['kimlik'], 'yeni_asama': 'MONTAJA_HAZIR', 'gerekce': 'hazır'},
           neyin_ustunde=[k001.hedef('NESNE', x)])


BELGE = {'ad': 'Kapsam_degisikligi.pdf', 'konum': '\\\\sunucu\\satis\\2611001\\kapsam.pdf'}
BUTCE = {'MALZEME': '32500.00', 'ISCILIK': '10000.00', 'FASON': '1000.00', 'GENEL_GIDER': '0.00'}


def tutar_degistir(api, kisi='K050', proje='2611001', yeni_tutar='56000.00', gerekce='Kapsam değişti', **kalemler):
    return api('POST', kisi, f'/projeler/{proje}/tutar-degisikligi',
               json={'yeni_tutar': yeni_tutar, 'butce': {**BUTCE, **kalemler}, 'gerekce': gerekce,
                     'belge_dosyasi': BELGE})


def kutu(api, kisi):
    return sorted(x['kural'] for x in api.c.giris(kisi, 'deneme').oku('BILDIRIMLER', kisi).deger
                  if x.get('kaynak') == 'M11A')
