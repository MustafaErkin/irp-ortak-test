"""Arama ve kod üretme (SPEC › 8.13, 8.4). Saf."""
import re
import unicodedata

KATLAMA = str.maketrans('çğıöşüâîû', 'cgiosuaiu')


def normal(metin):
    """Türkçe küçük harf (İ→i, I→ı, sonra küçült), ASCII'ye katlama, noktalama boşluğa, boşluklar teke."""
    if not metin:
        return ''
    s = str(metin).replace('İ', 'i').replace('I', 'ı').lower().translate(KATLAMA)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def arama_metni(*parcalar):
    return normal(' '.join(str(p) for p in parcalar if p))


def kelimeler(sorgu):
    return normal(sorgu).split()


def eslesir(sorgu, metin):
    """Sorgunun her kelimesi metinde geçmelidir (VE)."""
    m = normal(metin)
    return all(k in m for k in kelimeler(sorgu))


def kod_uret(ad, mevcut):
    """"Diğer…" unsurunun kodu: Türkçe harfler ASCII'ye, büyük harf, boşluk `_`; çakışırsa `_2`, `_3`…
    Desen ^[A-Z][A-Z0-9_]{1,39}$ (göçteki kısıt)."""
    taban = normal(ad).upper().replace(' ', '_') or 'UNSUR'
    if not taban[0].isalpha():
        taban = 'U_' + taban
    if len(taban) < 2:
        taban += '_'
    mevcut = set(mevcut)
    kod, n = taban[:40], 1
    while kod in mevcut:
        n += 1
        ek = f'_{n}'
        kod = taban[:40 - len(ek)] + ek
    return kod
