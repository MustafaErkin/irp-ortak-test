"""Modül sözleşmesi paketini üretir: onboarding/irp_sozlesme/ ve onboarding/irp_sozlesme.zip.

Paket, modül yazan ekibin kendi çalışma klasörüne koyduğu salt okunur klasördür (T18, karar 131).
İçeriği elle değiştirilmez; kaynaklardan bu betikle üretilir:
- modul_kiti/paket/          elle yazılan kısım: talimatlar, bağlantı katmanı, sahte bulut, araçlar, örnek, testler
- referans/cevap_anahtari/   çekirdeğin simülatörü (model, yurut.py) ve örnek firma (M3S04'ün ilk 50 adımı)
- modul_kiti/                künye denetleyicisi, katalog, şema, örnek künyeler
- onboarding/cekirdek_paketi/, tasarim/   ayrıntı için kaynak belgeler

Koşmak: python3 -I -B modul_kiti/paket_uret.py
"""
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

KOK = Path(__file__).resolve().parents[1]
KIT = KOK / 'modul_kiti'
CA = KOK / 'referans' / 'cevap_anahtari'
HEDEF = KOK / 'onboarding' / 'irp_sozlesme'
SURUM = '1.2'
CEKIRDEK = '10.2'


METIN = {'.py', '.md', '.json', '.sql', '.txt'}


def kopyala(kaynak, hedef):
    """Metin dosyalarında satır sonu LF olur (depo da öyle saklar; .gitattributes). Böylece BUTUNLUK.json'daki
    özetler her bilgisayarda tutar; çalışma kopyasında CRLF kalmış bir kaynak paketi bozmaz."""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if kaynak.suffix in METIN:
        hedef.write_bytes(kaynak.read_bytes().replace(b'\r\n', b'\n'))
    else:
        shutil.copy2(kaynak, hedef)


def agac_kopyala(kaynak, hedef):
    for p in sorted(kaynak.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            kopyala(p, hedef / p.relative_to(kaynak))


def ornek_firma():
    girdi = json.loads((CA / 'modul_sozlesmeleri' / 'modul3' / 'M3S04_modul_bildirimi.girdi.json').read_text('utf-8'))
    depo = girdi['depolar'][0]
    adimlar = depo['adimlar'][:50]
    assert not any(isinstance((a.get('args') or [None])[0], dict) and a['args'][0].get('eylem_kodu') == 'MODUL.TANIMLADIM'
                   for a in adimlar)
    son = adimlar[-1]['saat']
    return {'bicim_surumu': girdi['bicim_surumu'], 'senaryo': 'ornek_firma', 'cihaz_denemeleri': [],
            'saf_sorgular': [], 'depolar': [{'baslangic': depo['baslangic'], 'adimlar': adimlar,
                                             'son_saat': son, 'yontem': depo.get('yontem', 'kapsamli')}]}


def firma_belgesi(girdi):
    """Örnek firmanın kişileri, birimleri, projeleri: modül yazarı kimi hangi rolle denediğini bilsin."""
    sys.path.insert(0, str(CA))
    sys.path.insert(0, str(CA / 'model'))
    import importlib.util
    spec = importlib.util.spec_from_file_location('_paket_yurut', CA / 'yurut.py')
    y = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = y
    spec.loader.exec_module(y)
    depolar = []
    y.yurut(json.loads(json.dumps(girdi)), denetim_depolari=depolar)
    d = depolar[0]
    gorunurluk = 'HERKES'
    for a in girdi['depolar'][0]['adimlar']:
        o = (a.get('args') or [{}])[0]
        if isinstance(o, dict) and o.get('eylem_kodu') == 'AYAR.DEGISTIRDIM' \
                and o['girdiler'].get('anahtar') == 'proje_gorunurlugu':
            gorunurluk = o['girdiler'].get('deger')
    s = [f'# Örnek firma (simülatörün zemini)',
         '',
         f'*Üretildi: `modul_kiti/paket_uret.py` · çekirdek {CEKIRDEK} · Sentetik veri. Simülatör bu firmayla açılır; '
         f'sonra modülün künyesinden kurulum olayları yetkili K001 adına yazılır.*',
         '',
         f'- **Saat:** Zemin {d.saat.simdi().isoformat()} anında biter. Kurulum bir dakika sonra başlar.',
         f'- **Proje görünürlüğü:** `{gorunurluk}`. "UYELER": bir kişi yalnızca ekibinde olduğu projeyi görür (T9 › 6).',
         '- **Şifre:** Simülatörde ve yerel sahte bulutta şifre denetlenmez.',
         '', '## Kişiler', '', '| Kod | Ad | Birim | Yaka | Roller |', '|---|---|---|---|---|']
    for k, p in sorted(d.kisiler.items()):
        s.append(f'| {k} | {p["ad"]} | {p["birim"]} | {p["yaka"]} | {", ".join(p.get("roller", []))} |')
    s += ['', '## Birimler', '', '| Kod | Ad | Üst birim | Başı |', '|---|---|---|---|']
    for k, b in sorted(d.birimler.items()):
        s.append(f'| {k} | {b.get("ad", "")} | {b.get("ust_birim") or "—"} | {b.get("basi") or "—"} |')
    s += ['', '## Projeler', '', '| Kimlik | Kod | Ad | Sorumlu |', '|---|---|---|---|']
    for k, p in sorted(d.projeler.items()):
        s.append(f'| {k} | {p.get("kod", k)} | {p.get("ad", "")} | {p.get("sorumlu") or "—"} |')
    s += ['', '## Tezgâhlar', '', '| Kod | Birim |', '|---|---|']
    for k, t in sorted(d.tezgahlar.items()):
        s.append(f'| {k} | {t.get("birim", "")} |')
    s += ['', '## Nesne türleri', '']
    for k, t in d.nesne_turleri.items():
        asama = ' → '.join((a['kod'] if isinstance(a, dict) else a) for a in t['asamalar'])
        s.append(f'- **{k}** ({t.get("ad", "")}): {asama}')
    return '\n'.join(s) + '\n'


def uret(HEDEF=HEDEF, zip_yaz=True):
    if HEDEF.exists():
        if not (HEDEF / 'BUTUNLUK.json').exists():
            raise SystemExit(f'{HEDEF} üretilmiş bir paket değil; dokunmuyorum')
        shutil.rmtree(HEDEF)
    agac_kopyala(KIT / 'paket', HEDEF)
    # Yapay zekâ talimatı kaynakta başka adla durur; bizim depoda çalışan Claude ve Codex onu kendine almasın.
    talimat = HEDEF / '_yz_talimati.md'
    for ad in ('CLAUDE.md', 'AGENTS.md'):
        kopyala(talimat, HEDEF / ad)
    talimat.unlink()
    sim = HEDEF / 'simulator'
    for ad in ('yurut.py', 'uyum_v8.py', 'karsilastir.py', 'KULLANIM.md', 'olay_semasi.json',
               'modul_bildirimi_semasi.json'):
        kopyala(CA / ad, sim / ad)
    agac_kopyala(CA / 'model', sim / 'model')
    girdi = ornek_firma()
    (sim / 'ornek_firma.girdi.json').write_text(json.dumps(girdi, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    (sim / 'ornek_firma.md').write_text(firma_belgesi(girdi), 'utf-8')
    for ad in ('kunye_denetle.py', 'cekirdek_katalogu.json', 'kunye_semasi.json'):
        kopyala(KIT / ad, HEDEF / 'arac' / ad)
    for p in sorted((KIT / 'ornekler').iterdir()):
        if p.is_dir():
            agac_kopyala(p, HEDEF / 'ornekler' / 'kunyeler' / p.name)
    kaynak = HEDEF / 'kaynak'
    for ad in ('01_cekirdek.md', '02_modul_sozlesmesi.md', '03_sozluk.md'):
        kopyala(KOK / 'onboarding' / 'cekirdek_paketi' / ad, kaynak / ad)
    for ad in ('16_okumalar.md', '18_modul_sozlesmesi.md'):
        kopyala(KOK / 'tasarim' / ad, kaynak / ad)
    (HEDEF / 'SURUM').write_text(f'paket {SURUM} · çekirdek {CEKIRDEK} · {date.today().isoformat()}\n', 'utf-8')
    ozet = {}
    for p in sorted(HEDEF.rglob('*')):
        if p.is_file() and p.name != 'BUTUNLUK.json':
            ozet[p.relative_to(HEDEF).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    (HEDEF / 'BUTUNLUK.json').write_text(json.dumps({'paket': SURUM, 'cekirdek': CEKIRDEK, 'dosyalar': ozet},
                                                    ensure_ascii=False, indent=1) + '\n', 'utf-8')
    if zip_yaz:
        zip_yolu = HEDEF.with_suffix('.zip')
        with zipfile.ZipFile(zip_yolu, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(HEDEF.rglob('*')):
                if p.is_file():
                    z.write(p, Path('irp_sozlesme') / p.relative_to(HEDEF))
        print(f'Paket {SURUM}: {len(ozet) + 1} dosya → {HEDEF.relative_to(KOK)} ve {zip_yolu.relative_to(KOK)}')
    return HEDEF


if __name__ == '__main__':
    uret()
