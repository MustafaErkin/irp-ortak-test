"""Yeni eylemlerin alan sozlesmesi."""
from .olay import hedefler

def denetle(e):
    kod, g = e['eylem_kodu'], e['girdiler']
    if kod == 'KISI.AYRILDI':
        if g.get('iptal') is True:
            if g.get('ayrilis_tarihi'): raise ValueError('Iptal ve tarih birlikte olmaz')
        elif not g.get('ayrilis_tarihi'): raise ValueError('Ayrilis tarihi ya da iptal gerekli')
        if 'iptal' in g and type(g['iptal']) is not bool: raise ValueError('Iptal bool olmali')
    if kod == 'KISI.EKLEDIM' and 'ust' in g: raise ValueError('Ust yalniz birim agacindan gelir')
    if kod == 'IS.DEGISTIRDIM' and set(g['degisenler']) & {'nereye', 'proje', 'etap', 'parca_kodu', 'kategori'}:
        raise ValueError('Baglanti icin IS.BAGLANTI_DUZELTTIM gerekli')
    if kod == 'IS.BAGLANTI_DUZELTTIM':
        if len(hedefler(e, 'IS')) != 1: raise ValueError('Tek is hedefi gerekli')
        if set(g['degisenler']) - {'nereye', 'proje', 'etap', 'parca_kodu', 'kategori','nesne'}: raise ValueError('Baglanti alanlari')
    if kod == 'KOD.TANIMLADIM':
        if g['liste'] not in ('ARIZA', 'MOLA', 'PD', 'ROL','IZIN','DURUS','DURUS_NEDENI','YETKINLIK') or not isinstance(g['kod'], str) or not g['kod'].strip() or not isinstance(g['ad'], str) or type(g['aktif']) is not bool:
            raise ValueError('Kod listesi bicimi')
    if kod == 'YETKI.TANIMLADIM':
        if not isinstance(g['kimler'], list) or not all(isinstance(r, str) for r in g['kimler']) or len(set(g['kimler'])) != len(g['kimler']): raise ValueError('Kimler benzersiz rol listesi')
