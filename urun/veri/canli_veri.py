"""Canlı kısmın verisi (T19 › 3): gösterinin firması, son üç iş günü, Modül 3'ün kayıtları, bugünün havuzu.

Bütün tarihler --bugun'e göre kurulur; gelecek tarihli olay yoktur. Son olay bugünden önceki iş
gününün akşamındadır; bugünün işleri o akşam tanımlanır ve Modül 3 onları bugüne planlar.
Olaylar modelde tek tek eklenerek üretilir (kabul edilmeyen olay çıkarsa betik durur); sonra
cevap anahtarının yürütücüsü girdiyi baştan koşar ve beklenen dosyasını yazar.

Çıktı: urun/veri/canli.girdi.json ve canli.beklenen.json (cevap anahtarının biçimi).
Koşmak: python3 -I -B urun/veri/canli_veri.py --bugun 2026-11-09
Adlar plan/gosteri_adlari.json'dan; hepsi uydurmadır.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys

KOK = Path(__file__).resolve().parents[2]
CA = KOK / 'referans' / 'cevap_anahtari'
BURASI = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=3))
TATILLER = {date(2026, 10, 29)}
CIHAZ_HARFI = {'MAS': 'M', 'TEL': 'T', 'M3': 'P'}
ROL_ADLARI = {'K001': 'Yetkili', 'K004': 'Planlama Yöneticisi', 'K006': 'Satın Alma Uzmanı',
              'K009': 'İmalat Ekip Lideri', 'K017': 'Atölye Çalışanı 1', 'K023': 'Atölye Çalışanı 2',
              'K031': 'Saha Çalışanı', 'K012': 'Tasarım Yöneticisi', 'K041': 'Tasarımcı'}


class Ret(Exception):
    pass


def yurutucu():
    for yol in (str(CA), str(CA / 'model')):
        if yol not in sys.path:
            sys.path.insert(0, yol)
    spec = importlib.util.spec_from_file_location('_canli_yurut', CA / 'yurut.py')
    y = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = y
    spec.loader.exec_module(y)
    return y


def is_gunu(g):
    return g.weekday() < 5 and g not in TATILLER


def onceki_is_gunleri(bugun, n):
    gunler, g = [], bugun
    while len(gunler) < n:
        g -= timedelta(days=1)
        if is_gunu(g):
            gunler.append(g)
    return list(reversed(gunler))


def an(g, saat):
    s, d = map(int, saat.split(':'))
    return datetime.combine(g, time(s, d), TZ)


def iso(t):
    return t.isoformat()


class Uretici:
    """Olayları modelin deposuna tek tek ekler ve girdinin adımlarını biriktirir."""

    def __init__(self, y, baslangic):
        from irp.depo import Depo
        self.y = y
        self.d = Depo(y.saat_kur(self._saat(baslangic)), yontem='kapsamli')
        self.baslangic = baslangic
        self.adimlar = []
        self.sayac = Counter()
        self.son = baslangic
        self.sayim = Counter()

    @staticmethod
    def _saat(t):
        return {'demo': False, 'gercek': iso(t), 'simdi': iso(t)}

    def _ilerle(self, t):
        if t < self.son:
            raise ValueError(f'Zaman geri gidemez: {t} < {self.son}')
        self.son = t
        self.d.saat = self.y.saat_kur(self._saat(t))
        self.d.gorunum.saat = self.d.saat

    def kimlik(self, kim, harf, t):
        gun = t.strftime('%y%m%d')
        self.sayac[(kim, harf, gun)] += 1
        return f'{kim}-{gun}{self.sayac[(kim, harf, gun)]:04d}-{harf}'

    def kurulum(self, t, olaylar, kod_listeleri):
        self._ilerle(t)
        c = self.y.dene(self.d.kurulum, deepcopy(olaylar), deepcopy(kod_listeleri), servis=True)
        if (c.get('deger') or {}).get('sonuc') != 'BASARILI':
            raise Ret('kurulum: ' + json.dumps(c, ensure_ascii=False)[:400])
        self.adimlar.append({'tur': 'kurulum', 'args': [olaylar, kod_listeleri], 'kwargs': {'servis': True},
                             'saat': self._saat(t), 'yontem': 'kapsamli'})
        self.sayim['kurulum'] += 1

    def olay(self, t, kim, eylem, girdiler, ustunde=(), cihaz='MAS', servis=True, hassas=None, kanit=()):
        """ustunde: (tur, kimlik, surumlu) üçlüleri; sürümlü olanın sürümü eklemeden hemen önce modelden alınır."""
        from irp.kabul import nesne
        self._ilerle(t)
        harf = CIHAZ_HARFI[cihaz]
        kimlik = self.kimlik(kim, harf, t)
        nu = []
        for tur, k, surumlu in ustunde:
            s = nesne(self.d, tur, k).get('surum') if surumlu else None
            if surumlu and s is None:
                raise Ret(f'{eylem}: {tur} {k} modelde yok')
            nu.append({'kimlik': k, 'surum': s, 'tur': tur})
        e = {'adina': None, 'bildigi_son_hal_ani': iso(t), 'cihaz': f'{cihaz}-{kim}', 'duzelttigi_olay': None,
             'eylem_kodu': eylem, 'eylem_versiyonu': 1, 'girdiler': girdiler, 'giris_sekli': 'LISTE',
             'kanit': list(kanit), 'kim': kim, 'neyin_ustunde': nu, 'olay_kimligi': kimlik, 'oldugu_an': iso(t),
             'pc_ulasma_ani': None, 'saat_dilimi': '+03:00',
             'uygulama_surumu': 'AND-0.1.0' if cihaz == 'TEL' else 'WEB-0.1.0', 'yol': 'DISARIDA'}
        kw = {'hassas_ek': hassas, 'oturum': kim, 'servis': servis}
        c = self.y.dene(self.d.olay_ekle, deepcopy(e), **kw)
        deger = c.get('deger')
        if not (isinstance(deger, dict) and deger.get('sonuc') == 'BASARILI' and not deger.get('tekrar')):
            raise Ret(f'{eylem} ({kim}, {iso(t)}): ' + json.dumps(c, ensure_ascii=False)[:500])
        self.adimlar.append({'tur': 'olay', 'args': [e], 'kwargs': kw, 'saat': self._saat(t), 'yontem': 'kapsamli'})
        self.sayim[eylem] += 1
        return kimlik

    def bildirim(self, t, **kw):
        self._ilerle(t)
        kw['an'] = iso(t)
        c = self.y.dene(self.d.modul_bildirimi_birak, **deepcopy(kw))
        if 'hata_turu' in c or (isinstance(c.get('deger'), dict) and c['deger'].get('sonuc') not in (None, 'BASARILI')):
            raise Ret('modul_bildirimi: ' + json.dumps(c, ensure_ascii=False)[:400])
        self.adimlar.append({'tur': 'modul_bildirimi', 'ad': 'birak', 'args': [], 'kwargs': kw,
                             'saat': self._saat(t), 'yontem': 'kapsamli'})
        self.sayim['modul_bildirimi'] += 1

    def girdi(self, bugun):
        son = self.son + timedelta(seconds=1)
        return {'bicim_surumu': 4, 'senaryo': 'canli', 'kaynak': 'urun/veri/canli_veri.py --bugun ' + bugun.isoformat(),
                'cihaz_denemeleri': [], 'saf_sorgular': [],
                'depolar': [{'baslangic': self._saat(self.baslangic), 'adimlar': self.adimlar,
                             'son_saat': self._saat(son), 'yontem': 'kapsamli'}]}


def kurulum_paketi(kurulus):
    """Gösteri dosyasının kurulum paketi (yetkiler, kodlar, takvim, tatil, K001), kuruluş gününe taşınır."""
    kaynak = json.loads((KOK / 'plan' / 'gosteri' / 'gosteri_olaylari.json').read_text('utf-8'))['kurulum']
    eski = '2026-10-01'
    yeni = kurulus.isoformat()
    t = iso(an(kurulus, '07:00'))

    def tasi(x):
        if isinstance(x, dict):
            return {k: tasi(v) for k, v in x.items()}
        if isinstance(x, list):
            return [tasi(v) for v in x]
        if isinstance(x, str) and x.startswith(eski):
            return yeni + x[len(eski):]
        return x
    olaylar = []
    for i, e in enumerate(kaynak['olaylar'], 1):
        e = deepcopy(e)
        e['girdiler'] = tasi(e['girdiler'])
        if e['eylem_kodu'] == 'KISI.EKLEDIM' and e['girdiler'].get('kod') in ROL_ADLARI:
            e['girdiler']['ad'] = ROL_ADLARI[e['girdiler']['kod']]
        e['oldugu_an'] = e['bildigi_son_hal_ani'] = t
        e['olay_kimligi'] = f'K001-{kurulus.strftime("%y%m%d")}{i:04d}-M'
        olaylar.append(e)
    return olaylar, kaynak['kod_listeleri']


def yetki_ve_kodlar():
    """Ekim boyunca eklenen yetki tanımları ve kod listeleri (duruş nedenleri dahil); test kalıntıları hariç."""
    kaynak = json.loads((KOK / 'plan' / 'gosteri' / 'gosteri_olaylari.json').read_text('utf-8'))['adimlar']
    secilen = []
    for a in kaynak:
        e = a.get('olay') or {}
        if e.get('eylem_kodu') not in ('YETKI.TANIMLADIM', 'KOD.TANIMLADIM'):
            continue
        g = e['girdiler']
        if 'tohum_kontrol' in g or (g.get('eylem_kodu') == 'PROJE.HEPSINI_GORUR' and not g.get('kimler')):
            continue
        secilen.append((e['eylem_kodu'], g))
    return secilen


def m3_turleri():
    """Modül 3'ün parça ve teknik resim türleri; Hamdi'nin senaryolarındaki son biçim (fason dahil)."""
    g = json.loads((CA / 'modul_sozlesmeleri' / 'modul3' / 'M3S01_parca_satin_alma.girdi.json').read_text('utf-8'))
    turler, modul = {}, None
    for a in g['depolar'][0]['adimlar']:
        if a['tur'] != 'olay':
            continue
        e = a['args'][0]
        if e['eylem_kodu'] == 'NESNE_TURU.TANIMLADIM':
            turler[e['girdiler']['kod']] = e['girdiler']  # sonraki tanım öncekinin yerine geçer
        elif e['eylem_kodu'] == 'MODUL.TANIMLADIM':
            modul = e['girdiler']
    return turler['PARCA'], turler['BELGE'], modul


def uret(bugun):
    if not is_gunu(bugun):
        raise SystemExit(f'--bugun iş günü olmalı: {bugun}')
    y = yurutucu()
    adlar = json.loads((KOK / 'plan' / 'gosteri_adlari.json').read_text('utf-8'))
    # Mustafa (29 Ekim): kişilerin adı rol adı; ekranda kimin gözüyle bakıldığı hemen anlaşılır.
    ad = ROL_ADLARI.get
    d1, d2, d3 = onceki_is_gunleri(bugun, 3)
    kurulus = onceki_is_gunleri(d1, 1)[0]
    u = Uretici(y, an(kurulus, '06:59'))
    O = u.olay  # noqa: E741  (kısa yazım)

    # 1. Kurulum paketi ve firmanın ana verisi (kuruluş günü, yetkili K001).
    paket, kodlar = kurulum_paketi(kurulus)
    u.kurulum(an(kurulus, '07:00'), paket, kodlar)
    u.sayac[('K001', 'M', kurulus.strftime('%y%m%d'))] = len(paket)
    for eylem, g in yetki_ve_kodlar():
        O(an(kurulus, '07:02'), 'K001', eylem, g)
    t = an(kurulus, '07:05')
    dk = lambda n: t + timedelta(minutes=n)  # noqa: E731
    gun = kurulus.isoformat()

    def birim(n, kod, tur, ust, basi=None):
        return O(dk(n), 'K001', 'BIRIM.TANIMLADIM', {'ad': adlar['birimler'][kod], 'basi': basi, 'kod': kod,
                                                     'tur': tur, 'ust_birim': ust})

    def kisi(n, kod, birim_, roller, yaka):
        return O(dk(n), 'K001', 'KISI.EKLEDIM', {'ad': ad(kod), 'birim': birim_, 'giris_tarihi': gun, 'kod': kod,
                                                 'roller': roller, 'yaka': yaka})
    birim(0, 'PLANLAMA', 'MASA_BASI', 'YONETIM')
    kisi(1, 'K004', 'PLANLAMA', ['YONETICI'], 'BEYAZ')
    birim(2, 'PLANLAMA', 'MASA_BASI', 'YONETIM', 'K004')
    kisi(3, 'K006', 'PLANLAMA', ['BEYAZ_YAKA'], 'BEYAZ')
    birim(4, 'IMALAT', 'ATOLYE', 'PLANLAMA')
    kisi(5, 'K009', 'IMALAT', ['EKIP_LIDERI'], 'MAVI')
    birim(6, 'IMALAT', 'ATOLYE', 'PLANLAMA', 'K009')
    kisi(7, 'K017', 'IMALAT', ['CALISAN'], 'MAVI')
    kisi(8, 'K023', 'IMALAT', ['CALISAN'], 'MAVI')
    birim(9, 'MEK_TASARIM', 'MASA_BASI', 'YONETIM')
    kisi(10, 'K012', 'MEK_TASARIM', ['YONETICI'], 'BEYAZ')
    birim(11, 'MEK_TASARIM', 'MASA_BASI', 'YONETIM', 'K012')
    kisi(12, 'K041', 'MEK_TASARIM', ['BEYAZ_YAKA'], 'BEYAZ')
    # Saha: kurulum ve devreye alma; başı yok, üst birimin yöneticisi (Planlama Yöneticisi) yönetir.
    O(dk(12), 'K001', 'BIRIM.TANIMLADIM', {'ad': 'Kurulum ve Devreye Alma', 'basi': None, 'kod': 'KURULUM',
                                           'tur': 'ATOLYE', 'ust_birim': 'PLANLAMA'})
    kisi(12, 'K031', 'KURULUM', ['CALISAN'], 'MAVI')
    # Aylık maaşlar (hassas ek; yalnızca yetkili görür). 180 saatlik paydayla saat ücretleri gösterimdekilere yakın.
    maas = {'K001': 135000, 'K004': 117000, 'K006': 93600, 'K009': 70200, 'K012': 117000,
            'K017': 63000, 'K023': 63000, 'K031': 63000, 'K041': 93600}
    for i, (k, tutar) in enumerate(maas.items()):
        O(dk(13), 'K001', 'MAAS.GUNCELLEDIM', {'gecerli_baslangic': gun, 'kisi': k},
          hassas={'gecerli_baslangic': gun, 'nesne_kimlik': k, 'nesne_tur': 'KISI', 'tur': 'MAAS_AYLIK', 'tutar': tutar})
    O(dk(14), 'K001', 'TEZGAH.TANIMLADIM', {'ad': adlar['tezgahlar']['CNC-17'], 'birim': 'IMALAT', 'kod': 'CNC-17'})
    O(dk(14), 'K001', 'TEZGAH.TANIMLADIM', {'ad': adlar['tezgahlar']['CNC-02'], 'birim': 'IMALAT', 'kod': 'CNC-02'})
    P1, P2 = '2509084', '2509091'
    O(dk(15), 'K001', 'PROJE.ACTIM', {'ad': adlar['projeler'][P1], 'kod': P1, 'musteri': 'Örnek Rulman A.Ş.',
                                      'sorumlu': 'K004', 'teslim_tarihi': (bugun + timedelta(days=75)).isoformat()})
    O(dk(15), 'K001', 'PROJE.ACTIM', {'ad': adlar['projeler'][P2], 'kod': P2, 'musteri': 'Örnek Test Ltd.',
                                      'sorumlu': 'K004', 'teslim_tarihi': (bugun + timedelta(days=25)).isoformat()})

    def etap(n, proje, ad_, birim_, bas, bit, hedef, sorumlu):
        return O(dk(n), 'K004', 'ETAP.TANIMLADIM', {
            'ad': ad_, 'baslangic': (bugun + timedelta(days=bas)).isoformat(), 'birim': birim_,
            'bitis': (bugun + timedelta(days=bit)).isoformat(), 'hedef_saat': hedef, 'proje': proje, 'sorumlu': sorumlu})
    etap(16, P1, 'Planlama', 'PLANLAMA', -35, 10, 80, 'K004')
    E1_TAS = etap(16, P1, 'Mekanik Tasarım', 'MEK_TASARIM', -35, 20, 420, 'K012')
    E1_IML = etap(16, P1, 'İmalat', 'IMALAT', -14, 35, 900, 'K009')
    etap(17, P2, 'Mekanik Tasarım', 'MEK_TASARIM', -20, 5, 120, 'K012')
    E2_IML = etap(17, P2, 'İmalat', 'IMALAT', -10, 20, 300, 'K009')
    E2_KUR = etap(17, P2, 'Kurulum ve Devreye Alma', 'KURULUM', -5, 15, 80, 'K004')
    # Modül 3: tanımı, parça ve teknik resim türleri (Hamdi'nin senaryolarındaki gibi, modülün cihazından).
    parca_turu, belge_turu, modul = m3_turleri()
    O(dk(20), 'K001', 'NESNE_TURU.TANIMLADIM', parca_turu, cihaz='M3', servis=False)
    O(dk(20), 'K001', 'NESNE_TURU.TANIMLADIM', belge_turu, cihaz='M3', servis=False)
    O(dk(20), 'K001', 'MODUL.TANIMLADIM', modul, cihaz='M3', servis=False)

    # 2. İşler: planlama İmalat'a işleri tanımlar (kuruluş günü öğleden sonra).
    def isler(t_, kim, liste):
        k = O(t_, kim, 'IS.TANIMLADIM', {'isler': liste})
        return [f'{k}/{i}' for i in range(1, len(liste) + 1)]

    def is_(islem, parca, sure, tezgah=None, proje=P1, etap_=None, birim_='IMALAT'):
        x = {'birim': birim_, 'etap': etap_ or E1_IML, 'islem': islem, 'nereye': 'PROJE', 'on_isler': [],
             'onay_beklet': False, 'onay_gerekli': True, 'parca_kodu': parca, 'proje': proje,
             'tahmini_sure_dk': sure, 'tur': 'SURELI'}
        if tezgah:
            x.update(tezgah=tezgah, tezgah_rolu=None)
        return x
    gecmis = isler(an(kurulus, '14:00'), 'K004', [
        is_('20 CNC Torna', '2509084_02_01-03', 210, 'CNC-02'),
        is_('30 CNC Freze', '2509084_02_01-03', 270, 'CNC-17'),
        is_('20 CNC Torna', '2509084_02_02-01', 200, 'CNC-02'),
        is_('30 CNC Freze', '2509084_01_01-01', 280, 'CNC-17'),
        is_('40 Kaynak', '2509084_01_01-01', 210),
        is_('50 Taşlama', '2509084_02_01-03', 270),
        is_('10 Kesim', '2509084_01_02-04', 200),
        is_('40 Kaynak', '2509084_01_02-04', 280),
        is_('20 CNC Torna', '2509091_01_01-02', 210, 'CNC-02', P2, E2_IML),
        is_('60 Montaj öncesi kontrol', '2509091_01_01-02', 270, None, P2, E2_IML),
    ])
    saha = isler(an(kurulus, '14:05'), 'K004', [
        is_('Sahada mekanik montaj', '2509091_01_01-02', 210, None, P2, E2_KUR, 'KURULUM'),
        is_('Devreye alma testleri', '2509091_01_01-02', 270, None, P2, E2_KUR, 'KURULUM'),
    ])

    def lider(kisi_):  # saha biriminin başı yok; işini Planlama Yöneticisi atar ve onaylar
        return 'K004' if kisi_ == 'K031' else 'K009'
    # İş dağılımı: Atölye Çalışanı 1 üç gün; Atölye Çalışanı 2 iki gün (üçüncü gün izinli); Saha Çalışanı son gün.
    plan = {d1: {'K017': gecmis[0:2], 'K023': gecmis[6:8]},
            d2: {'K017': gecmis[2:4], 'K023': gecmis[8:10]},
            d3: {'K017': gecmis[4:6], 'K031': saha}}

    # 3. Modül 3'ün parçaları ve teknik resmi (kuruluş günü öğleden sonra, Elif Kaya modülden açar).
    parcalar = {}
    for i, (kod, ad_) in enumerate([
            ('2509084_01_01-01', 'Pres gövdesi'), ('2509084_01_02-04', 'Alt tabla'),
            ('2509084_02_01-03', 'Çakma pistonu'), ('2509084_02_02-01', 'Kılavuz mil'),
            ('2509084_03_01-02', 'Rulman yatağı'), ('2509084_03_02-01', 'Hidrolik silindir'),
            ('2509084_04_01-01', 'Koruma kapağı')]):
        parcalar[kod] = O(an(kurulus, '15:00') + timedelta(minutes=i), 'K006', 'NESNE.ACTIM', {
            'ad': f'{ad_} ({kod})', 'baglar': [{'kimlik': P1, 'tur': 'PROJE'}], 'kod': kod, 'proje': P1,
            'sorumlu': 'K006', 'tur': 'PARCA'}, cihaz='M3', servis=False)

    def asama(t_, kim, kod, yeni, gerekce):
        O(t_, kim, 'NESNE.ASAMA_GECIRDIM', {'gerekce': gerekce, 'hedef': parcalar[kod], 'yeni_asama': yeni},
          cihaz='M3', servis=False)
    belge = O(an(kurulus, '15:30'), 'K012', 'NESNE.ACTIM', {
        'ad': 'Pres gövdesi teknik resmi', 'baglar': [{'kimlik': P1, 'tur': 'PROJE'},
                                                     {'kimlik': parcalar['2509084_01_01-01'], 'tur': 'NESNE'}],
        'proje': P1, 'sorumlu': 'K041', 'tur': 'BELGE'}, cihaz='M3', servis=False)

    def surum(t_, adi):
        dosya = f'F-2509084_01_01-01_{adi}.pdf'
        O(t_, 'K041', 'NESNE.SURUM_EKLEDIM', {'aciklama': 'Çizim', 'dosyalar': [dosya], 'hedef': belge, 'surum_adi': adi},
          ustunde=[('NESNE', belge, True)], cihaz='M3', servis=False,
          kanit=[{'dosya_kimligi': dosya, 'parmak_izi': 'sha256-' + dosya}])

    # 4. Üç iş günü. Olaylar bir ajandaya yazılır ve saat sırasıyla eklenir (aynı anda yazılış sırası korunur).
    r = {}
    ajanda = []

    def A(t_, f):
        ajanda.append((t_, len(ajanda), f))

    def is_olayi(t_, kisi_, eylem, k, surumlu=False, **kw):
        A(t_, lambda: O(t_, kisi_, eylem, kw.pop('girdiler', {}), ustunde=[('IS', k, surumlu)],
                        cihaz=kw.pop('cihaz', 'TEL')))
    for gun_ in (d1, d2, d3):
        isci = plan[gun_]
        n = 0
        for kisi_, isler_ in isci.items():
            for sira, k in enumerate(isler_, 1):
                n += 1
                t_ = an(gun_, '07:40') + timedelta(minutes=n)
                A(t_, lambda t_=t_, kisi_=kisi_, sira=sira, k=k: O(
                    t_, lider(kisi_), 'IS.ATADIM', {'kisi': kisi_, 'sira': sira},
                    ustunde=[('IS', k, True), ('LISTE', kisi_, True)]))
        for kisi_, (a, b) in isci.items():
            A(an(gun_, '07:55'), lambda g=gun_, k=kisi_: O(an(g, '07:55'), k, 'MESAI.GIRDIM', {}, cihaz='TEL'))
            # Sabahki iş 08:00–11:30 (çay molası 10:00–10:15); öğleden sonraki 11:35–16:30 (yemek, ikindi çayı).
            is_olayi(an(gun_, '08:00'), kisi_, 'IS.BASLADIM', a)
            is_olayi(an(gun_, '10:15'), kisi_, 'IS.DEVAM_ETTIM', a)
            is_olayi(an(gun_, '11:30'), kisi_, 'IS.TAMAMLADIM', a)
            is_olayi(an(gun_, '11:35'), kisi_, 'IS.BASLADIM', b)
            is_olayi(an(gun_, '12:30'), kisi_, 'IS.DEVAM_ETTIM', b)
            is_olayi(an(gun_, '15:15'), kisi_, 'IS.DEVAM_ETTIM', b)
            is_olayi(an(gun_, '16:30'), kisi_, 'IS.TAMAMLADIM', b)
            for i, k in enumerate((a, b)):
                t_ = an(gun_, '16:45') + timedelta(minutes=i + (2 if kisi_ == 'K023' else 0))
                is_olayi(t_, lider(kisi_), 'IS.ONAYLADIM', k, True, cihaz='MAS')
            A(an(gun_, '18:00'), lambda g=gun_, k=kisi_: O(an(g, '18:00'), k, 'MESAI.CIKTIM', {}, cihaz='TEL'))
    k17 = plan[d1]['K017'][0]
    A(an(d1, '07:46'), lambda: asama(an(d1, '07:46'), 'K009', '2509084_01_01-01', 'ISLEMDE', 'İçeride yapılıyor'))
    A(an(d1, '07:47'), lambda: asama(an(d1, '07:47'), 'K009', '2509084_02_01-03', 'ISLEMDE', 'İçeride yapılıyor'))
    A(an(d1, '07:48'), lambda: asama(an(d1, '07:48'), 'K009', '2509084_01_02-04', 'ISLEMDE', 'İçeride yapılıyor'))
    A(an(d1, '08:45'), lambda: asama(an(d1, '08:45'), 'K006', '2509084_03_02-01', 'SIPARISTE', 'Sipariş verildi'))
    A(an(d1, '08:46'), lambda: asama(an(d1, '08:46'), 'K006', '2509084_02_02-01', 'SIPARISTE', 'Sipariş verildi'))
    A(an(d1, '08:47'), lambda: asama(an(d1, '08:47'), 'K006', '2509084_04_01-01', 'FASONDA', 'Boyaya gönderildi'))
    is_olayi(an(d1, '09:10'), 'K017', 'IS.MOLA_VERDIM', k17)
    is_olayi(an(d1, '09:20'), 'K017', 'IS.DEVAM_ETTIM', k17)

    def gorev_ata():
        k = O(an(d1, '09:30'), 'K012', 'GOREV.ATADIM', {'gorevler': [
            {'ad': 'Pres gövdesi montaj resmi', 'dosya_gerekli': False, 'etap': E1_TAS, 'kisi': 'K041',
             'nereye': 'PROJE', 'on_kosul': [], 'onay_gerekli': True, 'onaylayan': 'K012', 'proje': P1,
             'teslim_tarihi': d3.isoformat(), 'zaman_degeri': 16, 'zorluk': 2},
            {'ad': 'Çakma kalıbı detay resimleri', 'dosya_gerekli': False, 'etap': E1_TAS, 'kisi': 'K041',
             'nereye': 'PROJE', 'on_kosul': [], 'onay_gerekli': True, 'onaylayan': 'K012', 'proje': P1,
             'teslim_tarihi': (bugun + timedelta(days=3)).isoformat(), 'zaman_degeri': 12, 'zorluk': 2}]})
        r['g1'], r['g2'] = f'{k}/1', f'{k}/2'
    A(an(d1, '09:30'), gorev_ata)
    A(an(d1, '09:45'), lambda: O(an(d1, '09:45'), 'K041', 'GOREV.KABUL_ETTIM', {}, ustunde=[('GOREV', r['g1'], False)]))
    A(an(d1, '09:46'), lambda: O(an(d1, '09:46'), 'K041', 'GOREV.KABUL_ETTIM', {}, ustunde=[('GOREV', r['g2'], False)]))
    A(an(d1, '14:00'), lambda: surum(an(d1, '14:00'), 'Rev01'))
    A(an(d1, '15:00'), lambda: O(an(d1, '15:00'), 'K012', 'NESNE.SURUM_ONAYLADIM', {'hedef': belge, 'surum_no': 1},
                                 ustunde=[('NESNE', belge, True)], cihaz='M3', servis=False))

    def izin_iste():
        r['izin'] = O(an(d1, '16:00'), 'K023', 'IZIN.TALEP_ETTIM', {
            'baslangic': iso(an(d3, '08:00')), 'bitis': iso(an(d3, '18:00')), 'gerekce': 'Aile',
            'kisi': 'K023', 'tur': 'YILLIK'}, cihaz='TEL')
    A(an(d1, '16:00'), izin_iste)
    A(an(d1, '16:30'), lambda: O(an(d1, '16:30'), 'K009', 'IZIN.ONAYLADIM', {'hedef': r['izin']}))
    A(an(d2, '10:30'), lambda: asama(an(d2, '10:30'), 'K006', '2509084_02_02-01', 'GELDI', 'Teslim alındı'))
    # Tezgâh duruşu: Hakan'ın frezesi arızalanır; lider tezgâhı durdurur, giderilince devamı onaylar.
    b17 = plan[d2]['K017'][1]
    is_olayi(an(d2, '13:00'), 'K017', 'IS.ARIZA_BILDIRDIM', b17, True, girdiler={'neden': 'DURUS_NEDENI.MAKINE_CNC'})
    A(an(d2, '13:05'), lambda: O(an(d2, '13:05'), 'K009', 'TEZGAH.DURUS_BILDIRDIM', {'neden': 'ARIZA', 'tezgah': 'CNC-17'}))
    A(an(d2, '13:45'), lambda: O(an(d2, '13:45'), 'K009', 'TEZGAH.DURUS_BITTI', {'tezgah': 'CNC-17'}))
    is_olayi(an(d2, '13:46'), 'K009', 'IS.DEVAM_ONAYLADIM', b17, True, cihaz='MAS')
    A(an(d3, '10:30'), lambda: asama(an(d3, '10:30'), 'K009', '2509084_01_02-04', 'KALITE_ONAYLI', 'Ölçüler uygun'))
    A(an(d3, '11:00'), lambda: surum(an(d3, '11:00'), 'Rev02'))
    A(an(d3, '14:30'), lambda: O(an(d3, '14:30'), 'K041', 'GOREV.TAMAMLADIM', {}, ustunde=[('GOREV', r['g1'], False)]))
    A(an(d3, '16:50'), lambda: O(an(d3, '16:50'), 'K012', 'GOREV.ONAYLADIM', {}, ustunde=[('GOREV', r['g1'], True)]))
    for _, _, f in sorted(ajanda, key=lambda x: (x[0], x[1])):
        f()

    # 5. Bugünün havuzu: dün akşam tanımlanır, Modül 3 bugüne planlar; atamayı lider gösteride yapar.
    havuz = isler(an(d3, '18:10'), 'K004', [
        is_('20 CNC Torna', '2509084_02_02-01', 120, 'CNC-02'),
        is_('30 CNC Freze', '2509084_02_02-01', 150, 'CNC-17'),
        is_('50 Taşlama', '2509084_01_01-01', 180),
        is_('40 Kaynak', '2509091_01_01-02', 120, None, P2, E2_IML),
        is_('Müşteri eğitimi', '2509091_01_01-02', 120, None, P2, E2_KUR, 'KURULUM'),
    ])
    hedefler, bas = [], an(bugun, '08:00')
    for k, sure in zip(havuz, (120, 150, 180, 120, 120)):
        hedefler.append({'kimlik': k, 'planlanan_baslangic': iso(bas),
                         'planlanan_bitis': iso(bas + timedelta(minutes=sure)), 'tur': 'IS'})
    O(an(d3, '18:15'), 'K004', 'PLAN.TARIHLEDIM', {'hedefler': hedefler, 'kaynak': 'Modül 3'},
      ustunde=[('IS', k, True) for k in havuz], cihaz='M3', servis=False)
    u.bildirim(an(d3, '18:20'), servis_kimligi='SRV-M3', modul='M3', kural='TESLIM_YAKLASIYOR',
               kayit={'kimlik': parcalar['2509084_03_02-01'], 'modul_kaydi': 'sipariş SA-2026-0517', 'tur': 'NESNE'},
               alicilar=[{'kimlik': parcalar['2509084_03_02-01'], 'tur': 'NESNE_SORUMLUSU'}],
               metin=f'2509084_03_02-01 Hidrolik silindir: tedarikçi teslimi {(bugun + timedelta(days=2)).strftime("%d.%m.%Y")}. '
                     'Teslim alma hazırlığı.', onem='BILGI')
    u.bildirim(an(d3, '18:21'), servis_kimligi='SRV-M3', modul='M3', kural='PARCA_GEC_GELECEK',
               kayit={'kimlik': parcalar['2509084_03_01-02'], 'modul_kaydi': 'parça 2509084_03_01-02', 'tur': 'NESNE'},
               alicilar=[{'kimlik': parcalar['2509084_03_01-02'], 'tur': 'NESNE_SORUMLUSU'},
                         {'kimlik': 'PLANLAMA', 'tur': 'BIRIM_YONETICILERI'}],
               metin=f'2509084_03_01-02 Rulman yatağı montaja {(bugun + timedelta(days=9)).strftime("%d.%m.%Y")} tarihinde '
                     f'hazır olacak; montaj ihtiyacı {(bugun + timedelta(days=6)).strftime("%d.%m.%Y")}.', onem='UYARI')
    return y, u, {'kurulus': kurulus, 'gunler': [d1, d2, d3], 'havuz': havuz}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--bugun', required=True, type=date.fromisoformat)
    p.add_argument('--cikti', type=Path, default=BURASI)
    a = p.parse_args(argv)
    try:
        y, u, bilgi = uret(a.bugun)
    except Ret as h:
        raise SystemExit('Modelde kabul edilmedi: ' + str(h))
    girdi = u.girdi(a.bugun)
    # Resmî sınama: cevap anahtarının yürütücüsü girdiyi baştan koşar.
    sonuc = y.yurut(deepcopy(girdi))
    cevaplar = sonuc['depolar'][0]['cevaplar']
    kotu = [(i, c) for i, c in enumerate(cevaplar)
            if 'hata_turu' in c or (isinstance(c.get('deger'), dict) and c['deger'].get('sonuc') not in (None, 'BASARILI'))]
    hatalar = sonuc['depolar'][0]['son_hal'].get('isleme_hatalari', [])
    a.cikti.mkdir(parents=True, exist_ok=True)
    y.yaz(a.cikti / 'canli.girdi.json', girdi)
    y.yaz(a.cikti / 'canli.beklenen.json', sonuc)
    print(json.dumps({'bugun': a.bugun.isoformat(), 'kurulus': bilgi['kurulus'].isoformat(),
                      'gecmis_gunleri': [g.isoformat() for g in bilgi['gunler']], 'adim': len(girdi['depolar'][0]['adimlar']),
                      'kabul_edilmeyen': len(kotu), 'isleme_hatasi': len(hatalar),
                      'son_olay': girdi['depolar'][0]['adimlar'][-1]['saat']['simdi'],
                      'sayim': dict(sorted(u.sayim.items()))}, ensure_ascii=False, indent=1))
    if kotu or hatalar:
        print(json.dumps({'kabul_edilmeyen': kotu[:5], 'isleme_hatalari': hatalar[:5]}, ensure_ascii=False)[:2000])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
