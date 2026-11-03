"""A5/H20: şema, kimlik, temel yazma yetkisi ve değişmez içerik."""
import json
import re
from datetime import date, datetime
from .saat import an


def kodla(deger):
    return json.dumps(deger, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=lambda x: x.isoformat() if isinstance(x, (datetime, date)) else str(x))


EYLES = {
    'MESAI.GIRDIM': (), 'MESAI.CIKTIM': (),
    'IS.BASLADIM': (), 'IS.MOLA_VERDIM': (), 'IS.ARIZA_BILDIRDIM': (),
    'IS.DEVAM_ETTIM': (), 'IS.TAMAMLADIM': (), 'KAYIT.GECERSIZ_SAYDIM': ('hedef', 'gerekce'),
    'IS.ATADIM': ('sira',), 'IS.SIRALADIM': ('kisi', 'yeni_sira'),
    'IS.DEVRETTIM': ('kimden', 'kime'),
    'IS.PLANSIZ_TANIMLADIM': ('nereye', 'is_tanimi', 'tur', 'onay_gerekli', 'kisi', 'sira'),
    'IS.ONAYLADIM': (), 'IS.REDDETTIM': ('not',), 'IS.DEVAM_ONAYLADIM': (),
    'IS.SURE_EKLEDIM': ('baslangic', 'bitis', 'aciklama', 'is_bitti'),
    'IS.TANIMLADIM': ('isler',), 'GOREV.ATADIM': ('gorevler',),
    'GOREV.KABUL_ETTIM': (), 'GOREV.TAMAMLADIM': (), 'GOREV.ONAYLADIM': (),
    'GOREV.REDDETTIM': ('not', 'sebep_olan', 'revizyon_ver'),
    'GOREV.DEGISTIRDIM': ('degisenler',), 'GOREV.IPTAL_ETTIM': (),
    'NOT.YAZDIM': ('metin',), 'AYAR.YONLENDIRDIM': ('birim', 'kisiler'),
    'ETAP.TANIMLADIM': ('proje', 'ad', 'birim', 'baslangic', 'bitis', 'hedef_saat'),
    'KISI.EKLEDIM': ('kod', 'ad', 'birim', 'yaka', 'roller', 'giris_tarihi'),
    'KISI.DEGISTIRDIM': ('kisi', 'degisenler', 'gecerli_baslangic'),
    'KISI.AYRILDI': ('kisi',),
    'MAAS.GUNCELLEDIM': ('kisi', 'gecerli_baslangic'),
    'PROJE.ACTIM': ('kod', 'ad', 'teslim_tarihi'),
    'BIRIM.TANIMLADIM': ('kod', 'ad', 'tur', 'basi'),
    'TEZGAH.TANIMLADIM': ('kod', 'ad', 'birim'),
    'TAKVIM.TANIMLADIM': ( 'mesai_baslangic', 'mesai_bitis', 'calisma_gunleri', 'sabit_molalar'),
    'TATIL.EKLEDIM': ('tarih', 'ad'),
    'AYAR.ONAY_ORANI': ('deger',),
    'AYAR.SAAT_KAYDIRDIM': ('hedef',),
}
EYLES.update({
    'IS.DEGISTIRDIM': ('degisenler',), 'IS.IPTAL_ETTIM': ('gerekce',),
    'PROJE.DEGISTIRDIM': ('degisenler',), 'PROJE.KAPATTIM': (),
    'ETAP.DEGISTIRDIM': ('degisenler',),
    'AYAR.MAAS_PAYDASI': ('deger', 'gecerli_baslangic'), 'AYAR.PARCA_KODU_DESENI': ('deger',),
})

EYLES.update({'IS.BAGLANTI_DUZELTTIM': ('degisenler', 'gerekce'),
              'YETKI.TANIMLADIM': ('eylem_kodu', 'kimler', 'kapsam'),
              'KOD.TANIMLADIM': ('liste', 'kod', 'ad', 'aktif'),
              'TATIL.KALDIRDIM': ('tarih',), 'KURULUM.TAMAMLADIM': ()})

def hedefler(e, tur):
    return [x['kimlik'] for x in e['neyin_ustunde'] if x['tur'] == tur]

from .kurallar_v7 import SEMALAR
EYLES.update(SEMALAR)
EYLES['GOREV.REDDETTIM'] = ('not', 'revizyon_ver')
from .kurallar_v9 import SEMALAR as SEMALAR_V9
EYLES.update(SEMALAR_V9)
from .kurallar_v10_1 import SEMALAR as SEMALAR_V10_1
EYLES.update(SEMALAR_V10_1)
from .kurallar_v10_2 import SEMALAR as SEMALAR_V10_2
EYLES.update(SEMALAR_V10_2)
EYLES['PROJE.ACTIM'] = ('kod', 'ad')
EYLES['GUN_SONU.ONAYLADIM'] = ()
EYLES['GUN_SONU.GONDERDIM'] = ('gun',)
EYLES['SORUMLULUK.DOGRULADIM'] = ('hedef', 'karar')
EYLES['SORUMLULUK.ITIRAZI_DEGERLENDIRDIM'] = ('hedef', 'karar')

eylem_semalari = {k: {'eylem_versiyonu': 1, 'zorunlu': v} for k, v in EYLES.items()}


def hedefler(e, tur):
    return [x['kimlik'] for x in e['neyin_ustunde'] if x['tur'] == tur]


def bicim_kontrol(e):
    gerekli = ('olay_kimligi', 'eylem_kodu', 'eylem_versiyonu', 'neyin_ustunde', 'giris_sekli', 'kim', 'cihaz', 'uygulama_surumu', 'oldugu_an', 'saat_dilimi', 'bildigi_son_hal_ani', 'girdiler', 'kanit', 'yol')
    if any(k not in e or e[k] is None for k in gerekli):
        raise ValueError('Eksik olay alani')
    if not re.fullmatch(r'K\d{3}-\d{10}-[A-Z]', e['olay_kimligi']):
        raise ValueError('Kimlik deseni')
    if e['eylem_kodu'] not in EYLES or e['eylem_versiyonu'] != 1:
        raise ValueError('Bilinmeyen eylem/surum')
    if e['giris_sekli'] not in ('QR', 'LISTE', 'ELLE', 'AKTARIM') or e['yol'] not in ('ATOLYE', 'DISARIDA'):
        raise ValueError('Giris/yol')
    if not isinstance(e['girdiler'], dict) or not isinstance(e['neyin_ustunde'], list) or not isinstance(e['kanit'], list):
        raise ValueError('Olay alan tipi')
    an(e['oldugu_an']); an(e['bildigi_son_hal_ani'])
    g, kod = e['girdiler'], e['eylem_kodu']
    if any(k not in g for k in EYLES[kod]):
        raise ValueError('Eksik eylem girdisi: ' + kod)
    if 'degisenler' in g and (not isinstance(g['degisenler'], dict) or not g['degisenler']):
        raise ValueError('Degisenler dolu nesne olmali')
    for s in [g] + ([g['degisenler']] if isinstance(g.get('degisenler'), dict) else []):
        for alan in ('tarih', 'teslim_tarihi', 'giris_tarihi', 'ayrilis_tarihi'):
            if s.get(alan): date.fromisoformat(s[alan])
        if 'hedef_saat' in s and (type(s['hedef_saat']) not in (int,float) or not 0 <= s['hedef_saat'] < float('inf')):
            raise ValueError('Hedef saat negatif olmayan sonlu sayi')
        if kod.startswith('ETAP.'):
            for alan in ('baslangic','bitis'):
                if alan in s: date.fromisoformat(s[alan])
    if kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM', 'IS.DEGISTIRDIM'):
        satirlar = g['isler'] if kod == 'IS.TANIMLADIM' else [g['degisenler']] if kod == 'IS.DEGISTIRDIM' else [g]
        for s in satirlar:
            if s.get('onay_gerekli') and 'onay_beklet' not in s:
                raise ValueError('Onayli iste onay_beklet zorunlu')
            for a in ('onay_beklet', 'onay_gerekli'):
                if a in s and type(s[a]) is not bool: raise ValueError('Bool onay alani')
            if 'tahmini_sure_dk' in s and (type(s['tahmini_sure_dk']) is not int or s['tahmini_sure_dk'] < 0): raise ValueError('Tahmini sure')
    from .kurallar_v7 import bicim
    bicim(e)
    from .bicim_v6 import denetle
    denetle(e)
    if kod == 'AYAR.MAAS_PAYDASI' and (type(g['deger']) not in (int, float) or not 0 < g['deger'] < float('inf')):
        raise ValueError('Maas paydasi pozitif sonlu sayi')
    if kod == 'AYAR.PARCA_KODU_DESENI':
        if not isinstance(g['deger'], str): raise ValueError('Desen metin olmali')
        try: re.compile(g['deger'])
        except re.error: raise ValueError('Gecersiz parca kodu deseni')
    for tur, kodlar in [('IS', ('IS.DEGISTIRDIM', 'IS.IPTAL_ETTIM')),
                       ('PROJE', ('PROJE.DEGISTIRDIM', 'PROJE.KAPATTIM')),
                       ('ETAP', ('ETAP.DEGISTIRDIM',))]:
        if kod in kodlar and len(hedefler(e, tur)) != 1: raise ValueError('Tek hedef gerekli')
    for alan in ('is_bitti', 'onay_gerekli', 'revizyon_ver', 'onay_beklet', 'aktif'):
        if alan in g and type(g[alan]) is not bool: raise ValueError('Bool alan: ' + alan)
    for alan in ('sira', 'yeni_sira', 'kime_sira', 'zaman_degeri'):
        if alan in g and (type(g[alan]) is not int or g[alan] < 1): raise ValueError('Pozitif tamsayi: ' + alan)
    if kod == 'AYAR.ONAY_ORANI' and (type(g['deger']) not in (int, float) or not 0 <= g['deger'] <= 1):
        raise ValueError('Oran 0..1')
    if kod in ('IS.TANIMLADIM', 'GOREV.ATADIM'):
        satirlar = g['isler' if kod.startswith('IS.') else 'gorevler']
        if not isinstance(satirlar, list) or not satirlar or not all(isinstance(s, dict) for s in satirlar):
            raise ValueError('Bos/bozuk satir listesi')
        for satir in satirlar:
            for alan in ('onay_gerekli', 'dosya_gerekli'):
                if alan in satir and type(satir[alan]) is not bool: raise ValueError('Bool satir alani')
            if 'tahmini_sure_dk' in satir and (type(satir['tahmini_sure_dk']) is not int or satir['tahmini_sure_dk'] < 0): raise ValueError('Tahmini sure')
            if satir.get('nereye') == 'PROJE_DISI' and not satir.get('kategori'): raise ValueError('PD kategori gerekli')
            if satir.get('teslim_tarihi'): date.fromisoformat(satir['teslim_tarihi'])
    for alan in ('not', 'aciklama', 'metin', 'gerekce'):
        if alan in EYLES[kod] and not str(g[alan]).strip():
            raise ValueError('Bos ' + alan)
    if kod == 'IS.ARIZA_BILDIRDIM' and g.get('neden') == 'ARIZA.DIGER' and not g.get('not', '').strip():
        raise ValueError('Diger icin not zorunlu')
    if kod == 'IS.SURE_EKLEDIM':
        if not e.get('adina') or e['giris_sekli'] not in ('ELLE', 'AKTARIM') or an(g['bitis']) <= an(g['baslangic']):
            raise ValueError('Elle sure bicimi')
    if kod == 'GOREV.REDDETTIM' and g['revizyon_ver'] and any(k not in g for k in ('yeni_teslim_tarihi', 'zaman_degeri', 'kime')):
        raise ValueError('Revizyon alanlari')
    if e.get('duzelttigi_olay') and kod != 'KAYIT.GECERSIZ_SAYDIM': raise ValueError('Duzeltme yalniz isarette')
    if kod == 'KAYIT.GECERSIZ_SAYDIM' and g['hedef'] != e.get('duzelttigi_olay'): raise ValueError('Hedef esit olmali')
    if kod == 'IS.ATADIM' and not (g.get('kisi') or g.get('kisiler')): raise ValueError('Atanan gerekli')
    if kod.startswith('IS.') and kod not in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM') and not hedefler(e, 'IS'):
        raise ValueError('Is hedefi gerekli')
    if kod.startswith('GOREV.') and kod != 'GOREV.ATADIM' and not hedefler(e, 'GOREV'):
        raise ValueError('Gorev hedefi gerekli')
    if kod in ('GOREV.TAMAMLADIM', 'GOREV.REDDETTIM', 'GOREV.DEGISTIRDIM', 'GOREV.IPTAL_ETTIM') and len(hedefler(e, 'GOREV')) != 1:
        raise ValueError('Karar 44: tek gorev hedefi')
    if kod == 'NOT.YAZDIM' and not any(x['tur'] in ('PARCA', 'GOREV', 'PROJE', 'NESNE') for x in e['neyin_ustunde']):
        raise ValueError('Not hedefi gerekli')
    if kod == 'GOREV.ATADIM':
        for satir in g['gorevler']:
            for alan in ('ad', 'nereye', 'teslim_tarihi', 'zaman_degeri', 'zorluk', 'kisi', 'onay_gerekli', 'dosya_gerekli'):
                if alan not in satir:
                    raise ValueError('Gorev satiri: ' + alan)
            if type(satir['zaman_degeri']) is not int or satir['zaman_degeri'] < 1 or not 1 <= satir['zorluk'] <= 5:
                raise ValueError('Gorev sayisal alan')
            if satir['onay_gerekli'] and not satir.get('onaylayan'):
                raise ValueError('Onaylayan gerekli')


def yetki_kontrol(e, oturum, roller, servis=False):
    if e['giris_sekli'] == 'AKTARIM' and not servis:
        raise PermissionError('AKTARIM yalniz servis')
    if e['kim'] != oturum and not (servis and e['giris_sekli'] == 'AKTARIM'):
        raise PermissionError('Kim oturumla ayni olmali')
    # Adina yetkisi T3/4 veri tablosu ve zincirden gelir.
