"""Devri başlatmak (SPEC › 8.1)."""
from ..depo import devir as depo
from . import yetki
from .hatalar import ModulHatasi


def devri_baslat(b, proje_kimligi):
    """Tekrar güvenlidir: devir varsa var olan döner. Klasörler şablondan açılır."""
    proje = b.proje(proje_kimligi)
    if not proje.get('aktif'):
        raise ModulHatasi(409, 'PROJE_AKTIF_DEGIL', 'Proje aktif değil; devir başlatılamaz.')
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Devri proje sorumlusu ya da yetkili başlatır.')
    with b.vt.islem() as c:
        var = depo.devir(c, proje_kimligi)
        if var:
            return var, False
        devir = depo.devir_ekle(c, proje_kimligi, b.kisi, b.simdi())
        for s in depo.klasor_sablonu(c):
            depo.klasor_ekle(c, proje_kimligi, s['kod'], klasor_adi(proje['kod'], s['ad'], b.ayarlar.klasor_ayraci),
                             s['sorumlu_birim'])
    return devir, True


def klasor_adi(proje_kodu, sablon_adi, ayrac):
    """Ör. 2606028_3D TASARIM. Ayraç ayardandır (M11B_KLASOR_AYRACI); müşterinin cevabıyla (S-3) kesinleşir."""
    return f'{proje_kodu}{ayrac}{sablon_adi}'


def devir_gerek(c, proje_kimligi):
    devir = depo.devir(c, proje_kimligi)
    if not devir:
        raise ModulHatasi(409, 'DEVIR_YOK', 'Bu projenin devri başlatılmadı.')
    return devir
