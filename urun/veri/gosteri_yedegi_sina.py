"""Canlı ayarları okumadan, ayrı yerel firmalarla yedek ve geri dönüş kanıtı."""
import base64
from contextlib import contextmanager, redirect_stdout
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / '.runtime/python')]

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from modul_platformu.butunlesik_sina import ortam
from urun.veri.gosteri_yedegi import al, denetle, geri_yukle, YedekHatasi, KanitDeposu, _metadata, _depo_eslesmesi
from urun.veri.senaryo1_hazirla import modul_korumasi


class YerelKanitlar:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(mode=0o700)

    def ac(self, path):
        return (self.folder / path).open('rb')

    def tamamla(self, path, source, content_type):
        target = self.folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == source.read_bytes()
        else:
            shutil.copyfile(source, target)


def hata(call, expected=YedekHatasi):
    try:
        call()
    except expected:
        return
    raise AssertionError('İşlem reddedilmeliydi.')


def hazirla(actor, api):
    customer = api('M10', '/musteriler', 'POST', {'ad': 'Yedek Sınama Müşterisi', 'ulke': 'TR'}, 201)
    demand = api('M10', '/talepler', 'POST', {'musteri': customer['kimlik'], 'kaynak': 'YENI_IS', 'tur': 'KURUMSAL_SARTNAME',
        'konu': 'Yedekten Dönen Makine', 'gereksinimler': [{'metin': 'Yedekle korunacak girdi'}],
        'kapsam': {'dahil': ['Tasarım']}}, 201)
    content = 'Şartname\tTürkçe, iki satır\nDosya gerçekten korunmalı.\n'.encode()
    uploaded = api('M10', '/ortak-dosyalar', 'POST', {'kayit': {'tur': 'TALEP', 'kimlik': str(demand['kimlik'])},
        'ad': 'şartname.txt', 'icerik_base64': base64.b64encode(content).decode(), 'tur': 'text/plain'})
    api('M10', f'/talepler/{demand["kimlik"]}/dosyalar', 'POST',
        {'tur': 'SARTNAME', **{k: uploaded[k] for k in ('ad', 'konum', 'parmak_izi')}}, 201)
    version = api('M10', f'/talepler/{demand["kimlik"]}/surumler', 'POST', {'kaynak': 'BOS'}, 201)
    schedule = api('M10', f'/surumler/{version["kimlik"]}/takvim/sablondan', 'POST', {'toplam_hafta': 6})['satirlar']
    version = api('M10', f'/surumler/{version["kimlik"]}', 'PUT', {'surum': version['surum'], 'para_birimi': 'TRY',
        'fiyat_girisi': 'FIYAT', 'fiyat': '12000.00', 'toplam_hafta': 6, 'teslim_suresi_hafta': 6, 'gecerlilik_gun': 30,
        'kalemler': [{'unsur': 'ROBOT', 'aciklama': 'Malzeme', 'adet': '1', 'birim_fiyat': '10000.00', 'para_birimi': 'TRY'}],
        'takvim': [{k: r[k] for k in ('etap_kodu', 'ad', 'paralel_grup', 'baslangic_hafta', 'sure_hafta')} for r in schedule]})
    for action, body in [('onaya-gonder', {}), ('onayla', {}), ('gonderildi', {'gonderim_sekli': 'E_POSTA'})]:
        version = api('M10', f'/surumler/{version["kimlik"]}/{action}', 'POST', dict(body, surum=version['surum']))
    api('M10', f'/talepler/{demand["kimlik"]}/sonuc', 'POST', {'sonuc': 'KAZANILDI', 'kazanan_surum': version['kimlik']})
    today = actor.rpc('simdi', {})[:10]
    order = api('M11A', '/donustur', 'POST', {'surum': version['kimlik'], 'proje_kodu': 'YEDEK-1',
        'proje_adi': demand['konu'], 'sorumlu': 'K004', 'siparis_tarihi': today, 'teslim_tarihi': '2026-12-18'})
    api('M11B', '/projeler/YEDEK-1/devir', 'POST', {})
    return uploaded, content, customer, version, order


def tablo_ozeti(dsn):
    """Satır sırasından bağımsız içerik karşılaştırması; hassas değerleri yazdırmaz."""
    with psycopg.connect(dsn) as conn:
        structure, _ = _metadata(conn)
        result = {}
        for table in structure['tablolar']:
            name = (table['sema'], table['ad'])
            columns = [c[0] for c in table['sutunlar'] if not c[4] and not (name == ('eklenti', 'kurulumlar') and c[0] == 'rol')]
            query = sql.SQL('SELECT to_jsonb(t)::text FROM (SELECT {} FROM {}) t ORDER BY to_jsonb(t)::text').format(
                sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(*name))
            rows = [row[0] for row in conn.execute(query)]
            result[name] = (len(rows), hashlib.sha256('\n'.join(rows).encode()).hexdigest())
        return result


def dizi_hali(dsn):
    with psycopg.connect(dsn) as conn:
        structure, _ = _metadata(conn)
        return [conn.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(s[0], s[1]))).fetchone()
                for s in structure['diziler']]


@contextmanager
def sinirli_yonetici(dsn, readonly=False):
    """Yalnız uygulama sahibi rollerinin üyesi; superuser/rol oluşturma yetkisi yok."""
    name = 'irp_yedek_sinama_' + str(os.getpid())
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN INHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB').format(sql.Identifier(name)))
        owners = conn.execute('SELECT rol::text FROM eklenti.kurulumlar').fetchall()
        for owner in ['irp_sahibi'] + [r[0] + '_sahibi' for r in owners]:
            conn.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(owner), sql.Identifier(name)))
    try:
        options = '-c role=' + name + (' -c default_transaction_read_only=on' if readonly else '')
        yield make_conninfo(dsn, options=options)
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(name)))


def depo_tasimasi(folder):
    """Üretim adaptörünün HTTP yolları/anahtar/baytları; yalnız yerel taklit depo."""
    objects = {'olay/1-kanıt.txt': b'Orijinal'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            assert self.headers.get('apikey') == 'yalniz-yerel-sinama'
            path = unquote(self.path).removeprefix('/storage/v1/object/kanitlar/')
            value = objects.get(path)
            self.send_response(200 if value is not None else 400)
            self.end_headers()
            self.wfile.write(value if value is not None else b'{"statusCode":"404","message":"Object not found"}')
        def do_POST(self):
            assert self.headers.get('Authorization') == 'Bearer yalniz-yerel-sinama'
            assert self.headers.get('x-upsert') == 'false'
            path = unquote(self.path).removeprefix('/storage/v1/object/kanitlar/')
            data = self.rfile.read(int(self.headers['Content-Length']))
            if path in objects:
                self.send_response(409)
            else:
                objects[path] = data
                self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        storage = KanitDeposu('http://127.0.0.1:' + str(server.server_port), 'yalniz-yerel-sinama')
        with storage.ac('olay/1-kanıt.txt') as stream:
            assert stream.read() == b'Orijinal'
        source = folder / 'http-kanit'
        source.write_bytes(b'Yeni dosya')
        storage.tamamla('olay/2-yeni.txt', source, 'text/plain')
        storage.tamamla('olay/2-yeni.txt', source, 'text/plain')
        hata(lambda: storage.tamamla('olay/1-kanıt.txt', source, 'text/plain'))
        assert objects['olay/1-kanıt.txt'] == b'Orijinal'
        hata(lambda: storage.ac('../baska'))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    started = time.monotonic()
    checks = []
    def passed(name):
        checks.append(name)
        print('Geçti: ' + name, flush=True)
    with tempfile.TemporaryDirectory(prefix='irp-yedek-sina-') as temp:
        folder = Path(temp)
        backup = folder / 'yedek'
        _depo_eslesmesi('postgresql://postgres.ornek@ornek.pooler.supabase.com/postgres', 'https://ornek.supabase.co')
        hata(lambda: _depo_eslesmesi('postgresql://postgres.ornek@ornek.pooler.supabase.com/postgres', 'https://baska.supabase.co'))
        hata(lambda: _depo_eslesmesi('postgresql://postgres@localhost/test', 'https://ornek.supabase.co'))
        passed('veritabani_ve_dosya_deposu_projesi_eslesmeli')
        depo_tasimasi(folder)
        passed('kanit_http_indirme_yukleme_turkce_yol_ve_farkli_bayti_ezmeme')
        source_storage = YerelKanitlar(folder / 'kaynak-kanit')
        with ortam() as (db, core, web, platform, actor, api):
            with redirect_stdout(StringIO()):
                uploaded, content, customer, version, order = hazirla(actor, api)
            # Normal çekirdek olayına gerçek dosya tanımı; taşıma testinde dosya baytı ayrı depoda.
            original_rpc = actor.rpc
            evidence = b'Gercek cekirdek eki\n'
            storage_path = None
            def attach(name, body):
                nonlocal storage_path
                if name == 'olay_ekle':
                    event = body['olay']
                    event['kanit'] = [{'dosya_kimligi': 'F-' + event['olay_kimligi'] + '/1', 'ad': 'kanıt.txt',
                        'tur': 'text/plain', 'boyut': len(evidence), 'parmak_izi': hashlib.sha256(evidence).hexdigest()}]
                    storage_path = event['olay_kimligi'] + '/1-kanıt.txt'
                return original_rpc(name, body)
            actor.rpc = attach
            try:
                result = actor.event('PROJE.ACTIM', {'kod': 'YEDEK-CEKIRDEK', 'ad': 'Dosyalı Çekirdek Projesi'})
                assert result['sonuc'] == 'BASARILI', result
            finally:
                actor.rpc = original_rpc
            path = source_storage.folder / storage_path
            path.parent.mkdir()
            path.write_bytes(evidence)
            source_files = Path(platform.env['IRP_MODUL_DOSYA_DIZINI'])
            before = tablo_ozeti(db.dsn)
            with sinirli_yonetici(db.dsn, readonly=True) as readonly:
                manifest = al(readonly, backup, source_files, source_storage)
            assert before == tablo_ozeti(db.dsn)
            print('Yedek içeriği: modül=%d, fiziksel dosya=%d, alanlar=%s' % (len(manifest['yapi']['moduller']),
                  len(manifest['dosyalar']), ','.join(f['alan'] for f in manifest['dosyalar'])), flush=True)
            assert len(manifest['yapi']['moduller']) == 3 and len(manifest['dosyalar']) >= 2
            assert {f['alan'] for f in manifest['dosyalar']} == {'modul', 'kanit'}
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in backup.iterdir())
            assert backup.stat().st_mode & 0o777 == 0o700
            passed('salt_okunur_kaynak_3_modul_kanit_sartname_ve_uretilmis_pdfler')
            passed('yedek_sinirsiz_veritabani_yetkisi_olmadan_aliniyor')
            passed('ozel_klasor_ve_parca_izinleri')
            with psycopg.connect(db.dsn) as conn:
                hata(lambda: modul_korumasi(conn), RuntimeError)
            passed('eski_cekirdek_sifirlayici_modullu_firmayi_reddediyor')
            # Eksik / bozuk dosya tamamlanmış bir yedek bırakmamalı.
            module_file = source_files / uploaded['kimlik']
            module_file.unlink()
            hata(lambda: al(db.dsn, folder / 'eksik-yedek', source_files, source_storage))
            assert not (folder / 'eksik-yedek').exists() and not list(folder.glob('.tamamlanmamis-*'))
            module_file.write_bytes(b'Bozuk')
            hata(lambda: al(db.dsn, folder / 'bozuk-yedek', source_files, source_storage))
            module_file.write_bytes(content)
            path.unlink()
            hata(lambda: al(db.dsn, folder / 'eksik-kanit', source_files, source_storage), FileNotFoundError)
            path.write_bytes(evidence)
            passed('eksik_ve_bozuk_modul_kanit_dosyasi_yedegi_reddediyor')
            # Sonraki hedefte kullanılacak karşılaştırmalar; arşiv hiç bağlantı/parola içermez.
            first = manifest['tablolar'][0]
            copied = backup / first['parca']
            original = copied.read_bytes()
            copied.write_bytes(original + b'bozuk')
            hata(lambda: denetle(backup))
            copied.write_bytes(original)
            passed('degisen_yedek_parcasi_tespit_ediliyor')
        # Kaynak DB ve geçit kapandı/silindi. Uyumlu, yeni boş firma ayrı kuruluyor.
        with ortam() as (db, core, web, platform, actor, api):
            target_files = Path(platform.env['IRP_MODUL_DOSYA_DIZINI'])
            target_storage = YerelKanitlar(folder / 'hedef-kanit')
            target_before = tablo_ozeti(db.dsn)
            hata(lambda: geri_yukle(db.dsn, backup, target_files, target_storage))
            assert target_before == tablo_ozeti(db.dsn)
            passed('acik_geri_yukleme_secimi_olmadan_hedef_degismiyor')
            hata(lambda: geri_yukle(db.dsn, backup, target_files, target_storage, servisler_durdu=True, yerine_koy=True))
            assert target_before == tablo_ozeti(db.dsn)
            passed('farkli_giris_hesap_eslesmeleri_reddediliyor')
            # İki sıfırdan yerel kurulumun rastgele test UUID'lerini, aynı hesaplara dönüşü taklit edecek şekilde eşle.
            with psycopg.connect(db.dsn) as conn:
                conn.execute('DELETE FROM public.kisi_hesaplari')
                for identity, person in manifest['hesap_eslesmeleri']:
                    conn.execute('INSERT INTO public.kisi_hesaplari(auth_kimligi,kisi) VALUES(%s,%s)', (identity, person))
            target_before = tablo_ozeti(db.dsn)
            with psycopg.connect(db.dsn) as conn:
                conn.execute("UPDATE eklenti.kurulumlar SET surum='uyumsuz' WHERE kod='M10'")
            hata(lambda: geri_yukle(db.dsn, backup, target_files, target_storage, servisler_durdu=True, yerine_koy=True))
            with psycopg.connect(db.dsn) as conn:
                conn.execute("UPDATE eklenti.kurulumlar SET surum=%s WHERE kod='M10'", (manifest['yapi']['moduller'][0][1],))
            assert target_before == tablo_ozeti(db.dsn)
            passed('uyumsuz_surume_veri_yazilmiyor')
            # COPY'yi geçen fakat yabancı anahtarı bozan veri: SQL işlemi tümüyle geri alınmalı.
            tampered = folder / 'kisit-hatali'
            shutil.copytree(backup, tampered)
            invalid = json.loads((tampered / 'yedek.json').read_text())
            saved = next(t for t in invalid['tablolar'] if t['sema'] == 'mod_m10' and t['ad'] == 'musteri_kisileri')
            definition = next(t for t in invalid['yapi']['tablolar'] if t['sema'] == 'mod_m10' and t['ad'] == 'musteri_kisileri')
            columns = [c[0] for c in definition['sutunlar'] if not c[4]]
            row = {'kimlik': '99999', 'musteri': '99999', 'ad': 'Olmayan Müşteri Kişisi', 'aktif': 't'}
            (tampered / saved['parca']).write_text('\t'.join(row.get(c, '\\N') for c in columns) + '\n')
            saved['adet'] = 1
            saved['ozet'] = hashlib.sha256((tampered / saved['parca']).read_bytes()).hexdigest()
            (tampered / 'yedek.json').write_text(json.dumps(invalid))
            hata(lambda: geri_yukle(db.dsn, tampered, target_files, target_storage,
                                  servisler_durdu=True, yerine_koy=True), psycopg.errors.ForeignKeyViolation)
            assert target_before == tablo_ozeti(db.dsn)
            with psycopg.connect(db.dsn) as conn:
                assert _metadata(conn)[0] == manifest['yapi']
            passed('kisit_hatasinda_tum_sql_ve_tetikler_geri_aliniyor')
            # Son dizi bozuk: daha önce RESTART edilmiş diziler de aynı işlemle geri dönmeli.
            invalid = json.loads((backup / 'yedek.json').read_text())
            invalid['diziler'][-1]['son'] = 10 ** 40
            invalid['diziler'][-1]['cagrildi'] = True
            (tampered / 'yedek.json').write_text(json.dumps(invalid))
            # Tablo parçaları bu denemede geçerli; hata yalnız dizinin son aşamasında.
            for table in manifest['tablolar']:
                shutil.copyfile(backup / table['parca'], tampered / table['parca'])
            sequence_before = dizi_hali(db.dsn)
            hata(lambda: geri_yukle(db.dsn, tampered, target_files, target_storage,
                                  servisler_durdu=True, yerine_koy=True))
            assert sequence_before == dizi_hali(db.dsn) and target_before == tablo_ozeti(db.dsn)
            passed('son_asamadaki_hatada_tablolar_ve_dizi_restartlari_geri_aliniyor')
            # Hedefte farklı bayt varsa hiçbir şey ezilmemeli.
            conflict = target_files / uploaded['kimlik']
            conflict.write_bytes(b'Baska bayt')
            hata(lambda: geri_yukle(db.dsn, backup, target_files, target_storage, servisler_durdu=True, yerine_koy=True))
            assert conflict.read_bytes() == b'Baska bayt' and target_before == tablo_ozeti(db.dsn)
            conflict.unlink()
            passed('hedefte_farkli_dosya_ezilmiyor')
            with sinirli_yonetici(db.dsn) as limited:
                geri_yukle(limited, backup, target_files, target_storage, servisler_durdu=True, yerine_koy=True)
            passed('geri_yukleme_superuser_ve_kisit_kapatma_yetkisi_istemiyor')
            assert before == tablo_ozeti(db.dsn)
            assert (target_files / uploaded['kimlik']).read_bytes() == content
            assert (target_storage.folder / storage_path).read_bytes() == evidence
            assert api('M10', f'/surumler/{version["kimlik"]}')['kimlik'] == version['kimlik']
            assert api('M11A', '/projeler/YEDEK-1')['proje'] == 'YEDEK-1'
            assert api('M11B', '/projeler/YEDEK-1/siparis-kaynagi')['plan']
            assert actor.rpc('oku', {'veri': 'PROJE', 'hedef': 'YEDEK-CEKIRDEK', 'g': {}})['deger']['ad'] == 'Dosyalı Çekirdek Projesi'
            assert base64.b64decode(api('M10', '/ortak-dosyalar/' + uploaded['kimlik'])['icerik_base64']) == content
            passed('tum_tablolar_ve_butun_dosyalar_kaynakla_ayni')
            passed('geri_donen_3_modul_ve_cekirdek_normal_kapilardan_okunuyor')
            created = api('M10', '/musteriler', 'POST', {'ad': 'Geri Dönüşten Sonraki Müşteri'}, 201)
            assert created['kimlik'] > customer['kimlik']
            assert actor.event('PROJE.ACTIM', {'kod': 'YEDEK-SONRA', 'ad': 'Geri Dönüşten Sonra'})['sonuc'] == 'BASARILI'
            passed('geri_yuklemeden_sonra_tekil_kimlik_ve_yeni_islem_calisiyor')
        report = {'durum': 'GECTI', 'kapsam': 'Yalnız ayrı yerel PostgreSQL ve geçit; canlı Supabase/S25 değişmedi.',
                  'tablo': len(manifest['tablolar']), 'modul': 3, 'dosya': len(manifest['dosyalar']), 'kontroller': checks,
                  'saniye': round(time.monotonic() - started, 2)}
        (ROOT / 'codex/sonuclar/gosteri_yedegi_sonuc.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Yedek/geri dönüş geçti: %d kontrol; %d tablo, 3 modül, %d fiziksel dosya.' %
          (len(checks), report['tablo'], report['dosya']), flush=True)


if __name__ == '__main__':
    main()
