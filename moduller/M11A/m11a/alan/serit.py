"""Bütçe ölçümü kullanıcının gözüyle; bütçe şeridi, paneli ve bütçeler listesi (SPEC › 8.6).

Okumalar (proje başına): PROJE_DURUM, ETAPLAR, NESNELER. Para okunmaz, servis gözü kullanılmaz.
Saklanan yalnızca yüzdelerdir; tutar ve saat saklanmaz."""
import logging

from ..baglanti import CekirdekHatasi
from ..depo import ayarlar, butce as depo, projeler
from . import bildirim, olcum, yetki
from .butce import metin

gunluk = logging.getLogger('m11a.serit')

ETIKET = {'YESIL': ('●', 'Yolunda'), 'KIRMIZI': ('▲', 'Dolum ilerlemenin {s} puan önünde'),
          'GRI': ('○', 'Hesaplanamaz')}
KAPSAM_METNI = 'Dolum: yalnızca işçilik (malzeme ve fason M3 bağlanınca)'


def _sayi(x) -> str:
    """Bildirim metni için bir ondalık, virgülle: 62.0 → "62,0"."""
    return '—' if x is None else f'{x:.1f}'.replace('.', ',')


def sapma_metni(p: dict, o: dict) -> str:
    esik = o['esik_puan']
    esik_metni = f'{esik:.0f}' if float(esik).is_integer() else f'{esik:.1f}'.replace('.', ',')
    return (f'{p["proje"]} {p["proje_adi"]} · İşçilik dolumu %{_sayi(o["dolum_yuzde"])}, ilerleme '
            f'%{_sayi(o["ilerleme_yuzde"])} ({_sayi(o["sapma_puan"])} puan; eşik {esik_metni})')


def olc(i, p: dict) -> dict:
    """Ölçüm; aynı istekte iki kez ölçülmez. PROJE önceden kullanıcının gözüyle okunmuş olmalı."""
    anahtar = ('olcum', p['proje'])
    if anahtar in i.onbellek:
        return i.onbellek[anahtar]
    once = i.hesaplaniyor
    i.hesaplaniyor = False
    pd = i.oku('PROJE_DURUM', p['proje'])
    etaplar = i.oku('ETAPLAR', proje=p['proje'])
    parcalar = i.oku('NESNELER', proje=p['proje'])
    guncel_degil = i.hesaplaniyor
    i.hesaplaniyor = once or guncel_degil
    a = ayarlar.oku(i.b)
    satirlar = depo.satirlar(i.b, p['proje'])
    o = olcum.olcum({'para_birimi': p['para_birimi'], 'guncel': {s['kalem']: s['guncel'] for s in satirlar}},
                    etaplar, pd, olcum.ucret_birlestir(depo.proje_ucretleri(i.b, p['proje']),
                                                      ayarlar.saat_ucretleri(i.b)),
                    p['kurlar'], parcalar, a['sapma_esigi_puan'])
    o['an'] = i.simdi()
    o['hesaplaniyor'] = guncel_degil
    if not guncel_degil:
        depo.olcum_yaz(i.b, p['proje'], o['an'], i.kisi, o)
        uyar(i.cekirdek, i.b, p, o)
    i.onbellek[anahtar] = o
    return o


def uyar(cekirdek, b, p: dict, o: dict) -> None:
    """KIRMIZI ise BUTCE_SAPMASI bırakılır ya da (metin değiştiyse) güncellenir; değilse açık olan kaldırılır."""
    try:
        acik = bildirim.acik(b, p['proje']).get(bildirim.BUTCE_SAPMASI)
        if o['renk'] == 'KIRMIZI' and p['butce_durumu'] == 'ACIK':
            metin_ = sapma_metni(p, o)
            if not acik or acik['metin'] != metin_:
                bildirim.birak(cekirdek, b, p['proje'], bildirim.BUTCE_SAPMASI,
                               [{'tur': 'KISI', 'kimlik': p['satis_yoneticisi']}, {'tur': 'ROL', 'kimlik': 'YETKILI'}],
                               metin_, 'UYARI')
        elif acik:
            bildirim.kaldir(cekirdek, b, p['proje'], bildirim.BUTCE_SAPMASI)
    except CekirdekHatasi as h:
        gunluk.warning('%s BUTCE_SAPMASI: %s', p['proje'], h)


def serit(p: dict, o: dict) -> dict:
    """Şerit: yalnızca yüzdeler (M11A.BUTCE_YUZDELERI ile aynı); projeyi gören herkese."""
    simge, etiket = ETIKET[o['renk']]
    return {'proje': p['proje'], 'dolum_yuzde': o['dolum_yuzde'], 'ilerleme_yuzde': o['ilerleme_yuzde'],
            'sapma_puan': o['sapma_puan'], 'esik_puan': o['esik_puan'], 'renk': o['renk'], 'kapsam': o['kapsam'],
            'olcum_ani': o['an'], 'butce_durumu': p['butce_durumu'], 'po_bekleniyor': p['po_no'] is None,
            'simge': simge, 'etiket': etiket.format(s=_sayi(o['sapma_puan'])),
            'kapsam_metni': KAPSAM_METNI, 'hesaplaniyor': o['hesaplaniyor']}


def yuzdeler(p: dict, o: dict) -> dict:
    s = serit(p, o)
    return {k: s[k] for k in ('proje', 'dolum_yuzde', 'ilerleme_yuzde', 'sapma_puan', 'esik_puan', 'renk', 'kapsam',
                              'olcum_ani', 'butce_durumu', 'po_bekleniyor')}


def _dosya(i, kimlik):
    d = projeler.dosya(i.b, kimlik)
    return {'kimlik': d['kimlik'], 'ad': d['ad'], 'konum': d['konum']} if d else None


def kapanis(i, p: dict) -> dict | None:
    if p['butce_durumu'] != 'KAPALI':
        return None
    return {'kesin_kabul_tarihi': p['kapanis_kesin_kabul'].isoformat(), 'an': p['kapanis_ani'].isoformat(),
            'kapatan': p['kapatan'],
            'farklar': [{'kalem': f['kalem'], 'butce': metin(f['butce']), 'gerceklesen': metin(f['gerceklesen']),
                         'fark': metin(f['fark']), 'kaynak': f['kaynak']} for f in depo.kapanis_farklari(i.b, p['proje'])],
            'duzeltmeler': [{'kimlik': d['kimlik'], 'kalem': d['kalem'], 'tutar': metin(d['tutar']),
                             'gerekce': d['gerekce'], 'belge': _dosya(i, d['belge']), 'kim': d['kim'],
                             'an': d['an'].isoformat()} for d in depo.duzeltmeler(i.b, p['proje'])]}


def panel(i, p: dict, o: dict) -> dict:
    """Panel: tutarlar; yalnızca SATIS, MUHASEBE, YETKILI. Gerçekleşen rakamlar "tahmini gerçekleşen"dir."""
    return {
        'para_birimi': p['para_birimi'], 'sozlesme_tutari': metin(p['sozlesme_tutari']),
        'guncel_tutar': metin(p['guncel_tutar']), 'etiket': 'tahmini gerçekleşen',
        'kalemler': [{'kalem': s['kalem'], 'baslangic': metin(s['baslangic']), 'guncel': metin(s['guncel']),
                      'tahmini_gerceklesen': metin(o['gerceklesen'][s['kalem']]), 'kaynak': o['kaynaklar'][s['kalem']]}
                     for s in depo.satirlar(i.b, p['proje'])],
        'degisiklikler': [{'kimlik': d['kimlik'], 'an': d['an'].isoformat(), 'kim': d['kim'],
                           'eski_tutar': metin(d['eski_tutar']), 'yeni_tutar': metin(d['yeni_tutar']),
                           'butce_eski': d['butce_eski'], 'butce_yeni': d['butce_yeni'], 'gerekce': d['gerekce'],
                           'belge': _dosya(i, d['belge'])} for d in depo.tutar_degisiklikleri(i.b, p['proje'])],
        'iscilik': [{'etap': s['etap'], 'birim': s['birim'], 'saat': f'{s["saat"]:.1f}', 'ucret': metin(s['ucret']),
                     'para_birimi': s['para_birimi'], 'tutar': metin(s['tutar'])} for s in o['iscilik_satirlari']],
        'bilinmeyen_saat': f'{o["bilinmeyen_saat"]:.1f}',
        'ilerleme': o['ilerleme'],
        'kapanis': kapanis(i, p),
    }


def butce(i, proje: str) -> dict:
    from .proje import kayit
    p = kayit(i, proje)
    o = olc(i, p)
    cevap = {'serit': serit(p, o)}
    if i.rol_var(yetki.TUTAR_GORME):
        cevap['panel'] = panel(i, p, o)
    return i.cevap(cevap)


SIRA_RENK = {'KIRMIZI': 0, 'YESIL': 1, 'GRI': 2}


def butceler(i) -> dict:
    i.rol_gerek(yetki.BUTCELER, 'Bütçeler listesini satış, muhasebe ya da yetkili görür.')
    satirlar = []
    for p in projeler.acik_projeler(i.b):
        if not i.proje_gorur_mu(p['proje']):
            continue
        o = olc(i, p)
        satirlar.append({'proje': p['proje'], 'ad': p['proje_adi'], 'musteri': p['musteri_adi'],
                         **{k: v for k, v in serit(p, o).items() if k != 'proje'}})
    satirlar.sort(key=lambda s: (SIRA_RENK[s['renk']], -(s['sapma_puan'] or 0)))
    return i.cevap({'satirlar': satirlar})
