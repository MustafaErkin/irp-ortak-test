"""Bilgi notları ve "gördüm" (SPEC › 8.6).

Notun metni, alıcıya düşmesi ve "gördüm" çekirdektedir: NOT.YAZDIM etiket olarak alıcı birimi taşır; çekirdek
birimin yönlendirme listesindeki kişilere bir not görevi açar; alıcının GOREV.KABUL_ETTIM'i görevi BITTI yapar.
"""
import time

from irp_sozlesme.baglanti import CekirdekHatasi

from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from ..depo import notlar as depo
from . import yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi, gunluk, olay_reddi
from .zaman import an_metni

YONLENDIRME_UYARISI = 'Alıcı birimde not yönlendirmesi tanımlı değilse not kimseye görev olarak düşmez.'
PROJE_GORUNMUYOR = 'Bu notun projesini henüz göremiyorsunuz.'
SONDA_EN_COK, SONDA_DUR = 10, 3
DENEME = 3


# ------------------------------------------------------------------ yazanın tarafı

def not_yaz(b, proje_kimligi, govde):
    proje = b.proje(proje_kimligi)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Bilgi notunu proje sorumlusu ya da yetkili yazar.')
    metin = (govde.get('metin') or '').strip()
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        kategoriler = {k['kod'] for k in depo_devir.not_kategorileri(c)}
        ekler = [depo_dosya.dosya(c, d) for d in govde.get('ekler') or []]
    hatalar = []
    if govde.get('kategori') not in kategoriler:
        hatalar.append({'alan': 'kategori', 'mesaj': 'Kategori bulunamadı.'})
    if govde.get('alici_birim') not in {x['kimlik'] for x in b.birimler}:
        hatalar.append({'alan': 'alici_birim', 'mesaj': 'Alıcı birim bulunamadı.'})
    if not metin:
        hatalar.append({'alan': 'metin', 'mesaj': 'Metin boş olamaz.'})
    if any(d is None or d['proje'] != proje_kimligi for d in ekler):
        hatalar.append({'alan': 'ekler', 'mesaj': 'Ekler bu projenin dosya kayıtlarından olmalı.'})
    if govde.get('etap') and govde['etap'] not in {e['kimlik'] for e in b.oku('ETAPLAR', None, proje=proje_kimligi)}:
        hatalar.append({'alan': 'etap', 'mesaj': 'Etap bu projede değil.'})
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'Notta eksik ya da hatalı alan var.', hatalar=hatalar)
    neyin_ustunde = [{'tur': 'PROJE', 'kimlik': proje_kimligi}]          # not bir tanıklıktır; sürüm gerekmez
    if govde.get('bagli_gorev'):
        neyin_ustunde.append({'tur': 'GOREV', 'kimlik': govde['bagli_gorev']})
    cevap = b.olay('NOT.YAZDIM', {'metin': metin, 'etiketler': [govde['alici_birim']]}, neyin_ustunde)
    if not cevap.basarili:
        raise olay_reddi(cevap, 'NOT.YAZDIM')
    not_kimligi = cevap['olay_kimligi']
    _kaydet(b, cevap, lambda c: depo.not_ekle(
        c, not_kimligi, proje_kimligi, govde['kategori'], govde['alici_birim'], govde.get('etap'),
        govde.get('bagli_gorev'), b.kisi, b.simdi(), [d['kimlik'] for d in ekler]))
    try:
        alicilar=b.oku('NOT_ALICILARI',not_kimligi)
        n=len(alicilar['alicilar'])
        uyari=f'Bilgi notu {n} kişiye iletildi.' if n else 'Not yazıldı. Bu birimde not alıcısı tanımlı olmadığı için kimseye iletilmedi.'
    except CekirdekHatasi:
        uyari='Not yazıldı; alıcı listesi şu anda doğrulanamadı.'
    return {'not_kimligi':not_kimligi,'uyari':uyari}


def _kaydet(b, cevap, yaz):
    """Çekirdek kabul ettikten sonra modülün kaydı: birkaç kez denenir, olmazsa olay kimliğiyle günlüğe (SPEC › 10)."""
    for i in range(DENEME):
        try:
            with b.vt.islem() as c:
                yaz(c)
            return
        except Exception:  # noqa: BLE001
            if i == DENEME - 1:
                gunluk.exception('Not çekirdekte kabul edildi ama modülün kaydı yazılamadı: olay %s',
                                 cevap.get('olay_kimligi'))
                raise ModulHatasi(500, 'KAYIT', 'Beklenmeyen bir hata oldu.', olay_kimligi=cevap.get('olay_kimligi'))
            time.sleep(0.2 * (i + 1))


def _not_oku(b, not_kimligi):
    try:
        return b.oku('NOT', not_kimligi)
    except CekirdekHatasi as e:
        if e.tur == 'YETKI':
            return None
        raise


def not_listesi(b, proje_kimligi):
    b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        notlar = depo.notlar(c, proje_kimligi)
        kategoriler = depo_devir.not_kategorileri(c)
    satirlar = []
    for n in notlar:
        kayit = _not_oku(b, n['not_kimligi'])
        metin = kayit.get('metin') if kayit else None
        satirlar.append({**_not_bilgisi(b, n), 'metin_basi': _bas(metin)})
    return {'notlar': satirlar, 'uyari': YONLENDIRME_UYARISI,
            'kategoriler': [{'kod': k['kod'], 'ad': k['ad'], 'varsayilan_birim': k['varsayilan_birim'],
                             'acilis_listesinde': k['acilis_listesinde']} for k in kategoriler]}


def _bas(metin, uzunluk=80):
    if metin is None:
        return None
    return metin if len(metin) <= uzunluk else metin[:uzunluk - 1].rstrip() + '…'


def _not_bilgisi(b, n):
    return {'not_kimligi': n['not_kimligi'], 'kategori': n['kategori'], 'kategori_adi': n['kategori_adi'],
            'alici_birim': n['alici_birim'], 'etap': n['etap'], 'bagli_gorev': n['bagli_gorev'], 'yazan': n['yazan'],
            'yazan_adi': b.kisi_adi(n['yazan']), 'an': an_metni(n['yazma_ani'])}


def gordum_sondasi(oku, not_kimligi, en_cok=SONDA_EN_COK, dur=SONDA_DUR):
    """Not görevlerinin kimliği <not>/<n>. n = 1'den sırayla okunur; YETKI "yok ya da göremiyorsunuz" demektir.
    Üst üste `dur` kez YETKI gelince durulur. `oku(kimlik)` görevi döndürür ya da CekirdekHatasi verir."""
    gorevler, ust_uste = [], 0
    for n in range(1, en_cok + 1):
        try:
            g = oku(f'{not_kimligi}/{n}')
        except CekirdekHatasi as e:
            if e.tur != 'YETKI':
                raise
            ust_uste += 1
            if ust_uste >= dur:
                break
            continue
        ust_uste = 0
        gorevler.append(g)
    return gorevler


def not_ayrintisi(b, proje_kimligi, not_kimligi):
    b.proje(proje_kimligi)
    with b.vt.islem() as c:
        n = depo.not_(c, not_kimligi)
        if not n or n['proje'] != proje_kimligi:
            raise ModulHatasi(404, 'NOT_YOK', 'Not bu projede bulunamadı.')
        ekler = depo.ekler(c, not_kimligi)
    kayit = _not_oku(b, not_kimligi)
    gercek_alicilar=b.oku('NOT_ALICILARI',not_kimligi)
    alicilar = [{'kisi': g.get('kisi'), 'kisi_adi': b.kisi_adi(g.get('kisi')), 'gorev': g['gorev'],
                 'durum': g.get('durum'), 'gordu': g.get('durum') == 'BITTI', 'kabul_ani': g.get('kabul_ani')}
                for g in gercek_alicilar['alicilar']]
    gordu = sum(1 for a in alicilar if a['gordu'])
    return {**_not_bilgisi(b, n), 'metin': kayit.get('metin') if kayit else None,
            'ekler': [dict(e) for e in ekler], 'alicilar': alicilar,
            'liste_tam':gercek_alicilar['liste_tam'],
            'gordu_ozeti': f'Gördü: {gordu}/{len(alicilar)}'+('' if gercek_alicilar['liste_tam'] else ' (görebildiğiniz alıcılar)')}


# ------------------------------------------------------------------ alıcının tarafı

def gorulmemis_not_gorevleri(b):
    """Oturumdaki kişinin not görevlerinden ATANDI olanlar. Not görevini çekirdek notun metniyle açar."""
    return [g for g in b.oku('GOREV', b.kisi) if g.get('tur') == 'NOT' and g.get('durum') == 'ATANDI']


def notlarim(b):
    """Metin, yazan ve an görevin kendisinden gelir. Proje bilgisi yalnızca kullanıcı projeyi görebiliyorsa
    gösterilir; göremiyorsa modülün o projeye ait kaydı gösterilmez (SPEC › 6, M11B-09)."""
    satirlar = []
    for g in gorulmemis_not_gorevleri(b):
        satir = {'gorev': g['kimlik'], 'gorev_surum': g.get('surum'), 'metin': g.get('ad'), 'yazan': g.get('veren'),
                 'yazan_adi': b.kisi_adi(g.get('veren')), 'an': g.get('atama_ani'), 'not_kimligi': g.get('kaynak'),
                 'proje': None, 'proje_gorunmuyor': False}
        with b.vt.islem() as c:
            n = depo.not_(c, g.get('kaynak')) if g.get('kaynak') else None
        if n:
            try:
                proje = b.proje(n['proje'])
            except ModulHatasi as e:
                if e.kod != 'PROJE_GORUNMUYOR':
                    raise
                satir.update(proje_gorunmuyor=True, mesaj=PROJE_GORUNMUYOR)
            else:
                with b.vt.islem() as c:
                    ekler = depo.ekler(c, n['not_kimligi'])
                kayit = _not_oku(b, n['not_kimligi'])
                satir.update(proje={'kimlik': proje['kimlik'], 'kod': proje.get('kod'), 'ad': proje.get('ad')},
                             kategori=n['kategori'], kategori_adi=n['kategori_adi'], etap=n['etap'],
                             ekler=[dict(e) for e in ekler], metin=(kayit or {}).get('metin') or satir['metin'])
        satirlar.append(satir)
    return {'notlar': satirlar}


def gordum(b, gorev_kimligi):
    """GOREV.KABUL_ETTIM, okunan sürümle. Kapı değildir; yalnızca teyittir."""
    try:
        g = b.oku('GOREV', gorev_kimligi)
    except CekirdekHatasi as e:
        if e.tur == 'YETKI':
            raise ModulHatasi(404, 'GOREV_YOK', 'Not görevi bulunamadı.') from None
        raise
    if g.get('tur') != 'NOT':
        raise ModulHatasi(409, 'NOT_GOREVI_DEGIL', 'Bu görev bir not görevi değil.')
    cevap = b.olay('GOREV.KABUL_ETTIM', {}, [b.oturum.hedef('GOREV', g)])
    if not cevap.basarili:
        raise olay_reddi(cevap, 'GOREV.KABUL_ETTIM')
    return {'gorev': gorev_kimligi, 'durum': 'BITTI', 'olay_kimligi': cevap['olay_kimligi']}
