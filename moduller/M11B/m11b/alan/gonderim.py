"""Planı göndermek: "Onayla ve yayımla" (SPEC › 8.2.2).

Satırlar toplu iş gibi tek tek gönderilir (irp_sozlesme/sozlesme/01_baglanti.md › 2.3):
- Değişikliğin satırı gönderim boyunca bir bağlantıda kilitli kalır (FOR UPDATE NOWAIT); ikinci gönderme 409 alır.
- Her satırın sonucu gönderimin hemen ardından, ayrı ve kısa bir işlemle yazılır. Gönderim yarıda kesilirse
  kilitli işlem geri alınır ama sonuçlar kalır; sürdürülünce BASARILI satırlar yeniden gönderilmez.
- Ret gelince durulur, değişiklik YARIM olur. BAYAT kendiliğinden yeniden gönderilmez.
"""
import time

from . import yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi, gunluk, olay_reddi
from .plan import NEDENLER, _kilitle, plan_durumu
from ..depo import dosya as depo_dosya
from ..depo import plan as depo

DENEME = 3


def gonder(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Planı proje sorumlusu ya da yetkili onaylar.')
    with b.vt.havuz.connection() as a:
        devir_gerek(a, proje_kimligi)
        d = _kilitle(a, proje_kimligi)
        if d is None:
            raise ModulHatasi(409, 'TASLAK_YOK', 'Gönderilecek plan yok; önce taslağı kaydedin.')
        satirlar = depo.satirlar(a, d['kimlik'])
        _gondermeden_once(a, d, satirlar)
        depo.degisiklik_guncelle(a, d['kimlik'], durum='GONDERILIYOR')
        for s in satirlar:
            if s['sonuc'] == 'BASARILI':
                continue
            cevap = _satiri_gonder(b, proje_kimligi, d, s)
            if cevap is not None and not cevap.basarili:
                depo.degisiklik_guncelle(a, d['kimlik'], durum='YARIM')
                a.commit()
                hata = olay_reddi(cevap, 'ETAP')
                hata.ek.update(satir=s['sira'], durum='YARIM', asama='SATIR')
                raise hata
        girdiler = {'proje': proje_kimligi}
        if d['tur'] == 'DEGISIKLIK':
            girdiler['gerekce'] = f"{NEDENLER[d['neden']]}: {d['gerekce']}"
        cevap = b.olay('PLAN.ONAYLADIM', girdiler)
        if not cevap.basarili:
            depo.degisiklik_guncelle(a, d['kimlik'], durum='YARIM')
            a.commit()
            hata = olay_reddi(cevap, 'PLAN.ONAYLADIM')
            hata.ek.update(durum='YARIM', asama='ONAY',
                           uyari='Etaplar çekirdekte değişti ama plan onaylanmadı. "Yeniden dene" yalnızca onayı gönderir.')
            raise hata
        # Numara modül sayacından türetilmez: dışarıda onaylanan sürümler de çekirdektedir.
        surumler = b.oku('PLAN', proje_kimligi, surumler=True).get('surumler', [])
        son_no = surumler[-1]['no'] if surumler else None
        surum_no = int(son_no[1:]) if son_no and son_no.startswith('B') else None
        onaylanan = depo.degisiklik_guncelle(
            a, d['kimlik'], durum='ONAYLANDI', plan_olayi=cevap['olay_kimligi'], onaylayan=b.kisi,
            onay_ani=b.simdi(), surum_no=surum_no)
    return {**plan_durumu(b, proje_kimligi), 'bildirim': _onay_sonrasi(b, proje_kimligi, onaylanan)}


def _onay_sonrasi(b, proje_kimligi, onaylanan):
    """Bildirim başarısızsa plan geri alınmaz; kural işi telafi eder (SPEC › 8.2.2 › 5)."""
    from .bildirim import plan_yayimlandi_birak
    try:
        return plan_yayimlandi_birak(b, proje_kimligi, onaylanan)
    except Exception:  # noqa: BLE001
        gunluk.exception('PLAN_YAYIMLANDI bırakılamadı (proje %s); kural işi telafi edecek', proje_kimligi)
        return None


def _gondermeden_once(c, d, satirlar):
    hatalar = []
    if not satirlar:
        hatalar.append({'alan': 'satirlar', 'mesaj': 'En az bir etap olmalı.'})
    if d['tur'] == 'DEGISIKLIK':
        if d['neden'] not in NEDENLER:
            hatalar.append({'alan': 'neden', 'mesaj': 'Değişikliğin nedeni seçilmeli.'})
        if not (d['gerekce'] or '').strip():
            hatalar.append({'alan': 'gerekce', 'mesaj': 'Gerekçe boş olamaz.'})
        kanitlar = [depo_dosya.dosya(c, k) for k in depo.kanitlar(c, d['kimlik'])]
        if not any(k and k['tur'] == 'PLAN_KANITI' for k in kanitlar):
            hatalar.append({'alan': 'kanitlar', 'mesaj': 'En az bir plan kanıtı (dosya kaydı) gerekli.'})
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'Plan gönderilmeden önce tamamlanmalı.', hatalar=hatalar)


def _satiri_gonder(b, proje, d, s):
    """Satırı gönderir ve sonucunu hemen yazar. Değişmeden kalan var olan etabın eki olaysız yazılır."""
    if s['islem'] == 'TANIMLA':
        cevap = b.olay('ETAP.TANIMLADIM', s['girdiler'])
        etap = cevap['olay_kimligi'] if cevap.basarili else None
    elif s['girdiler'].get('degisenler'):
        cevap = b.olay('ETAP.DEGISTIRDIM', {'degisenler': s['girdiler']['degisenler']},
                       neyin_ustunde=[{'tur': 'ETAP', 'kimlik': s['etap'], 'surum': s['okunan_surum']}])
        etap = s['etap']
    else:
        cevap, etap = None, s['etap']
    basarili = cevap is None or cevap.basarili
    olay = cevap.get('olay_kimligi') if cevap is not None else None
    _sonucu_yaz(b, proje, d['kimlik'], s, basarili, olay, etap, cevap)
    return cevap


def _sonucu_yaz(b, proje, degisiklik, s, basarili, olay, etap, cevap):
    """Çekirdek kabul ettikten sonra kaydı yazamamak sonraki gönderimde aynı etabı ikinci kez tanımlatır;
    bu yüzden birkaç kez denenir, olmazsa olay kimliğiyle günlüğe yazılır."""
    for i in range(DENEME):
        try:
            with b.vt.islem() as c:
                if basarili:
                    depo.satir_sonucu(c, degisiklik, s['sira'], 'BASARILI', olay, etap=etap)
                    depo.etap_eki_yaz(c, etap, proje, s['etap_eki'])
                else:
                    depo.satir_sonucu(c, degisiklik, s['sira'], 'REDDEDILDI', olay, cevap.get('kod'),
                                      cevap.get('neden'))
            return
        except Exception:  # noqa: BLE001
            if i == DENEME - 1:
                gunluk.exception('Plan satırının sonucu yazılamadı: değişiklik %s, satır %s, olay %s, sonuç %s',
                                 degisiklik, s['sira'], olay, 'BASARILI' if basarili else 'REDDEDILDI')
                raise ModulHatasi(500, 'KAYIT', 'Beklenmeyen bir hata oldu.', olay_kimligi=olay) from None
            time.sleep(0.2 * (i + 1))


def yeniden_oku(b, proje_kimligi, sira):
    """BAYAT satırın güncel halini okur ve okunan sürümü yeniler; gönderim o satırdan sürer (SPEC › 8.2.2 › 3)."""
    proje = b.proje(proje_kimligi)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Planı proje sorumlusu ya da yetkili onaylar.')
    with b.vt.islem() as c:
        d = _kilitle(c, proje_kimligi)
        if d is None or d['durum'] != 'YARIM':
            raise ModulHatasi(409, 'YARIM_DEGIL', 'Yeniden okunacak yarım bir gönderim yok.')
        s = depo.satir(c, d['kimlik'], sira)
        if s is None or s['sonuc'] == 'BASARILI':
            raise ModulHatasi(404, 'SATIR_YOK', 'Bu satır yeniden okunamaz.')
        guncel = b.oku('ETAP', s['etap']) if s['etap'] else None
        depo.satir_surumu(c, d['kimlik'], sira, guncel.get('surum') if guncel else None)
    return {'guncel': guncel, 'plan': plan_durumu(b, proje_kimligi)}
