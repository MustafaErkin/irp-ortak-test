"""Aynı adresteki modül API'leri ve tek bağlantı katmanının güvenilir yönlendirmesi.

Tarayıcıya yalnız normal kullanıcı oturumu gider. Modül servis anahtarı rastgele,
modüle özgü ve yalnız süreç belleğindedir. Gerçek veri izinlerini çekirdek ve
sağlayıcı modül uygular; bu geçit onları genişletmez.
"""
from collections import defaultdict,deque
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs,urlsplit,urlencode

from .kayit import ROOT,oku

class Hata(Exception):
    def __init__(self,status,message):
        self.status,self.message=status,message

def http(url,method='POST',value=None,headers=None,timeout=15,raw=False):
    data=value if raw else None if value is None else json.dumps(value).encode()
    req=urllib.request.Request(url,data=data,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(4*1024*1024+1)
            if len(body)>4*1024*1024:raise Hata(502,'Yanıt sınırı aşıldı.')
            return r.status,dict(r.headers),body
    except urllib.error.HTTPError as e:
        return e.code,dict(e.headers),e.read(128*1024)
    except (OSError,TimeoutError):
        raise Hata(503,'Bağlantı kurulamadı; işlemi yeniden değerlendirin.') from None

class Platform:
    def __init__(self,root=ROOT,env=None,remote=None):
        self.root=root;self.env=dict(os.environ if env is None else env)
        self.rows=oku(root);self.children={};self.secrets={};self.addresses={}
        self.remote=remote or self._core
        self.limits=defaultdict(deque);self.lock=threading.Lock()

    def _core(self,name,body,authorization):
        url=self.env['IRP_SB_TEST_URL'].rstrip('/')+'/rest/v1/rpc/'+name
        code,_,data=http(url,value=body,headers={'Content-Type':'application/json',
             'apikey':self.env['IRP_SB_TEST_ANON'],'Authorization':authorization})
        if code!=200:
            raise Hata(401 if code in (401,403) else 403,'Oturumunuz veya bu işlem için yetkiniz geçerli değil.')
        return json.loads(data)

    def proof(self,authorization,code=None):
        if not authorization.startswith('Bearer ') or len(authorization)<15:
            raise Hata(401,'Çalışma alanına giriş yapın.')
        result=self.remote('modul_oturum',{'modul':code},authorization)
        if not result.get('kisi') or code and not any(r['kod']==code for r in result['moduller']):
            raise Hata(403,'Bu modül devrede değil.')
        return result

    def list(self,authorization):
        result=self.proof(authorization)
        return {'moduller':[r for r in result['moduller'] if r['kod'] in self.addresses],
                'kisi':result['kisi']}

    def start(self,web_port):
        if not self.rows or not self.env.get('IRP_SB_TEST_DB'):return
        import psycopg
        from .kur import kimlik
        with psycopg.connect(self.env['IRP_SB_TEST_DB'],autocommit=True,prepare_threshold=None) as c:
            installed=dict(c.execute('SELECT kod,ozet FROM eklenti.kurulumlar WHERE etkin').fetchall())
        for code,row in self.rows.items():
            if not row.get('etkin') or installed.get(code)!=row['ozet']:continue
            if code in self.children and self.children[code].poll() is None:continue
            _,credentials,_=kimlik(self.env['IRP_SB_TEST_DB'],code)
            with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as c:
                c.execute('SELECT 1')
            secret=secrets.token_urlsafe(32)
            with socket.socket() as s:
                s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            from psycopg.conninfo import make_conninfo
            prefix=row['ortam_oneki']
            # Genel DSN ve servis anahtarı alt sürece miras kalmaz.
            safe={k:self.env[k] for k in ('PATH','LANG','LC_ALL','TMPDIR','SYSTEMROOT','PYTHONIOENCODING') if k in self.env}
            safe.update({'PYTHONPATH':os.pathsep.join((str(self.root),str(self.root/'.runtime/python'),str(self.root/'onboarding'))),
                'IRP_MODUL_KOD':code,'IRP_MODUL_PORT':str(port),'IRP_MODUL_IC_ANAHTAR':secret,
                'IRP_CEKIRDEK':'http','IRP_TABAN':f'http://127.0.0.1:{web_port}/irp/cekirdek/{code}',
                'IRP_ANON':self.env['IRP_SB_TEST_ANON'],'IRP_SERVIS':secret,
                prefix+'_VERITABANI':make_conninfo(**credentials),prefix+'_KUNYE':str(row['klasor']/'kunye.json'),
                prefix+'_KURAL_ARALIGI_DK':'15'})
            process=subprocess.Popen([sys.executable,'-B','-m','modul_platformu.calistir'],cwd=self.root,env=safe,
                      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            self.children[code]=process;self.secrets[code]=secret;self.addresses[code]=f'http://127.0.0.1:{port}'
            until=time.monotonic()+15
            while time.monotonic()<until:
                if process.poll() is not None:raise Hata(503,'Modül arka yüzü başlatılamadı.')
                try:
                    status,_,_=http(self.addresses[code]+'/irp-saglik',method='GET',headers={'X-IRP-Gecit':secret},timeout=1)
                    if status==200:break
                except Hata:pass
                time.sleep(.1)
            else:raise Hata(503,'Modül arka yüzü hazır değil.')

    def close(self):
        for p in self.children.values():
            if p.poll() is None:p.terminate()
        for p in self.children.values():
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        self.children.clear();self.secrets.clear();self.addresses.clear()

    def limit(self,row,person,category):
        maximum=row['kunye'].get('sinirlar',{}).get(category,60)
        with self.lock:
            window=self.limits[(row['kod'],person,category)]
            now=time.monotonic()
            while window and window[0]<now-60:window.popleft()
            if len(window)>=maximum:raise Hata(429,'Çok sayıda işlem var; birazdan yeniden deneyin.')
            window.append(now)

    def api(self,code,path,method,body,authorization):
        row=self.rows.get(code)
        if not row or code not in self.addresses:raise Hata(404,'Modül devrede değil.')
        proof=self.proof(authorization,code)
        if row.get('kimler') and not set(row['kimler']).intersection(proof['roller']):
            raise Hata(403,'Bu çalışma alanı için yetkiniz bulunmuyor.')
        self.limit(row,proof['kisi'],'okuma_dakika')
        if not path.startswith('/api/') or '..' in path or len(path)>2048:raise Hata(400,'Geçersiz işlem yolu.')
        return http(self.addresses[code]+path,method=method,value=body,raw=True,
             headers={'Content-Type':'application/json','Authorization':authorization,'X-IRP-Gecit':self.secrets[code]},timeout=45)

    def service(self,code,name,body):
        import psycopg
        from .kur import kimlik
        if name not in ('servis_oku','modul_bildirimi_birak','modul_bildirimi_kaldir'):raise Hata(403,'Servis bu işlemi yapamaz.')
        _,credentials,_=kimlik(self.env['IRP_SB_TEST_DB'],code)
        with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as c:
            try:
                if name=='servis_oku':
                    return c.execute('SELECT public.servis_oku(%s,%s,%s::jsonb)',
                         (body['veri'],body.get('hedef'),json.dumps(body.get('g') or {}))).fetchone()[0]
                return c.execute('SELECT public.'+name+'(%s::jsonb)',(json.dumps(body['g']),)).fetchone()[0]
            except psycopg.Error as e:
                message=e.diag.message_primary or ''
                if message.startswith('IRP|'):raise Hata(403,message) from None
                raise Hata(503,'IRP|URUN|Servis işlemi tamamlanamadı') from None

    def rpc(self,code,name,body,authorization):
        row=self.rows.get(code)
        if not row or code not in self.secrets:raise Hata(404,'IRP|YETKI|Modul etkin degil')
        token=authorization.removeprefix('Bearer ')
        if secrets.compare_digest(token,self.secrets[code]):
            return self.service(code,name,body)
        if name=='simdi':return self.remote('simdi',{},'Bearer '+self.env['IRP_SB_TEST_ANON'])
        proof=self.proof(authorization,code)
        self.limit(row,proof['kisi'],'okuma_dakika')
        if name in ('modul_dosya_yukle','modul_dosya_oku'):
            from .dosyalar import islem
            return islem(self,row,name,body,authorization)
        if name=='oku':
            veri=body.get('veri','')
            if veri not in row['kunye']['kapilar']['okumalar']:raise Hata(403,'IRP|YETKI|Okuma kunyede yok')
            if '.' in veri:return self.provider(row,veri,body,authorization)
            if (body.get('g') or {}).keys() & {'kim','cagiran','oturum'}:raise Hata(403,'IRP|YETKI|Kullanici degistirilemez')
            return self.remote('oku',body,authorization)
        if name=='olay_ekle':
            event=body.get('olay') or {}
            if event.get('eylem_kodu') not in row['kunye']['kapilar']['olaylar'] or event.get('kim')!=proof['kisi'] \
              or event.get('cihaz')!='MODUL-'+code or not str(event.get('olay_kimligi','')).endswith('-'+row['kunye']['cihaz_harfi']):
                raise Hata(403,'IRP|YETKI|Olay modul sozlesmesine uymuyor')
            return self.remote(name,body,authorization)
        raise Hata(403,'IRP|YETKI|Modul kapisi kapali')

    def provider(self,consumer,veri,body,authorization):
        provider=next((r for r in self.rows.values() if any(p['ad']==veri for p in r['kunye'].get('saglananlar',[]))),None)
        if provider is None or provider['kod'] not in self.addresses:raise Hata(503,'IRP|SAGLAYICI_YOK|Bilgi saglayan modul devrede degil')
        # Önceden denetlenmiş künye bağımlılığı zorunludur; başka modül tablosuna erişilmez.
        dependencies=consumer['kunye'].get('bagimliliklar',[])
        if not any(x.get('modul')==provider['kod'] and veri in x.get('okumalar',[]) for x in dependencies):
            raise Hata(403,'IRP|YETKI|Saglayici bagimliligi kunyede yok')
        self.proof(authorization,provider['kod'])
        params=dict(body.get('g') or {})
        if body.get('hedef') is not None:params.setdefault('proje',body['hedef'])
        declaration=next(p for p in provider['kunye']['saglananlar'] if p['ad']==veri)
        allowed=set(declaration.get('parametreler',[]))
        if set(params)-allowed or any(params.get(k) is None for k in allowed):
            raise Hata(400,'IRP|BICIM|Saglayici parametreleri eksik veya gecersiz')
        status,_,data=http(self.addresses[provider['kod']]+'/api/saglanan/'+veri+'?'+urlencode(params),method='GET',
                    headers={'Authorization':authorization,'X-IRP-Gecit':self.secrets[provider['kod']]})
        if status in (401,403):raise Hata(403,'IRP|YETKI|Saglayici okumasi kabul edilmedi')
        if status==404:raise Hata(404,'IRP|BILGI_YOK|Saglayicida istenen bilgi bulunamadi')
        if status in (400,422):raise Hata(400,'IRP|BICIM|Saglayici sorgusu uygun degil')
        if status!=200:raise Hata(503,'IRP|BAGLANTI|Saglayici yanit vermiyor')
        return {'deger':json.loads(data),'hesap':'GUNCEL'}
