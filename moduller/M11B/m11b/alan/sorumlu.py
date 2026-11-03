"""Proje sorumlusunu değiştirmek (SPEC › 8.11). Modülün kuralı YETKILI; olayı çekirdek ayrıca denetler."""
from . import yetki
from .hatalar import ModulHatasi, olay_reddi


def sorumlu_degistir(b, proje_kimligi, sorumlu, proje_surum=None):
    proje = b.proje(proje_kimligi)
    yetki.gerek(b.yetkili, 'Proje sorumlusunu yalnızca yetkili değiştirir.')
    if sorumlu not in {k['kimlik'] for k in b.kisiler if k.get('aktif')}:
        raise ModulHatasi(422, 'DOGRULAMA', 'Sorumlu aktif bir kişi olmalı.',
                          hatalar=[{'alan': 'sorumlu', 'mesaj': 'Kişi bulunamadı.'}])
    cevap = b.olay('PROJE.DEGISTIRDIM', {'degisenler': {'sorumlu': sorumlu}},
                   [{'tur': 'PROJE', 'kimlik': proje_kimligi, 'surum': proje_surum or proje.get('surum')}])
    if not cevap.basarili:
        raise olay_reddi(cevap, 'PROJE.DEGISTIRDIM')
    yeni = b.proje_yenile(proje_kimligi)
    return {'sorumlu': yeni.get('sorumlu'), 'sorumlu_adi': b.kisi_adi(yeni.get('sorumlu')), 'surum': yeni.get('surum')}
