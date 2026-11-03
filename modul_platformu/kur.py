"""Denetlenen modülü ileri göçle kurar; çekirdek olayları yetkilinin oturumundan gelir.

Sırlar yalnız süreç belleğinde kalır. Modül, genel veritabanı veya service_role
anahtarını almaz; kendi şemasının dar giriş rolüyle çalışır.
"""
import hashlib
import hmac
import json
import re
import sys

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from .kayit import ROOT

def kimlik(dsn,code):
    """Aynı veritabanı/modül için kararlı dar kimlik; hiçbir değer dosyaya yazılmaz."""
    base=conninfo_to_dict(dsn)
    user=base.get('user','postgres')
    database=base.get('dbname','postgres')
    local=base.get('host','') in ('localhost','127.0.0.1','::1','')
    role='mod_'+code.lower()
    if local and 'test' in database:
        role+='_'+hashlib.sha256(database.encode()).hexdigest()[:8]
    password=hmac.new(dsn.encode(),('irp-modul-v1:'+code).encode(),hashlib.sha256).hexdigest()
    username=role+'.'+user.split('.',1)[1] if not local and '.' in user else role
    return role,{**base,'user':username,'password':password,'connect_timeout':'10'},password

def denetle(row,root=ROOT):
    from modul_kiti.kunye_denetle import klasor_denetle
    manifest,result=klasor_denetle(row['klasor'])
    if manifest!=row['kunye']:
        raise ValueError('Denetlenen künye çalışma tanımıyla farklı.')
    # Denetleyici Sonuc nesnesinin hata listesi dışarıya ham SQL/sır taşımaz.
    if result.hatalar:
        raise ValueError('Modül künye/göç denetimi geçmedi.')
    return result

def kur(dsn,row,olay_gonder,modul_hali,root=ROOT):
    """Önce güvenli şema/göç, sonra normal yetkili olayları, en son etkinleştirme."""
    from modul_kiti.kunye_denetle import kurulum_olaylari,kayit_denetle
    denetle(row,root)
    code=row['kod']; manifest=row['kunye']; schema=manifest['veritabani']['sema']
    role,credentials,password=kimlik(dsn,code)
    schema_role=role+'_sahibi'
    migrations=sorted((row['klasor']/'veritabani').glob('[0-9][0-9][0-9]_*.sql'))
    applied=0
    with psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as c:
        c.execute('SELECT pg_advisory_lock(202627,hashtext(%s))',(code,))
        others=[r[0] for r in c.execute('SELECT kunye FROM eklenti.kurulumlar WHERE kod<>%s',(code,)).fetchall()]
        if kayit_denetle([*others,manifest]).hatalar:
            raise ValueError('Modül diğer kurulumlarla çakışıyor veya bağımlılığı eksik.')
        old=c.execute('SELECT ozet,etkin FROM eklenti.kurulumlar WHERE kod=%s',(code,)).fetchone()
        state=modul_hali(code)
        same=bool(old and old[0]==row['ozet'] and old[1] and state and state.get('aktif'))
        with c.transaction():
            c.execute('SELECT pg_advisory_xact_lock(202627,1)')
            exists=c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
            if not exists:
                c.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 8 PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
            else:
                # Başka uygulamanın rolünü devralma; yalnız bu kurulumun rolü güncellenebilir.
                owner=c.execute('SELECT kod FROM eklenti.kurulumlar WHERE rol=%s',(role,)).fetchone()
                if not owner or owner[0]!=code:
                    raise ValueError('Modül rolü başka kuruluma ait; değiştirilmedi.')
                c.execute(sql.SQL('ALTER ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
            owner_exists=c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(schema_role,)).fetchone()
            if owner_exists and not old:
                raise ValueError('Modül sahip rolü başka kuruluma ait; değiştirilmedi.')
            if not owner_exists:
                c.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION').format(sql.Identifier(schema_role)))
            admin=c.execute('SELECT current_user').fetchone()[0]
            c.execute(sql.SQL('GRANT {},{} TO {}').format(sql.Identifier(role),sql.Identifier(schema_role),sql.Identifier(admin)))
            c.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}').format(sql.Identifier(schema),sql.Identifier(schema_role)))
            schema_owner=c.execute('SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s',(schema,)).fetchone()[0]
            if schema_owner==role and old:
                # İlk pilotun tek rolünü veri silmeden T18'in sahip/giriş ayrımına yükselt.
                c.execute(sql.SQL('REASSIGN OWNED BY {} TO {}').format(sql.Identifier(role),sql.Identifier(schema_role)))
            elif schema_owner!=schema_role:
                raise ValueError('Modül şemasının sahibi farklı; değiştirilmedi.')
            web={key:row[key] for key in ('ad','yol','ekran','kimler')}
            c.execute('INSERT INTO eklenti.kurulumlar(kod,rol,kunye,ozet,surum,etkin,web) VALUES(%s,%s,%s::jsonb,%s,%s,false,%s::jsonb) '
                      'ON CONFLICT(kod) DO UPDATE SET rol=excluded.rol,kunye=excluded.kunye,ozet=excluded.ozet,surum=excluded.surum,web=excluded.web,etkin=false',
                      (code,role,json.dumps(manifest),row['ozet'],manifest['surum'],json.dumps(web)))
            for p in migrations:
                digest=hashlib.sha256(p.read_bytes()).hexdigest()
                prev=c.execute('SELECT ozet FROM eklenti.gocler WHERE kod=%s AND ad=%s',(code,p.name)).fetchone()
                if prev:
                    if prev[0]!=digest:raise ValueError('Uygulanmış modül göçü değişmiş: '+p.name)
                    continue
                c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(schema_role)))
                c.execute('ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC')
                c.execute(p.read_text())
                c.execute('RESET ROLE')
                c.execute('INSERT INTO eklenti.gocler VALUES(%s,%s,%s)',(code,p.name,digest));applied+=1
            c.execute(sql.SQL('GRANT EXECUTE ON FUNCTION public.servis_oku(text,text,jsonb),public.modul_bildirimi_birak(jsonb),public.modul_bildirimi_kaldir(jsonb),public.simdi() TO {},{}').format(sql.Identifier(role),sql.Identifier(schema_role)))
            c.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {},{}').format(sql.Identifier(role),sql.Identifier(schema_role)))
            c.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
            c.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
            c.execute(sql.SQL('GRANT USAGE,SELECT,UPDATE ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
            c.execute(sql.SQL('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
            c.execute(sql.SQL('ALTER ROLE {} SET search_path TO {},pg_catalog').format(sql.Identifier(role),sql.Identifier(schema)))
            c.execute(sql.SQL("ALTER ROLE {} SET statement_timeout TO '15s'").format(sql.Identifier(role)))
            c.execute(sql.SQL("ALTER ROLE {} SET lock_timeout TO '3s'").format(sql.Identifier(role)))
        if not same:
            approved=row.get('onayli_yetki_onerileri',[])
            for event in kurulum_olaylari(manifest):
                if event['eylem_kodu']=='YETKI.TANIMLADIM' and event['girdiler'] not in approved:
                    continue
                result=olay_gonder(event['eylem_kodu'],event['girdiler'])
                if result.get('sonuc')!='BASARILI':
                    raise ValueError('Modül kurulum olayı kabul edilmedi: '+event['eylem_kodu'])
        c.execute('UPDATE eklenti.kurulumlar SET etkin=true WHERE kod=%s',(code,))
        c.execute("NOTIFY pgrst, 'reload schema'")
    return {'kod':code,'goc':applied,'surum':manifest['surum'],'zaten_kurulu':same}

def kapat(dsn,row,olay_gonder):
    """Kendi açık bildirimlerini temizle, normal yetkili olayıyla pasifleştir; veriyi silme."""
    from modul_kiti.kunye_denetle import pasiflestirme_olaylari
    role,credentials,_=kimlik(dsn,row['kod'])
    with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as m:
        # Kayıtları normal modül kapılarıyla kapatmak için tanımlı hedefler işletim bağlantısında okunur.
        with psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as c:
            targets=c.execute("SELECT DISTINCT hal->>'kural',hal->'kayit' FROM public.modul_bildirimleri WHERE hal->>'kaynak'=%s AND (hal->>'gecerli')::boolean",(row['kod'],)).fetchall()
            for rule,target in targets:
                m.execute('SELECT public.modul_bildirimi_kaldir(%s::jsonb)',(json.dumps({'modul':row['kod'],'kural':rule,'kayit':target,'an':c.execute('SELECT public.simdi()').fetchone()[0].isoformat()}),))
    event=pasiflestirme_olaylari(row['kunye'])[0]
    result=olay_gonder(event['eylem_kodu'],event['girdiler'])
    if result.get('sonuc')!='BASARILI':raise ValueError('Modül kapatma olayı kabul edilmedi.')
    with psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as c:
        c.execute('UPDATE eklenti.kurulumlar SET etkin=false WHERE kod=%s',(row['kod'],))
        c.execute(sql.SQL('ALTER ROLE {} NOLOGIN').format(sql.Identifier(role)))
        c.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename=%s AND pid<>pg_backend_pid()',(role,))
