"""GET /api/saglanan/{ad}: modülün sağladığı okumalar (Ek D.4). Kullanıcının gözü: çağıran, kullanıcının anahtarını
olduğu gibi iletir; modül `cekirdek.oturum(anahtar)` ile açar ve kişiyi KISILER'den tanır."""
from fastapi import APIRouter, Depends, Query

from .. import hatalar, vt
from ..alan import saglanan
from .baglam import ERISIM_YOK, Baglam, baglam
from .yanit import yanit

yol = APIRouter()


@yol.get('/saglanan/{ad}')
def oku(ad: str, surum: int | None = Query(default=None), bg: Baglam = Depends(baglam)):
    if ad == 'M10.KAZANAN_SURUMLER':
        if not bg.kisi.erisim:
            raise hatalar.yetki(ERISIM_YOK)
        with vt.islem() as b:
            rows = b.execute("SELECT s.kimlik AS surum,t.konu,m.ad AS musteri,"
                             "t.talep_no||'/V'||s.no AS etiket FROM talepler t "
                             "JOIN musteriler m ON m.kimlik=t.musteri JOIN teklif_surumleri s ON s.kimlik=t.kazanan_surum "
                             "WHERE t.durum='KAZANILDI' AND s.durum='GONDERILDI' ORDER BY t.kimlik DESC").fetchall()
            return yanit({'surumler': rows}, baglam=bg)
    if ad == 'M10.KAZANAN_SURUM':
        # Görme (ROL): SATIS, YETKILI ya da yönetim birimi
        if not bg.kisi.erisim:
            raise hatalar.yetki(ERISIM_YOK)
        if surum is None:
            raise hatalar.dogrulama([hatalar.hata('surum', 'surum parametresi gerekli.')])
        with vt.islem() as b:
            return yanit(saglanan.kazanan_surum(b, surum), baglam=bg)
    if ad == 'M10.KATALOG_TEMIN_SURELERI':
        # Görme (KAYDI_GOREN): oturumu olan herkes; fiyat yok
        with vt.islem() as b:
            return yanit(saglanan.katalog_temin_sureleri(b), baglam=bg)
    raise hatalar.ModulHatasi(404, 'TANIMSIZ_VERI', f'{ad} adında bir okuma yok.')
