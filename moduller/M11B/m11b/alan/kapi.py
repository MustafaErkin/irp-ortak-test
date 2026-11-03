"""Tasarım girdisi kapısı (SPEC › 8.5). Tasarım girdisi yokken modülden tasarım görevi atanmaz."""
from ..depo import dosya as depo_dosya
from ..depo import kapi as depo
from . import yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi
from .zaman import an_metni

ACIK, KAPALI = 'ACIK', 'KAPALI'
KAPALI_MESAJI = 'Tasarım girdisi yüklenmeden tasarım görevi atanamaz.'


def kapi_durumu(tasarim_girdisi_sayisi, gecis_sayisi):
    if tasarim_girdisi_sayisi > 0:
        return {'durum': ACIK, 'neden': 'GIRDI_VAR'}
    if gecis_sayisi > 0:
        return {'durum': ACIK, 'neden': 'GECIS'}
    return {'durum': KAPALI, 'neden': None}


def proje_kapisi(c, proje):
    return kapi_durumu(depo_dosya.dosya_sayisi(c, proje, 'TASARIM_GIRDISI'), len(depo.gecisler(c, proje)))


def kapi(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        durum = proje_kapisi(c, proje_kimligi)
        gecisler = depo.gecisler(c, proje_kimligi)
        girdiler = depo_dosya.dosyalar(c, proje_kimligi, 'TASARIM_GIRDISI')
    return {**durum, 'proje': proje_kimligi, 'gecebilir': b.sorumlu_mu(proje) and durum['durum'] == KAPALI,
            'gecisler': [{'kimlik': g['kimlik'], 'gecen': g['gecen'], 'an': an_metni(g['an']), 'gerekce': g['gerekce']}
                         for g in gecisler],
            'tasarim_girdileri': [{'kimlik': d['kimlik'], 'ad': d['ad'], 'konum': d['konum']} for d in girdiler]}


def gecis(b, proje_kimligi, gerekce):
    """Yalnızca proje sorumlusu geçer; kayıt kalır ve geçiş proje içindir."""
    proje = b.proje(proje_kimligi)
    yetki.gerek(b.sorumlu_mu(proje), 'Kapıdan gerekçeyle yalnızca proje sorumlusu geçer.')
    if not (gerekce or '').strip():
        raise ModulHatasi(422, 'DOGRULAMA', 'Gerekçe boş olamaz.', hatalar=[{'alan': 'gerekce', 'mesaj': 'Boş olamaz.'}])
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        depo.gecis_ekle(c, proje_kimligi, b.kisi, b.simdi(), gerekce.strip())
    return kapi(b, proje_kimligi)
