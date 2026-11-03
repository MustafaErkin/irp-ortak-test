"""Açılış toplantısı (SPEC › 8.8)."""
from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from . import dosya, yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi
from .zaman import gun, kayit


def sunum_kaydet(b, proje_kimligi, govde):
    """Yalnızca proje sorumlusu. Tutanak isteğe bağlı dosya kaydıdır (TUTANAK, TOPLANTI_PLANLAMA).
    Sonraki toplantıların tutanakları dosya kaydı olarak eklenir."""
    proje = b.proje(proje_kimligi)
    yetki.gerek(b.sorumlu_mu(proje), 'Açılış toplantısını proje sorumlusu kaydeder.')
    simdi = b.simdi()
    tarih = govde.get('tarih')
    an = simdi if not tarih or gun(tarih) == gun(simdi) else f'{tarih}T00:00:00+03:00'
    if gun(an) > gun(simdi):
        raise ModulHatasi(422, 'DOGRULAMA', 'Toplantı tarihi ileride olamaz.',
                          hatalar=[{'alan': 'tarih', 'mesaj': 'İleride olamaz.'}])
    with b.vt.islem() as c:
        devir = devir_gerek(c, proje_kimligi)
        if devir['sunum_ani'] is not None:
            raise ModulHatasi(409, 'SUNUM_VAR', 'Açılış toplantısı zaten kaydedildi; sonraki toplantıların '
                                                'tutanaklarını dosya kaydı olarak ekleyin.')
        if govde.get('tutanak'):
            d = depo_dosya.dosya(c, govde['tutanak'])
            if not d or d['proje'] != proje_kimligi or d['tur'] != 'TUTANAK':
                raise ModulHatasi(422, 'DOGRULAMA', 'Seçilen kayıt bu projenin tutanağı değil.',
                                  hatalar=[{'alan': 'tutanak', 'mesaj': 'Tutanak değil.'}])
        elif govde.get('yeni_tutanak'):
            dosya.dosya_ekle(b, proje_kimligi, {**govde['yeni_tutanak'], 'tur': 'TUTANAK'}, c=c)
        depo_devir.sunum_yaz(c, proje_kimligi, an, b.kisi)
        return kayit(depo_devir.devir(c, proje_kimligi))
