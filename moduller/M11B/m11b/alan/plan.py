"""Plan: başlangıç planı (B0) ve değişiklikler (B1, B2…) (SPEC › 8.2).

Etaplar ve plan sürümleri çekirdektedir. Modülde yalnızca taslak, satırların gönderim sonucu, değişikliğin nedeni,
kanıtı ve etabın eki (şablon kodu, sıra, paralel grup, tasarım kapısı) durur.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

import psycopg

from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from ..depo import plan as depo
from . import yetki
from .devir import devir_gerek
from .hatalar import ModulHatasi
from .zaman import an_metni, gun

ETAP_ALANLARI = ('ad', 'birim', 'baslangic', 'bitis', 'hedef_saat', 'sorumlu')
DEGISEBILIR = ('ad', 'baslangic', 'bitis', 'hedef_saat', 'sorumlu')       # ETAP.DEGISTIRDIM'in izinli alanları
NEDENLER = {'MUSTERI_OTELEMESI': 'Müşteri ötelemesi', 'KARSILIKLI_ANLASMA': 'Karşılıklı anlaşma'}   # P0454
B0_UYARISI = 'B0 projenin bütün etaplarını dondurur.'
ONAYSIZ_UYARISI = 'Çekirdekte onaylanmamış etap değişikliği var.'
DIS_SURUM_NOTU = 'İlk plan modül dışında onaylanmış; sürüm numaraları çekirdekten gelince gösterilecek.'


# ------------------------------------------------------------------ saf fonksiyonlar

def yuvarla(x):
    """Yarım yukarı yuvarlama (0,5 → 1)."""
    return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def on_doldurma_gunleri(proje, devir_gunu):
    """P0 = başlangıç tarihi, yoksa devrin başladığı gün. P1 = kesin kabul, yoksa teslim; yoksa None."""
    p0 = gun(proje.get('baslangic_tarihi')) or gun(devir_gunu)
    p1 = gun(proje.get('kesin_kabul_tarihi')) or gun(proje.get('teslim_tarihi'))
    return p0, p1


def on_doldur(sablon, p0, p1, birimler):
    """Şablonun satırlarından taslak satırlar: "Gantt sıfırdan hazırlanmaz". P1 yoksa tarihler boş gelir."""
    basi = {x['kimlik']: x.get('basi') for x in birimler}
    n = (p1 - p0).days if p1 else None
    satirlar = []
    for s in sablon:
        birim = s.get('varsayilan_birim')
        satirlar.append({
            'islem': 'TANIMLA', 'etap': None, 'okunan_surum': None, 'ad': s['ad'], 'birim': birim,
            'baslangic': (p0 + timedelta(days=yuvarla(Decimal(s['bas_orani']) * n))).isoformat() if p1 else None,
            'bitis': (p0 + timedelta(days=yuvarla(Decimal(s['bit_orani']) * n))).isoformat() if p1 else None,
            'hedef_saat': 0, 'sorumlu': basi.get(birim), 'sablon_kodu': s['kod'], 'paralel_grup': s['paralel_grup'],
            'tasarim_kapisi': s['tasarim_kapisi']})
    return satirlar


def degisenler(istenen, taban):
    """ETAP.DEGISTIRDIM'e yalnızca değişen ve izinli alanlar gider."""
    return {k: istenen.get(k) for k in DEGISEBILIR if istenen.get(k) != taban.get(k)}


def satir_dogrula(s, birimler, kisiler, sorumlu_denetle=True):
    """Göndermeden önce modülde doğrulama (SPEC › 8.2.1). Hata listesi döner. Var olan etabın değişmeyen
    sorumlusu çekirdeğe gönderilmediği için denetlenmez (sorumlu_denetle=False)."""
    hatalar = []

    def hata(alan, mesaj):
        hatalar.append({'sira': s.get('sira'), 'alan': alan, 'mesaj': mesaj})

    if not (s.get('ad') or '').strip():
        hata('ad', 'Etabın adı boş olamaz.')
    bas, bit = s.get('baslangic'), s.get('bitis')
    if not bas or not bit:
        hata('baslangic', 'Başlangıç ve bitiş tarihi gerekli.')
    elif gun(bas) > gun(bit):
        hata('bitis', 'Başlangıç bitişten sonra olamaz.')
    if s.get('birim') not in {b['kimlik'] for b in birimler}:
        hata('birim', 'Birim bulunamadı.')
    h = s.get('hedef_saat')
    if not isinstance(h, int) or isinstance(h, bool) or h < 0:
        hata('hedef_saat', 'Hedef saat 0 ya da pozitif tam sayı olmalı.')
    if sorumlu_denetle and s.get('sorumlu') and s['sorumlu'] not in {k['kimlik'] for k in kisiler if k.get('aktif')}:
        hata('sorumlu', 'Sorumlu aktif bir kişi değil.')
    return hatalar


# ------------------------------------------------------------------ okuma: planın ekranı

def _plan_okumasi(b, proje):
    plan = b.oku('PLAN', proje, surumler=True)
    etaplar = {e['kimlik']: e for e in b.oku('ETAPLAR', None, proje=proje)}
    return plan, etaplar


def plan_turu(plan):
    return 'DEGISIKLIK' if plan.get('B0') else 'BASLANGIC'


def plan_durumu(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir = devir_gerek(c, proje_kimligi)
        acik = depo.acik_degisiklik(c, proje_kimligi)
        satirlar = depo.satirlar(c, acik['kimlik']) if acik else []
        kanitlar = depo.kanitlar(c, acik['kimlik']) if acik else []
        ekler = depo.etap_ekleri(c, proje_kimligi)
        sablon = depo_devir.etap_sablonu(c, yalniz_aktif=True)
    plan, etaplar = _plan_okumasi(b, proje_kimligi)
    tur = acik['tur'] if acik else plan_turu(plan)
    if acik:
        gosterilen = [_kayitli_satir(s, etaplar) for s in satirlar]
    else:
        gosterilen = oneri(b, proje, devir, tur, etaplar, ekler, sablon)
    uyarilar = []
    if etaplar and tur == 'BASLANGIC':
        uyarilar.append(B0_UYARISI)
    if plan.get('onaysiz_degisti'):
        uyarilar.append(ONAYSIZ_UYARISI)
    return {
        'tur': tur, 'b0_var': bool(plan.get('B0')), 'onaysiz_degisti': bool(plan.get('onaysiz_degisti')),
        'degisiklik': _degisiklik(acik, kanitlar), 'oneri': acik is None, 'satirlar': gosterilen,
        'surum_defteri': cekirdek_defteri(plan), 'surum_notu': None, 'uyarilar': uyarilar,
        'cekirdek_surumleri': plan.get('surumler', []),
        'nedenler': [{'kod': k, 'ad': v} for k, v in NEDENLER.items()],
    }


def cekirdek_defteri(plan):
    """Ekran/sağlayıcı defteri de ortak onay listesidir; yerel sayaç esas alınmaz."""
    return [dict(s,ad=s['no'],surum_no=int(s['no'][1:])) for s in plan.get('surumler',[])]


def oneri(b, proje, devir, tur, etaplar, ekler, sablon):
    """Açık değişiklik yoksa: çekirdekte var olan etaplar (değiştirilebilir, çıkarılamaz) ve başlangıç planında
    şablonun henüz bağlanmamış aktif satırları, ön doldurmayla."""
    satirlar = []
    for e in sorted(etaplar.values(), key=lambda e: (ekler.get(e['kimlik'], {}).get('sira') or 10_000, e['baslangic'])):
        ek = ekler.get(e['kimlik'], {})
        satirlar.append({'islem': 'DEGISTIR', 'etap': e['kimlik'], 'okunan_surum': e.get('surum'),
                         **{k: e.get(k) for k in ETAP_ALANLARI}, 'sablon_kodu': ek.get('sablon_kodu'),
                         'paralel_grup': ek.get('paralel_grup'), 'tasarim_kapisi': bool(ek.get('tasarim_kapisi'))})
    if tur == 'BASLANGIC':
        bagli = {ek.get('sablon_kodu') for ek in ekler.values()}
        p0, p1 = on_doldurma_gunleri(proje, devir['baslama_ani'])
        from . import siparis
        gelen=siparis.oneri(b,proje['kimlik'],sablon)
        satirlar += ([s for s in gelen if s.get('sablon_kodu') not in bagli] if gelen is not None
                     else on_doldur([s for s in sablon if s['kod'] not in bagli], p0, p1, b.birimler))
    for i, s in enumerate(satirlar, 1):
        s.update(sira=i, sonuc=None, red_kodu=None, red_nedeni=None, olay_kimligi=None, var_olan=bool(s['etap']))
    return satirlar


def _kayitli_satir(s, etaplar):
    g, ek = s['girdiler'], s['etap_eki']
    if s['islem'] == 'TANIMLA':
        degerler = {k: g.get(k) for k in ETAP_ALANLARI}
    else:
        e = etaplar.get(s['etap'], {})
        degerler = {**{k: e.get(k) for k in ETAP_ALANLARI}, **g.get('degisenler', {})}
    return {'sira': s['sira'], 'islem': s['islem'], 'etap': s['etap'], 'okunan_surum': s['okunan_surum'], **degerler,
            'sablon_kodu': ek.get('sablon_kodu'), 'paralel_grup': ek.get('paralel_grup'),
            'tasarim_kapisi': bool(ek.get('tasarim_kapisi')), 'sonuc': s['sonuc'], 'red_kodu': s['red_kodu'],
            'red_nedeni': s['red_nedeni'], 'olay_kimligi': s['olay_kimligi'], 'var_olan': s['islem'] == 'DEGISTIR',
            'degisenler': g.get('degisenler') if s['islem'] == 'DEGISTIR' else None}


def _degisiklik(d, kanitlar):
    if not d:
        return None
    return {'kimlik': d['kimlik'], 'tur': d['tur'], 'durum': d['durum'], 'neden': d['neden'], 'gerekce': d['gerekce'],
            'hazirlayan': d['hazirlayan'], 'hazirlama_ani': an_metni(d['hazirlama_ani']), 'kanitlar': kanitlar}


def surum_defteri(c, proje):
    kayitlar = []
    for d in depo.onaylananlar(c, proje):
        kayitlar.append({'kimlik': d['kimlik'], 'surum_no': d['surum_no'],
                         'ad': f"B{d['surum_no']}" if d['surum_no'] is not None else None, 'tur': d['tur'],
                         'onay_ani': an_metni(d['onay_ani']), 'onaylayan': d['onaylayan'], 'neden': d['neden'],
                         'neden_adi': NEDENLER.get(d['neden']), 'gerekce': d['gerekce'], 'plan_olayi': d['plan_olayi'],
                         'kanitlar': [_kanit(depo_dosya.dosya(c, k)) for k in depo.kanitlar(c, d['kimlik'])]})
    dis = any(k['surum_no'] is None for k in kayitlar)
    return {'kayitlar': kayitlar, 'not': DIS_SURUM_NOTU if dis else None}


def _kanit(d):
    return {'kimlik': d['kimlik'], 'ad': d['ad'], 'konum': d['konum']}


# ------------------------------------------------------------------ taslak

def taslak_kaydet(b, proje_kimligi, govde):
    """Taslağı oluşturur ya da günceller. YARIM değişiklikte gönderilmiş (BASARILI) satırlar korunur."""
    proje = b.proje(proje_kimligi)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Planı proje sorumlusu ya da yetkili hazırlar.')
    plan, etaplar = _plan_okumasi(b, proje_kimligi)
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        acik = _kilitle(c, proje_kimligi)
        if acik and acik['durum'] not in ('TASLAK', 'YARIM'):
            raise ModulHatasi(409, 'GONDERIM_SURUYOR', 'Plan şu anda gönderiliyor.')
        tur = acik['tur'] if acik and acik['durum'] == 'YARIM' else plan_turu(plan)
        korunan = {s['sira']: s for s in depo.satirlar(c, acik['kimlik'])
                   if s['sonuc'] == 'BASARILI'} if acik else {}
        sablon = {s['kod']: s for s in depo_devir.etap_sablonu(c)}
        satirlar = _satirlari_hazirla(b, proje_kimligi, govde, etaplar, korunan, sablon)
        _kanitlari_dogrula(c, proje_kimligi, govde.get('kanitlar') or [])
        neden, gerekce = govde.get('neden'), (govde.get('gerekce') or '').strip() or None
        if tur == 'BASLANGIC':
            neden = gerekce = None
        if acik is None:
            acik = depo.degisiklik_ekle(c, proje_kimligi, tur, b.kisi, b.simdi(), neden, gerekce)
        else:
            acik = depo.degisiklik_guncelle(c, acik['kimlik'], tur=tur, neden=neden, gerekce=gerekce)
        depo.satirlari_sil(c, acik['kimlik'], yalniz_gonderilmemis=True)
        for s in satirlar:
            depo.satir_ekle(c, acik['kimlik'], s)
        depo.kanitlari_yaz(c, acik['kimlik'], govde.get('kanitlar') or [])
    return plan_durumu(b, proje_kimligi)


def taslak_sil(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b, proje), 'Planı proje sorumlusu ya da yetkili hazırlar.')
    with b.vt.islem() as c:
        acik = _kilitle(c, proje_kimligi)
        if not acik:
            raise ModulHatasi(404, 'TASLAK_YOK', 'Silinecek taslak yok.')
        if acik['durum'] != 'TASLAK':
            raise ModulHatasi(409, 'TASLAK_DEGIL', 'Gönderilmeye başlanmış değişiklikten vazgeçilemez; '
                                                   'tanımlanan etap çekirdekte silinemez.')
        depo.degisiklik_sil(c, acik['kimlik'])
    return plan_durumu(b, proje_kimligi)


def _kilitle(c, proje):
    try:
        return depo.acik_degisiklik(c, proje, kilitle=True)
    except psycopg.errors.LockNotAvailable:
        raise ModulHatasi(409, 'GONDERIM_SURUYOR', 'Plan şu anda gönderiliyor.') from None


def _satirlari_hazirla(b, proje, govde, etaplar, korunan, sablon):
    istenen = [s for s in govde.get('satirlar') or [] if s.get('sira') not in korunan]
    hatalar = []
    if not istenen and not korunan:
        hatalar.append({'sira': None, 'alan': 'satirlar', 'mesaj': 'En az bir etap olmalı.'})
    siralar = [s.get('sira') for s in istenen] + list(korunan)
    if len(siralar) != len(set(siralar)):
        hatalar.append({'sira': None, 'alan': 'sira', 'mesaj': 'Satır sıraları tekil olmalı.'})
    gelen_etaplar = {s.get('etap') for s in istenen if s.get('etap')} | {s['etap'] for s in korunan.values()}
    for e in etaplar:
        if e not in gelen_etaplar:
            hatalar.append({'sira': None, 'alan': 'etap',
                            'mesaj': f"Çekirdekteki etap çıkarılamaz: {etaplar[e]['ad']}. {B0_UYARISI}"})
    hazir = []
    for s in istenen:
        s = {**s, 'sorumlu': s.get('sorumlu') or None}
        taban = etaplar.get(s.get('etap')) if s.get('etap') else None
        hatalar += satir_dogrula(s, b.birimler, b.kisiler,
                                 sorumlu_denetle=taban is None or s['sorumlu'] != taban.get('sorumlu'))
        if s.get('sablon_kodu') and s['sablon_kodu'] not in sablon:
            hatalar.append({'sira': s['sira'], 'alan': 'sablon_kodu', 'mesaj': 'Şablon kodu bulunamadı.'})
        varsayilan_kapi = sablon.get(s.get('sablon_kodu'), {}).get('tasarim_kapisi', False)
        ek = {'sablon_kodu': s.get('sablon_kodu'), 'sira': s['sira'], 'paralel_grup': s.get('paralel_grup') or None,
              'tasarim_kapisi': s['tasarim_kapisi'] if s.get('tasarim_kapisi') is not None else varsayilan_kapi}
        if s.get('etap'):
            if taban is None:
                hatalar.append({'sira': s['sira'], 'alan': 'etap', 'mesaj': 'Etap bu projede bulunamadı.'})
                continue
            if s.get('birim') != taban.get('birim'):
                hatalar.append({'sira': s['sira'], 'alan': 'birim', 'mesaj': 'Var olan etabın birimi değiştirilemez.'})
            hazir.append({'sira': s['sira'], 'islem': 'DEGISTIR', 'etap': s['etap'],
                          'okunan_surum': s.get('okunan_surum') or taban.get('surum'),
                          'girdiler': {'degisenler': degisenler(s, taban)}, 'etap_eki': ek})
        else:
            girdiler = {'proje': proje, **{k: s.get(k) for k in ETAP_ALANLARI if k != 'sorumlu'}}
            if s.get('sorumlu'):
                girdiler['sorumlu'] = s['sorumlu']
            hazir.append({'sira': s['sira'], 'islem': 'TANIMLA', 'girdiler': girdiler, 'etap_eki': ek})
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'Planda düzeltilmesi gereken satırlar var.', hatalar=hatalar)
    return hazir


def _kanitlari_dogrula(c, proje, kanitlar):
    for k in kanitlar:
        d = depo_dosya.dosya(c, k)
        if not d or d['proje'] != proje or d['tur'] != 'PLAN_KANITI':
            raise ModulHatasi(422, 'DOGRULAMA', 'Kanıt, bu projenin PLAN_KANITI türünde bir dosya kaydı olmalı.',
                              hatalar=[{'sira': None, 'alan': 'kanitlar', 'mesaj': f'Geçersiz kanıt: {k}'}])
