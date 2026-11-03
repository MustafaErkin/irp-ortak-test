"""T3/4: tarihli veri tablosu, sabit iliskiler ve birim agaci."""
from .saat import an, gun
from .olay import EYLES, hedefler

ROLLER = ('YETKILI', 'YONETICI', 'EKIP_LIDERI', 'CALISAN', 'BEYAZ_YAKA', 'IK')


def varsayilan_kodlar(surum=10.2):
    veriler = {'ROL': ROLLER + (('MALIYET',) if surum >= 10.2 else ()), 'ARIZA': ('ARIZA.MAKINE', 'ARIZA.DIGER'),
               'MOLA': ('KISISEL',), 'PD': ('PD.IDARI_MALI', 'PD.BAKIM_ONARIM',
               'PD.TERTIP_DUZEN', 'PD.EGITIM_GELISIM', 'PD.SOSYAL', 'PD.DIGER')}
    veriler.update(IZIN=('YILLIK','SAATLIK','MAZERET','UCRETLI','UCRETSIZ','SAGLIK','SERBEST_ZAMAN'),DURUS=('ELEKTRIK','ARIZA','BAKIM'))
    return {liste + ':' + kod: dict(liste=liste, kod=kod, ad=kod, aktif=True)
            for liste, kodlar in veriler.items() for kod in kodlar}


def varsayilan_yetkiler(surum=10.2):
    from .kisi_gunu import CALISAN
    tablo = {}
    def ekle(kodlar, kimler, kapsam='BIRIM'):
        for kod in kodlar:
            tablo[kod] = dict(eylem_kodu=kod, kimler=kimler, kapsam=kapsam)
    ekle(CALISAN, ['BIRIM_YONETICISI'])
    ekle(['IS.TANIMLADIM'], ['BIRIM_BASI', 'YETKILI'])
    ekle(['IS.' + k for k in ('ATADIM', 'SIRALADIM', 'DEVRETTIM', 'PLANSIZ_TANIMLADIM',
          'DEVAM_ONAYLADIM', 'SURE_EKLEDIM', 'DEGISTIRDIM', 'IPTAL_ETTIM', 'ONAYLADIM', 'REDDETTIM')], ['BIRIM_YONETICISI'])
    ekle(['IS.BAGLANTI_DUZELTTIM'], ['YONETICI'])
    ekle(['KAYIT.GECERSIZ_SAYDIM'], ['BIRIM_YONETICISI'])
    ekle(['AYAR.YONLENDIRDIM'], ['BIRIM_BASI'])
    ekle(['GOREV.ATADIM'], ['YONETICI', 'EKIP_LIDERI', 'YETKILI'], 'FIRMA')
    ekle(['GOREV.DEGISTIRDIM', 'GOREV.IPTAL_ETTIM'], ['YETKILI'], 'FIRMA')
    ekle(['ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM'], ['YONETICI', 'YETKILI'], 'FIRMA')
    ekle([k for k in EYLES if k.startswith(('AYAR.', 'KISI.', 'MAAS.', 'PROJE.', 'BIRIM.',
          'TEZGAH.', 'TAKVIM.', 'TATIL.', 'KOD.')) and k != 'AYAR.YONLENDIRDIM'], ['YETKILI'], 'FIRMA')
    from .kurallar_v7 import varsayilan_yetkiler as v7
    tablo.update({r['eylem_kodu']:r for r in v7()})
    from .kurallar_v9 import varsayilan_yetkiler as v9
    tablo.update({r['eylem_kodu']:r for r in v9()})
    if surum >= 10:
        tablo.pop('PROJE.HEPSINI_GORUR', None)
        for k in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM', 'PLAN.ONAYLADIM'):
            tablo[k] = dict(eylem_kodu=k, kimler=['YETKILI'], kapsam='FIRMA')
        for k in ('PROJE.ERISIM_VERDIM', 'PROJE.ERISIM_KALDIRDIM'):
            tablo.pop(k, None)  # T9 §6.4 sabit proje ilişkisi.
    if surum >= 10.1:
        ekle(['PLAN.TARIHLEDIM'], ['YONETICI', 'EKIP_LIDERI', 'YETKILI'], 'FIRMA')
        ekle(['MODUL.TANIMLADIM'], ['YETKILI'], 'FIRMA')
    if surum >= 10.2:
        ekle(['KISI.YETKINLIK_TANIMLADIM'], ['BIRIM_YONETICISI', 'YETKILI'])
    else: tablo.pop('KISI.YETKINLIK_TANIMLADIM', None)
    return [tablo[k] for k in sorted(tablo)]


def istihdamda(d, kisi, tarih):
    p = d.kisiler.get(kisi, {})
    donemler = p.get('istihdam_donemleri', [{'giris': p.get('giris_tarihi'), 'ayrilis': p.get('ayrilis_tarihi')}])
    return any(x.get('giris') and gun(x['giris']) <= gun(tarih)
               and (not x.get('ayrilis') or gun(tarih) <= gun(x['ayrilis'])) for x in donemler)


def simdi(d):
    return getattr(d, '_an', None) or d.saat.simdi()


def yoneticiler(d, birim):
    adaylar = {d.birimler.get(birim, {}).get('basi')}
    adaylar.update(k for k, p in d.kisiler.items() if p.get('birim') == birim and 'EKIP_LIDERI' in p.get('roller', []))
    return {k for k in adaylar if k and istihdamda(d, k, simdi(d))}


def birim_ustleri(d, birim):
    sonuc, gezilen = set(), set()
    b = d.birimler.get(birim, {}).get('ust_birim')
    while b and b not in gezilen:
        gezilen.add(b); sonuc.update(yoneticiler(d, b))
        b = d.birimler.get(b, {}).get('ust_birim')
    return sonuc


def ustler(d, kisi):
    b = d.kisiler.get(kisi, {}).get('birim')
    return (yoneticiler(d, b) | birim_ustleri(d, b)) - {kisi}


def yetkili_mi(d, e, servis=False):
    if e['giris_sekli'] == 'AKTARIM': return servis
    from .kurallar_v10_2 import yetki as yetki_v10_2
    karar = yetki_v10_2(d, e)
    if karar is not None: return karar
    from .kurallar_v10_1 import yetki as yetki_v10_1
    karar = yetki_v10_1(d, e)
    if karar is not None: return karar
    from .kurallar_v10 import yetki as yetki_v10
    karar = yetki_v10(d, e)
    if karar is not None: return karar
    from .kurallar_v9 import yetki as yetki_v9
    karar = yetki_v9(d,e)
    if karar is not None: return karar
    from .kurallar_v7 import yetki as yetki_v7
    karar = yetki_v7(d,e)
    if karar is not None: return karar
    from .kisi_gunu import CALISAN
    kim, kod, g = e['kim'], e['eylem_kodu'], e['girdiler']
    t = simdi(d)
    if not istihdamda(d, kim, t): return False
    if e.get('adina') and not istihdamda(d, e['adina'], t): return False
    roller = set(d.kisiler[kim].get('roller', []))
    if kod == 'KURULUM.TAMAMLADIM': return False
    if kod.startswith('MAAS.') or kod == 'YETKI.TANIMLADIM': return 'YETKILI' in roller
    isler = [d.isler.get(k, {}) for k in hedefler(e, 'IS')]
    gorevler = [d.gorevler.get(k, {}) for k in hedefler(e, 'GOREV')]
    if kod in ('GOREV.KABUL_ETTIM', 'GOREV.TAMAMLADIM') and any(x and not istihdamda(d, x.get('kisi'), t) for x in gorevler): return False
    if kod in ('IS.ONAYLADIM', 'IS.REDDETTIM') and any(i.get('tamamlayan') == kim for i in isler): return False
    if kod in ('GOREV.ONAYLADIM', 'GOREV.REDDETTIM') and any(x.get('kisi') == kim for x in gorevler): return False
    if kod == 'GOREV.ATADIM' and any(x['kisi'] == kim or x.get('onaylayan') == x['kisi'] for x in g['gorevler']): return False
    if kod == 'GOREV.DEGISTIRDIM':
        for x in gorevler:
            s = dict(x, **g['degisenler'])
            if s.get('onaylayan') == s.get('kisi'): return False

    def iliski(k): return k == kim or (k and kim in ustler(d, k))
    birimler, iliskiler = [], []
    if kod == 'NOT.YAZDIM': return True
    if kod in CALISAN:
        if not e.get('adina'): return True
        iliskiler = [e['adina']]
        birimler = [i.get('birim') for i in isler] or [d.kisiler[e['adina']].get('birim')]
    elif kod.startswith('IS.'):
        if kod in ('IS.ONAYLADIM', 'IS.REDDETTIM'): iliskiler = [i.get('atayan') for i in isler]
        birimler = [i.get('birim') for i in isler]
        if kod == 'IS.TANIMLADIM': birimler = [x.get('birim') for x in g['isler']]
        if kod == 'IS.PLANSIZ_TANIMLADIM': birimler = [g.get('birim') or d.kisiler[kim]['birim']]
    elif kod.startswith('GOREV.'):
        alan = 'kisi' if kod in ('GOREV.KABUL_ETTIM', 'GOREV.TAMAMLADIM') else 'onaylayan' if kod in ('GOREV.ONAYLADIM', 'GOREV.REDDETTIM') else 'veren'
        iliskiler = [x.get(alan) for x in gorevler]
        birimler = [d.kisiler.get(x.get('kisi'), {}).get('birim') for x in gorevler]
        if kod == 'GOREV.ATADIM': birimler = [d.kisiler.get(x['kisi'], {}).get('birim') for x in g['gorevler']]
    elif kod == 'KAYIT.GECERSIZ_SAYDIM':
        olaylar = d.olaylar.values() if hasattr(d.olaylar, 'values') else d.olaylar
        h = next((x for x in olaylar if x['olay_kimligi'] == g['hedef']), {})
        iliskiler = [h.get('kim')]
        birimler = [d.kisiler.get(h.get('adina') or h.get('kim'), {}).get('birim')]
    else:
        birimler = [g.get('birim') or d.kisiler.get(g.get('kisi'), {}).get('birim')]
    kurallar = [r for r in d.yetki_kurallari if r['eylem_kodu'] == kod and not r.get('gecerli_bitis') and r['kimler']]
    def tablo_izni(b):
        for r in kurallar:
            kimler = set(r['kimler'])
            if r['kapsam'] == 'FIRMA':
                if roller & kimler: return True
                if any(set(p.get('roller', [])) & kimler and istihdamda(d, k, t) and kim in ustler(d, k) for k, p in d.kisiler.items()): return True
            elif b:
                if d.kisiler[kim].get('birim') == b and roller & kimler: return True
                if 'BIRIM_YONETICISI' in kimler and kim in yoneticiler(d, b): return True
                if 'BIRIM_BASI' in kimler and kim == d.birimler.get(b, {}).get('basi'): return True
                if kim in birim_ustleri(d, b): return True
        return False
    # Her toplu hedef ayri yetkilendirilir; bir hedef digerini acamaz.
    n = max(len(birimler), len(iliskiler), 1)
    return all((j < len(iliskiler) and iliski(iliskiler[j])) or tablo_izni(birimler[j] if j < len(birimler) else None) for j in range(n))
