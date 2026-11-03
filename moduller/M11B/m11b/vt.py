"""Modülün veritabanı: bağlantı havuzu ve işlem yardımcıları. SQL elle ve parametreli yazılır; ORM yok."""
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .ayarlar import SEMA


def havuz_ac(adres, en_az=1, en_cok=4):
    return ConnectionPool(adres, min_size=en_az, max_size=en_cok,
                          kwargs={'row_factory': dict_row, 'prepare_threshold': None}, open=True)


class Vt:
    """Havuzun önünde ince bir katman. Her `islem()` kendi işlemidir: çıkışta işlenir, hatada geri alınır."""

    def __init__(self, havuz):
        self.havuz = havuz

    @contextmanager
    def islem(self):
        with self.havuz.connection() as b:
            yield b


def tablolar():
    """Modülün veri tabloları, bağımlılık sırasıyla (testlerde ve sıfırlamada boşaltmak için)."""
    return [f'{SEMA}.{t}' for t in (
        'gorev_atamalari', 'not_ekleri', 'bilgi_notlari', 'plan_kanitlari', 'plan_satirlari', 'plan_degisiklikleri',
        'kapi_gecisleri', 'dosya_kayitlari', 'klasorler', 'etap_ekleri', 'devirler', 'not_kategorileri',
        'klasor_sablonu', 'etap_sablonu', 'olay_sayaci')]
