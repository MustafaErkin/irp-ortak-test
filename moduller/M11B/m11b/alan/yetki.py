"""Modülün kendi kuralları: yalnızca modülün tablolarına yazılan işler için (SPEC › 6).

Çekirdeğe giden her olayı ayrıca çekirdek denetler; modül yetkiyi genişletmez. Sorumlunun üstleri modülün kendi
kayıtlarında yetkili sayılmaz: modül hiyerarşi kuralını kendi içinde kurmaz.
"""
from .hatalar import ModulHatasi

GOREV_ATAYAN_ROLLER = ('YONETICI', 'EKIP_LIDERI', 'YETKILI')


def sorumlu_ya_da_yetkili(b, proje):
    return b.sorumlu_mu(proje) or b.yetkili


def gerek(kosul, mesaj='Bu işi proje sorumlusu yapar.'):
    if not kosul:
        raise ModulHatasi(403, 'MODUL_YETKI', mesaj)


def izinler(b, proje, klasorler=()):
    """Kullanıcının bu projedeki izinleri; ekran düğmeleri buna göre görünür."""
    sy = sorumlu_ya_da_yetkili(b, proje)
    return {
        'devri_baslatabilir': sy,
        'plan_degistirebilir': sy,
        'kapidan_gecebilir': b.sorumlu_mu(proje),
        'not_yazabilir': sy,
        'sunum_kaydedebilir': b.sorumlu_mu(proje),
        'gorev_atayabilir': b.rolu_var(*GOREV_ATAYAN_ROLLER),
        'sorumlu_degistirebilir': b.yetkili,
        'dosya_klasorleri': [k['kimlik'] for k in klasorler if dosya_ekleyebilir(b, proje, k)],
    }


def dosya_ekleyebilir(b, proje, klasor):
    return sorumlu_ya_da_yetkili(b, proje) or (klasor.get('sorumlu_birim') and
                                               klasor['sorumlu_birim'] == b.ben.get('birim'))
