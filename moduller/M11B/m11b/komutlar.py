"""Komutlar: python -m m11b.komutlar <komut>

  gelistirme-vt-sifirla   şemayı silip açar, göçleri ve örnek firmanın ayarlarını koşar (yalnızca geliştirme)
  kurallari-calistir      kural işi: PLAN_YAYIMLANDI bildirimlerini telafi eder ya da kaldırır (SPEC › 8.12)
  bildirimleri-kaldir     modül kapatılmadan önce bütün açık bildirimleri kaldırır
"""
import json
import logging
import sys

from .ayarlar import Ayarlar


def gelistirme_vt_sifirla(ayarlar):
    from .gocler import sema_sifirla
    for yol in sema_sifirla(ayarlar.veritabani):
        print(f'koştu: {yol.name}')


def _cekirdek_ve_vt(ayarlar):
    from .baglanti import cekirdek_ac
    from .vt import Vt, havuz_ac
    havuz = havuz_ac(ayarlar.veritabani)
    return cekirdek_ac(ayarlar, havuz), Vt(havuz)


def kurallari_calistir(ayarlar):
    from .alan.kurallar import kurallari_calistir as calistir
    cekirdek, vt = _cekirdek_ve_vt(ayarlar)
    print(json.dumps(calistir(cekirdek, vt), ensure_ascii=False))


def bildirimleri_kaldir(ayarlar):
    from .alan.kurallar import bildirimleri_kaldir as kaldir
    cekirdek, vt = _cekirdek_ve_vt(ayarlar)
    print(json.dumps(kaldir(cekirdek, vt), ensure_ascii=False))


KOMUTLAR = {'gelistirme-vt-sifirla': gelistirme_vt_sifirla, 'kurallari-calistir': kurallari_calistir,
            'bildirimleri-kaldir': bildirimleri_kaldir}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in KOMUTLAR:
        print(__doc__)
        return 2
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    KOMUTLAR[argv[0]](Ayarlar.ortamdan())
    return 0


if __name__ == '__main__':
    sys.exit(main())
