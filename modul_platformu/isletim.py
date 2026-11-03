"""Yetkili kullanıcının normal oturumuyla modül kurulumu; anahtar/sırlar yazdırılmaz."""
from datetime import datetime,timedelta
import json
import os
from pathlib import Path
import re
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    __package__='modul_platformu'

from .gecit import http
from .kayit import ROOT,oku
from .kur import kur,kapat,kimlik

class Yetkili:
    def __init__(self,env,token,person):
        self.env=env;self.token=token;self.person=person;self.last=None
        # DDL yetkisi kullanılmadan önce gerçek kullanıcı yetkisi doğrulanır.
        self.rpc('oku',{'veri':'WEB_FIRMA','hedef':None,'g':{}})
        self.device='WEB-MODUL-KURULUM-'+person
        self.letter=self.rpc('cihaz_kaydol',{'cihaz':self.device})

    def rpc(self,name,body):
        code,_,data=http(self.env['IRP_SB_TEST_URL'].rstrip('/')+'/rest/v1/rpc/'+name,value=body,
             headers={'Content-Type':'application/json','apikey':self.env['IRP_SB_TEST_ANON'],'Authorization':'Bearer '+self.token})
        if code!=200:raise ValueError('Yetkili işlemi kabul edilmedi.')
        return json.loads(data)

    def modul(self,code):
        rows=self.rpc('oku',{'veri':'WEB_FIRMA','hedef':None,'g':{}})['deger']['moduller']
        return rows.get(code) if isinstance(rows,dict) else next((r for r in rows if r['kod']==code),None)

    def event(self,action,inputs,targets=()):
        now=self.rpc('simdi',{});at=datetime.fromisoformat(now)
        if self.last is not None and at<=self.last:at=self.last+timedelta(microseconds=1)
        self.last=at;now=at.isoformat();day=at.strftime('%y%m%d')
        ids=self.rpc('oku',{'veri':'BUGUNKU_KIMLIKLER','hedef':self.letter,'g':{}})['deger']
        serial=1+max((int(v.split('-')[1][6:]) for v in ids if v.startswith(self.person+'-'+day)),default=0)
        targets=list(targets)
        if action=='MODUL.TANIMLADIM':
            old=self.modul(inputs['kod'])
            if old and old.get('surum'):targets=[{'tur':'MODUL','kimlik':inputs['kod'],'surum':old['surum']}]
        event={'olay_kimligi':f'{self.person}-{day}{serial:04d}-{self.letter}',
          'kim':self.person,'adina':None,'eylem_kodu':action,'eylem_versiyonu':1,'girdiler':inputs,
          'oldugu_an':now,'bildigi_son_hal_ani':now,'pc_ulasma_ani':None,'saat_dilimi':'+03:00',
          'cihaz':self.device,'giris_sekli':'LISTE','yol':'DISARIDA','kanit':[],
          'neyin_ustunde':targets,'duzelttigi_olay':None,'uygulama_surumu':'WEB-1.1.0'}
        return self.rpc('olay_ekle',{'olay':event,'hassas_ek':None})

def main(env=None,config_path=None):
    env=os.environ if env is None else env
    path=Path(config_path or Path.home()/'irp_gosteri/web/ayar.json')
    config=json.loads(path.read_text())
    person=next((r for r in config.get('gosteri_kisileri',[]) if r['kod']=='K001'),None)
    if not person:raise ValueError('Yetkili kurulum oturumu bulunamadı.')
    status,_,body=http(env['IRP_SB_TEST_URL'].rstrip('/')+'/auth/v1/token?grant_type=password',
       value={'email':person['kod'].lower()+'@calisan.irp','password':person['sifre']},
       headers={'Content-Type':'application/json','apikey':env['IRP_SB_TEST_ANON']})
    if status!=200:raise ValueError('Yetkili kurulum girişi yapılamadı.')
    actor=Yetkili(env,json.loads(body)['access_token'],person['kod'])
    results=[]
    for row in oku().values():
        if row.get('etkin'):
            results.append(kur(env['IRP_SB_TEST_DB'],row,actor.event,actor.modul))
            import psycopg
            role,credentials,_=kimlik(env['IRP_SB_TEST_DB'],row['kod'])
            with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as c:
                if c.execute('SELECT session_user=%s',(role,)).fetchone()[0] is not True:
                    raise ValueError('Dar servis giriş rolü doğrulanamadı.')
                if 'PROJE' in row['kunye']['kapilar']['servis_okumalari']:
                    projects=actor.rpc('oku',{'veri':'PROJELER','hedef':None,'g':{}})['deger']
                    target=projects[0]['kimlik'] if projects else None
                    value=c.execute('SELECT public.servis_oku(%s,%s,%s::jsonb)',('PROJE',target,'{}')).fetchone()[0]['deger']
                    if value and 'musteri' in value:raise ValueError('Servis alan sınırı doğrulanamadı.')
                try:
                    c.execute('SELECT * FROM public.olaylar LIMIT 1')
                except psycopg.errors.InsufficientPrivilege:pass
                else:raise ValueError('Dar rolün çekirdek tablo sınırı doğrulanamadı.')
    print('Modül kurulumu tamamlandı; mevcut işler korundu. Modül:',len(results),flush=True)
    print('Gerçek modül giriş rolü, servis okuması ve ham çekirdek tablo engeli doğrulandı.',flush=True)
    report=ROOT/'codex/sonuclar/modul_canli_kurulum.json'
    report.write_text(json.dumps({'durum':'GECTI','moduller':results,
        'kontroller':['gercek_giris_rolu','dar_servis_okumasi','ham_cekirdek_tablosu_reddedildi'],
        'is_verisi_sifirlandi':False},ensure_ascii=False,indent=1)+'\n')
    return results

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('Modül kurulumu tamamlanamadı ('+type(e).__name__+'). Sırlar yazdırılmadı.')
        raise SystemExit(1)
