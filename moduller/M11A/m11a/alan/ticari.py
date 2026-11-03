"""PO ve sözleşme, ticari devir formu, dosya kaydı, VEGA kodları (SPEC › 8.2, 8.3, 8.4)."""
from decimal import Decimal

from ..api.hatalar import ModulHatasi, dogrulama
from ..depo import projeler as proje_deposu, ticari as depo
from . import butce, devir, eksik, proje as proje_kaydi, yetki

FORM_ALANLARI = depo.FORM_ALANLARI


def _metinler(satir: dict, alanlar) -> dict:
    return {a: (butce.metin(satir[a]) if isinstance(satir[a], Decimal) else
                satir[a].isoformat() if hasattr(satir[a], 'isoformat') else satir[a]) for a in alanlar}


def form(i, proje: str) -> dict:
    i.rol_gerek(yetki.TUTAR_GORME, 'Ticari bilgileri satış, muhasebe ya da yetkili görür.')
    p = proje_kaydi.kayit(i, proje)
    t = depo.kosullar(i.b, proje)
    odemeler, teminatlar = depo.odemeler(i.b, proje), depo.teminatlar(i.b, proje)
    eksikler = eksik.eksik_alanlar(p['po_no'], p['sozlesme_dosyasi'], t, len(odemeler), len(teminatlar))
    toplam = butce.odeme_toplami(odemeler, p['para_birimi'], p['kurlar'])
    uyarilar = []
    if odemeler and toplam != p['guncel_tutar']:
        uyarilar.append('Ödeme takvimi güncel tutarla tutmuyor.')
    d = depo.devir(i.b, proje)
    return i.cevap({
        'proje': proje, 'surum': t['surum'], 'para_birimi': p['para_birimi'],
        'guncel_tutar': butce.metin(p['guncel_tutar']),
        **{a: t[a] for a in FORM_ALANLARI},
        'odeme_satirlari': [_metinler(o, ('sira', 'kosul', 'tarih', 'tutar', 'para_birimi', 'aciklama'))
                            for o in odemeler],
        'teminatlar': [_metinler(x, ('kimlik', 'tur', 'tutar', 'para_birimi', 'banka', 'bitis_tarihi', 'dosya',
                                     'aciklama')) for x in teminatlar],
        'odeme_toplami': butce.metin(toplam), 'uyarilar': uyarilar,
        'eksik_alanlar': [{'alan': e, 'ne': eksik.ALANLAR[e]} for e in eksikler],
        'eksik_bilgiler': [eksik_satiri(e) for e in depo.eksikler(i.b, proje)],
        'devir': devir_ozeti(d), 'po_no': p['po_no'],
        'po_dosyasi': proje_deposu.dosya(i.b, p['po_dosyasi']),
        'sozlesme_dosyasi': proje_deposu.dosya(i.b, p['sozlesme_dosyasi']),
        'vega_cari_kodu': p['vega_cari_kodu'], 'vega_proje_kodu': p['vega_proje_kodu'],
        'vega_cari_onerisi': None if p['vega_cari_kodu'] else depo.vega_cari_onerisi(i.b, proje, p['m10_musteri']),
    })


def eksik_satiri(e: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in e.items() if k != 'proje'}


def devir_ozeti(d: dict | None) -> dict | None:
    if not d:
        return None
    return {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in d.items() if k != 'proje'}


def form_yaz(i, proje: str, g) -> dict:
    i.rol_gerek(yetki.SIPARIS_VE_TICARI)
    p = proje_kaydi.kayit(i, proje)
    hatalar = []
    for n, o in enumerate(g.odeme_satirlari, 1):
        if o.kosul == 'TARIH' and not o.tarih:
            hatalar.append({'alan': 'odeme_satirlari.tarih', 'sira': n, 'mesaj': 'TARIH koşulunda tarih zorunlu.'})
    for n, t in enumerate(g.teminatlar, 1):
        if t.dosya is not None:
            d = proje_deposu.dosya(i.b, t.dosya)
            if not d or d['proje'] != proje:
                hatalar.append({'alan': 'teminatlar.dosya', 'sira': n, 'mesaj': 'Dosya kaydı bu projede yok.'})
    if g.tesvik != 'VAR' and g.tesvik_belge_no:
        g.tesvik_belge_no = None
    if hatalar:
        raise dogrulama(hatalar)
    an = i.simdi()
    with i.b.transaction():
        if not depo.form_yaz(i.b, proje, g.surum, g.model_dump(include=set(FORM_ALANLARI)),
                             [o.model_dump() for o in g.odeme_satirlari], [t.model_dump() for t in g.teminatlar],
                             i.kisi, an):
            raise ModulHatasi(409, 'DEGISTI', 'Form siz düzenlerken değişti.', guncel=form(i, proje))
        devir.eksikleri_esitle(i, p)
    return form(i, proje)


def siparis_yaz(i, proje: str, g) -> dict:
    i.rol_gerek(yetki.SIPARIS_VE_TICARI)
    p = proje_kaydi.kayit(i, proje)
    an = i.simdi()
    with i.b.transaction():
        po_dosyasi, sozlesme = p['po_dosyasi'], p['sozlesme_dosyasi']
        if g.po_dosyasi:
            po_dosyasi = proje_deposu.dosya_ekle(i.b, proje, 'PO', g.po_dosyasi.model_dump(), i.kisi, an)
        if g.sozlesme_dosyasi:
            sozlesme = proje_deposu.dosya_ekle(i.b, proje, 'SOZLESME', g.sozlesme_dosyasi.model_dump(), i.kisi, an)
        po_no = p['po_no'] if g.po_no is None else (g.po_no.strip() or None)
        depo.siparis_yaz(i.b, proje, po_no, po_dosyasi, sozlesme)
        devir.eksikleri_esitle(i, proje_deposu.getir(i.b, proje))
    from .donusturme import siparis_adi
    from ..depo import ayarlar
    p = proje_deposu.getir(i.b, proje)
    return i.cevap({'proje': proje, 'po_no': p['po_no'], 'po_bekleniyor': p['po_no'] is None,
                    'siparis_adi': siparis_adi(ayarlar.oku(i.b), p),
                    'po_dosyasi': proje_deposu.dosya(i.b, p['po_dosyasi']),
                    'sozlesme_dosyasi': proje_deposu.dosya(i.b, p['sozlesme_dosyasi'])})


def dosya_ekle(i, proje: str, g) -> dict:
    i.rol_gerek(yetki.SIPARIS_VE_TICARI)
    proje_kaydi.kayit(i, proje)
    if not g.ad.strip() or not g.konum.strip():
        raise dogrulama([{'alan': 'konum', 'sira': None, 'mesaj': 'Dosyanın adı ve konumu gerekli.'}])
    kimlik = proje_deposu.dosya_ekle(i.b, proje, g.tur, g.model_dump(exclude={'tur'}), i.kisi, i.simdi())
    return i.cevap({'dosya': _metinler(proje_deposu.dosya(i.b, kimlik),
                                       ('kimlik', 'tur', 'ad', 'konum', 'aciklama', 'parmak_izi', 'ekleyen',
                                        'ekleme_ani'))})


def vega_yaz(i, proje: str, g) -> dict:
    i.rol_gerek(yetki.MUHASEBE_ISI)
    proje_kaydi.kayit(i, proje)
    temiz = lambda x: (x or '').strip() or None  # noqa: E731
    depo.vega_yaz(i.b, proje, temiz(g.vega_cari_kodu), temiz(g.vega_proje_kodu))
    p = proje_deposu.getir(i.b, proje)
    return i.cevap({'proje': proje, 'vega_cari_kodu': p['vega_cari_kodu'], 'vega_proje_kodu': p['vega_proje_kodu']})
