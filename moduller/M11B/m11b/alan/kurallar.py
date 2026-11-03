"""Kural işi (SPEC › 8.12): python -m m11b.komutlar kurallari-calistir; arka yüzde M11B_KURAL_ARALIGI_DK'da bir.

Tekrar güvenlidir: bırakma ve kaldırma aynı anahtarla tekildir. Servis gözüyle okunan veri yalnızca alıcı listesini
kurar, ekrana gitmez. Servis okuması gerçek bulutta MVP'den sonra gelir; o zamana kadar bu iş simülatörde çalışır.
"""
from irp_sozlesme.baglanti import CekirdekHatasi

from ..depo import devir as depo_devir
from ..depo import plan as depo_plan
from . import bildirim
from .hatalar import gunluk


def kurallari_calistir(cekirdek, vt):
    servis = cekirdek.servis()
    sonuc = {'birakilan': 0, 'kaldirilan': 0, 'hata': 0}
    with vt.islem() as c:
        devirler = depo_devir.devirler(c)
    for d in devirler:
        try:
            proje = servis.oku('PROJE', d['proje']).deger
            if not proje.get('aktif'):
                if servis.bildirim_kaldir(bildirim.KURAL, {'tur': 'PROJE', 'kimlik': d['proje']}).get('kaldirilan'):
                    sonuc['kaldirilan'] += 1
                continue
            with vt.islem() as c:
                bekleyen = depo_plan.bildirim_bekleyenler(c, d['proje'])
            if not bekleyen:
                continue
            etaplar = servis.oku('ETAPLAR', None, proje=d['proje']).deger
            bildirim.birak(servis, proje, etaplar, bekleyen[-1])
            with vt.islem() as c:
                depo_plan.bildirim_isaretle(c, d['proje'])
            sonuc['birakilan'] += 1
        except CekirdekHatasi as e:
            sonuc['hata'] += 1
            gunluk.warning('Kural işi proje %s için çalışamadı: %s', d['proje'], e)
    return sonuc


def bildirimleri_kaldir(cekirdek, vt):
    """Modül kapatılmadan önce bütün açık bildirimleri kaldırır (irp_sozlesme/sozlesme/02_kurallar.md › 5)."""
    servis = cekirdek.servis()
    with vt.islem() as c:
        devirler = depo_devir.devirler(c)
    kaldirilan = 0
    for d in devirler:
        if servis.bildirim_kaldir(bildirim.KURAL, {'tur': 'PROJE', 'kimlik': d['proje']}).get('kaldirilan'):
            kaldirilan += 1
    return {'kaldirilan': kaldirilan}
