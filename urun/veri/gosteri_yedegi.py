"""Aynı uyumlu MVP kurulumu için özel iş verisi yedeği; Auth/sır yedeği değildir.

Kaynakta yalnız REPEATABLE READ/READ ONLY kullanılır. Geri yükleme ayrı hedef
bağlantısı, durmuş servisler ve açık değiştirme bayrağı ister. SQL çalıştıran
arşiv değil, COPY verisi ve doğrulanan dosya baytları taşır.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[2]
FORMAT = 1


class YedekHatasi(Exception):
    """Yalnız sır içermeyen, bizim yazdığımız açıklamalar."""


def _require(condition, message):
    if not condition:
        raise YedekHatasi(message)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _private(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')


def _digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _part(folder, name):
    _require(isinstance(name, str) and re.fullmatch(r'(tablo|dosya)_[0-9]{6}\.(copy|bin)', name),
             'Yedekte geçersiz parça yolu var.')
    path = folder / name
    _require(not path.is_symlink() and path.is_file(), 'Yedeğin bir parçası eksik.')
    return path


def _object_path(value):
    _require(isinstance(value, str) and value and '\\' not in value
             and all(p not in ('', '.', '..') for p in value.split('/')),
             'Dosya nesnesinin yolu uygun değil.')
    return value


def _depo_eslesmesi(dsn, url):
    """Ayrı hedef değişkenlerinin yanlışlıkla iki farklı firmaya gitmesini önle."""
    info = conninfo_to_dict(dsn)
    host = info.get('host', '').lower()
    storage_host = urlsplit(url).hostname or ''
    local = ('localhost', '127.0.0.1', '::1', '')
    if host in local:
        _require(storage_host in local, 'Yerel veritabanı ile dış dosya deposu eşleştirilemez.')
        return
    user = info.get('user', '')
    project = user.split('.', 1)[1] if user.startswith('postgres.') else ''
    if not project and host.startswith('db.') and host.endswith('.supabase.co'):
        project = host.split('.')[1]
    _require(project and storage_host == project + '.supabase.co'
             and (host.endswith('.supabase.com') or host == 'db.' + project + '.supabase.co'),
             'Veritabanı ve kanıt deposu aynı Supabase projesine ait olmalı.')


class KanitDeposu:
    """Mevcut özel kanitlar kovası. Anahtar yalnız süreç belleğinde tutulur."""
    def __init__(self, url, key):
        parsed = urlsplit(url)
        _require(parsed.scheme == 'https' or parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
                 'Dosya deposu güvenli bağlantı veya yerel test adresi olmalı.')
        _require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                 'Dosya deposu adresi uygun değil.')
        self.base = url.rstrip('/') + '/storage/v1/object/kanitlar/'
        self.headers = {'apikey': key, 'Authorization': 'Bearer ' + key}

    def ac(self, path):
        url = self.base + '/'.join(quote(p, safe='') for p in _object_path(path).split('/'))
        return urlopen(Request(url, headers=self.headers), timeout=45)

    def tamamla(self, path, source, content_type):
        """Var olan farklı baytı ezme; eksik nesneyi oluştur, ardından geri oku."""
        from urllib.error import HTTPError
        try:
            with self.ac(path) as stream:
                existing = hashlib.file_digest(stream, 'sha256').hexdigest()
            _require(existing == _digest(source), 'Hedefte aynı yolda farklı dosya var; değiştirilmedi.')
            return
        except HTTPError as error:
            # Storage sürümleri eksik nesne için 400 veya 404 döndürebilir.
            if error.code not in (400, 404):
                raise
        url = self.base + '/'.join(quote(p, safe='') for p in _object_path(path).split('/'))
        headers = {**self.headers, 'Content-Type': content_type, 'x-upsert': 'false'}
        with urlopen(Request(url, data=source.read_bytes(), headers=headers, method='POST'), timeout=45):
            pass
        with self.ac(path) as stream:
            _require(hashlib.file_digest(stream, 'sha256').hexdigest() == _digest(source),
                     'Yüklenen kanıt dosyası doğrulanamadı.')


def _metadata(conn):
    modules = conn.execute('SELECT k.kod,k.surum,k.ozet,k.kunye,k.rol::text,k.etkin,r.rolcanlogin '
                           'FROM eklenti.kurulumlar k LEFT JOIN pg_roles r ON r.rolname=k.rol ORDER BY k.kod').fetchall()
    schemas = []
    for code, version, digest, manifest, role, enabled, login in modules:
        _require(login is not None, 'Kurulu modülün dar çalışma rolü bulunamadı.')
        schema = manifest['veritabani']['sema']
        _require(schema == 'mod_' + code.lower() and re.fullmatch(r'mod_[a-z][a-z0-9_]+', schema),
                 'Kurulu modülün şeması sözleşmeyle uyuşmuyor.')
        schemas.append(schema)
    tables = conn.execute("""SELECT c.oid,n.nspname,c.relname,c.relkind,c.relispartition
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind IN ('r','p','m') AND
        ((c.relowner='irp_sahibi'::regrole AND n.nspname NOT IN ('auth','storage')) OR n.nspname=ANY(%s))
        ORDER BY n.nspname,c.relname""", (schemas,)).fetchall()
    result = []
    for oid, schema, name, kind, partition in tables:
        _require(kind == 'r' and not partition, 'Bu yedek biçimi bölümlenmiş tablo/görünüm desteklemiyor.')
        columns = conn.execute("""SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
            a.attidentity::text,a.attgenerated::text,pg_get_expr(d.adbin,d.adrelid)
            FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""", (oid,)).fetchall()
        constraints = conn.execute('SELECT conname,contype::text,pg_get_constraintdef(oid),condeferrable,condeferred '
                                   'FROM pg_constraint WHERE conrelid=%s ORDER BY conname', (oid,)).fetchall()
        triggers = conn.execute('SELECT tgname,tgenabled::text,pg_get_triggerdef(oid) FROM pg_trigger '
                                'WHERE tgrelid=%s AND NOT tgisinternal ORDER BY tgname', (oid,)).fetchall()
        result.append({'sema': schema, 'ad': name, 'sutunlar': columns, 'kisitlar': constraints, 'tetikler': triggers})
    _require(result and any(t['sema'] == 'public' and t['ad'] == 'olaylar' for t in result),
             'Çekirdek tabloları bulunamadı.')
    sequences = conn.execute("""SELECT n.nspname,c.relname,s.seqincrement,s.seqmin,s.seqmax,s.seqcycle
        FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE (c.relowner='irp_sahibi'::regrole AND n.nspname NOT IN ('auth','storage')) OR n.nspname=ANY(%s)
        ORDER BY n.nspname,c.relname""", (schemas,)).fetchall()
    # Rol adı hedef kurulumun kendi dar rolüdür; parolalar/rol DDL'i taşınmaz.
    return json.loads(_json({
        'cekirdek_gocleri': conn.execute('SELECT ad,ozet FROM irp.gocler ORDER BY ad').fetchall(),
        'moduller': [[r[0], r[1], r[2], r[5], r[6]] for r in modules],
        'modul_gocleri': conn.execute('SELECT kod,ad,ozet FROM eklenti.gocler ORDER BY kod,ad').fetchall(),
        'tablolar': result, 'diziler': sequences,
    })), {r[0]: r[4] for r in modules}


def _file_refs(conn):
    refs = {}
    def add(area, target, size, digest, content_type):
        _object_path(target)
        _require(isinstance(size, int) and size > 0 and isinstance(digest, str)
                 and re.fullmatch('[0-9a-f]{64}', digest), 'Dosya boyutu veya özeti eksik.')
        if area == 'modul':
            _require(re.fullmatch('MF-[0-9a-f]{40}', target), 'Modül dosya kimliği uygun değil.')
        item = {'alan': area, 'hedef': target, 'boyut': size, 'parmak_izi': digest,
                'tur': content_type or 'application/octet-stream'}
        previous = refs.setdefault((area, target), item)
        _require(previous == item, 'Aynı dosyaya ait bilgiler çelişiyor.')
    for identity, size, digest, content_type in conn.execute('SELECT kimlik,boyut,parmak_izi,tur FROM eklenti.dosyalar ORDER BY kimlik'):
        add('modul', identity, size, digest, content_type)
    # Geçersiz sayılmış/eski olayların kanıtlarını da koru; yalnız son hal yetmez.
    for event, evidence in conn.execute("SELECT olay_kimligi,icerik->'kanit' FROM public.olaylar ORDER BY kabul_no"):
        for index, item in enumerate(evidence or [], 1):
            identity = item.get('dosya_kimligi', '')
            position = identity.rsplit('/', 1)[-1] if '/' in identity else str(index)
            path = item.get('yol') or event + '/' + position + '-' + item['ad']
            add('kanit', path, item.get('boyut'), item.get('parmak_izi'), item.get('tur'))
    return list(refs.values())


def _copy_file(stream, target, expected_size, expected_digest):
    digest = hashlib.sha256()
    size = 0
    with _private(target) as output:
        while block := stream.read(min(1024 * 1024, max(1, expected_size - size + 1))):
            size += len(block)
            _require(size <= expected_size, 'Dosyanın boyutu beklenenden fazla.')
            digest.update(block)
            output.write(block)
    _require(size == expected_size and digest.hexdigest() == expected_digest,
             'Dosya eksik veya içeriği beklenen özetle uyuşmuyor.')


def _private_destination(path):
    path = Path(path).expanduser().absolute()
    # İş/ücret bilgileri kaynak ağacına veya sunulan web dizinine yazılamaz.
    forbidden = (ROOT, Path.home() / 'irp_gosteri' / 'web')
    _require(not any(path.resolve().is_relative_to(p.resolve()) for p in forbidden),
             'Yedek için git ve web dizini dışında özel bir klasör seçin.')
    _require(not path.exists() and not path.is_symlink(), 'Hedef yedek klasörü zaten var; üzerine yazılmadı.')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _require(not path.parent.stat().st_mode & 0o077, 'Yedek üst klasörü yalnız kullanıcıya açık olmalı (700).')
    return path


def al(dsn, destination, module_folder, storage=None):
    """Kaynağı değiştirmeden tek anın tablolarını ve başvurulan baytları al."""
    destination = _private_destination(destination)
    stage = Path(tempfile.mkdtemp(prefix='.tamamlanmamis-', dir=destination.parent))
    try:
        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            conn.execute('SET LOCAL statement_timeout = 120000')
            conn.execute('SET LOCAL lock_timeout = 3000')
            conn.execute("SET LOCAL timezone = 'UTC'")
            conn.execute("SET LOCAL datestyle = 'ISO, YMD'")
            conn.execute('SET LOCAL row_security = off')
            structure, _ = _metadata(conn)
            tables = []
            for index, table in enumerate(structure['tablolar']):
                part = 'tablo_%06d.copy' % index
                columns = [c[0] for c in table['sutunlar'] if not c[4]]
                query = sql.SQL('COPY {} ({}) TO STDOUT').format(
                    sql.Identifier(table['sema'], table['ad']), sql.SQL(',').join(map(sql.Identifier, columns)))
                with _private(stage / part) as output, conn.cursor() as cursor:
                    with cursor.copy(query) as copy:
                        for block in copy:
                            output.write(block)
                    count = cursor.rowcount
                tables.append({'sema': table['sema'], 'ad': table['ad'], 'parca': part,
                               'adet': count, 'ozet': _digest(stage / part)})
            sequences = []
            for schema, name, increment, minimum, maximum, cycle in structure['diziler']:
                last, called = conn.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(schema, name))).fetchone()
                sequences.append({'sema': schema, 'ad': name, 'son': last, 'cagrildi': called})
            files = _file_refs(conn)
            for index, file in enumerate(files):
                file['parca'] = 'dosya_%06d.bin' % index
                if file['alan'] == 'modul':
                    path = Path(module_folder) / file['hedef']
                    _require(path.is_file() and not path.is_symlink(), 'Modülün fiziksel dosyası eksik.')
                    stream = path.open('rb')
                else:
                    _require(storage is not None, 'Çekirdek kanıt dosyaları için depo bağlantısı gerekli.')
                    stream = storage.ac(file['hedef'])
                with closing(stream):
                    _copy_file(stream, stage / file['parca'], file['boyut'], file['parmak_izi'])
            manifest = {'bicim': FORMAT, 'zaman': datetime.now(timezone.utc).isoformat(),
                        'yapi': structure, 'tablolar': tables, 'diziler': sequences, 'dosyalar': files,
                        'hesap_eslesmeleri': [list(r) for r in conn.execute('SELECT auth_kimligi::text,kisi FROM public.kisi_hesaplari ORDER BY kisi')]}
        with _private(stage / 'yedek.json') as output:
            output.write(_json(manifest).encode())
        denetle(stage)
        stage.rename(destination)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def denetle(folder):
    """Bütün parça/dosya özetleri geçmeden yedek hazır kabul edilmez."""
    folder = Path(folder)
    _require(not (folder / 'yedek.json').is_symlink(), 'Yedek bildirimi bağlantı olamaz.')
    manifest = json.loads((folder / 'yedek.json').read_text())
    _require(manifest['bicim'] == FORMAT, 'Yedek biçimi desteklenmiyor.')
    _require([(t['sema'], t['ad']) for t in manifest['tablolar']] ==
             [(t['sema'], t['ad']) for t in manifest['yapi']['tablolar']], 'Yedekte tablo listesi eksik.')
    _require([(s['sema'], s['ad']) for s in manifest['diziler']] ==
             [(s[0], s[1]) for s in manifest['yapi']['diziler']], 'Yedekte dizi listesi eksik.')
    parts = set()
    for table in manifest['tablolar']:
        path = _part(folder, table['parca'])
        _require(path.name not in parts and _digest(path) == table['ozet'], 'Tablo parçası eksik, yinelenmiş veya bozuk.')
        parts.add(path.name)
    for file in manifest['dosyalar']:
        path = _part(folder, file['parca'])
        _object_path(file['hedef'])
        _require(file['alan'] in ('kanit', 'modul'), 'Yedekte bilinmeyen dosya alanı var.')
        if file['alan'] == 'modul':
            _require(re.fullmatch('MF-[0-9a-f]{40}', file['hedef']), 'Modül dosya kimliği uygun değil.')
        _require(path.name not in parts and path.stat().st_size == file['boyut']
                 and _digest(path) == file['parmak_izi'], 'Dosya parçası eksik, yinelenmiş veya bozuk.')
        parts.add(path.name)
    return manifest


def geri_yukle(dsn, folder, module_folder, storage=None, *, servisler_durdu=False, yerine_koy=False):
    """Uyumlu TEST kurulumunda iş verisinin tamamını tek işlemle geri koy.

    Auth, rol parolaları ve kurulum DDL'i değişmez. Dosyalar önce doğrulanır;
    SQL başarısız olursa yalnız zararsız, henüz başvurulmayan dosyalar kalabilir.
    """
    _require(servisler_durdu and yerine_koy, 'Geri yüklemek için durmuş servisler ve açık değiştirme seçimi gerekli.')
    folder = Path(folder)
    manifest = denetle(folder)
    with psycopg.connect(dsn, prepare_threshold=None) as conn:
        conn.execute('SET LOCAL lock_timeout = 3000')
        conn.execute('SET LOCAL statement_timeout = 120000')
        conn.execute('SET LOCAL row_security = off')
        conn.execute("SET LOCAL timezone = 'UTC'")
        conn.execute("SET LOCAL datestyle = 'ISO, YMD'")
        _require(conn.execute('SELECT test.ortam()').fetchone()[0] == 'TEST', 'Geri yükleme yalnız mevcut TEST kurulumuna uygulanır.')
        if conn.execute("SELECT to_regclass('cron.job')").fetchone()[0]:
            _require(not conn.execute("SELECT 1 FROM cron.job WHERE jobname IN ('irp-motor-saat','irp-motor-bekleyen','irp-motor-log-temizle') AND active").fetchone(),
                     'Geri yüklemeden önce motor zamanlayıcısı kapatılmalı.')
        structure, roles = _metadata(conn)
        _require(structure == manifest['yapi'], 'Çekirdek/modül sürümü veya tablo yapısı yedekle uyuşmuyor.')
        accounts = [list(r) for r in conn.execute('SELECT auth_kimligi::text,kisi FROM public.kisi_hesaplari ORDER BY kisi')]
        _require(accounts == manifest['hesap_eslesmeleri'], 'Hedef giriş hesaplarının kişi eşleşmeleri farklı.')
        tables = structure['tablolar']
        names = sql.SQL(',').join(sql.Identifier(t['sema'], t['ad']) for t in tables)
        conn.execute(sql.SQL('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE').format(names))
        # Kilitten önce yeni kurulum/göç yapılmış olmasını da fark et.
        _require(_metadata(conn)[0] == structure, 'Hedef yapısı işlem sırasında değişti.')
        _require([list(r) for r in conn.execute('SELECT auth_kimligi::text,kisi FROM public.kisi_hesaplari ORDER BY kisi')] == accounts,
                 'Hedef giriş hesapları işlem sırasında değişti.')
        for file in manifest['dosyalar']:
            source = _part(folder, file['parca'])
            if file['alan'] == 'kanit':
                _require(storage is not None, 'Kanıtları geri koymak için depo bağlantısı gerekli.')
                storage.tamamla(file['hedef'], source, file['tur'])
            else:
                directory = Path(module_folder)
                directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                _require(not directory.is_symlink(), 'Hedef dosya dizini bağlantı olamaz.')
                target = directory / file['hedef']
                if target.exists() or target.is_symlink():
                    _require(target.is_file() and not target.is_symlink() and _digest(target) == file['parmak_izi'],
                             'Hedefte aynı kimlikte farklı modül dosyası var; değiştirilmedi.')
                else:
                    # Disk hatası yarım dosyayı asıl kimlikle bırakmasın; var olanı ezme.
                    with tempfile.TemporaryDirectory(prefix='.geri-donus-', dir=directory) as temp:
                        staged = Path(temp) / 'hazir'
                        with source.open('rb') as stream:
                            _copy_file(stream, staged, file['boyut'], file['parmak_izi'])
                        try:
                            os.link(staged, target)
                        except FileExistsError:
                            _require(not target.is_symlink() and target.is_file() and _digest(target) == file['parmak_izi'],
                                     'Hedef dosya işlem sırasında değişti; üzerine yazılmadı.')
        for table in tables:
            name = sql.Identifier(table['sema'], table['ad'])
            conn.execute(sql.SQL('ALTER TABLE {} DISABLE TRIGGER USER').format(name))
            for constraint, kind, definition, deferrable, deferred in table['kisitlar']:
                if kind == 'f':
                    conn.execute(sql.SQL('ALTER TABLE {} ALTER CONSTRAINT {} DEFERRABLE INITIALLY DEFERRED').format(
                        name, sql.Identifier(constraint)))
        conn.execute('SET CONSTRAINTS ALL DEFERRED')
        # CASCADE yok: kapsam dışı bir tabloyu silmek yerine işlem reddedilir.
        conn.execute(sql.SQL('TRUNCATE {}').format(names))
        for table, saved in zip(tables, manifest['tablolar'], strict=True):
            columns = [c[0] for c in table['sutunlar'] if not c[4]]
            query = sql.SQL('COPY {} ({}) FROM STDIN').format(sql.Identifier(table['sema'], table['ad']),
                       sql.SQL(',').join(map(sql.Identifier, columns)))
            with _part(folder, saved['parca']).open('rb') as stream, conn.cursor() as cursor:
                with cursor.copy(query) as copy:
                    while block := stream.read(1024 * 1024):
                        copy.write(block)
                _require(cursor.rowcount == saved['adet'], 'Geri yüklenen tablo satır sayısı farklı.')
        for code, role in roles.items():
            conn.execute('UPDATE eklenti.kurulumlar SET rol=%s WHERE kod=%s', (role, code))
        _require(_file_refs(conn) == [{k: v for k, v in f.items() if k != 'parca'} for f in manifest['dosyalar']],
                 'Veritabanındaki dosya bilgileri yedekteki bayt listesiyle uyuşmuyor.')
        # Bütün yabancı anahtarlar gerçekten doğrulanır; kısıtlar kapalı bırakılmaz.
        conn.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for table in tables:
            name = sql.Identifier(table['sema'], table['ad'])
            for constraint, kind, definition, deferrable, deferred in table['kisitlar']:
                if kind == 'f':
                    mode = ('DEFERRABLE INITIALLY ' + ('DEFERRED' if deferred else 'IMMEDIATE')) if deferrable else 'NOT DEFERRABLE'
                    conn.execute(sql.SQL('ALTER TABLE {} ALTER CONSTRAINT {} ' + mode).format(name, sql.Identifier(constraint)))
            for trigger, mode, definition in table['tetikler']:
                verb = {'O': 'ENABLE', 'D': 'DISABLE', 'R': 'ENABLE REPLICA', 'A': 'ENABLE ALWAYS'}[mode]
                conn.execute(sql.SQL('ALTER TABLE {} ' + verb + ' TRIGGER {}').format(name, sql.Identifier(trigger)))
        # setval geri alınamaz. RESTART işlemi ise verilerle birlikte geri alınır.
        for state, spec in zip(manifest['diziler'], structure['diziler'], strict=True):
            schema, name, increment, minimum, maximum, cycle = spec
            next_value = state['son'] + increment if state['cagrildi'] else state['son']
            if cycle and not minimum <= next_value <= maximum:
                next_value = minimum if increment > 0 else maximum
            _require(minimum <= next_value <= maximum, 'Dizinin sonraki değeri sınır dışında; geri yükleme durdu.')
            conn.execute(sql.SQL('ALTER SEQUENCE {} RESTART WITH {}').format(
                sql.Identifier(schema, name), sql.Literal(next_value)))
        _require(_metadata(conn)[0] == structure, 'Geri yükleme sonrası tablo/kısıt/tetik yapısı farklı.')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument('--al', metavar='OZEL_KLASOR')
    command.add_argument('--denetle', metavar='YEDEK_KLASORU')
    command.add_argument('--geri-yukle', metavar='YEDEK_KLASORU')
    parser.add_argument('--modul-dizini', type=Path,
                        default=Path(os.environ['IRP_MODUL_DOSYA_DIZINI']) if os.environ.get('IRP_MODUL_DOSYA_DIZINI') else None)
    parser.add_argument('--servisler-durdu', action='store_true')
    parser.add_argument('--yerine-koy', action='store_true')
    args = parser.parse_args()
    try:
        storage = None
        prefix = 'IRP_YEDEK_HEDEF' if args.geri_yukle else 'IRP_SB_TEST'
        if not args.denetle and os.environ.get(prefix + '_URL') and os.environ.get(prefix + '_SERVIS'):
            _depo_eslesmesi(os.environ[prefix + '_DB'], os.environ[prefix + '_URL'])
            storage = KanitDeposu(os.environ[prefix + '_URL'], os.environ[prefix + '_SERVIS'])
        if args.al:
            module_folder = args.modul_dizini or Path.home() / 'irp_gosteri/.runtime/modul_dosyalari'
            manifest = al(os.environ['IRP_SB_TEST_DB'], args.al, module_folder, storage)
        elif args.denetle:
            manifest = denetle(args.denetle)
        else:
            # Kaynak adresine otomatik düşme yok; hedef mutlaka ayrı adla verilir.
            _require(args.modul_dizini is not None, 'Geri yükleme hedefinin modül dosya dizinini açıkça verin.')
            manifest = geri_yukle(os.environ['IRP_YEDEK_HEDEF_DB'], args.geri_yukle, args.modul_dizini, storage,
                                 servisler_durdu=args.servisler_durdu, yerine_koy=args.yerine_koy)
        print('İşlem tamamlandı: %d tablo, %d modül, %d doğrulanmış dosya. Sırlar çıktıya/arşive yazılmadı.' %
              (len(manifest['tablolar']), len(manifest['yapi']['moduller']), len(manifest['dosyalar'])))
    except Exception as error:
        message = str(error) if isinstance(error, YedekHatasi) else type(error).__name__
        print('Yedek işlemi tamamlanamadı: ' + message)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
