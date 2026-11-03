"""Mevcut çalışma ağacını sır ve geçmiş arşiv taşımadan yeni ortak test deposuna al."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEPLOYED = Path.home() / 'irp_gosteri/web'
FOLDERS = {'istemci', 'urun', 'referans', 'moduller', 'modul_platformu', 'modul_kiti'}
SUFFIXES = {'.py','.sql','.js','.mjs','.dart','.html','.css','.json','.md','.yaml','.yml','.toml','.ini','.txt','.sh','.command','.xml','.gradle','.kts','.properties','.lock','.svg','.png','.ttf','.plist','.swift','.kt','.h','.m','.xcworkspacedata','.pbxproj','.xcscheme','.xcconfig','.storyboard','.xib','.entitlements'}


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f'Uyarlama noktası değişmiş: {path.name}')
    path.write_text(text.replace(old, new))


def secret_scan(target):
    # Bilinen özel değerleri yalnız bellekte karşılaştır; değerleri yazdırma.
    private = Path.home() / 'irp_gizli'
    people = json.loads((private / 'gosteri_kisileri.json').read_text())
    secrets = [p['sifre'].encode() for p in people]
    for line in (private / 'supabase.env').read_text().splitlines():
        if '=' not in line or line.startswith('#'): continue
        key, value = line.removeprefix('export ').split('=',1)
        if 'ANON' not in key.upper() and 'URL' not in key.upper():
            value = value.strip().strip('\"\'')
            if len(value) > 12: secrets.append(value.encode())
    hits = []
    for p in target.rglob('*'):
        if p.is_file() and '.git' not in p.parts:
            data = p.read_bytes()
            if any(secret and secret in data for secret in secrets):
                hits.append(str(p.relative_to(target)))
    if hits: raise RuntimeError('Özel değer bulundu; paylaşma: '+', '.join(hits))


def prepare(target):
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise SystemExit('Hedef boş olmalı; mevcut çalışmayı ezmiyorum.')
    target.mkdir(parents=True, exist_ok=True)
    candidates = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    for name in sorted(set(candidates)):
        if not name: continue
        rel = Path(name)
        include = rel.parts[0] in FOLDERS or name.startswith('onboarding/irp_sozlesme/') or name=='onboarding/MODUL_GELISTIRME_KISA.md'
        if not include or rel.suffix not in SUFFIXES: continue
        if any(x in rel.parts for x in ('build','.dart_tool','__pycache__','gecici','.runtime','node_modules','yalitim')): continue
        if rel.name in ('local.properties','ayar.json','google-services.json') or rel.name.startswith('canli.'): continue
        source = ROOT / rel
        if source.is_symlink() or not source.is_file(): continue
        dest = target / rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
    shutil.copyfile(ROOT/'.gitattributes',target/'.gitattributes')
    (target/'.gitignore').write_text((ROOT/'.gitignore').read_text()+'\n# Kişisel erişim ve yerel ayarlar\n**/gosteri_kisileri.json\n**/.env\n**/.env.*\n**/local.properties\n**/ayar.json\n!docs/ayar.json\n')
    web = target/'istemci/web'
    for name in ('erisim.js','erisim.html','erisim_sayfasi.js'):
        shutil.copyfile(HERE/name,web/name)
    app = web/'app.js'
    app.write_text("import {loadSharedConfig} from './erisim.js';\n"+app.read_text())
    app.write_text(app.read_text().replace("validateConfig(await getJSON('ayar.json'))","validateConfig(await loadSharedConfig())"))
    observer = web/'olaylar.js'
    observer.write_text("import {loadSharedConfig} from './erisim.js';\n"+observer.read_text())
    replace_once(observer,"validateConfig(await (await fetch('ayar.json',{cache:'no-store'})).json())","validateConfig(await loadSharedConfig())")
    replace_once(web/'modules.js'," const generation=client.generation,write=", " if(client.config?.ortak_test)throw new UserError('Modüllerin uzaktan bağlantısı bu paylaşımda açık değil. Çekirdek testine devam edebilirsiniz.');\n const generation=client.generation,write=")
    replace_once(web/'pages.js'," async accountAdmin(person,mode){", " async accountAdmin(person,mode){\n  if(this.c.config?.ortak_test)throw new Error('Hesap açma ve şifre sıfırlama bu paylaşımda açık değil. Mustafa’nın verdiği hazır profilleri kullanın.');")
    out = target/'docs'
    out.mkdir()
    # Kaynakta kalan telefon denemesini yeni köprüye derleme. Yerelde çalışan baytlar.
    shutil.copytree(DEPLOYED/'assets',out/'assets',ignore=shutil.ignore_patterns('*.map','*.deps'))
    raw = json.loads((DEPLOYED/'ayar.json').read_text())
    key=raw['supabase_anon']
    public=key.startswith('sb_publishable_')
    if not public:
        payload=key.split('.')[1];public=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4))).get('role')=='anon'
    if not public: raise RuntimeError('Genel bağlantı anahtarı gerekli.')
    config={k:raw[k] for k in ('supabase_url','supabase_anon','senaryo')}
    config['ortak_test']=True
    (out/'ayar.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    runpy.run_path(str(web/'paylasim/guncelle.py'),run_name='__main__')
    manifest={'kaynak_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'calisma_agaci_dahil':True,'dagitim':'mevcut kurulu web; yalnız paylaşım giriş/sınır uyarlaması',
              'core_sha256':hashlib.sha256((out/'assets/core.js').read_bytes()).hexdigest(),
              'motor_gocu_yapildi':False,'dosyalar':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}}
    (out/'surum.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    secret_scan(target)
    print('Kaynaklar ve Pages paketi hazır; bilinen özel değer taraması temiz:',target)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--hedef',required=True)
    prepare(Path(parser.parse_args().hedef))
