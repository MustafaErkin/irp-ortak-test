"""kapi_gecisleri ve gorev_atamalari."""
from ..ayarlar import SEMA


def gecisler(b, proje):
    return b.execute(f'SELECT * FROM {SEMA}.kapi_gecisleri WHERE proje = %s ORDER BY an', (proje,)).fetchall()


def gecis_ekle(b, proje, gecen, an, gerekce):
    return b.execute(f'INSERT INTO {SEMA}.kapi_gecisleri (proje, gecen, an, gerekce) VALUES (%s, %s, %s, %s) '
                     'RETURNING *', (proje, gecen, an, gerekce)).fetchone()


def gorev_atamalari(b, proje):
    return b.execute(f'SELECT * FROM {SEMA}.gorev_atamalari WHERE proje = %s ORDER BY atama_ani', (proje,)).fetchall()


def gorev_atamasi_ekle(b, gorev, proje, etap, atayan, an, kapi, tgg_dosyasi):
    b.execute(f'INSERT INTO {SEMA}.gorev_atamalari (gorev, proje, etap, atayan, atama_ani, kapi, tgg_dosyasi) '
              'VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (gorev) DO NOTHING',
              (gorev, proje, etap, atayan, an, kapi, tgg_dosyasi))


def gorev_atamasi_sayisi(b, proje):
    return b.execute(f'SELECT count(*) AS n FROM {SEMA}.gorev_atamalari WHERE proje = %s', (proje,)).fetchone()['n']
