"""Numaralı SQL göçlerini ayrı test veritabanına uygula; sırlar kaydedilmez.

Yerel: IRP_TEST_DB, yalnız adında test geçen veritabanı.
Bulut (T19 › 1): --hedef supabase-test --onay <proje kimliği>; adres IRP_SB_TEST_DB'den,
yalnız *.supabase.com havuz adresi ve kimliği --onay ile aynı olan proje.
"""
import argparse
import hashlib
import os
from pathlib import Path
from time import perf_counter
from urllib.parse import unquote, urlparse


def supabase_projesi(dsn, onay):
    """Bulut korumasi: havuz adresi ve kullanıcı adındaki proje kimliği --onay ile aynı olmalı."""
    uri = urlparse(dsn)
    host = (uri.hostname or '').lower()
    if uri.scheme not in ('postgres', 'postgresql') or not host.endswith('.supabase.com'):
        raise ValueError('Bulut kurulumu yalnız *.supabase.com havuz adresine yapılır')
    kullanici = unquote(uri.username or '')
    proje = kullanici.split('.', 1)[1] if kullanici.startswith('postgres.') else ''
    if not proje or proje != onay:
        raise ValueError('Adresteki proje kimliği --onay ile aynı değil')
    return proje


def kur(dsn, sifirdan=False, test=False, bulut=False, proje=None):
    import psycopg
    uri = urlparse(dsn)
    if not bulut and (uri.scheme not in ('postgres', 'postgresql') or 'test' not in unquote(uri.path).lower()):
        raise ValueError('Kurulum yalnız adında test geçen veritabanına uygulanır')
    klasor = Path(__file__).resolve().parent / 'veritabani'
    bas = perf_counter()
    with psycopg.connect(dsn, autocommit=True) as conn:
        if bulut:
            # Supabase'te veritabanının adı her zaman postgres; koruma supabase_projesi'nde.
            conn.execute('SET statement_timeout = 0')
        else:
            with conn.cursor() as cur:
                cur.execute('SELECT current_database()')
                if 'test' not in cur.fetchone()[0].lower():
                    raise ValueError('Sunucunun döndürdüğü veritabanı test değil')
        if uri.hostname in ('localhost', '127.0.0.1', '::1'):
            conn.execute((klasor / 'yerel/000_supabase_taklidi.sql').read_text(encoding='utf-8'))
        if bulut:
            for yol in sorted((klasor / 'supabase_once').glob('[0-9][0-9][0-9]_*.sql')):
                conn.execute(yol.read_text(encoding='utf-8'))
        if sifirdan:
            # Yalnız bu uygulamanın sahibi ve şemaları; başka public nesnesi silinmez.
            conn.execute("""DO $$ DECLARE r record; BEGIN
              IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='irp_sahibi') THEN
                FOR r IN SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                         WHERE n.nspname='public' AND c.relowner='irp_sahibi'::regrole AND c.relkind IN ('r','p') LOOP
                  EXECUTE format('DROP TABLE %I.%I CASCADE',r.nspname,r.relname);
                END LOOP;
                FOR r IN SELECT p.oid::regprocedure::text AS ad FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                         WHERE n.nspname='public' AND p.proowner='irp_sahibi'::regrole LOOP
                  EXECUTE 'DROP FUNCTION '||r.ad||' CASCADE';
                END LOOP;
              END IF;
            END $$""")
            for sema in ('test', 'okuma', 'motor', 'saat', 'kg', 'gorev', 'ana_veri', 'kapi', 'takvim',
                         'k6', 'k7', 'k9', 'k10', 'k10_1', 'k10_2', 'is_', 'liste', 'surum',
                         'zaman', 'yetki_v6', 'yasam_v5', 'kapilar_v3', 'kapilar_v5', 'maliyet_izi_v6', 'irp'):
                conn.execute('DROP SCHEMA IF EXISTS ' + sema + ' CASCADE')
        dosyalar = [p for p in sorted(klasor.glob('[0-9][0-9][0-9]_*.sql')) if test or '_test' not in p.name]
        # Göç içindeki rol ve DDL tek işlemde; yarım uygulanmış göç bırakılmaz.
        for yol in dosyalar:
            sql = yol.read_text(encoding='utf-8')
            ozet = hashlib.sha256(sql.encode()).hexdigest()
            if yol.name != '001_iskelet.sql':
                eski = conn.execute('SELECT ozet FROM irp.gocler WHERE ad=%s', (yol.name,)).fetchone()
                if eski:
                    if eski[0] != ozet:
                        raise ValueError('Uygulanmış göç değişmiş; yeni göç veya --sifirdan gerekli: ' + yol.name)
                    continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute('INSERT INTO irp.gocler(ad,ozet) VALUES(%s,%s) ON CONFLICT(ad) DO NOTHING', (yol.name, ozet))
            print('Uygulandı: ' + yol.name, flush=True)
        if bulut:
            supabase_ekleri(conn, klasor, proje if test else None)
    return {'dosya': len(dosyalar), 'saniye': perf_counter() - bas}


def supabase_ekleri(conn, klasor, test_projesi=None):
    """Yalnız Supabase'te: anlık iletim yayını, kanıt kovası ve kuralları, açık kapıların dökümü.

    test_projesi verilirse (--test): test kapılarının TEST denetimi bu proje kimliğine bağlanır.
    """
    if conn.execute("SELECT to_regclass('public.degisim_sinyalleri') IS NOT NULL").fetchone()[0]:
        if conn.execute("SELECT 1 FROM pg_publication WHERE pubname='supabase_realtime'").fetchone():
            if not conn.execute("SELECT 1 FROM pg_publication_tables WHERE pubname='supabase_realtime' "
                                "AND schemaname='public' AND tablename='degisim_sinyalleri'").fetchone():
                conn.execute('ALTER PUBLICATION supabase_realtime ADD TABLE public.degisim_sinyalleri')
            print('Anlık iletim: degisim_sinyalleri yayında', flush=True)
    if test_projesi:
        conn.execute("INSERT INTO irp.sozluk(ad,hal) VALUES('supabase_test_projesi',to_jsonb(%s::text)) "
                     "ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal", (test_projesi,))
    alt = ['supabase'] + (['supabase_test'] if test_projesi else [])
    for yol in [y for a in alt for y in sorted((klasor / a).glob('[0-9][0-9][0-9]_*.sql'))]:
        with conn.transaction():
            conn.execute(yol.read_text(encoding='utf-8'))
        print('Uygulandı (Supabase): ' + yol.parent.name + '/' + yol.name, flush=True)
    # İstemci rollerine açık kapılar; beklenmeyen bir ad çıkarsa kurulumdan sonra bakılır.
    for rol in ('anon', 'authenticated'):
        adlar = [r[0] for r in conn.execute(
            "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' AND has_function_privilege(%s, p.oid, 'EXECUTE') ORDER BY 1", (rol,))]
        tablolar = [r[0] for r in conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p','v') "
            "AND has_table_privilege(%s, c.oid, 'SELECT') ORDER BY 1", (rol,))]
        print(f'{rol}: kapılar {adlar}; okunabilen tablolar {tablolar}', flush=True)


def zamanlayici(dsn, ac=True):
    """pg_cron saat ve bekleyen hesap işleri; veri yüklenip gerçek saate bırakılınca açılır.
    Yeniden kurulum, test koşusu ve canlı veri yüklemesinden önce kapatılır (ac=False)."""
    import psycopg
    klasor = Path(__file__).resolve().parent / 'veritabani'
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute('CREATE EXTENSION IF NOT EXISTS pg_cron')
        with conn.transaction():
            if ac:
                for yol in sorted((klasor / 'zamanlayici').glob('[0-9][0-9][0-9]_*.sql')):
                    conn.execute(yol.read_text(encoding='utf-8'))
            else:
                for ad in ('irp-motor-saat', 'irp-motor-bekleyen', 'irp-motor-log-temizle'):
                    if conn.execute('SELECT 1 FROM cron.job WHERE jobname=%s', (ad,)).fetchone():
                        conn.execute('SELECT cron.unschedule(%s)', (ad,))
        return [list(r) for r in conn.execute('SELECT jobname, schedule, command, active FROM cron.job ORDER BY 1')]


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sifirdan', action='store_true')
    p.add_argument('--test', action='store_true')
    p.add_argument('--hedef', choices=('yerel', 'supabase-test'), default='yerel')
    p.add_argument('--onay', help='bulutta: proje kimliği (adresteki ile aynı olmalı)')
    p.add_argument('--sil-onay', action='store_true', help='bulutta --sifirdan için ayrıca gerekir')
    p.add_argument('--zamanlayici', choices=('ac', 'kapat'), help='bulutta: göç yerine pg_cron saat işini aç/kapat')
    args = p.parse_args()
    if args.hedef == 'supabase-test':
        dsn = os.environ.get('IRP_SB_TEST_DB')
        if not dsn:
            p.error('IRP_SB_TEST_DB tanımlı değil')
        if args.sifirdan and not args.sil_onay:
            p.error('Bulutta --sifirdan ayrıca --sil-onay ister')
        try:
            supabase_projesi(dsn, args.onay or '')
        except ValueError as h:
            p.error(str(h))
        if args.zamanlayici:
            print(json.dumps(zamanlayici(dsn, args.zamanlayici == 'ac'), ensure_ascii=False, default=str))
        else:
            print(json.dumps(kur(dsn, args.sifirdan, args.test, bulut=True, proje=args.onay), ensure_ascii=False))
    else:
        dsn = os.environ.get('IRP_TEST_DB')
        if not dsn:
            p.error('IRP_TEST_DB tanımlı değil')
        print(json.dumps(kur(dsn, args.sifirdan, args.test), ensure_ascii=False))
