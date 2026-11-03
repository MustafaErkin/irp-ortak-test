"""Modülün PostgreSQL bağlantısı ve göçler (SPEC › 7, Ek B). Yalnızca mod_m11a şemasına dokunulur."""
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from .ayarlar import KOK, ortam

GOCLER = KOK / 'veritabani'
GELISTIRME = KOK / 'gelistirme'


def baglan(url: str | None = None, autocommit: bool = False) -> psycopg.Connection:
    """Anlar çekirdeğin saat dilimiyle (+03:00) döner; ekrana giden ISO metni böylece çekirdeğin saatidir."""
    return psycopg.connect(url or ortam().veritabani, row_factory=dict_row, autocommit=autocommit, prepare_threshold=None,
                           options='-c TimeZone=Europe/Istanbul')


def _kos(b: psycopg.Connection, yol: Path) -> None:
    b.execute(yol.read_text('utf-8'))


def sema_kur(b: psycopg.Connection, ornek_ayarlar: bool = False) -> list[str]:
    """Yalnızca geliştirme ve test: şemayı baştan açar, göçleri numara sırasıyla koşar."""
    kosulan = []
    with b.transaction():
        for yol in [GELISTIRME / 'sema_ac.sql', *sorted(GOCLER.glob('*.sql'))] + (
                [GELISTIRME / 'ornek_ayarlar.sql'] if ornek_ayarlar else []):
            _kos(b, yol)
            kosulan.append(yol.name)
    return kosulan
