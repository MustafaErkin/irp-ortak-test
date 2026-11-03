"""Ticari devirdeki eksik bilgi (SPEC › 8.3). Saf fonksiyonlar."""

ALANLAR = {
    'PO': 'PO numarası',
    'SOZLESME': 'İmzalı sözleşme',
    'ODEME_TAKVIMI': 'Ödeme takvimi',
    'FATURALAMA': 'Faturalama biçimi',
    'TESLIM_SEKLI': 'Teslim şekli',
    'IHRACAT': 'Yurt içi / ihracat',
    'TESVIK': 'Teşvik (belge no)',
    'TEMINAT': 'Teminat',
}
ACIK_DURUMLAR = ('EKSIK', 'ISTENDI')
KIMDEN = ('MUSTERI', 'SATIS', 'DIGER')


def _bos(x) -> bool:
    return x is None or (isinstance(x, str) and not x.strip())


def eksik_alanlar(po_no, sozlesme_dosyasi, ticari: dict, odeme_sayisi: int, teminat_sayisi: int) -> list[str]:
    """Alan kodu → eksik sayılma koşulu; sıra ALANLAR'ınkidir."""
    t = ticari or {}
    eksik = {
        'PO': _bos(po_no),
        'SOZLESME': sozlesme_dosyasi is None,
        'ODEME_TAKVIMI': odeme_sayisi == 0,
        'FATURALAMA': _bos(t.get('faturalama_bicimi')),
        'TESLIM_SEKLI': _bos(t.get('teslim_sekli')),
        'IHRACAT': t.get('ihracat') is None,
        'TESVIK': t.get('tesvik') is None or (t.get('tesvik') == 'VAR' and _bos(t.get('tesvik_belge_no'))),
        'TEMINAT': t.get('teminat_gerekli') is None or (t.get('teminat_gerekli') == 'VAR' and teminat_sayisi == 0),
    }
    return [k for k in ALANLAR if eksik[k]]


def esitle(satirlar: list[dict], eksikler: list[str]) -> tuple[list[str], list[tuple[int, str]]]:
    """Devirden sonra her kayıtta: dolan alanın satırı ALINDI, yeniden boşalanın satırı EKSIK, yoksa açılır.
    Dönen: (açılacak alanlar, [(satır kimliği, yeni durum)]). Elle satırlara (alanı boş) dokunulmaz."""
    alanli = {s['alan']: s for s in satirlar if s.get('alan')}
    acilacak = [a for a in eksikler if a not in alanli]
    degisen = []
    for alan, s in alanli.items():
        if alan in eksikler and s['durum'] == 'ALINDI':
            degisen.append((s['kimlik'], 'EKSIK'))
        elif alan not in eksikler and s['durum'] != 'ALINDI':
            degisen.append((s['kimlik'], 'ALINDI'))
    return acilacak, degisen


def acik_sayisi(satirlar: list[dict]) -> int:
    return sum(s['durum'] in ACIK_DURUMLAR for s in satirlar)


def gecis_hatasi(satir: dict, yeni: str, kimden: str | None) -> str | None:
    """Elle durum değişikliği: EKSIK → ISTENDI (kimden zorunlu) → ALINDI. Otomatik satır ALINDI'ya yalnızca alan
    dolunca geçer; elle satırı muhasebe kapatır. Hata varsa mesajı döner."""
    eski, otomatik = satir['durum'], bool(satir.get('alan'))
    if yeni == eski:
        return None
    if yeni == 'ISTENDI':
        if eski != 'EKSIK':
            return 'Yalnızca eksik satır istenebilir.'
        if kimden not in KIMDEN:
            return 'Kimden istendiği seçilmeli.'
        return None
    if yeni == 'ALINDI':
        if otomatik:
            return 'Bu satır alan dolunca kendiliğinden kapanır.'
        return None
    return 'Geçersiz durum değişikliği.'
