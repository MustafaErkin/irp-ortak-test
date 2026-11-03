"""Çekirdeğe bağlantı: uygulamada tek Cekirdek örneği, olay kimliğinin sırası modülün tablosunda.

Sürücüyü (simülatör ya da HTTP) bağlantı katmanı ortam değişkenlerinden seçer; bu dosya bilmez.
"""
from irp_sozlesme.baglanti import Cekirdek

from .ayarlar import SEMA


class TabloSayac:
    """Olay kimliğinin kişi ve gün başına sırası (irp_sozlesme/sozlesme/04_veritabani.md › 3).

    İsteğin işleminden bağımsız, havuzdan aldığı bağlantının kendi kısa işleminde artar. Böylece geri alınan
    bir istek aynı sırayı ikinci kez dağıtmaz; modülün birden çok kopyası aynı kimliği vermez."""

    def __init__(self, havuz):
        self.havuz = havuz

    def sonraki(self, kisi, gun):
        with self.havuz.connection() as b:
            return b.execute(f'SELECT {SEMA}.olay_sirasi(%s, %s) AS sira', (kisi, gun)).fetchone()['sira']


def cekirdek_ac(ayarlar, havuz):
    return Cekirdek.ac(str(ayarlar.kunye), sayac=TabloSayac(havuz))
