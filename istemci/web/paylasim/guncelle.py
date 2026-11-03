"""Ortak test deposunda web kaynaklarını Pages paketine eşle; motoru dağıtmaz."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / 'istemci/web'
OUT = ROOT / 'docs'


def update():
    if not (OUT / 'assets/core.js').is_file():
        raise SystemExit('İlk paket ve doğrulanmış assets/core.js bulunamadı.')
    for pattern in ('*.js', '*.html', '*.css', 'cekirdek_onkosullari.json'):
        for source in WEB.glob(pattern):
            shutil.copyfile(source, OUT / source.name)
    static = sorted(str(p.relative_to(OUT)) for p in OUT.rglob('*')
                    if p.is_file() and p.suffix in ('.js', '.css', '.html', '.json')
                    and p.name not in ('service_worker.js', 'ayar.json', 'surum.json'))
    digest = hashlib.sha256(b''.join((OUT / p).read_bytes() for p in static)).hexdigest()[:16]
    worker = (WEB / 'service_worker.js').read_text().replace('__BUILD__', digest).replace('__STATIC__', json.dumps(static))
    (OUT / 'service_worker.js').write_text(worker)
    (OUT / '.nojekyll').touch()
    print('Pages paketi hazır. Mevcut derlenmiş Dart köprüsü korundu. SQL/motor dağıtımı yapılmadı.')


if __name__ == '__main__':
    update()
