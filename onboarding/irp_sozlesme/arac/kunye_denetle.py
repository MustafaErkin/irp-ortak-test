"""Modül künyesi denetleyicisi (T18 › 5, 7, 9).

Üç düzey:
- künye: tek modülün künyesi kurallara uyuyor mu (V01–V24)
- kayıt: bütün modüller birlikte çakışıyor mu (R01–R11)
- göç: modülün SQL dosyaları yalnızca kendi şemasına dokunuyor mu (G01–G09)
Ayrıca künyeden kurulum olaylarını üretir (T18 › 9.1); kurulum betiği bunları YETKILI adına yazar.

Koşmak:
  python3 -I -B modul_kiti/kunye_denetle.py <künye.json ya da modül klasörü> ...
  python3 -I -B modul_kiti/kunye_denetle.py --kurulum <künye.json>
Çıkış kodu: HATA varsa 1.
"""
import json
from pathlib import Path
import re
import sys

KATALOG_YOLU = Path(__file__).resolve().parent / 'cekirdek_katalogu.json'

HATA, UYARI = 'HATA', 'UYARI'
UST_ALANLAR = {
    'kunye_surumu', 'kod', 'ad', 'surum', 'cekirdek', 'sahip', 'aciklama', 'servis_kimligi', 'arka_yuz',
    'olay_yolu', 'cihaz_harfi', 'kapilar', 'nesne_turleri', 'tur_uzantilari', 'roller', 'kod_listeleri',
    'yetki_onerileri', 'veritabani', 'on_yuz', 'saglananlar', 'bagimliliklar', 'kisisel_veri', 'para',
    'sinirlar', 'istekler'}
ZORUNLU = ['kunye_surumu', 'kod', 'ad', 'surum', 'cekirdek', 'sahip', 'servis_kimligi', 'arka_yuz', 'olay_yolu',
           'kapilar', 'veritabani', 'sinirlar', 'para', 'kisisel_veri']
KAPI_ALANLARI = {'okumalar', 'servis_okumalari', 'olaylar', 'plan', 'belge_surumu', 'bildirimler', 'abonelikler','dosyalar'}
SINIR_UST = {'bildirim_dakika': 120, 'okuma_dakika': 1200, 'servis_okuma_dakika': 600}
KOD_DESENI = re.compile(r'^[A-Z][A-Z0-9]{1,5}$')
ROL_DESENI = re.compile(r'^[A-Z][A-Z_]{2,20}$')
KURAL_DESENI = re.compile(r'^[A-Z][A-Z0-9_]{2,40}$')
SURUM_DESENI = re.compile(r'^\d+\.\d+\.\d+$')
CEKIRDEK_DESENI = re.compile(r'^>=(\d+)\.(\d+)$')
SAGLANAN_DESENI = re.compile(r'^([A-Z][A-Z0-9]{1,5})\.([A-Z][A-Z0-9_]{1,40})$')
ISTEK_DURUMLARI = {'ACIK', 'KARSILANDI', 'REDDEDILDI', 'MODULDE_COZULDU'}
ON_YUZ_TURLERI = {'UYGULAMA_ICI', 'AYRI_UYGULAMA', 'YOK'}
BAGLAMLAR = {'PROJE', 'NESNE', 'IS', 'GOREV', 'TEZGAH', 'KISI'}
GORME_TURLERI = {'KAYDI_GOREN', 'YETKILI', 'KENDISI_VE_USTLERI', 'ROL'}


def katalog_yukle(yol=KATALOG_YOLU):
    return json.loads(Path(yol).read_text('utf-8'))


class Bulgular(list):
    def ekle(self, seviye, kural, yol, mesaj):
        self.append({'seviye': seviye, 'kural': kural, 'yol': yol, 'mesaj': mesaj})

    def hata(self, kural, yol, mesaj):
        self.ekle(HATA, kural, yol, mesaj)

    def uyari(self, kural, yol, mesaj):
        self.ekle(UYARI, kural, yol, mesaj)

    @property
    def hatalar(self):
        return [b for b in self if b['seviye'] == HATA]


def _eslesir(eylem, desenler):
    return any(eylem == d or (d.endswith('.*') and eylem.startswith(d[:-1])) for d in desenler)


def _liste(x):
    return x if isinstance(x, list) else []


def _surum_sayi(metin):
    a, b = metin.split('.')[:2]
    return int(a), int(b)


# ---------------------------------------------------------------- künye düzeyi

def kunye_denetle(k, katalog=None, kayit_rolleri=()):
    """Tek künyeyi denetler. kayit_rolleri: başka modüllerin tanımladığı roller (kayıt düzeyinden)."""
    katalog = katalog or katalog_yukle()
    b = Bulgular()
    if not isinstance(k, dict):
        b.hata('V01', '', 'Künye bir JSON nesnesi olmalı')
        return b

    # V01 alanlar
    for alan in ZORUNLU:
        if alan not in k:
            b.hata('V01', alan, 'Zorunlu alan eksik')
    for alan in sorted(set(k) - UST_ALANLAR):
        b.hata('V01', alan, 'Bilinmeyen alan (yazım hatası mı?)')
    if k.get('kunye_surumu') != 1:
        b.hata('V01', 'kunye_surumu', 'Künye biçiminin sürümü 1 olmalı')
    if not isinstance(k.get('ad'), str) or not k.get('ad', '').strip():
        b.hata('V01', 'ad', 'Modülün adı boş olamaz')

    # V02 kod
    kod = k.get('kod', '')
    if not isinstance(kod, str) or not KOD_DESENI.match(kod):
        b.hata('V02', 'kod', 'Kod 2–6 karakter, büyük harf ve rakam, harfle başlar (ör. M3, KAL)')
        kod = str(kod)
    elif kod in katalog['ayrilmis_kodlar']:
        b.hata('V02', 'kod', f'{kod} çekirdeğe ayrılmış bir ad')

    # V03 servis kimliği
    if k.get('servis_kimligi') != f'SRV-{kod}':
        b.hata('V03', 'servis_kimligi', f'Servis kimliği SRV-{kod} olmalı')

    # V04 sürümler
    if not SURUM_DESENI.match(str(k.get('surum', ''))):
        b.hata('V04', 'surum', 'Sürüm üç parçalı olmalı (ör. 0.1.0)')
    m = CEKIRDEK_DESENI.match(str(k.get('cekirdek', '')))
    if not m:
        b.hata('V04', 'cekirdek', 'Çekirdek sürümü ">=10.2" biçiminde olmalı')
    elif (int(m.group(1)), int(m.group(2))) > _surum_sayi(katalog['cekirdek_surumu']):
        b.hata('V04', 'cekirdek', f'Bu çekirdek {katalog["cekirdek_surumu"]}; künye daha yenisini istiyor')

    kapilar = k.get('kapilar') if isinstance(k.get('kapilar'), dict) else {}
    for alan in sorted(set(kapilar) - KAPI_ALANLARI):
        b.hata('V01', f'kapilar.{alan}', 'Bilinmeyen kapı alanı')
    if 'dosyalar' in kapilar and not isinstance(kapilar['dosyalar'],bool):
        b.hata('V01','kapilar.dosyalar','Dosya kapısı true/false olmalı')
    arka_yuz = k.get('arka_yuz') is True
    olay_yolu = k.get('olay_yolu')
    olaylar = _liste(kapilar.get('olaylar'))
    bildirimler = _liste(kapilar.get('bildirimler'))
    kisisel_veri = _liste(k.get('kisisel_veri'))
    para = k.get('para') is True
    bagimliliklar = {x.get('modul'): x for x in _liste(k.get('bagimliliklar')) if isinstance(x, dict)}
    roller = {r.get('kod') for r in _liste(k.get('roller')) if isinstance(r, dict)}
    tum_roller = set(katalog['roller']) | roller | set(kayit_rolleri)

    # V05 olay yolu ve cihaz harfi
    if olay_yolu not in ('ARKA_YUZ', 'ISTEMCI', 'YOK'):
        b.hata('V05', 'olay_yolu', 'olay_yolu ARKA_YUZ, ISTEMCI ya da YOK olmalı')
    if olaylar and olay_yolu == 'YOK':
        b.hata('V05', 'olay_yolu', 'Olay yazan modülün olay yolu YOK olamaz')
    if not olaylar and olay_yolu in ('ARKA_YUZ', 'ISTEMCI'):
        b.uyari('V05', 'olay_yolu', 'Olay yolu var ama kapilar.olaylar boş')
    harf = k.get('cihaz_harfi')
    if olay_yolu == 'ARKA_YUZ':
        if not arka_yuz:
            b.hata('V05', 'arka_yuz', 'Olayı arka yüz yazıyorsa arka_yuz true olmalı')
        if not (isinstance(harf, str) and re.match(r'^[A-Z]$', harf)):
            b.hata('V05', 'cihaz_harfi', 'Olayı arka yüz yazan modüle tek büyük harf ayrılır (K-5)')
        elif harf in katalog['cihaz_harf_sirasi'][:9]:
            b.uyari('V05', 'cihaz_harfi', f'{harf} cihazların ilk aldığı harflerden; sonradan eklenirse '
                                          'çekirdek "kullanılmış harf" diye reddedebilir. Sondan seçin (S, R, Q, P…)')
    elif harf is not None:
        b.hata('V05', 'cihaz_harfi', 'Cihaz harfi yalnızca olay yolu ARKA_YUZ olan modüle verilir; istemciler '
                                     'normal cihaz kaydıyla harf alır (K-5)')

    # V06 okumalar
    for i, ad in enumerate(_liste(kapilar.get('okumalar'))):
        yol = f'kapilar.okumalar[{i}]'
        s = SAGLANAN_DESENI.match(ad) if isinstance(ad, str) else None
        if s:
            if s.group(1) == kod:
                b.hata('V06', yol, 'Modül kendi okumasını çekirdekten istemez')
            elif s.group(1) not in bagimliliklar:
                b.hata('V06', yol, f'{ad}: {s.group(1)} modülü bagimliliklar\'da yok')
            continue
        o = katalog['okumalar'].get(ad)
        if o is None:
            b.hata('V06', yol, f'{ad}: çekirdekte böyle bir okuma yok (T16 › 4)')
            continue
        if o['katman'] == 'S' and not o.get('urunde_mevcut'):
            b.uyari('V06', yol, f'{ad} MVP\'de yok (T16 katman S)')
        if o['kisisel'] and not kisisel_veri:
            b.hata('V06', yol, f'{ad} kişisel veri döndürür; kisisel_veri beyanı gerekli')
        if o['para'] and not para:
            b.hata('V06', yol, f'{ad} para döndürür; para: true beyanı gerekli')

    # V07 servis okumaları
    servis_okumalari = _liste(kapilar.get('servis_okumalari'))
    if servis_okumalari and not arka_yuz:
        b.hata('V07', 'kapilar.servis_okumalari', 'Servis okuması yalnızca arka yüzü olan modülde olur')
    for i, ad in enumerate(servis_okumalari):
        if ad not in katalog['servis_okumalari']:
            b.hata('V07', f'kapilar.servis_okumalari[{i}]',
                   f'{ad} servis gözüyle okunamaz: kişisel veri ya da para (T18 › 4.3). Kullanıcının oturumuyla oku')

    # V08 olaylar
    for i, e in enumerate(olaylar):
        yol = f'kapilar.olaylar[{i}]'
        if e not in katalog['eylemler']:
            b.hata('V08', yol, f'{e}: çekirdekte böyle bir eylem yok')
        elif e in katalog['kurulum_eylemleri']:
            b.hata('V08', yol, f'{e} kurulum eylemidir; künyenin roller/nesne_turleri/kod_listeleri/'
                               'yetki_onerileri bölümünde bildirilir')
        elif _eslesir(e, katalog['cekirdek_ekrani']):
            b.hata('V08', yol, f'{e} firmanın ayarı ya da denetimidir; yalnızca çekirdeğin ekranından yazılır')
        elif e in katalog['mavi_yaka_dugmeleri']:
            b.hata('V08', yol, f'{e} mavi yakanın düğmesidir; mavi yakanın tek yolu çekirdeğin telefonudur')
        else:
            for desen, beyan in katalog['hassas_eylemler'].items():
                if _eslesir(e, [desen]):
                    if beyan == 'para' and not para:
                        b.hata('V08', yol, f'{e} para içerir; para: true beyanı gerekli')
                    if beyan == 'kisisel_veri' and not kisisel_veri:
                        b.hata('V08', yol, f'{e} kişisel veri içerir; kisisel_veri beyanı gerekli')

    # V10 plan ve belge
    if kapilar.get('plan') is True and 'PLAN.TARIHLEDIM' not in olaylar:
        b.hata('V10', 'kapilar.plan', 'Plan kapısını kullanan modül PLAN.TARIHLEDIM yazar')
    if kapilar.get('belge_surumu') is True and 'NESNE.SURUM_EKLEDIM' not in olaylar:
        b.hata('V10', 'kapilar.belge_surumu', 'Belge sürümü kullanan modül NESNE.SURUM_EKLEDIM yazar')
    if 'PLAN.TARIHLEDIM' in olaylar and kapilar.get('plan') is not True:
        b.uyari('V10', 'kapilar.plan', 'PLAN.TARIHLEDIM yazılıyor ama plan: true değil')

    # V11 bildirim kuralları
    if bildirimler and not arka_yuz:
        b.hata('V11', 'kapilar.bildirimler', 'Bildirimi modülün arka yüzü bırakır; arka_yuz true olmalı')
    gorulen = set()
    bk = katalog['bildirim']
    for i, x in enumerate(bildirimler):
        yol = f'kapilar.bildirimler[{i}]'
        if not isinstance(x, dict):
            b.hata('V11', yol, 'Bildirim kuralı bir nesne olmalı')
            continue
        kural = x.get('kural', '')
        if not KURAL_DESENI.match(str(kural)):
            b.hata('V11', yol + '.kural', 'Kural kodu büyük harf, rakam ve _ (ör. SIPARIS_GECIKTI)')
        if kural in gorulen:
            b.hata('V11', yol + '.kural', f'{kural} iki kez tanımlı')
        gorulen.add(kural)
        if not x.get('ad'):
            b.hata('V11', yol + '.ad', 'Kuralın adı kişinin anlayacağı biçimde yazılır')
        if x.get('onem') not in bk['onem']:
            b.hata('V11', yol + '.onem', 'Önem BILGI ya da UYARI')
        for t in _liste(x.get('kayit_turleri')) or [None]:
            if t not in bk['kayit_turleri']:
                b.hata('V11', yol + '.kayit_turleri', f'{t}: bildirim kaydı {"|".join(bk["kayit_turleri"])} '
                                                       'olabilir (TEZGAH ve KISI için çekirdeğe istek İ-3)')
        for t in _liste(x.get('alici_turleri')) or [None]:
            if t not in bk['alici_turleri']:
                b.hata('V11', yol + '.alici_turleri', f'{t}: tanımsız alıcı türü')
        for r in _liste(x.get('roller')):
            if r not in tum_roller:
                b.hata('V11', yol + '.roller', f'{r}: tanımsız rol')

    # V12 abonelikler
    abonelikler = _liste(kapilar.get('abonelikler'))
    if abonelikler and not arka_yuz:
        b.hata('V12', 'kapilar.abonelikler', 'Abonelik arka yüz içindir; istemci kullanıcının kanallarını dinler')
    for i, a in enumerate(abonelikler):
        if a not in katalog['servis_kanallari']:
            b.hata('V12', f'kapilar.abonelikler[{i}]', f'{a}: servis yalnızca {", ".join(katalog["servis_kanallari"])} '
                                                       'kanallarını dinler (kişi ve birim kanalları kişiseldir)')

    # V13 nesne türleri
    for i, t in enumerate(_liste(k.get('nesne_turleri'))):
        _tur_denetle(b, f'nesne_turleri[{i}]', t, katalog, tum_roller)

    # V14 tür uzantıları
    sema = f'mod_{kod.lower()}'
    for i, u in enumerate(_liste(k.get('tur_uzantilari'))):
        yol = f'tur_uzantilari[{i}]'
        if not str(u.get('tablo', '')).startswith(sema + '.'):
            b.hata('V14', yol + '.tablo', f'Uzantı tablosu modülün şemasında olur: {sema}.<tablo>')
        if not u.get('tur'):
            b.hata('V14', yol + '.tur', 'Uzantının nesne türü yazılır')

    # V15 roller
    for i, r in enumerate(_liste(k.get('roller'))):
        yol = f'roller[{i}]'
        if not ROL_DESENI.match(str(r.get('kod', ''))):
            b.hata('V15', yol + '.kod', 'Rol kodu büyük harf ve _ , 3–21 karakter')
        elif r['kod'] in katalog['roller']:
            b.hata('V15', yol + '.kod', f'{r["kod"]} çekirdeğin rolü; modül yeniden tanımlamaz, kullanır')
        if not r.get('ad'):
            b.hata('V15', yol + '.ad', 'Rolün adı gerekli')

    # V16 kod listeleri
    for i, x in enumerate(_liste(k.get('kod_listeleri'))):
        yol = f'kod_listeleri[{i}]'
        liste = x.get('liste', '')
        if liste == 'ROL':
            b.hata('V16', yol + '.liste', 'Roller roller bölümünde tanımlanır')
        elif liste not in katalog['kod_listeleri']:
            b.hata('V16', yol + '.liste', f'{liste}: çekirdeğin kod listeleri sabittir '
                                          f'({", ".join(sorted(katalog["kod_listeleri"]))}); modülün kendi '
                                          f'listesi mod_{kod.lower()} şemasında tutulur')
        elif liste in katalog['mavi_yaka_listeleri']:
            b.uyari('V16', yol + '.liste', f'{liste} mavi yakanın telefondaki seçimidir; her kod seçimi uzatır')
        if not x.get('kod') or not x.get('ad'):
            b.hata('V16', yol, 'Kodun kodu ve adı gerekli')

    # V17 yetki önerileri
    for i, y in enumerate(_liste(k.get('yetki_onerileri'))):
        yol = f'yetki_onerileri[{i}]'
        e = y.get('eylem_kodu')
        if e not in katalog['eylemler']:
            b.hata('V17', yol, f'{e}: çekirdekte böyle bir eylem yok')
        elif e in katalog['kurulum_eylemleri'] or _eslesir(e, katalog['cekirdek_ekrani']):
            b.hata('V17', yol, f'{e} için yetki önerilemez (kurulum ya da çekirdek ekranı)')
        if y.get('kapsam') not in katalog['nesne_kapsamlari']:
            b.hata('V17', yol + '.kapsam', 'Kapsam FIRMA ya da BIRIM')
        for r in _liste(y.get('kimler')) or [None]:
            if r not in tum_roller | set(katalog.get('sozde_roller',[])):
                b.hata('V17', yol + '.kimler', f'{r}: tanımsız rol')
        if e and e not in olaylar:
            b.uyari('V17', yol, f'{e} modülün olaylarında yok; öneri çekirdeğin ekranlarını da etkiler')

    # V18 veritabanı
    vt = k.get('veritabani') if isinstance(k.get('veritabani'), dict) else {}
    if vt.get('sema') != sema:
        b.hata('V18', 'veritabani.sema', f'Modülün şeması {sema} olmalı')

    # V19 ön yüz ve derin bağlantılar
    oy = k.get('on_yuz') if isinstance(k.get('on_yuz'), dict) else {'tur': 'YOK'}
    if oy.get('tur') not in ON_YUZ_TURLERI:
        b.hata('V19', 'on_yuz.tur', 'Ön yüz UYGULAMA_ICI, AYRI_UYGULAMA ya da YOK')
    if olay_yolu == 'ISTEMCI' and oy.get('tur') not in ('UYGULAMA_ICI', 'AYRI_UYGULAMA'):
        b.hata('V19', 'on_yuz', 'Olayı istemci yazıyorsa modülün bir ön yüzü olmalı')
    for i, d in enumerate(_liste(oy.get('derin_baglantilar'))):
        yol = f'on_yuz.derin_baglantilar[{i}]'
        if d.get('baglam') not in BAGLAMLAR:
            b.hata('V19', yol + '.baglam', f'Bağlam {", ".join(sorted(BAGLAMLAR))}')
        if not str(d.get('yol', '')).startswith('/') or '{kimlik}' not in str(d.get('yol', '')):
            b.hata('V19', yol + '.yol', 'Yol / ile başlar ve {kimlik} taşır (ör. /parca/{kimlik})')
        if not d.get('ad'):
            b.hata('V19', yol + '.ad', 'Bağlantının ekranda görünen adı gerekli')
        for r in _liste(d.get('kimler')):
            if r not in tum_roller:
                b.hata('V19', yol + '.kimler', f'{r}: tanımsız rol')

    # V20 sağlanan okumalar
    for i, s in enumerate(_liste(k.get('saglananlar'))):
        yol = f'saglananlar[{i}]'
        m = SAGLANAN_DESENI.match(str(s.get('ad', '')))
        if not m or m.group(1) != kod:
            b.hata('V20', yol + '.ad', f'Sağlanan okumanın adı {kod}.<AD>')
        if s.get('gorme') not in GORME_TURLERI:
            b.hata('V20', yol + '.gorme', f'Görme kuralı {", ".join(sorted(GORME_TURLERI))}')
        if (s.get('kisisel') or s.get('para')) and s.get('gorme') == 'KAYDI_GOREN':
            b.hata('V20', yol + '.gorme', 'Kişisel ya da parasal okuma kaydı gören herkese açılmaz')
        if s.get('para') and not para:
            b.hata('V20', yol, 'Parasal okuma sağlayan modül para: true beyan eder')

    # V21 bağımlılıklar
    for i, (m_kod, x) in enumerate(bagimliliklar.items()):
        yol = f'bagimliliklar[{i}]'
        if m_kod == kod:
            b.hata('V21', yol, 'Modül kendine bağımlı olamaz')
        if x.get('zorunlu') is not False:
            b.hata('V21', yol + '.zorunlu', 'Bağımlılık isteğe bağlıdır (zorunlu: false): sağlayan pasifken '
                                            'tüketen çalışmaya devam eder. Zorunluysa iki modül tek modüldür')
        for o in _liste(x.get('okumalar')):
            if not str(o).startswith(f'{m_kod}.'):
                b.hata('V21', yol + '.okumalar', f'{o} {m_kod} modülünün okuması değil')

    # V22 kişisel veri
    for i, x in enumerate(kisisel_veri):
        if not isinstance(x, dict) or not x.get('alan') or not x.get('neden'):
            b.hata('V22', f'kisisel_veri[{i}]', 'Her kişisel veri alanı ve tutulma nedeniyle yazılır (KVKK)')
    if not isinstance(k.get('para'), bool):
        b.hata('V22', 'para', 'para true ya da false')

    # V23 sınırlar
    sinir = k.get('sinirlar') if isinstance(k.get('sinirlar'), dict) else {}
    if bildirimler and 'bildirim_dakika' not in sinir:
        b.hata('V23', 'sinirlar.bildirim_dakika', 'Bildirim bırakan modül dakikadaki üst sınırını yazar')
    if servis_okumalari and 'servis_okuma_dakika' not in sinir:
        b.hata('V23', 'sinirlar.servis_okuma_dakika', 'Servis okuması yapan modül dakikadaki üst sınırını yazar')
    for ad, deger in sinir.items():
        if ad not in SINIR_UST:
            b.hata('V23', f'sinirlar.{ad}', 'Bilinmeyen sınır')
        elif not isinstance(deger, int) or not 1 <= deger <= SINIR_UST[ad]:
            b.hata('V23', f'sinirlar.{ad}', f'1 ile {SINIR_UST[ad]} arasında bir tam sayı')

    # V24 istekler
    for i, x in enumerate(_liste(k.get('istekler'))):
        if x.get('durum') not in ISTEK_DURUMLARI or not x.get('baslik'):
            b.hata('V24', f'istekler[{i}]', f'İsteğin başlığı ve durumu ({", ".join(sorted(ISTEK_DURUMLARI))})')
    return b


def _tur_denetle(b, yol, t, katalog, tum_roller):
    """V13: türün tanımı çekirdeğin NESNE_TURU.TANIMLADIM kapılarından önce burada yakalanır."""
    if not isinstance(t, dict):
        b.hata('V13', yol, 'Tür bir nesne olmalı')
        return
    kod = t.get('kod', '')
    if not ROL_DESENI.match(str(kod)):
        b.hata('V13', yol + '.kod', 'Tür kodu büyük harf ve _ (ör. KALITE_KAYDI)')
    if kod in katalog['nesne_turleri']:
        b.hata('V13', yol + '.kod', f'{kod} çekirdeğin türü; değişiklik çekirdeğe istek olarak gelir (T18 › 11)')
    for alan in ('ad', 'asamalar', 'baslangic_asamasi', 'gecisler', 'baglanabilir_turler', 'acabilenler'):
        if alan not in t:
            b.hata('V13', f'{yol}.{alan}', 'Zorunlu alan eksik')
    asamalar = [a if isinstance(a, dict) else {'kod': a, 'son': False} for a in _liste(t.get('asamalar'))]
    kodlar = [a.get('kod') for a in asamalar]
    son = {a['kod'] for a in asamalar if a.get('son')}
    if len(kodlar) != len(set(kodlar)):
        b.hata('V13', yol + '.asamalar', 'Aşama kodu iki kez yazılmış')
    if len(asamalar) < 2 or not son:
        b.hata('V13', yol + '.asamalar', 'En az iki aşama ve en az bir son aşama')
    bas = t.get('baslangic_asamasi')
    if bas not in kodlar:
        b.hata('V13', yol + '.baslangic_asamasi', 'Başlangıç aşaması aşamalardan biri olmalı')
    elif bas in son:
        b.hata('V13', yol + '.baslangic_asamasi', 'Başlangıç aşaması son aşama olamaz')
    kenar = {}
    for j, g in enumerate(_liste(t.get('gecisler'))):
        gy = f'{yol}.gecisler[{j}]'
        den, e = g.get('den'), g.get('e')
        if den not in kodlar or e not in kodlar:
            b.hata('V13', gy, f'{den} → {e}: aşamalarda olmayan aşama')
            continue
        if den in son:
            b.hata('V13', gy, f'{den} son aşama; ondan geçiş olmaz')
        if den == e:
            b.hata('V13', gy, 'Aşama kendine geçmez')
        if (den, e) in kenar:
            b.hata('V13', gy, f'{den} → {e} iki kez tanımlı')
        kenar[(den, e)] = g
        if g.get('kapsam', 'FIRMA') not in katalog['nesne_kapsamlari']:
            b.hata('V13', gy + '.kapsam', 'Kapsam FIRMA ya da BIRIM')
        for r in _liste(g.get('kimler')) or [None]:
            if r not in tum_roller:
                b.hata('V13', gy + '.kimler', f'{r}: tanımsız rol')
    if bas in kodlar:
        ulasilan, sira = {bas}, [bas]
        while sira:
            x = sira.pop()
            for (den, e) in kenar:
                if den == x and e not in ulasilan:
                    ulasilan.add(e)
                    sira.append(e)
        for a in kodlar:
            if a not in ulasilan:
                b.hata('V13', yol + '.gecisler', f'{a} aşamasına başlangıçtan ulaşılmıyor')
        for a in kodlar:
            if a in son:
                continue
            gidilen, sira = {a}, [a]
            while sira:
                x = sira.pop()
                for (den, e) in kenar:
                    if den == x and e not in gidilen:
                        gidilen.add(e)
                        sira.append(e)
            if not gidilen & son:
                b.hata('V13', yol + '.gecisler', f'{a} aşamasından son aşamaya yol yok (çıkmaz)')
    for bt in _liste(t.get('baglanabilir_turler')):
        if bt not in katalog['baglanabilir_turler']:
            b.hata('V13', yol + '.baglanabilir_turler', f'{bt}: bağ türü {"|".join(katalog["baglanabilir_turler"])}')
    ac = t.get('acabilenler')
    ac = {'kimler': ac, 'kapsam': 'FIRMA'} if isinstance(ac, list) else (ac or {})
    for r in _liste(ac.get('kimler')) or [None]:
        if r not in tum_roller:
            b.hata('V13', yol + '.acabilenler', f'{r}: tanımsız rol')
    so = t.get('surum_onaylayanlar')
    if so is not None:
        for r in _liste(so.get('kimler')) if isinstance(so, dict) else [None]:
            if r not in tum_roller:
                b.hata('V13', yol + '.surum_onaylayanlar', f'{r}: tanımsız rol')


# ---------------------------------------------------------------- kayıt düzeyi

def kayit_denetle(kunyeler, katalog=None):
    """Bütün modüller birlikte (R01–R11). kunyeler: [künye, ...]"""
    katalog = katalog or katalog_yukle()
    b = Bulgular()
    sahip = {}
    for alan, kural in (('kod', 'R01'), ('servis_kimligi', 'R02'), ('cihaz_harfi', 'R03')):
        gorulen = {}
        for k in kunyeler:
            v = k.get(alan)
            if v is None:
                continue
            if v in gorulen:
                b.hata(kural, f'{k.get("kod")}.{alan}', f'{v} hem {gorulen[v]} hem {k.get("kod")} modülünde')
            gorulen[v] = k.get('kod')
    harfler = [k['cihaz_harfi'] for k in kunyeler if k.get('cihaz_harfi')]
    if len(harfler) > 8:
        b.uyari('R11', 'cihaz_harfi', f'{len(harfler)} modül harf aldı; kişilerin cihazlarına {26 - len(harfler)} '
                                      'harf kalıyor. Olayı istemciden yazmayı düşünün')
    for t in katalog['nesne_turleri']:
        sahip[t] = 'CEKIRDEK'
    rol_sahibi = {r: 'CEKIRDEK' for r in katalog['roller']}
    saglanan = {}
    for k in kunyeler:
        for t in _liste(k.get('nesne_turleri')):
            if t.get('kod') in sahip:
                b.hata('R04', f'{k["kod"]}.nesne_turleri', f'{t.get("kod")} türünün sahibi {sahip[t["kod"]]}; '
                                                           'bir türün tek sahibi olur')
            else:
                sahip[t.get('kod')] = k['kod']
        for r in _liste(k.get('roller')):
            if r.get('kod') in rol_sahibi:
                b.hata('R05', f'{k["kod"]}.roller', f'{r.get("kod")} rolünün sahibi {rol_sahibi[r["kod"]]}')
            else:
                rol_sahibi[r.get('kod')] = k['kod']
        for s in _liste(k.get('saglananlar')):
            saglanan[s.get('ad')] = k['kod']
    kodlar = {k.get('kod'): k for k in kunyeler}
    for k in kunyeler:
        for x in _liste(k.get('bagimliliklar')):
            if x.get('modul') not in kodlar:
                b.hata('R06', f'{k["kod"]}.bagimliliklar', f'{x.get("modul")} modülü kayıtlı değil')
            for o in _liste(x.get('okumalar')):
                if saglanan.get(o) != x.get('modul'):
                    b.hata('R07', f'{k["kod"]}.bagimliliklar', f'{o}: {x.get("modul")} böyle bir okuma sağlamıyor')
        for o in _liste((k.get('kapilar') or {}).get('okumalar')):
            m = SAGLANAN_DESENI.match(str(o))
            if m and saglanan.get(o) != m.group(1):
                b.hata('R07', f'{k["kod"]}.kapilar.okumalar', f'{o}: sağlayan modülde tanımlı değil')
        for u in _liste(k.get('tur_uzantilari')):
            if u.get('tur') not in sahip:
                b.hata('R10', f'{k["kod"]}.tur_uzantilari', f'{u.get("tur")} türü ne çekirdekte ne bir modülde')
        baskasinin = {rol_sahibi.get(r) for r in _kullanilan_roller(k)} - {'CEKIRDEK', k['kod'], None}
        bagli = {x.get('modul') for x in _liste(k.get('bagimliliklar'))}
        for m_kod in sorted(baskasinin - bagli):
            b.uyari('R09', f'{k["kod"]}', f'{m_kod} modülünün rolünü kullanıyor ama ona bağımlı değil')
        for r in _kullanilan_roller(k):
            if r not in rol_sahibi:
                b.hata('R09', f'{k["kod"]}', f'{r}: hiçbir yerde tanımlı olmayan rol')
    # R08 döngü
    kenar = {k.get('kod'): [x.get('modul') for x in _liste(k.get('bagimliliklar'))] for k in kunyeler}

    def dongu(x, yol):
        for y in kenar.get(x, []):
            if y in yol:
                return yol[yol.index(y):] + [y]
            d = dongu(y, yol + [y])
            if d:
                return d
        return None
    bildirilen = set()
    for x in kenar:
        d = dongu(x, [x])
        if d and frozenset(d) not in bildirilen:
            bildirilen.add(frozenset(d))
            b.hata('R08', 'bagimliliklar', 'Döngü: ' + ' → '.join(d))
    for k in kunyeler:
        for x in kunye_denetle(k, katalog, kayit_rolleri=set(rol_sahibi)):
            b.append(dict(x, yol=f'{k.get("kod")}.{x["yol"]}'))
    return b


def _kullanilan_roller(k):
    r = set()
    for t in _liste(k.get('nesne_turleri')):
        for g in _liste(t.get('gecisler')):
            r |= set(_liste(g.get('kimler')))
        ac = t.get('acabilenler')
        r |= set(ac if isinstance(ac, list) else _liste((ac or {}).get('kimler')))
    for y in _liste(k.get('yetki_onerileri')):
        r |= set(_liste(y.get('kimler')))
    for x in _liste((k.get('kapilar') or {}).get('bildirimler')):
        r |= set(_liste(x.get('roller')))
    for d in _liste((k.get('on_yuz') or {}).get('derin_baglantilar')):
        r |= set(_liste(d.get('kimler')))
    return r


# ---------------------------------------------------------------- göç düzeyi

_YORUM = re.compile(r'--[^\n]*|/\*.*?\*/', re.S)
_METIN = re.compile(r"'(?:[^']|'')*'")
_AD = r'((?:"?[A-Za-z_][\w$]*"?\.)?"?[A-Za-z_][\w$]*"?)'
_DDL = [
    ('G01', re.compile(r'\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:UNLOGGED\s+)?(?:TABLE|VIEW|MATERIALIZED\s+VIEW|SEQUENCE|'
                       r'TYPE|FUNCTION|PROCEDURE|DOMAIN)\s+(?:IF\s+NOT\s+EXISTS\s+)?' + _AD, re.I), 'oluşturulan nesne'),
    ('G01', re.compile(r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\s+)?ON\s+'
                       r'(?:ONLY\s+)?' + _AD, re.I), 'dizinin tablosu'),
    ('G06', re.compile(r'\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:CONSTRAINT\s+)?TRIGGER\s+\w+.*?\bON\s+' + _AD, re.I | re.S),
     'tetikleyicinin tablosu'),
    ('G01', re.compile(r'\bALTER\s+(?:TABLE|VIEW|SEQUENCE|FUNCTION|TYPE|MATERIALIZED\s+VIEW)\s+(?:IF\s+EXISTS\s+)?'
                       r'(?:ONLY\s+)?' + _AD, re.I), 'değiştirilen nesne'),
    ('G05', re.compile(r'\bDROP\s+(?:TABLE|VIEW|SEQUENCE|FUNCTION|TYPE|INDEX|MATERIALIZED\s+VIEW)\s+(?:IF\s+EXISTS\s+)?'
                       + _AD, re.I), 'silinen nesne'),
    ('G08', re.compile(r'\bREFERENCES\s+' + _AD, re.I), 'yabancı anahtarın tablosu'),
]
_YASAK = [
    ('G03', re.compile(r'\b(CREATE|ALTER|DROP)\s+(ROLE|USER|SCHEMA|EXTENSION|PUBLICATION|EVENT\s+TRIGGER)\b', re.I),
     'Rol, şema, eklenti ve yayın çekirdeğin kurulumundadır (künyeden)'),
    ('G03', re.compile(r'\b(GRANT|REVOKE)\b', re.I), 'Haklar kurulumda künyeden verilir; göçte GRANT/REVOKE olmaz'),
    ('G09', re.compile(r'\b(LISTEN|NOTIFY)\b|\bpg_notify\s*\(', re.I),
     'Değişiklik haberi degisim_sinyalleri kanallarından alınır (T16 › 7)'),
    ('G09', re.compile(r'\bSET\s+(?:SESSION\s+)?ROLE\b|\bSET\s+session_replication_role\b', re.I),
     'Rol değiştirmek ve tetikleyicileri susturmak yasak'),
]


def goc_denetle(kod, sql, dosya='goc.sql', katalog=None):
    katalog = katalog or katalog_yukle()
    b = Bulgular()
    sema = f'mod_{kod.lower()}'
    yorumsuz = _YORUM.sub(' ', sql)
    for m in re.finditer(r"cron\.schedule\s*\(\s*'([^']*)'", yorumsuz, re.I):
        if not m.group(1).startswith(sema + '_'):
            b.hata('G07', dosya, f'Zamanlanmış işin adı {sema}_ ile başlar: {m.group(1)}')
    if re.search(r"\bEXECUTE\s+(?:format\s*\(|'|\$|[a-z_]\w*\s*(?:;|USING\b|\|\|))", yorumsuz, re.I):
        b.uyari('G02', dosya, 'Dinamik SQL (EXECUTE) denetlenemez; elle gözden geçirin')
    temiz = _METIN.sub("''", yorumsuz)
    for kural, desen, ne in _DDL:
        for m in desen.finditer(temiz):
            ad = m.group(1).replace('"', '')
            if not ad.lower().startswith(sema + '.'):
                b.hata(kural, dosya, f'{ne} ({ad}) modülün şemasında olmalı: {sema}.<ad>')
    for kural, desen, neden in _YASAK:
        for m in desen.finditer(temiz):
            b.hata(kural, dosya, f'{m.group(0).strip()}: {neden}')
    semalar = '|'.join(katalog['cekirdek_semalari'])
    for m in re.finditer(r'\b(' + semalar + r'|mod_[a-z0-9]+)\s*\.\s*"?([A-Za-z_]\w*)"?(\s*\()?', temiz, re.I):
        s, ad, cagri = m.group(1).lower(), m.group(2), m.group(3)
        if s == sema:
            continue
        tam = f'{s}.{ad}'
        if cagri and tam in katalog['izinli_fonksiyonlar']:
            continue
        if s.startswith('mod_'):
            b.hata('G02', dosya, f'{tam}: başka modülün şeması okunmaz; sağladığı okumayı kullanın (T18 › 8)')
        else:
            b.hata('G02', dosya, f'{tam}: çekirdeğin tablosuna ya da izinsiz fonksiyonuna dokunulmaz (T18 › 7)')
    for m in re.finditer(r'\bSECURITY\s+DEFINER\b', temiz, re.I):
        govde_sonu = temiz.find(';', m.end())
        bas = temiz.rfind('CREATE', 0, m.start())
        parca = temiz[bas:govde_sonu if govde_sonu > 0 else len(temiz)]
        if not re.search(r'\bSET\s+search_path\b', parca, re.I):
            b.hata('G04', dosya, 'SECURITY DEFINER fonksiyonu search_path\'i sabitler (SET search_path = ...)')
    return b


# ---------------------------------------------------------------- kurulum

def kurulum_olaylari(k):
    """Künyeden, YETKILI'nin kurulumda yazacağı olayların girdileri (sırayla)."""
    olaylar = []
    g = {'kod': k['kod'], 'ad': k['ad'], 'servis_kimligi': k['servis_kimligi'], 'aktif': True}
    if k.get('cihaz_harfi'):
        g['cihaz_harfi'] = k['cihaz_harfi']
    olaylar.append({'eylem_kodu': 'MODUL.TANIMLADIM', 'girdiler': g})
    for r in _liste(k.get('roller')):
        olaylar.append({'eylem_kodu': 'KOD.TANIMLADIM',
                        'girdiler': {'liste': 'ROL', 'kod': r['kod'], 'ad': r['ad'], 'aktif': True}})
    for x in _liste(k.get('kod_listeleri')):
        girdi = {'liste': x['liste'], 'kod': x['kod'], 'ad': x['ad'], 'aktif': True}
        if x.get('ust'):
            girdi['ust'] = x['ust']
        olaylar.append({'eylem_kodu': 'KOD.TANIMLADIM', 'girdiler': girdi})
    for t in _liste(k.get('nesne_turleri')):
        olaylar.append({'eylem_kodu': 'NESNE_TURU.TANIMLADIM', 'girdiler': json.loads(json.dumps(t))})
    for y in _liste(k.get('yetki_onerileri')):
        olaylar.append({'eylem_kodu': 'YETKI.TANIMLADIM',
                        'girdiler': {'eylem_kodu': y['eylem_kodu'], 'kimler': y['kimler'], 'kapsam': y['kapsam']}})
    return olaylar


def pasiflestirme_olaylari(k):
    g = {'kod': k['kod'], 'ad': k['ad'], 'servis_kimligi': k['servis_kimligi'], 'aktif': False}
    if k.get('cihaz_harfi'):
        g['cihaz_harfi'] = k['cihaz_harfi']
    return [{'eylem_kodu': 'MODUL.TANIMLADIM', 'girdiler': g}]


# ---------------------------------------------------------------- komut satırı

def klasor_denetle(klasor, katalog=None):
    """Bir modül klasörü: kunye.json + veritabani/*.sql"""
    katalog = katalog or katalog_yukle()
    klasor = Path(klasor)
    k = json.loads((klasor / 'kunye.json').read_text('utf-8'))
    b = kunye_denetle(k, katalog)
    vt = (k.get('veritabani') or {}).get('gocler')
    if vt:
        for sql in sorted((klasor / vt).glob('*.sql')):
            b.extend(goc_denetle(k['kod'], sql.read_text('utf-8'), sql.name, katalog))
    return k, b


def _yaz(baslik, bulgular):
    print(f'== {baslik}: {len(bulgular.hatalar)} hata, {len(bulgular) - len(bulgular.hatalar)} uyarı')
    for x in bulgular:
        print(f'  {x["seviye"]:5} {x["kural"]} {x["yol"]}: {x["mesaj"]}')


def main(argv):
    katalog = katalog_yukle()
    if argv[:1] == ['--kurulum']:
        k = json.loads(Path(argv[1]).read_text('utf-8'))
        print(json.dumps(kurulum_olaylari(k), ensure_ascii=False, indent=1))
        return 0
    kunyeler, hata = [], False
    for yol in argv:
        p = Path(yol)
        if p.is_dir():
            k, b = klasor_denetle(p, katalog)
        else:
            k = json.loads(p.read_text('utf-8'))
            b = kunye_denetle(k, katalog)
        kunyeler.append(k)
        _yaz(k.get('kod', yol), b)
        hata |= bool(b.hatalar)
    if len(kunyeler) > 1:
        b = kayit_denetle(kunyeler, katalog)
        b = Bulgular(x for x in b if x['kural'].startswith('R'))
        _yaz('kayıt', b)
        hata |= bool(b.hatalar)
    return 1 if hata else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
