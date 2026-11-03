"""Ortak sınama zemini (SPEC › Ek D.10; M1.0'ın SPEC'inde birebir aynı)."""


def _basarili(cevap, eylem):
    if cevap.get('sonuc') != 'BASARILI':
        raise AssertionError(f'Zemin olayı reddedildi: {eylem} {cevap}')
    return cevap


def a_ekibi_zemini(c, *, satis_rolu_kur=False):
    """M1.0 ve M1.1A testlerinin ortak zemini. M1.0'ın künyesi SATIS rolünü ve PROJE.ACTIM yetkisini kendisi
    kurar; M1.1A'nın testinde M1.0 kurulu olmadığı için satis_rolu_kur=True ile elle kurulur."""
    s = c.surucu
    s.saat('2026-11-02T09:00:00+03:00')
    y = lambda e, g: _basarili(s.yetkili_olay(e, g), e)  # noqa: E731
    if satis_rolu_kur:
        y('KOD.TANIMLADIM', {'liste': 'ROL', 'kod': 'SATIS', 'ad': 'Satış yöneticisi', 'aktif': True})
        y('YETKI.TANIMLADIM', {'eylem_kodu': 'PROJE.ACTIM', 'kimler': ['SATIS'], 'kapsam': 'FIRMA'})
    y('BIRIM.TANIMLADIM', {'kod': 'SATIS', 'ad': 'Satış', 'tur': 'MASA_BASI', 'basi': None, 'ust_birim': 'YONETIM'})
    y('BIRIM.TANIMLADIM', {'kod': 'MUHASEBE', 'ad': 'Muhasebe ve Finans', 'tur': 'MASA_BASI', 'basi': None, 'ust_birim': 'YONETIM'})
    y('KISI.EKLEDIM', {'kod': 'K050', 'ad': 'Satış Yöneticisi', 'birim': 'SATIS', 'yaka': 'BEYAZ',
                       'roller': ['YONETICI'], 'giris_tarihi': '2026-01-01'})
    y('KISI.EKLEDIM', {'kod': 'K060', 'ad': 'Muhasebe Uzmanı', 'birim': 'MUHASEBE', 'yaka': 'BEYAZ',
                       'roller': ['BEYAZ_YAKA'], 'giris_tarihi': '2026-01-01'})
    y('KISI.DEGISTIRDIM', {'kisi': 'K050', 'degisenler': {'roller': ['YONETICI', 'SATIS']}, 'gecerli_baslangic': c.simdi()})
    # MUHASEBE rolü yalnızca M1.1A kuruluysa vardır:
    if 'MUHASEBE' in {r['kod'] for r in c.kunye.get('roller', [])}:
        y('KISI.DEGISTIRDIM', {'kisi': 'K060', 'degisenler': {'roller': ['BEYAZ_YAKA', 'MUHASEBE']},
                               'gecerli_baslangic': c.simdi()})
