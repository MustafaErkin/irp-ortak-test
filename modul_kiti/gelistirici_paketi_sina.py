"""Paylaşımın bağımsız açılışını sınar; canlı sistem, SQL veya sır kullanmaz.

python3 -I -B modul_kiti/gelistirici_paketi_sina.py [--tarayici]
Mac: bash istemci/mac_derle.sh web --gelistirici-paketi-sina (yalnız bu kontrol; dağıtım yapmaz).
"""
import argparse
import functools
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import zipfile

HERE = Path(__file__).resolve().parent
KOK = HERE.parent
spec = importlib.util.spec_from_file_location('paylasim_uret', HERE / 'gelistirici_paketi_uret.py')
paket = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paket)


def komut(*args, cwd):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError('Komut başarısız: ' + ' '.join(args) + '\n' + result.stdout + result.stderr)
    return result.stdout + result.stderr


def denetle(root):
    paket.butunluk(root)
    sdk = paket.butunluk(root / 'irp_sozlesme')
    assert sdk == paket.butunluk(paket.SDK), 'SDK sürümü veya baytları farklı'
    for name in paket.ORTAK:
        assert (root / 'arayuz/ortak' / name).read_bytes() == (KOK / 'istemci/web' / name).read_bytes()
    for source in paket.dosyalar(KOK / 'moduller/M11B'):
        assert (root / 'ornekler/M11B' / source.relative_to(KOK / 'moduller/M11B')).read_bytes() == source.read_bytes()
    feedback = paket.oku(root / 'durum/geri_bildirimler.json')
    expected = {f'{module}-{i:02d}' for module, count in (('M10', 6), ('M11A', 9), ('M11B', 10)) for i in range(1, count+1)}
    assert len(feedback['istekler']) == 25 and {x['kod'] for x in feedback['istekler']} == expected
    assert len(feedback['is_paketleri']) == 12 and not feedback['modul_kabul_edildi']
    assert all(not x['istek_karsilandi'] for x in feedback['istekler'])
    caps = paket.oku(root / 'durum/cekirdek_durumu.json')
    assert len(caps['yetenekler']) == 27 and caps['son_urun_sql_gocu'] == 154
    assert (root / 'ortak_api/modul_platformu/dosya_api.py').read_bytes() == (KOK / 'modul_platformu/dosya_api.py').read_bytes()
    version = paket.oku(root / 'SURUM.json')
    assert version['gelistirici_paketi_surumu'] == '2.0' and version['ilk_cikti'] == 'GELISTIRME_TALIMATI.md'
    assert sdk['paket'] == '1.2' and version['ornek_M11B_surumu'] == '0.1.2'
    # Yeni belgelerin bütün bağlantıları paket içinde çözülür. SDK'nın tarihsel kaynakları aynen korunur.
    for source in paket.dosyalar(HERE / 'paylasim_kaynagi'):
        if source.suffix == '.md' and source.name != '_yz_talimati.md':
            doc = root / source.relative_to(HERE / 'paylasim_kaynagi')
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', doc.read_text('utf-8')):
                if link.startswith(('http:', 'https:', '#')):
                    continue
                dest = (doc.parent / link.split('#', 1)[0]).resolve()
                assert dest.is_relative_to(root.resolve()) and dest.exists(), f'Kırık bağlantı: {doc.name}: {link}'
    patterns = (rb'sb_(?:secret|publishable)_[A-Za-z0-9_-]{16,}',
                rb'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}',
                rb'-----BEGIN .*PRIVATE KEY-----')
    for path in paket.dosyalar(root):
        assert path.name not in ('ayar.json', '.env') and path.suffix not in ('.pem', '.key')
        assert not any(re.search(p, path.read_bytes()) for p in patterns), 'Anahtar benzeri içerik: ' + str(path.relative_to(root))
    komut(sys.executable, '-I', '-B', 'KONTROL.py', cwd=root)
    komut(sys.executable, '-I', '-B', 'irp_sozlesme/arac/paket_denetle.py', cwd=root)
    sdk_result = komut(sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', 'irp_sozlesme/testler', cwd=root)
    assert re.search(r'Ran \d+ tests?', sdk_result) and '\nOK' in sdk_result, sdk_result
    print('Çıkarılmış genel paket 2.0: bütünlük, aynı SDK 1.2/kod, 25 başvuru, 27 yetenek, yeni modül şablonları, belge bağlantıları ve SDK testleri geçti.', flush=True)


def tarayici(root):
    sys.path.insert(0, str(KOK / 'istemci/web/test'))
    from tarayici import Browser, StaticHandler, StaticServer
    server = StaticServer(('127.0.0.1', 0), functools.partial(StaticHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    browser = None
    try:
        browser = Browser()
        browser.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])
        browser.navigate('http://127.0.0.1:' + str(server.server_port) + '/arayuz/')
        browser.wait("document.querySelectorAll('#module-preview tbody tr').length===2")
        assert browser.js('getComputedStyle(document.body).backgroundColor') == 'rgb(255, 255, 255)'
        assert browser.js('getComputedStyle(document.documentElement).colorScheme') == 'light'
        assert browser.js('document.documentElement.scrollWidth<=innerWidth+1')
        assert browser.js("!document.body.innerText.includes('K004') && !document.body.innerText.includes('DEMO-01')")
        browser.js("document.querySelector('[data-ornek-not]').value='<Taslak & Not>';document.querySelector('[data-ornek-not]').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#preview-refresh').click()")
        browser.wait("document.querySelector('[data-ornek-not]')?.value==='<Taslak & Not>'")
        browser.js("document.querySelector('#preview-project').value='DEMO-02';document.querySelector('#preview-project').dispatchEvent(new Event('change'))")
        browser.wait("document.querySelector('#module-preview h2')?.textContent==='Örnek Paketleme Makinesi'")
        assert browser.js("document.querySelector('[data-ornek-not]').value===''"), 'Projeler arası taslak sızıntısı'
        browser.js("document.querySelector('#preview-project').value='DEMO-01';document.querySelector('#preview-project').dispatchEvent(new Event('change'))")
        browser.wait("document.querySelector('[data-ornek-not]')?.value==='<Taslak & Not>'")
        browser.js("document.querySelector('[data-ornek-islem=ayrinti]').click()")
        browser.wait("document.querySelector('dialog')?.open")
        browser.js("document.querySelector('#preview-remount').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('[data-ornek-not]')?.value===''")
        for mode, marker in (('empty', 'Henüz Etap Yok'), ('error', 'bilgiler alınamadı')):
            browser.js("document.querySelector('#preview-mode').value=" + json.dumps(mode) + ";document.querySelector('#preview-mode').dispatchEvent(new Event('change'))")
            browser.wait('document.querySelector("#module-preview").innerText.includes(' + json.dumps(marker) + ')')
        browser.js("document.querySelector('#preview-mode').value='normal';document.querySelector('#preview-mode').dispatchEvent(new Event('change'))")
        browser.wait("document.querySelectorAll('#module-preview tbody tr').length===2")
        browser.screenshot(KOK / 'codex/sonuclar/modul_gelistirici_paketi_onizleme.png')
        assert not browser.errors, '\n'.join(browser.errors)
        assert not browser.network_errors, str(browser.network_errors)
        print('Tarayıcı: sabit beyaz tema, tablo/pencere, boş/hata, yenilemede taslak, proje ayrılığı ve kapatma geçti.', flush=True)
    finally:
        if browser:
            browser.close()
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tarayici', action='store_true')
    args = parser.parse_args()
    root = paket.uret()
    with tempfile.TemporaryDirectory(prefix='irp-paylasim-') as temp:
        with zipfile.ZipFile(root.with_suffix('.zip')) as archive:
            assert all(Path(n).parts[0] == root.name and '..' not in Path(n).parts for n in archive.namelist())
            archive.extractall(temp)
        extracted = Path(temp) / root.name
        denetle(extracted)
        if args.tarayici:
            tarayici(extracted)
    print('Paylaşım klasörü ve ZIP doğrulandı. Canlı sistem değiştirilmedi.', flush=True)


if __name__ == '__main__':
    main()
