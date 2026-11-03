"""Dosya kaydı eklemek (SPEC › 8.4). Dosya yüklenmez; kayıt adı, konumu ve isteğe bağlı parmak izini taşır.
Dosya kayıtları çekirdeğe `kanit` olarak gönderilmez (M11B-05)."""
import re

from ..depo import devir as depo_devir
from ..depo import dosya as depo
from . import yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi

TURLER = ('TASARIM_GIRDISI', 'RISK_ANALIZI', 'TGG', 'TUTANAK', 'PLAN_KANITI', 'DIGER')
VARSAYILAN_KLASOR = {'TASARIM_GIRDISI': 'TEKNIK_DOKUMANLAR', 'RISK_ANALIZI': 'TEKNIK_DOKUMANLAR',
                     'TGG': 'PROJE_GOZDEN_GECIRME', 'TUTANAK': 'TOPLANTI_PLANLAMA', 'PLAN_KANITI': 'ETUD_ONAY'}
PARMAK_IZI = re.compile(r'^[0-9a-f]{64}$')


def dogrula(govde):
    """Saf doğrulama: hata listesi."""
    hatalar = []
    if govde.get('tur') not in TURLER:
        hatalar.append({'alan': 'tur', 'mesaj': 'Dosya türü geçersiz.'})
    if not (govde.get('ad') or '').strip():
        hatalar.append({'alan': 'ad', 'mesaj': 'Ad boş olamaz.'})
    if not (govde.get('konum') or '').strip():
        hatalar.append({'alan': 'konum', 'mesaj': 'Konum (sunucudaki yol ya da bağlantı) boş olamaz.'})
    iz = govde.get('parmak_izi')
    if iz and not PARMAK_IZI.match(iz.lower()):
        hatalar.append({'alan': 'parmak_izi', 'mesaj': 'Parmak izi 64 karakter SHA-256 (hex) olmalı.'})
    if govde.get('tur') == 'DIGER' and not govde.get('klasor'):
        hatalar.append({'alan': 'klasor', 'mesaj': 'Klasör seçilmeli.'})
    return hatalar


def dosya_ekle(b, proje_kimligi, govde, c=None):
    """Dosya kaydını ekler; `c` verilirse o işlemde (ör. görev atamasının TGG kaydı)."""
    proje = b.proje(proje_kimligi)
    hatalar = dogrula(govde)
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'Dosya kaydında eksik ya da hatalı alan var.', hatalar=hatalar)
    if c is None:
        with b.vt.islem() as c:
            return _ekle(b, c, proje, govde)
    return _ekle(b, c, proje, govde)


def _ekle(b, c, proje, govde):
    devir_gerek(c, proje['kimlik'])
    klasorler = depo_devir.klasorler(c, proje['kimlik'])
    if govde.get('klasor'):
        klasor = next((k for k in klasorler if k['kimlik'] == govde['klasor']), None)
    else:
        klasor = next((k for k in klasorler if k['sablon_kodu'] == VARSAYILAN_KLASOR[govde['tur']]), None)
    if klasor is None:
        raise ModulHatasi(422, 'DOGRULAMA', 'Klasör bu projede bulunamadı.',
                          hatalar=[{'alan': 'klasor', 'mesaj': 'Klasör bulunamadı.'}])
    yetki.gerek(yetki.dosya_ekleyebilir(b, proje, klasor),
                'Dosya kaydını proje sorumlusu, yetkili ya da klasörün sorumlu birimi ekler.')
    iz = (govde.get('parmak_izi') or '').lower() or None
    return depo.dosya_ekle(c, proje['kimlik'], klasor['kimlik'], govde['tur'], govde['ad'].strip(),
                           govde['konum'].strip(), iz, (govde.get('aciklama') or '').strip() or None, b.kisi,
                           b.simdi())
