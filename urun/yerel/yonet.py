"""Hizmet kurmadan kullanıcı klasöründe PostgreSQL 17: kur/baslat/durdur/durum."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import winreg
import zipfile

KOK = Path(os.environ['LOCALAPPDATA']) / 'irp_pg'
BIN = KOK / 'pgsql/bin'
VERI = KOK / 'veri17'
SURUM = '17.6-1'
URL = f'https://get.enterprisedb.com/postgresql/postgresql-{SURUM}-windows-x64-binaries.zip'
DSN = 'postgresql://postgres@localhost:5433/irp_test'


def calistir(ad, *args, kontrol=True):
    # pg_ctl'nin başlattığı sunucu boru tutamacını miras alabilir; dosya EOF bekletmez.
    with tempfile.TemporaryFile() as cikti:
        sonuc = subprocess.run([str(BIN / (ad + '.exe')), *map(str, args)],
                               stdout=cikti, stderr=cikti, creationflags=subprocess.CREATE_NO_WINDOW)
        cikti.seek(0)
        print(cikti.read().decode('utf-8', errors='replace'), end='', flush=True)
    if kontrol:
        sonuc.check_returncode()
    return sonuc


def kur():
    KOK.mkdir(parents=True, exist_ok=True)
    if not (BIN / 'postgres.exe').exists():
        arsiv = KOK / f'postgresql-{SURUM}.zip'
        if not arsiv.exists():
            parcali = arsiv.with_suffix('.indirme')
            print('EDB PostgreSQL ikilileri indiriliyor: ' + URL, flush=True)
            with urllib.request.urlopen(URL, timeout=60) as cevap, parcali.open('wb') as dosya:
                while veri := cevap.read(1024 * 1024):
                    dosya.write(veri)
            parcali.replace(arsiv)
        with zipfile.ZipFile(arsiv) as paket:
            for ad in paket.namelist():
                if not (KOK / ad).resolve().is_relative_to(KOK.resolve()):
                    raise RuntimeError('Arşiv hedef klasörünün dışına çıkıyor')
            paket.extractall(KOK)
        (KOK / 'indirme.json').write_text(json.dumps({'url': URL, 'sha256': hashlib.file_digest(arsiv.open('rb'), 'sha256').hexdigest()}, indent=2), encoding='utf-8')
    calistir('postgres', '--version')
    if not (VERI / 'PG_VERSION').exists():
        calistir('initdb', '-D', VERI, '-U', 'postgres', '--auth=trust', '--encoding=UTF8',
                 '--locale=English_United States.1252', '--locale-provider=icu', '--icu-locale=en-US')
        with (VERI / 'postgresql.conf').open('a', encoding='utf-8') as f:
            f.write("\n# IRP: yalnız yerel sentetik test verisi\nlisten_addresses = 'localhost'\nport = 5433\ntimezone = 'Europe/Istanbul'\n")
    baslat()
    sonuc = subprocess.run([str(BIN / 'psql.exe'), '-h', 'localhost', '-p', '5433', '-U', 'postgres',
                             '-d', 'postgres', '-Atc', "SELECT 1 FROM pg_database WHERE datname='irp_test'"],
                            capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if sonuc.stdout.strip() != '1':
        calistir('createdb', '-h', 'localhost', '-p', '5433', '-U', 'postgres', 'irp_test')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Environment') as reg:
        winreg.SetValueEx(reg, 'IRP_TEST_DB', 0, winreg.REG_SZ, DSN)
    print('Kullanıcı ortam değişkeni IRP_TEST_DB yerel irp_test için ayarlandı.', flush=True)


def baslat():
    if calistir('pg_ctl', '-D', VERI, 'status', kontrol=False).returncode:
        calistir('pg_ctl', '-D', VERI, '-l', KOK / 'postgresql.log', '-w', 'start')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('islem', choices=('kur', 'baslat', 'durdur', 'durum'))
    args = p.parse_args()
    if args.islem == 'kur':
        kur()
    elif args.islem == 'baslat':
        baslat()
    elif args.islem == 'durdur':
        calistir('pg_ctl', '-D', VERI, '-m', 'fast', '-w', 'stop')
    else:
        raise SystemExit(calistir('pg_ctl', '-D', VERI, 'status', kontrol=False).returncode)
