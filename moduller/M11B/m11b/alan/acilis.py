"""Açılış listesi ve devrin tamamlanması (SPEC › 8.9). Kapı değildir; adımlar herhangi bir sırayla yapılabilir."""
from irp_sozlesme.baglanti import CekirdekHatasi

from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from ..depo import kapi as depo_kapi
from ..depo import notlar as depo_notlar
from .hatalar import gunluk
from .zaman import an_metni

KLASOR_SAYISI = 10


def acilis_listesi(plan_var, klasor_sayisi, tasarim_girdisi_sayisi, gecis_var, kategoriler, dolu_kategoriler,
                   sunum_ani, gorev_sayisi):
    """Altı adım, her biri ✓ ya da eksik. kategoriler: [{kod, ad, acilis_listesinde}]."""
    aranan = [k for k in kategoriler if k['acilis_listesinde']]
    eksik = [k['ad'] for k in aranan if k['kod'] not in dolu_kategoriler]
    girdi_aciklama = None
    if not tasarim_girdisi_sayisi:
        girdi_aciklama = 'Gerekçeyle geçildi' if gecis_var else 'Tasarım girdisi yok'
    adimlar = [
        {'no': 1, 'kod': 'PLAN', 'ad': 'Plan', 'tamam': bool(plan_var),
         'aciklama': None if plan_var else 'B0 onaylanmadı'},
        {'no': 2, 'kod': 'KLASOR', 'ad': 'Klasör', 'tamam': klasor_sayisi >= KLASOR_SAYISI,
         'aciklama': f'{klasor_sayisi}/{KLASOR_SAYISI} klasör'},
        {'no': 3, 'kod': 'TASARIM_GIRDILERI', 'ad': 'Tasarım girdileri', 'tamam': tasarim_girdisi_sayisi > 0,
         'aciklama': girdi_aciklama},
        {'no': 4, 'kod': 'NOTLAR', 'ad': 'Notlar', 'tamam': not eksik,
         'aciklama': ('Eksik: ' + ', '.join(eksik)) if eksik else None, 'eksikler': eksik},
        {'no': 5, 'kod': 'SUNUM', 'ad': 'Sunum', 'tamam': sunum_ani is not None,
         'aciklama': None if sunum_ani else 'Açılış toplantısı kaydedilmedi'},
        {'no': 6, 'kod': 'GOREV_ATAMA', 'ad': 'Görev atama', 'tamam': gorev_sayisi > 0,
         'aciklama': None if gorev_sayisi else 'Modülden görev atanmadı'},
    ]
    return {'adimlar': adimlar, 'tamam_sayisi': sum(a['tamam'] for a in adimlar), 'toplam': len(adimlar)}


def acilis(b, proje_kimligi, plan_var=None):
    """Açılış listesini hesaplar; altısı ✓ ise devrin tamamlanma anını bir kez yazar.
    plan_var verilmezse PLAN okunur (B0 boş değil mi); projeler listesi GANTT'tan verir."""
    if plan_var is None:
        plan_var = bool(b.oku('PLAN', proje_kimligi).get('B0'))
    with b.vt.islem() as c:
        devir = depo_devir.devir(c, proje_kimligi)
        liste = acilis_listesi(
            plan_var, depo_devir.klasor_sayisi(c, proje_kimligi),
            depo_dosya.dosya_sayisi(c, proje_kimligi, 'TASARIM_GIRDISI'),
            bool(depo_kapi.gecisler(c, proje_kimligi)), depo_devir.not_kategorileri(c),
            depo_notlar.kategori_kodlari_dolu(c, proje_kimligi), devir['sunum_ani'],
            depo_kapi.gorev_atamasi_sayisi(c, proje_kimligi))
        if liste['tamam_sayisi'] == liste['toplam'] and devir['tamamlanma_ani'] is None:
            depo_devir.tamamlandi_yaz(c, proje_kimligi, b.simdi())
            devir = depo_devir.devir(c, proje_kimligi)
    return {**liste, 'tamamlanma_ani': an_metni(devir['tamamlanma_ani'])}


def degerlendir(b, proje_kimligi):
    """Bir işten sonra listeyi yeniden hesaplar (tamamlanma anı için). İşin kendisini bozmaz."""
    try:
        return acilis(b, proje_kimligi)
    except CekirdekHatasi as e:
        gunluk.warning('Açılış listesi hesaplanamadı (proje %s): %s', proje_kimligi, e)
        return None
