"""T20: yerel web iş uygulamasını derle. Ayar ve sır dosyası üretmez/kopyalamaz."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def build(target=None):
    out = Path(target) if target else HERE / 'build'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'task_templates.js').unlink(missing_ok=True)
    assets = out / 'assets'
    assets.mkdir(exist_ok=True)
    # SDK'nin kendisi derler; Flutter sarmalayıcısının SDK önbelleğini yazması gerekmez.
    dart = Path.home() / 'development/flutter/bin/cache/dart-sdk/bin/dart'
    config = ROOT / 'istemci/uygulama/.dart_tool/package_config.json'
    if not config.exists():
        raise SystemExit('Önce istemci/uygulama içinde flutter pub get çalıştırılmalı.')
    subprocess.run([str(dart), 'compile', 'js', '--packages=' + str(config), '-O2',
                    '--no-source-maps', '-o', str(assets / 'core.js'), str(HERE / 'kopru.dart')], check=True)
    for pattern in ('*.html', '*.css', '*.js', 'cekirdek_onkosullari.json'):
        for source in HERE.glob(pattern):
            shutil.copyfile(source, out / source.name)
    shutil.copyfile(ROOT / 'referans/eylem_semalari.json', assets / 'eylem_semalari.json')
    shutil.copyfile(ROOT / 'istemci/uygulama/assets/gosterim.json', assets / 'gosterim.json')
    static=sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.suffix in ('.js','.css','.html','.json') and p.name not in ('service_worker.js','flutter_service_worker.js','ayar.json'))
    digest=hashlib.sha256(b''.join((out/p).read_bytes() for p in static)).hexdigest()[:16]
    worker=(HERE/'service_worker.js').read_text().replace('__BUILD__',digest).replace('__STATIC__',__import__('json').dumps(static))
    (out/'service_worker.js').write_text(worker)
    print('Web iş uygulaması hazır:', out)
    print('Tema: sabit beyaz. Motor: mevcut Supabase. İstemci çekirdeği: mevcut Dart paketi.')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hedef')
    build(parser.parse_args().hedef)
