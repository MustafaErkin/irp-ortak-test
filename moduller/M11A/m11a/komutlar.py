"""Komutlar: python -m m11a.komutlar <komut>  (SPEC › 8.7, 15)."""
import sys

from . import vt


def gelistirme_vt_sifirla() -> None:
    with vt.baglan() as b:
        for ad in vt.sema_kur(b, ornek_ayarlar=True):
            print(ad)


def kurallari_calistir() -> None:
    from .alan import kurallar
    from .baglanti import cekirdek_ac
    cekirdek = cekirdek_ac()
    with vt.baglan(autocommit=True) as b:
        print(kurallar.calistir(cekirdek, b))


def bildirimleri_kaldir() -> None:
    from .alan import kurallar
    from .baglanti import cekirdek_ac
    cekirdek = cekirdek_ac()
    with vt.baglan(autocommit=True) as b:
        print(f'{kurallar.hepsini_kaldir(cekirdek, b)} bildirim kaldırıldı')


KOMUTLAR = {'gelistirme-vt-sifirla': gelistirme_vt_sifirla, 'kurallari-calistir': kurallari_calistir,
            'bildirimleri-kaldir': bildirimleri_kaldir}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in KOMUTLAR:
        print('Komutlar: ' + ', '.join(KOMUTLAR))
        return 2
    KOMUTLAR[argv[0]]()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
