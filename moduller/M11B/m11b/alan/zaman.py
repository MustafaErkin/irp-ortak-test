"""Tarih ve an yardımcıları. Çekirdeğin saati +03:00'tür; modülün anları cekirdek.simdi()'den gelir."""
from datetime import date, datetime, timedelta, timezone

DILIM = timezone(timedelta(hours=3))


def an_metni(an):
    """timestamptz → çekirdeğin biçimi (ISO 8601, +03:00)."""
    if an is None:
        return None
    if isinstance(an, str):
        an = datetime.fromisoformat(an)
    return an.astimezone(DILIM).isoformat()


def an(metin):
    return datetime.fromisoformat(metin) if isinstance(metin, str) else metin


def gun(metin):
    """'2026-11-02' ya da '2026-11-02T09:00:00+03:00' → date (çekirdeğin saat diliminde)."""
    if metin is None:
        return None
    if isinstance(metin, datetime):
        return metin.astimezone(DILIM).date()
    if isinstance(metin, date):
        return metin
    return an(metin).astimezone(DILIM).date() if 'T' in metin else date.fromisoformat(metin)


def kayit(satir):
    """Veritabanı satırını JSON'a hazırlar: anlar +03:00 metni, tarihler ISO."""
    if satir is None:
        return None
    return {k: (an_metni(v) if isinstance(v, datetime) else v.isoformat() if isinstance(v, date) else v)
            for k, v in satir.items()}
