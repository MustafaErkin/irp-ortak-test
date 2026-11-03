"""Paylaşım klasörünün bütünlüğünü doğrular; ağ, firma veya veritabanı kullanmaz."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent

def denetle(root=ROOT):
    manifest=json.loads((root/'BUTUNLUK.json').read_text(encoding='utf-8'))
    issues=[]
    for name,digest in manifest['dosyalar'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():issues.append('Eksik/geçersiz: '+name)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:issues.append('Değişmiş: '+name)
    for path in root.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc' and path.name!='.DS_Store' and path!=root/'BUTUNLUK.json':
            if path.relative_to(root).as_posix() not in manifest['dosyalar']:issues.append('Paket dışı: '+path.relative_to(root).as_posix())
    return manifest,issues

if __name__=='__main__':
    manifest,issues=denetle()
    for issue in issues:print(issue)
    print('Paket sağlam.' if not issues else 'Paket değişmiş veya eksik.')
    print('Dosya:',len(manifest['dosyalar']),'· SDK:',manifest['sdk_surumu'])
    sys.exit(bool(issues))
