"""Arkadaşın geliştiren yapay zekâsı için çevrimdışı, sürümlü paylaşım klasörü.

Kaynak: genel geliştirme standardı, SDK 1.2, gerçek web yardımcıları, güncel M11B örneği.
Canlı ayar/veri, depo geçmişi ve sır klasörleri okunmaz. SDK yeniden yazılmaz.
Çalıştırma: python3 -I -B modul_kiti/gelistirici_paketi_uret.py
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

KOK = Path(__file__).resolve().parents[1]
KAYNAK = KOK / 'modul_kiti/paylasim_kaynagi'
SDK = KOK / 'onboarding/irp_sozlesme'
HEDEF = KOK / 'onboarding/modul_gelistirici_paketi_v2'
KIMLIK = 'sibernetik-modul-gelistirici-paketi'
SURUM = '2.0'
ORTAK = ('styles.css', 'erp.css', 'ui.js', 'presentation.js', 'actions.js', 'modul_ui.js')


def oku(path):
    return json.loads(path.read_text('utf-8'))


def yaz(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dosyalar(root):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Paylaşım kaynağında simgesel bağ olamaz: ' + str(path.relative_to(root)))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc' and path.name != '.DS_Store':
            yield path


def butunluk(root):
    manifest = oku(root / 'BUTUNLUK.json')
    expected = manifest['dosyalar']
    actual = {p.relative_to(root).as_posix(): sha(p) for p in dosyalar(root)
              if p != root / 'BUTUNLUK.json'}
    if expected != actual:
        raise ValueError('Paket değişmiş/eksik/fazla dosyalı; üzerine yazılmadı: ' + str(root))
    return manifest


def kopyala(source, target):
    if source.is_symlink() or not source.is_file():
        raise ValueError('Geçersiz paylaşım kaynağı: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def agac(source, target):
    for path in dosyalar(source):
        kopyala(path, target / path.relative_to(source))


def durum_yaz(target, git_commit):
    caps = oku(KOK / 'modul_kiti/cekirdek_yetenekleri.json')
    catalog = oku(KOK / 'modul_kiti/cekirdek_katalogu.json')
    feedback = oku(KOK / 'modul_kiti/istek_degerlendirmeleri.json')
    # Kaynak değişince önce envanter ve bu sürümün anlatımı güncellenmelidir.
    latest_sql = max(int(p.name.split('_', 1)[0]) for p in (KOK / 'urun/veritabani').glob('[0-9]*_*.sql'))
    if latest_sql != 154 or any(sha(KOK / name) != digest for name, digest in caps['kaynak_ozetleri'].items()
                                if name.startswith('urun/veritabani/')):
        raise ValueError('SQL kaynağı değişmiş; önce yetenek envanterini ve paket durumunu güncelle.')
    yaz(target / 'durum/cekirdek_durumu.json', {
        'kaynak_commit': git_commit,
        'uyari': 'Sınırlı kanıt özeti; bütün çekirdeğin veya modüllerin kabulü değildir. 03_CEKIRDEK_DURUMU.md ile oku.',
        'cekirdek_tasarim_surumu': catalog['cekirdek_surumu'],
        'son_urun_sql_gocu': 154,
        'normal_okuma_sayisi': len(catalog['okumalar']),
        'servis_okuma_sayisi': len(catalog['servis_okumalari']),
        'eylem_sayisi': len(catalog['eylemler']),
        'gercek_sql_kaniti_kaynakla_eslesiyor': caps['sql_kaniti_kaynakla_eslesiyor'],
        'modul_pilotu_sql_kaynagiyla_eslesiyor': caps['modul_pilotu_sql_kaynagiyla_eslesiyor'],
        'durum_sayilari': dict(Counter(x['durum'] for x in caps['yetenekler'])),
        'yetenekler': [{k: x[k] for k in ('kod', 'ad', 'durum', 'kapsam', 'okumalar')} for x in caps['yetenekler']],
        'mvp_teknik_kaniti': {
            'kaynak': 'codex/sonuclar/moduller_mvp.json',
            'sha256': sha(KOK / 'codex/sonuclar/moduller_mvp.json'),
            'durum': oku(KOK / 'codex/sonuclar/moduller_mvp.json')['durum'],
            'ortam': 'Ayrı gerçek PostgreSQL ve tarayıcı; mevcut Supabase kurulum/rol okumaları ayrıca doğrulandı.',
            'moduller': oku(KOK / 'codex/sonuclar/moduller_mvp.json')['moduller'],
            'kullanici_kabulu': False,
        },
    })
    # Yalnız paylaşılabilir değerlendirme alanları: özel dosya yolları ve tüm kanıt deposu taşınmaz.
    jobs = ('kod', 'ad', 'sahip', 'oncelik', 'gerekce', 'kabul_olcutleri', 'durum', 'uygulama_notu')
    requests = ('kod', 'baslik', 'sha256', 'sahip', 'isler', 'karar_siniri',
                'istek_karsilandi', 'teknik_durum')
    answers = dict(re.findall(r'^\| (M\w+-\d+) \| (.+) \|$',
                             (KAYNAK / '04_GERI_BILDIRIMLER.md').read_text('utf-8'), re.MULTILINE))
    if set(answers) != {x['kod'] for x in feedback['istekler']}:
        raise ValueError('Güncel geri bildirim tablosu bütün istekleri kapsamıyor.')
    job_states = {x['kod']: x['durum'] for x in feedback['is_paketleri']}
    yaz(target / 'durum/geri_bildirimler.json', {
        'kaynak_commit': git_commit, 'sdk_surumu': feedback['paket_surumu'],
        'uygulama_durumu': feedback['uygulama_durumu'],
        'modul_kabul_edildi': feedback['modul_kabul_edildi'],
        'uyari': 'istek_karsilandi kullanıcı kabulünü ifade eder. Teknik düzeltme veya ilk pilot bunu kendiliğinden true yapmaz.',
        'guncel_cevap_kaynagi': '04_GERI_BILDIRIMLER.md; ilk sınıflandırma tarihsel bağlamdır, güncel eksik/hazır durumu değildir.',
        'is_paketleri': [{k: x[k] for k in jobs if k in x} for x in feedback['is_paketleri']],
        'istekler': [{**{k: x[k] for k in requests if k in x},
                     'ilk_degerlendirme_sinifi': x['degerlendirme'], 'guncel_cevap': answers[x['kod']],
                     'bagli_islerin_durumu': {job: job_states[job] for job in x['isler']}}
                    for x in feedback['istekler']],
    })
    providers = []
    for path in (KOK / 'moduller/M10/kunye.json', KOK / 'moduller/M11A/kunye.json',
                 KOK / 'moduller/M11B/kunye.json'):
        module = oku(path)
        providers.append({k: module[k] for k in ('kod', 'ad', 'surum', 'saglananlar', 'bagimliliklar')})
    yaz(target / 'durum/saglayicilar.json', {
        'uyari': 'Mevcut MVP künyeleridir. M10→M11A→M11B teknik devri sınandı; yeni modülün yanıt/izin/bağımlılık uyumu ayrıca sınanır. Kullanıcı kabulü değildir.',
        'moduller': providers,
    })


def uret(hedef=HEDEF, zip_yaz=True):
    hedef = Path(hedef)
    sdk = butunluk(SDK)
    if hedef.exists():
        if not (hedef / 'SURUM.json').is_file() or oku(hedef / 'SURUM.json').get('kimlik') != KIMLIK:
            raise ValueError('Hedef bizim üretilmiş klasörümüz değil; dokunulmadı: ' + str(hedef))
        butunluk(hedef)  # Yerel not/değişiklik varsa kaybettirme.
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=KOK, text=True).strip()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.gelistirici-paketi-', dir=hedef.parent) as temp:
        stage = Path(temp) / 'paket'
        agac(KAYNAK, stage)
        talimat = stage / '_yz_talimati.md'
        for name in ('AGENTS.md', 'CLAUDE.md'):
            kopyala(talimat, stage / name)
        talimat.unlink()
        agac(SDK, stage / 'irp_sozlesme')
        agac(KOK / 'moduller/M11B', stage / 'ornekler/M11B')
        for name in ORTAK:
            kopyala(KOK / 'istemci/web' / name, stage / 'arayuz/ortak' / name)
        kopyala(KOK / 'modul_platformu/dosya_api.py', stage / 'ortak_api/modul_platformu/dosya_api.py')
        (stage / 'ortak_api/modul_platformu/__init__.py').write_text('', 'utf-8')
        kopyala(KOK / 'codex/sonuclar/modul_ortak_baglanti_ekranlar/plan.png', stage / 'arayuz/proje_planlama_ornegi.png')
        for name in ('GELISTIRME_TALIMATI.md', 'TESLIM.md'):
            kopyala(SDK / 'sablonlar' / name, stage / 'sablonlar' / name)
        lock = (KOK / 'modul_platformu/requirements.lock').read_text('utf-8')
        (stage / 'arayuz/requirements-ornek.txt').write_text(
            '# Python 3.13 ilk çalışan ortam. Önizleme/SDK testleri bunu gerektirmez.\n'
            '# Yalnız ihtiyaç duyulan bağımlılıklar modülün kendi kilidine alınır.\n' + lock.rstrip() +
            '\npsycopg[binary]==3.3.6\n', 'utf-8')
        durum_yaz(stage, commit)
        yaz(stage / 'SURUM.json', {
            'kimlik': KIMLIK, 'gelistirici_paketi_surumu': SURUM,
            'uretildi': datetime.now().astimezone().isoformat(timespec='seconds'),
            'kaynak_commit': commit, 'sdk_surumu': sdk['paket'], 'cekirdek_tasarim_surumu': sdk['cekirdek'],
            'son_urun_sql_gocu': 154, 'amac': 'BUTUN_YENI_MODULLER_ICIN_GELISTIRME_GIRDISI',
            'ilk_cikti': 'GELISTIRME_TALIMATI.md',
            'uyum_raporu': 'Yalnız eski modül güncelleniyorsa kısa fark notu; yeni modül için ön koşul değil.',
            'ornek_M11B_surumu': oku(KOK / 'moduller/M11B/kunye.json')['surum'],
            'kaynaklar': {
                name: sha(KOK / name) for name in (
                    'modul_kiti/cekirdek_yetenekleri.json', 'modul_kiti/istek_degerlendirmeleri.json',
                    'modul_platformu/requirements.lock', 'onboarding/irp_sozlesme/BUTUNLUK.json',
                    *('istemci/web/' + name for name in ORTAK), 'moduller/M11B/kunye.json',
                    'modul_platformu/dosya_api.py', 'codex/sonuclar/moduller_mvp.json')},
        })
        yaz(stage / 'BUTUNLUK.json', {
            'kimlik': KIMLIK, 'paket_surumu': SURUM, 'sdk_surumu': sdk['paket'],
            'dosyalar': {p.relative_to(stage).as_posix(): sha(p) for p in dosyalar(stage)},
        })
        butunluk(stage)
        zip_temp = Path(temp) / 'paket.zip'
        if zip_yaz:
            with zipfile.ZipFile(zip_temp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in dosyalar(stage):
                    archive.write(path, Path(hedef.name) / path.relative_to(stage))
        if hedef.exists():
            shutil.rmtree(hedef)
        stage.rename(hedef)
        if zip_yaz:
            zip_temp.replace(hedef.with_suffix('.zip'))
    print(f'Geliştirici paketi {SURUM} · SDK {sdk["paket"]} · {len(butunluk(hedef)["dosyalar"])+1} dosya → {hedef}')
    return hedef


if __name__ == '__main__':
    uret()
