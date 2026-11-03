"""M1.1A'nın sağladığı okumalar (SPEC › 8.10, Ek D.7). Her biri önce PROJE'yi kullanıcının gözüyle okur."""
from ..api.hatalar import ModulHatasi
from ..depo import projeler as depo


def kayit(i, proje: str) -> dict:
    """PROJE → 403; M1.1A kaydı yok → 404 BULUNAMADI; ACILIYOR → 409 KAPI."""
    if not proje:
        raise ModulHatasi(422, 'DOGRULAMA', 'proje parametresi gerekli.',
                          hatalar=[{'alan': 'proje', 'sira': None, 'mesaj': 'Gerekli.'}])
    cekirdekte = i.proje(proje)
    p = depo.getir(i.b, proje)
    if not p or (cekirdekte is None and p['durum'] == 'ACIK'):
        raise ModulHatasi(404, 'BULUNAMADI', 'Bu projenin M1.1A kaydı yok.')
    if p['durum'] != 'ACIK':
        raise ModulHatasi(409, 'KAPI', 'Projenin açılışı tamamlanmadı.')
    return p


def baslangic_plani(i, proje: str) -> dict:
    p = kayit(i, proje)
    return i.cevap({
        'proje': p['proje'], 'kaynak': p['teklif_etiketi'], 'siparis_tarihi': p['siparis_tarihi'].isoformat(),
        'teslim_tarihi': p['teslim_tarihi'].isoformat(),
        'kesin_kabul_tarihi': p['kesin_kabul_tarihi'].isoformat() if p['kesin_kabul_tarihi'] else None,
        'teslim_suresi_hafta': p['teslim_suresi_hafta'],
        'etaplar': [dict(s, baslangic=s['baslangic'].isoformat(), bitis=s['bitis'].isoformat())
                    for s in depo.baslangic_plani(i.b, p['proje'])]})


def teklif_girdileri(i, proje: str) -> dict:
    """Gereksinim, kapsam, talep dosyaları, müşteri PDF'inin kaydı; maliyet, kâr ve fiyat yok."""
    p = kayit(i, proje)
    t = p['donmus_teklif']
    from . import teknik
    return i.cevap({'proje': p['proje'], 'kaynak': p['teklif_etiketi'], 'konu': t.get('konu'),
                    'gereksinimler': t.get('gereksinimler') or [],
                    'kapsam': t.get('kapsam') or {'dahil': [], 'haric': []},
                    **teknik.gorunum(i,p),
                    'musteri_pdf': {'ad': p['pdf_ad'], 'parmak_izi': p['pdf_parmak_izi'],
                                    'rol_gerekli': True}})


def butce_yuzdeleri(i, proje: str) -> dict:
    """Tutar yok; her çağrı ölçümü kullanıcının gözüyle yeniden yapar."""
    from . import serit
    p = kayit(i, proje)
    return i.cevap(serit.yuzdeler(p, serit.olc(i, p)))


def proje_butcesi(i, proje: str) -> dict:
    """Görme: ROL (SATIS, MUHASEBE, YETKILI); para. Rol kuralı çekirdeğe gitmeden uygulanır."""
    from . import serit, yetki
    i.rol_gerek(yetki.TUTAR_GORME, 'Bu bilgiyi satış, muhasebe ya da yetkili görür.')
    p = kayit(i, proje)
    pn = serit.panel(i, p, serit.olc(i, p))
    return i.cevap({
        'proje': p['proje'], 'para_birimi': pn['para_birimi'], 'sozlesme_tutari': pn['sozlesme_tutari'],
        'guncel_tutar': pn['guncel_tutar'],
        'kalemler': [{k: x[k] for k in ('kalem', 'baslangic', 'guncel', 'tahmini_gerceklesen', 'kaynak')}
                     for x in pn['kalemler']],
        'degisiklikler': [{k: d[k] for k in ('an', 'kim', 'eski_tutar', 'yeni_tutar', 'gerekce')}
                          for d in pn['degisiklikler']],
        'butce_durumu': p['butce_durumu'],
        'kapanis': pn['kapanis'] and {k: pn['kapanis'][k] for k in ('kesin_kabul_tarihi', 'an', 'farklar',
                                                                   'duzeltmeler')}})


def teklif_pdf(i, proje: str) -> tuple[bytes, str]:
    """Müşteriye giden PDF'i projeyi gören herkes açabilir."""
    from . import yetki
    i.rol_gerek(yetki.TUTAR_GORME,'Onaylı teklifin tutarını görme yetkiniz yok.')
    p = kayit(i, proje)
    pdf = bytes(i.b.execute('SELECT pdf FROM mod_m11a.projeler WHERE proje = %s', (proje,)).fetchone()['pdf'])
    return pdf, p['pdf_ad']


OKUMALAR = {'M11A.BASLANGIC_PLANI': baslangic_plani, 'M11A.TEKLIF_GIRDILERI': teklif_girdileri,
            'M11A.BUTCE_YUZDELERI': butce_yuzdeleri, 'M11A.PROJE_BUTCESI': proje_butcesi}


def oku(i, ad: str, proje: str) -> dict:
    f = OKUMALAR.get(ad)
    if not f:
        raise ModulHatasi(404, 'TANIMSIZ_VERI', f'{ad} okuması yok.')
    return f(i, proje)
