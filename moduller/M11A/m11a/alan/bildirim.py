"""Bildirimler: servis gözüyle bırakılır, çekirdeğin kutusunda durur (SPEC › 8.4–8.7). Olay değildir.

Metinde tutar ve başka projeden söz yoktur; yalnızca kaydın kendi bilgisi."""
import logging

from ..baglanti import CekirdekHatasi
from ..depo import ticari

gunluk = logging.getLogger('m11a.bildirim')

TICARI_DEVIR, TUTAR_DEGISTI, BUTCE_SAPMASI = 'TICARI_DEVIR', 'TUTAR_DEGISTI', 'BUTCE_SAPMASI'
MODUL_KAYDI = {TICARI_DEVIR: 'ticari devir', TUTAR_DEGISTI: 'tutar değişikliği', BUTCE_SAPMASI: 'bütçe'}
NEDENLER = {'PROJEYI_GOREMEZ': 'projeyi göremiyor', 'AYRILDI': 'ayrıldı', 'ISTIHDAM_DISI': 'istihdam dışı'}


def _kayit(proje: str, kural: str) -> dict:
    return {'tur': 'PROJE', 'kimlik': proje, 'modul_kaydi': MODUL_KAYDI[kural]}


def acik(b, proje: str) -> dict[str, dict]:
    return {r['kural']: r for r in b.execute('SELECT * FROM mod_m11a.acik_bildirimler WHERE proje = %s', (proje,))}


def birak(cekirdek, b, proje: str, kural: str, alicilar: list[dict], metin: str, onem: str) -> dict:
    """Bırakır ya da günceller (tekillik). CekirdekHatasi çağırana geçer."""
    an = cekirdek.simdi()
    cevap = cekirdek.servis().bildirim_birak(kural, _kayit(proje, kural), alicilar, metin, onem, an=an)
    if cevap.get('alicilar'):
        b.execute("""INSERT INTO mod_m11a.acik_bildirimler (proje, kural, modul_kaydi, metin, an)
                     VALUES (%s, %s, %s, %s, %s) ON CONFLICT (proje, kural)
                     DO UPDATE SET metin = EXCLUDED.metin, an = EXCLUDED.an""",
                  (proje, kural, MODUL_KAYDI[kural], metin, an))
    return cevap


def kaldir(cekirdek, b, proje: str, kural: str) -> bool:
    """Yalnızca açık duranı kaldırır; çekirdeğe ulaşılamazsa satır kalır, kural işi yeniden dener."""
    if not b.execute('SELECT 1 FROM mod_m11a.acik_bildirimler WHERE proje = %s AND kural = %s',
                     (proje, kural)).fetchone():
        return False
    try:
        cekirdek.servis().bildirim_kaldir(kural, _kayit(proje, kural))
    except CekirdekHatasi as h:
        gunluk.warning('%s %s kaldırılamadı: %s', proje, kural, h)
        return False
    b.execute('DELETE FROM mod_m11a.acik_bildirimler WHERE proje = %s AND kural = %s', (proje, kural))
    return True


def suzulen_uyarisi(alicilar: list, suzulenler: list[dict]) -> str | None:
    if not suzulenler:
        return None
    kim = ', '.join(f'{s["kisi"]}: {NEDENLER.get(s.get("neden"), s.get("neden"))}' for s in suzulenler)
    bas = 'Muhasebede bu projeyi gören kimse yok' if not alicilar else 'Bildirim muhasebede herkese ulaşmadı'
    return f'{bas} ({kim}). Yetkili, çekirdeğin Proje erişimi ekranından erişim vermeli.'


# ---- TICARI_DEVIR
def ticari_devir_metni(p: dict, eksik_sayisi: int) -> str:
    return f'{p["proje"]} {p["proje_adi"]} · Ticari devir: {eksik_sayisi} eksik'


def ticari_devir_birak(cekirdek, b, p: dict, eksik_sayisi: int) -> dict | None:
    """Devir satırına alıcıları ve süzülenleri yazar. Başarısızsa bildirim_birakildi yanlış kalır."""
    try:
        cevap = birak(cekirdek, b, p['proje'], TICARI_DEVIR, [{'tur': 'ROL', 'kimlik': 'MUHASEBE'}],
                      ticari_devir_metni(p, eksik_sayisi), 'BILGI')
    except CekirdekHatasi as h:
        gunluk.warning('%s TICARI_DEVIR bırakılamadı: %s', p['proje'], h)
        ticari.devir_bildirimi_yaz(b, p['proje'], False)
        return None
    ticari.devir_bildirimi_yaz(b, p['proje'], True, cevap.get('alicilar') or [], cevap.get('suzulenler') or [])
    return cevap
