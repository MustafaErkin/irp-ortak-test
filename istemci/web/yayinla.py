"""T20 dağıtımı. Mevcut buluta yalnız ileri göç; firma verisini sıfırlamaz."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
from urllib.parse import unquote, urlparse

ROOT=Path(__file__).resolve().parents[2]
TARGET=Path.home()/'irp_gosteri'


def cloud():
    if str(ROOT) not in sys.path:
        sys.path.insert(0,str(ROOT))
    from urun.kur import kur,supabase_projesi
    dsn=os.environ['IRP_SB_TEST_DB']
    ref=unquote(urlparse(dsn).username or '').split('.',1)[-1]
    supabase_projesi(dsn,ref)
    result=kur(dsn,test=True,bulut=True,proje=ref)
    print('Bulut ileri göçü tamamlandı; firma verisi korundu. Dosya:',result['dosya'],flush=True)


def start():
    result=subprocess.run(['lsof','-nP','-iTCP:8080','-sTCP:LISTEN','-t'],capture_output=True,text=True)
    for pid in set(result.stdout.split()):
        cwd=subprocess.run(['lsof','-a','-p',pid,'-d','cwd','-Fn'],capture_output=True,text=True).stdout
        command=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True).stdout
        if 'n'+str(TARGET)+'\n' not in cwd or 'sunucu.py' not in command:
            raise RuntimeError('8080 portunda başka bir program var; durdurulmadı.')
        os.kill(int(pid),signal.SIGTERM)
    until=time.monotonic()+8
    while time.monotonic()<until:
        r=subprocess.run(['lsof','-nP','-iTCP:8080','-sTCP:LISTEN','-t'],capture_output=True)
        if not r.stdout.strip():
            break
        time.sleep(.1)
    log=Path('/private/tmp/irp-web-server.log')
    fd=os.open(log,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as out:
        process=subprocess.Popen(['/bin/bash',str(TARGET/'baslat.command')],cwd=TARGET,
                                 stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)
    (TARGET/'sunucu.pid').write_text(str(process.pid)+'\n')
    until=time.monotonic()+35
    while time.monotonic()<until:
        try:
            with urllib.request.urlopen('http://localhost:8080/irp/durum',timeout=2) as response:
                data=json.load(response)
            if data.get('surum')=='WEB-20':
                print('Web açık: http://localhost:8080/ | hesap yönetimi:',data['hesap_yonetimi'],flush=True)
                return
        except (OSError,ValueError):
            time.sleep(.2)
    raise RuntimeError('Yerel web sunucusu doğrulanamadı.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bulut',action='store_true')
    parser.add_argument('--calistir',action='store_true')
    args=parser.parse_args()
    try:
        if args.bulut:
            cloud()
        if args.calistir:
            start()
    except Exception as error:
        # Bağlantı hataları DSN veya anahtar içerebilir; ayrıntı basılmaz.
        print('Dağıtım tamamlanamadı ('+type(error).__name__+'). Sırlar yazdırılmadı.',file=sys.stderr)
        raise SystemExit(1)
