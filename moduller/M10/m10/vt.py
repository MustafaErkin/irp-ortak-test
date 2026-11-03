"""Modülün veritabanı: bağlantı havuzu ve işlem yardımcısı.

SQL elle ve parametreli yazılır; tablolar şema adı olmadan anılır, şemayı `search_path` verir
(SEMA tek ayar sabitindedir).
"""
from contextlib import contextmanager
import threading

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import ayarlar

_havuz = None
_kilit = threading.Lock()


def _ayarla(b):
    b.execute(f'SET search_path TO {ayarlar.SEMA}, pg_temp')
    # Anlar çekirdeğin saat dilimiyle döner (+03:00, Ek D.2)
    b.execute("SET TIME ZONE 'Europe/Istanbul'")
    b.commit()


def _ac(adres):
    return ConnectionPool(adres, min_size=1, max_size=4, kwargs={'row_factory': dict_row, 'prepare_threshold': None},
                          configure=_ayarla, open=True)


def havuz():
    global _havuz
    with _kilit:
        if _havuz is None:
            _havuz = _ac(ayarlar.veritabani())
        return _havuz


def kur(adres):
    """Testler havuzu test veritabanına çevirir."""
    global _havuz
    with _kilit:
        if _havuz is not None:
            _havuz.close()
        _havuz = _ac(adres)


def kapat():
    global _havuz
    with _kilit:
        if _havuz is not None:
            _havuz.close()
            _havuz = None


@contextmanager
def islem():
    """Tek işlem: hata yoksa işlenir, varsa geri alınır."""
    with havuz().connection() as b:
        yield b
