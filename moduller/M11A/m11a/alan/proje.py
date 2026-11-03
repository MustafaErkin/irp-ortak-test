"""Projenin M1.1A kaydına erişim: her proje işinden önce PROJE kullanıcının gözüyle okunur (SPEC › 6)."""
from ..api.hatalar import ModulHatasi
from ..depo import projeler as depo

ACILIYOR_MESAJI = 'Açılış tamamlanmadı.'


def kayit(i, proje: str, acilmamis_da: bool = False) -> dict:
    """PROJE → 403 "Bu projeyi göremiyorsunuz"; M1.1A kaydı yoksa 404. ACILIYOR yalnızca açan kişiye görünür."""
    cekirdekte = i.proje(proje)
    p = depo.getir(i.b, proje)
    if not p or (p['durum'] == 'ACILIYOR' and p['acan'] != i.kisi) or (cekirdekte is None and p['durum'] == 'ACIK'):
        raise ModulHatasi(404, 'BULUNAMADI', 'Bu projenin M1.1A kaydı yok.')
    if p['durum'] == 'ACILIYOR' and not acilmamis_da:
        raise ModulHatasi(409, 'ACILIYOR', ACILIYOR_MESAJI, proje=proje)
    return p


def kart(i, proje: str) -> dict:
    """Proje kartı: özet, sipariş adı, PO işareti, devir durumu, bütçe şeridi (ölçümle), kullanıcının izinleri."""
    from ..depo import ayarlar, ticari
    from . import serit, yetki
    from .donusturme import siparis_adi
    p = kayit(i, proje, acilmamis_da=True)
    if p['durum'] == 'ACILIYOR':
        return i.cevap({'proje': proje, 'durum': 'ACILIYOR', 'mesaj': ACILIYOR_MESAJI})
    c = i.proje(proje)
    d = ticari.devir(i.b, proje)
    return i.cevap({
        'proje': proje, 'durum': p['durum'], 'ad': c.get('ad'), 'musteri': p['musteri_adi'],
        'sorumlu': c.get('sorumlu'), 'aktif': c.get('aktif'), 'siparis_adi': siparis_adi(ayarlar.oku(i.b), p),
        'teklif_etiketi': p['teklif_etiketi'], 'talep_no': p['talep_no'], 'kaynak': p['kaynak'],
        'ana_proje': p['ana_proje'], 'satis_yoneticisi': p['satis_yoneticisi'],
        'siparis_tarihi': p['siparis_tarihi'].isoformat(), 'teslim_tarihi': c.get('teslim_tarihi'),
        'kesin_kabul_tarihi': c.get('kesin_kabul_tarihi'), 'po_no': p['po_no'], 'po_bekleniyor': p['po_no'] is None,
        'vega_cari_kodu': p['vega_cari_kodu'], 'vega_proje_kodu': p['vega_proje_kodu'],
        'devir_durumu': d['durum'] if d else None, 'butce_durumu': p['butce_durumu'],
        'izinler': yetki.izinler(i.roller),
        'serit': serit.serit(p, serit.olc(i, p)),
    })
