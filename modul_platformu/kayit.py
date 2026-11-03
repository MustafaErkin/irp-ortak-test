"""Sunucunun güvendiği yerel künye kaydı; istekten dosya/servis adresi alınmaz."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def oku(root=ROOT):
    path=root/'moduller/kayit.json'
    if not path.exists():
        return {}
    result={}
    for row in json.loads(path.read_text())['moduller']:
        code=row['kod']
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,19}',code) or code in result:
            raise ValueError('Modül kodu geçersiz veya yineleniyor.')
        if row['paket']!=code or not re.fullmatch(r'[a-z][\w.]*:[a-zA-Z_]\w*',row['arka_yuz']):
            raise ValueError('Modülün çalışma yolu geçersiz.')
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.js',row['ekran']):
            raise ValueError('Modülün ekran yolu geçersiz.')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,60}',row['yol']) or any(r['yol']==row['yol'] for r in result.values()):
            raise ValueError('Modülün web adresi geçersiz.')
        folder=root/'moduller'/code
        if not folder.resolve().is_relative_to((root/'moduller').resolve()):
            raise ValueError('Modül paket yolu çalışma alanı dışında.')
        manifest=json.loads((folder/'kunye.json').read_text())
        if manifest['kod']!=code or manifest['veritabani']['sema']!='mod_'+code.lower():
            raise ValueError('Künye kodu/şeması çalışma yoluyla uyuşmuyor.')
        if manifest['on_yuz']['tur']!='UYGULAMA_ICI':
            raise ValueError('Modül ekranı ortak web standardını kullanmalı.')
        result[code]={**row,'klasor':folder,'kunye':manifest,
                      'ozet':hashlib.sha256((folder/'kunye.json').read_bytes()).hexdigest()}
    return result
