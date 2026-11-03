"""Çekirdek kataloğunu üretir: modülün künyesinin denetlendiği liste (T18 › 5).

Kaynaklar elle kopyalanmaz, buradan okunur:
- okumalar: modelin `gorunum_v10_2` okuma adları + T16 › 4.1–4.3 tabloları (görme kuralı, katman)
- eylemler: `referans/eylem_semalari.json` (sınıf)
- roller ve kod listeleri: modelin `yetki_v6.varsayilan_kodlar`
Sınıflandırmalar (kurulum, çekirdek ekranı, mavi yaka düğmesi, hassas, servis okuması) T18'in kurallarıdır
ve aşağıda sabit olarak durur.

Koşmak: python3 -I -B modul_kiti/katalog_uret.py          (dosyayı yazar)
        python3 -I -B modul_kiti/katalog_uret.py --denetle (dosya güncel değilse 1 döner)
"""
import json
from pathlib import Path
import re
import sys

KOK = Path(__file__).resolve().parents[1]
MODEL = KOK / 'referans' / 'cevap_anahtari' / 'model'
CIKTI = Path(__file__).resolve().parent / 'cekirdek_katalogu.json'

CEKIRDEK_SURUMU = '10.2'
SOZDE_ROLLER = ['BIRIM_BASI','BIRIM_YONETICISI','BIRIM_UYESI','PROJE_SORUMLUSU']

# T18 › 4.2: modülün çalışırken yazamadığı, yalnızca künyeden kurulumda yazılan eylemler.
KURULUM_EYLEMLERI = ['KOD.TANIMLADIM', 'MODUL.TANIMLADIM', 'NESNE_TURU.TANIMLADIM', 'YETKI.TANIMLADIM']
# T18 › 4.2: firmanın ayarı, görünürlüğü ve denetimi; yalnızca çekirdeğin ekranlarından.
CEKIRDEK_EKRANI = ['AYAR.*', 'GUN_ONAYI.AYARLADIM', 'KAYIT.GECERSIZ_SAYDIM', 'KURULUM.TAMAMLADIM',
                   'PROJE.ERISIM_KALDIRDIM', 'PROJE.ERISIM_VERDIM']
# T18 › 4.2 (mavi yaka tek yol): bu düğmeler yalnızca çekirdeğin telefon ekranındadır.
MAVI_YAKA_DUGMELERI = ['DURUS.BASLADI', 'DURUS.BITTI', 'IS.ARIZA_BILDIRDIM', 'IS.BASLADIM', 'IS.DEVAM_ETTIM',
                       'IS.MOLA_VERDIM', 'IS.TAMAMLADIM', 'MESAI.CIKTIM', 'MESAI.GIRDIM']
# T18 › 4.2: kişisel veri ya da para; künyede beyan ister.
HASSAS_EYLEMLER = {'KISI.*': 'kisisel_veri', 'IZIN.*': 'kisisel_veri', 'MAAS.*': 'para',
                   'EK_MESAI.*': 'kisisel_veri'}
# T18 › 4.3: servis gözü. Kişisel veri ve para yok; kural içindir, ekrana gitmez.
SERVIS_OKUMALARI = ['BIRIMLER', 'ETAP', 'ETAPLAR', 'GECERLI_SURUM', 'KISILER', 'KODLAR', 'NESNE', 'NESNELER',
                    'PROJE', 'PROJELER', 'TEZGAHLAR', 'TEZGAH_GOSTERGESI', 'TEZGAH_UYGUNLUK', 'TOP_KIMDE']
SERVIS_KANALLARI = ['firma', 'proje:*']
# Kişisel veri ya da para döndüren okumalar (künyede beyan ister).
KISISEL_OKUMALAR = ['NOT_ALICILARI','BIRIM_PERFORMANS', 'BUGUNKU_KIMLIKLER', 'ELLE_SURELER', 'FAZLA_MESAI', 'GECIKME_RAPORU', 'GUN',
                    'GUN_ISLERI', 'HAM_OLAY', 'IZIN', 'IZIN_DETAY', 'KIM_NEREDE', 'KISININ_GUNU', 'PERFORMANS',
                    'PERSONEL_DAGILIMI', 'SAAT_NEREYE_GITTI', 'SUPHELILER', 'TELEFON', 'UYGUNLUK']
PARA_OKUMALARI = ['ISCILIK_MALIYETI', 'MAAS', 'MAAS_DAGILIMI', 'PROJE_MALIYETI', 'SAAT_MALIYETI', 'TEZGAH_UCRETI']
# Çekirdeğin kod listeleri sabittir (modelin bicim_v6.denetle'si); modülün kendi listesi kendi şemasındadır.
CEKIRDEK_KOD_LISTELERI = ['ARIZA', 'DURUS', 'DURUS_NEDENI', 'IZIN', 'MOLA', 'PD', 'ROL', 'YETKINLIK']
# Mavi yakanın telefonda seçtiği listeler: kod eklemek seçimi uzatır (uyarı).
MAVI_YAKA_LISTELERI = ['ARIZA', 'DURUS', 'DURUS_NEDENI', 'MOLA']
# Modül kodu olamayacak adlar: çekirdeğin şemaları, kaynak adları, cihaz önekleri.
AYRILMIS_KODLAR = ['AUTH', 'CEKIRDEK', 'IRP', 'KAPI', 'MAS', 'MODUL', 'MOTOR', 'PUBLIC', 'REALTIME', 'SISTEM',
                   'SRV', 'STORAGE', 'TEL', 'TEST', 'WEB']
CEKIRDEK_SEMALARI = ['auth', 'cron', 'extensions', 'graphql', 'kapi', 'motor', 'net', 'pgsodium', 'public',
                     'realtime', 'storage', 'supabase_functions', 'test', 'vault']
# Modülün SQL'inde çağrılabilecek çekirdek fonksiyonları (T18 › 7).
IZINLI_FONKSIYONLAR = ['auth.jwt', 'auth.uid', 'cron.schedule', 'cron.unschedule', 'public.modul_bildirimi_birak',
                       'public.modul_bildirimi_kaldir', 'public.servis_oku', 'public.simdi']


def model_okumalari():
    sys.path.insert(0, str(MODEL))
    from irp.gorunum_v10_2 import ESKI_VERILER, YENI_VERILER
    return set(YENI_VERILER) | set(ESKI_VERILER)


def t16_okumalari():
    metin = (KOK / 'tasarim' / '16_okumalar.md').read_text('utf-8')
    bolum = metin[metin.index('### 4.1'):metin.index('## 5.')]
    sonuc, basliklar = {}, None
    for satir in bolum.splitlines():
        if not satir.startswith('|') or satir.startswith('|---'):
            continue
        hucre = [h.strip() for h in satir.strip().strip('|').split('|')]
        if hucre[0] == 'Veri':
            basliklar = hucre
            continue
        gorme = next(i for i, b in enumerate(basliklar) if b.startswith('Görme'))
        katman = basliklar.index('Katman')
        for ad in re.findall(r'`([A-Z_]+)`', hucre[0]):
            sonuc[ad] = {'gorme': hucre[gorme], 'katman': hucre[katman] if katman < len(hucre) else ''}
    return sonuc


def katalog():
    sys.path.insert(0,str(KOK))
    sys.path.insert(0, str(MODEL))
    from irp.yetki_v6 import varsayilan_kodlar
    semalar = json.loads((KOK / 'referans' / 'eylem_semalari.json').read_text('utf-8'))
    t16 = t16_okumalari()
    model = model_okumalari()
    okumalar = {}
    # Katman tasarım niyetidir; uygulanmış SQL kapısı ayrı ve kaynaklı bilgidir.
    from modul_kiti.yetenek_envanteri import sources
    sql_okumalar,_=sources()
    for ad in sorted(model | set(t16) | {n for n in sql_okumalar if not n.startswith('WEB_')}):
        x = t16.get(ad, {'gorme': 'modelde', 'katman': 'S'})
        okumalar[ad] = {'gorme': x['gorme'], 'katman': x['katman'] or 'S',
                        'kisisel': ad in KISISEL_OKUMALAR, 'para': ad in PARA_OKUMALARI,
                        'urunde_mevcut': ad in sql_okumalar, 'urun_kaynagi':sql_okumalar.get(ad),
                        'simulator': 'PAKET_UYARLAMASI' if ad=='PROJELER' else 'MODEL' if ad in model else 'URUN_SQL_GEREKLI'}
    kodlar = {liste: [] for liste in CEKIRDEK_KOD_LISTELERI}
    for k in varsayilan_kodlar(surum=10.2):
        liste, kod = k.split(':', 1)
        kodlar[liste].append(kod)
    return {
        'aciklama': 'Üretilmiş dosya; elle değiştirme. Kaynak: modul_kiti/katalog_uret.py (T18 › 5).',
        'cekirdek_surumu': CEKIRDEK_SURUMU,
        'okumalar': okumalar,
        'servis_okumalari': SERVIS_OKUMALARI,
        'servis_kanallari': SERVIS_KANALLARI,
        'eylemler': {k: {'sinif': v.get('sinif'), 'eylem_versiyonu': v.get('eylem_versiyonu', 1),
                         'zorunlu': sorted(v.get('girdi_semasi', {}).get('required', []))}
                     for k, v in sorted(semalar.items())},
        'kurulum_eylemleri': KURULUM_EYLEMLERI,
        'cekirdek_ekrani': CEKIRDEK_EKRANI,
        'mavi_yaka_dugmeleri': MAVI_YAKA_DUGMELERI,
        'hassas_eylemler': HASSAS_EYLEMLER,
        'roller': kodlar.pop('ROL'),
        'sozde_roller': SOZDE_ROLLER,
        'kod_listeleri': {k: sorted(v) for k, v in sorted(kodlar.items())},
        'mavi_yaka_listeleri': MAVI_YAKA_LISTELERI,
        'nesne_turleri': ['BELGE', 'PARCA'],
        'nesne_kapsamlari': ['BIRIM', 'FIRMA'],
        'baglanabilir_turler': ['GOREV', 'IS', 'NESNE', 'PROJE'],
        'bildirim': {'kayit_turleri': ['GOREV', 'IS', 'NESNE', 'PROJE','MODUL'],
                     'alici_turleri': ['BIRIM_YONETICILERI', 'KISI', 'NESNE_SORUMLUSU', 'PROJEDE_YETKILILER', 'ROL'],
                     'onem': ['BILGI', 'UYARI']},
        'cihaz_harf_sirasi': 'TUVWXYZABCDEFGHIJKLMNOPQRS',
        'ayrilmis_kodlar': AYRILMIS_KODLAR,
        'cekirdek_semalari': CEKIRDEK_SEMALARI,
        'izinli_fonksiyonlar': IZINLI_FONKSIYONLAR,
    }


def metin():
    return json.dumps(katalog(), ensure_ascii=False, indent=1, sort_keys=False) + '\n'


if __name__ == '__main__':
    sys.path.insert(0,str(KOK))
    yeni = metin()
    if '--denetle' in sys.argv:
        guncel = CIKTI.exists() and CIKTI.read_text('utf-8') == yeni
        print('katalog güncel' if guncel else 'katalog eski: katalog_uret.py ile yeniden üret')
        sys.exit(0 if guncel else 1)
    CIKTI.write_text(yeni, 'utf-8')
    print(f'yazıldı: {CIKTI.name} ({len(json.loads(yeni)["okumalar"])} okuma, '
          f'{len(json.loads(yeni)["eylemler"])} eylem)')
