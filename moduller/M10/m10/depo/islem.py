"""İşlem geçmişi (SPEC › 8.15): talebe ve sürüme yapılan her değişiklik; kim, ne, ne zaman, ayrıntı."""
from datetime import date, datetime
from decimal import Decimal

from psycopg.types.json import Jsonb


def _jsonla(x):
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, (date, datetime)):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: _jsonla(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonla(v) for v in x]
    return x


def yaz(b, talep, islem, kim, an, ayrinti=None, surum=None, onayci_duzeltmesi=False):
    b.execute('INSERT INTO islem_gecmisi (talep, surum, kim, an, islem, ayrinti, onayci_duzeltmesi) '
              'VALUES (%s, %s, %s, %s, %s, %s, %s)',
              (talep, surum, kim, an, islem, Jsonb(_jsonla(ayrinti or {})), onayci_duzeltmesi))


def farklar(eski, yeni, alanlar):
    """[{alan, eski, yeni}]: yalnızca değişen alanlar."""
    return [{'alan': a, 'eski': _jsonla(eski.get(a)), 'yeni': _jsonla(yeni.get(a))}
            for a in alanlar if _jsonla(eski.get(a)) != _jsonla(yeni.get(a))]


def liste(b, talep, yalniz_onayci=False):
    return b.execute('SELECT i.kimlik, i.surum, s.no AS surum_no, i.kim, i.an, i.islem, i.ayrinti, i.onayci_duzeltmesi '
                     'FROM islem_gecmisi i LEFT JOIN teklif_surumleri s ON s.kimlik = i.surum WHERE i.talep = %s'
                     + (' AND i.onayci_duzeltmesi' if yalniz_onayci else '') + ' ORDER BY i.an, i.kimlik',
                     (talep,)).fetchall()
