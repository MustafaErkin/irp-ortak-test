"""Klasörler ve dosya kayıtları (SPEC › 8.4)."""
from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from . import yetki
from .devir import devir_gerek
from .zaman import an_metni

FIZIKSEL_NOT = 'Dosyalar şirket sunucusunda; yeri konum alanında.'


def klasorler(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        klasorler = depo_devir.klasorler(c, proje_kimligi)
        dosyalar = depo_dosya.dosyalar(c, proje_kimligi)
    return {
        'not': FIZIKSEL_NOT,
        'klasorler': [{**_klasor(k), 'dosya_ekleyebilir': bool(yetki.dosya_ekleyebilir(b, proje, k)),
                       'dosyalar': [dosya_metni(d) for d in dosyalar if d['klasor'] == k['kimlik']]} for k in klasorler],
    }


def _klasor(k):
    return {'kimlik': k['kimlik'], 'kod': k['sablon_kodu'], 'ad': k['ad'], 'aciklama': k['aciklama'],
            'sorumlu_birim': k['sorumlu_birim']}


def dosya_metni(d):
    return {'kimlik': d['kimlik'], 'klasor': d['klasor'], 'tur': d['tur'], 'ad': d['ad'], 'konum': d['konum'],
            'parmak_izi': d['parmak_izi'], 'aciklama': d['aciklama'], 'kaydeden': d['kaydeden'],
            'kayit_ani': an_metni(d['kayit_ani'])}
