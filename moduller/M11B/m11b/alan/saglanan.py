"""Sağlanan okumalar (SPEC › 8.13): M11B.TASARIM_KAPISI, M11B.PROJE_SATIRI.

İkisi de kullanıcının anahtarıyla çağrılır; önce PROJE okunur, yani görünürlüğü çekirdek uygular. Çekirdeğin bunları
modüller arasında nasıl yönlendireceği sözleşmede henüz yok; Faz 1'de modülün API'sinde durur.
"""
from .hatalar import ModulHatasi
from .kapi import proje_kapisi
from .projeler import proje_satiri


def tasarim_kapisi(b, proje):
    b.proje(proje)
    with b.vt.islem() as c:
        return {'proje': proje, **proje_kapisi(c, proje)}


OKUMALAR = {'M11B.TASARIM_KAPISI': tasarim_kapisi, 'M11B.PROJE_SATIRI': proje_satiri}


def oku(b, ad, proje):
    if ad not in OKUMALAR:
        raise ModulHatasi(404, 'TANIMSIZ_VERI', f'Tanımsız okuma: {ad}')
    if not proje:
        raise ModulHatasi(422, 'DOGRULAMA', 'proje parametresi gerekli.', hatalar=[{'alan': 'proje', 'mesaj': 'Gerekli.'}])
    return OKUMALAR[ad](b, proje)
