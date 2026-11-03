"""Yetenek envanteri için ayrı test firmasından dar kapsamlı, salt okunur kanıt.

Bu, modül kabulü değildir. Web sınamasının kurduğu geçici gerçek SQL motorunu
kullanır; canlı firmaya bağlanmaz. İş verisini rapora kopyalamaz.
"""
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'codex/sonuclar/cekirdek_yetenekleri/sql_kaniti.json'


def denetle(database, output=OUTPUT):
    if not database.name.startswith('irp_web_t20_test_'):
        raise ValueError('Yetenek denetimi yalnız ayrı yerel web test firmasında çalışır.')
    driver = database.driver()
    try:
        if driver._cagir('SELECT test.ortam()', kontrol=True) != 'TEST':
            raise ValueError('TEST ortamı gerekli.')
        functions = driver._cagir("""SELECT coalesce(jsonb_agg(jsonb_build_object(
          'ad',p.proname,'imza',pg_get_function_identity_arguments(p.oid),
          'authenticated',has_function_privilege('authenticated',p.oid,'EXECUTE'),
          'service_role',has_function_privilege('service_role',p.oid,'EXECUTE')) ORDER BY p.proname),'[]')
          FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname='public' AND p.proowner='irp_sahibi'::regrole""", kontrol=True)
        migrations = driver._cagir("SELECT jsonb_object_agg(ad,ozet) FROM irp.gocler", kontrol=True)
        actions = driver._cagir("SELECT irp.sabit('eylemler')", kontrol=True)
    finally:
        driver.kapat()

    tests = []
    def read(name, target=None, params=None, person='K001', expected='OK'):
        try:
            value = database.rpc(person,'oku',{'veri':name,'hedef':target,'g':params or {}})['deger']
            result={'ad':name,'beklenen':expected,'sonuc':'OK','eslesti':expected=='OK',
                    'bicim':type(value).__name__,'eleman':len(value) if isinstance(value,(dict,list)) else None}
        except Exception as error:
            result={'ad':name,'beklenen':expected,'sonuc':type(error).__name__,
                    'eslesti':expected==type(error).__name__}
            value=None
        tests.append(result)
        return value, result

    projects,_ = read('PROJELER')
    project = (projects or [{}])[0].get('kimlik') or (projects or [{}])[0].get('kod')
    today=date.today()
    window={'bas':(today-timedelta(days=31)).isoformat(),'bit':(today+timedelta(days=31)).isoformat()}
    gantt, gantt_test = read('GANTT',project,window)
    if isinstance(gantt,list):
        gantt_test['planli_satir']=sum(bool(r.get('planlanan_baslangic') or r.get('planlanan_bitis')) for r in gantt)
        gantt_test['gerceklesen_satir']=sum(bool(r.get('gerceklesen_baslangic')) for r in gantt)
        gantt_test['not']='Okuma ve veri alanları doğrulandı; rol bağımsız etap toplamı ve M11B kabulü bu kanıtın dışında.'
    plan, plan_test = read('PLAN',project)
    if isinstance(plan,dict):
        plan_test['alanlar']=sorted(plan)
        plan_test['baslangic_plani_dolu']=bool(plan.get('B0'))
    read('PROJE_ISCILIGI',project,window)
    read('PROJE_MALIYETI',project,{'ay':today.replace(day=1).isoformat()})
    read('ETAPLAR',project)
    read('KISILER');read('BIRIMLER');read('BILDIRIMLER','K001')
    read('WEB_KISI','K017',person='K004')
    read('MAAS','K001',{'ay':today.replace(day=1).isoformat()},person='K017',expected='PermissionError')
    read('M10.KAZANAN_SURUM',params={'surum':1},expected='ValueError')
    events=Counter(code for _,code,result in database.events if result.get('sonuc')=='BASARILI')
    calls=Counter(name for _,rpc,name in database.calls if rpc=='oku' and name)
    errors=Counter(name for _,rpc,name,*_ in database.errors if rpc=='oku' and name)
    http_reads={name:{'cagri':count,'hata':errors[name]} for name,count in sorted(calls.items())}
    hashes_ok=all((ROOT/'urun/veritabani'/name).exists() and
                  hashlib.sha256((ROOT/'urun/veritabani'/name).read_bytes()).hexdigest()==digest
                  for name,digest in migrations.items())
    result={'bicim':1,'ortam':'ayri_yerel_PostgreSQL_TEST','kapsam':'SQL okuma/olay gözlemi; modül kabulü değil',
            'gocler_kaynakla_ayni':hashes_ok,'gocler':migrations,
            'public_kapilar':functions,'tanimli_eylemler':sorted(actions),
            'web_okumalari':http_reads,'basarili_olaylar':dict(sorted(events.items())),
            'odak_kontrolleri':tests,'dosya_deposu':'yerel taklit; gerçek Storage kanıtı sayılmaz',
            'realtime':'yerel taklit; gerçek Supabase kanıtı sayılmaz'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert hashes_ok,'Test motorunun göçleri kaynakla farklı.'
    failed=[t['ad'] for t in tests if not t['eslesti']]
    assert not failed,'Beklenmeyen yetenek sonucu: '+', '.join(failed)
    print('Yetenek kanıtı: '+str(len(http_reads))+' web okuması, '+str(len(events))+
          ' başarılı olay türü, '+str(len(tests))+' odak kontrolü. Canlıya yazılmadı.',flush=True)
    return result
