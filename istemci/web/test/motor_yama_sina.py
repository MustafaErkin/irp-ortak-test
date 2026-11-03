"""158: gerçek pg_cron, kilit, kesinti ve yayımlanmış işlem makbuzu kabulü.

IRP_TEST_DB yalnız ayrı 5544 test kümesine ait olmalı. Canlı kopyası ve üç cron
işi önceden kurulur. Sonuçlar IRP_MOTOR_TEST_OUT'a yazılır; sır/olay içeriği yok.
"""
from motor_yama_ortami import *
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

db=DB();actor=Actor(db);results=[]
def check(name,fn):
    start=time.monotonic();details=fn() or {}
    row={'test':name,'sonuc':'GECTI','saniye':round(time.monotonic()-start,3),**details}
    results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (OUT/'motor_yama_sql.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
def active(on):sqlrun("UPDATE cron.job SET active=%s WHERE jobname='irp-motor-bekleyen'",(on,))
def receipt(e,person=None):return db.rpc(person or e['kim'],'islem_sonucu',{'olay_kimligi':e['olay_kimligi']})['durum']
def wait(e,expected='TAMAMLANDI',timeout=30):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        result=receipt(e)
        if result in ([expected] if isinstance(expected,str) else expected):return round(time.monotonic()-start,3)
        time.sleep(.1)
    raise AssertionError((expected,result))
def event(code,g,targets=(),person='K001'):return actor.event(person,code,g,targets)
def send(e):
    r=db.rpc(e['kim'],'olay_ekle',{'olay':e});assert r['sonuc']=='BASARILI',r;return r
def pending(e):
    active(False);ready=threading.Event()
    def hold():
        with psycopg.connect(DSN) as c:
            c.execute('SELECT pg_advisory_xact_lock(202620,1)');ready.set();time.sleep(2.4)
    t=threading.Thread(target=hold);t.start();assert ready.wait(5)
    r=send(e);t.join();assert r['hesap']=='BEKLIYOR',r;assert receipt(e)=='BEKLIYOR'
    return r
def note(text):return event('NOT.YAZDIM',{'metin':text,'etiketler':[]},[('PROJE','DG-P')])

def permissions():
    e=note('Yetki sınaması');send(e);wait(e)
    assert receipt(e,'K004')=='BULUNAMADI'
    assert db.rpc('K004','islem_sonucu',{'olay_kimligi':'YOK'})['durum']=='BULUNAMADI'
    for role in ('anon','service_role'):
        with psycopg.connect(DSN) as c:
            c.execute('SET LOCAL ROLE '+role)
            try:c.execute('SELECT public.islem_sonucu(%s)',(e['olay_kimligi'],));raise AssertionError(role)
            except psycopg.errors.InsufficientPrivilege:pass
    assert not any(r[0] for r in sqlrun("SELECT has_function_privilege(r,'motor.bekleyen_isi()','EXECUTE') FROM unnest(ARRAY['anon','authenticated','service_role']) r"))
    return {'roller':3}
def idle():
    db.drain();before=sqlrun('SELECT son_yayin_ani,islenen_nokta,(SELECT count(*) FROM motor.olcumler) FROM motor.durum')[0]
    runs=sqlrun("SELECT count(*) FROM cron.job_run_details WHERE jobid=(SELECT jobid FROM cron.job WHERE jobname='irp-motor-bekleyen') AND status='succeeded'")[0][0]
    time.sleep(5)
    after=sqlrun('SELECT son_yayin_ani,islenen_nokta,(SELECT count(*) FROM motor.olcumler) FROM motor.durum')[0]
    after_runs=sqlrun("SELECT count(*) FROM cron.job_run_details WHERE jobid=(SELECT jobid FROM cron.job WHERE jobname='irp-motor-bekleyen') AND status='succeeded'")[0][0]
    assert before==after,(before,after);assert after_runs-runs>=3
    return {'bos_cagri':after_runs-runs,'ek_hesap':0}
def nonblocking():
    e=note('Kilit sürdürme');pending(e)
    with psycopg.connect(DSN) as holder:
        holder.execute('SELECT pg_advisory_xact_lock(202620,1)')
        start=time.monotonic();assert sqlrun('SELECT motor.bekleyen_isi()')[0][0]==0
        duration=time.monotonic()-start;assert duration<.5,duration
        assert receipt(e)=='BEKLIYOR'
    active(True);duration_done=wait(e)
    assert duration_done<6,duration_done
    return {'kilitte_cagri_s':round(duration,3),'kilit_sonrasi_yayin_s':duration_done}
def parallel():
    e=note('Eşzamanlı işçiler');pending(e)
    with ThreadPoolExecutor(max_workers=12) as pool:values=list(pool.map(lambda _:sqlrun('SELECT motor.bekleyen_isi()')[0][0],range(24)))
    assert sum(values)==1,values;assert receipt(e)=='TAMAMLANDI'
    r=send(e);assert r['tekrar'] is True
    assert sqlrun('SELECT count(*) FROM public.olaylar WHERE olay_kimligi=%s',(e['olay_kimligi'],))[0][0]==1
    active(True);return {'isçi':24,'hesap_yapan':sum(values),'kaynak_olay':1}
def crash():
    e=note('Yayın kesintisi');pending(e)
    # Yalnız ayrı TEST sunucusunda, yayın işlemi ortasında kontrollü SQL hatası.
    sqlrun("CREATE OR REPLACE FUNCTION test.yayin_kes() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'YAMA_TEST_KESINTI'; END$$")
    sqlrun('CREATE TRIGGER yama_test_kes BEFORE UPDATE OF son_yayin_ani ON motor.durum FOR EACH ROW EXECUTE FUNCTION test.yayin_kes()')
    before=sqlrun('SELECT son_yayin_ani,okuma_kabul_no FROM motor.durum')[0];active(True)
    try:
        start=time.monotonic();failure=False
        while time.monotonic()-start<6:
            failure=bool(sqlrun("SELECT 1 FROM cron.job_run_details WHERE jobid=(SELECT jobid FROM cron.job WHERE jobname='irp-motor-bekleyen') AND return_message LIKE '%YAMA_TEST_KESINTI%'"))
            if failure:break
            time.sleep(.1)
        assert failure,'Gerçek cron hatası görülmedi'
        assert before==sqlrun('SELECT son_yayin_ani,okuma_kabul_no FROM motor.durum')[0]
        assert receipt(e)=='BEKLIYOR'
    finally:sqlrun('DROP TRIGGER yama_test_kes ON motor.durum')
    duration=wait(e);assert duration<6
    return {'yarim_yayin':False,'kendiliginden_toparlanma_s':duration}
def suspect():
    s=json.loads((OUT/'setup.json').read_text())
    row={'ad':'Yama Teslim Sınaması','is_tanimi':'Yalnız ayrı test','kisi':'K004','nereye':'PROJE','proje':'DG-P','etap':s['stage'],'teslim_tarihi':'2026-12-10','zaman_degeri':1,'zorluk':2,'onay_gerekli':True,'onaylayan':'K001','dosya_gerekli':False,'oncelik':'NORMAL','on_kosul':[]}
    assignment=event('GOREV.ATADIM',{'gorevler':[row]});send(assignment);wait(assignment)
    target=[('GOREV',assignment['olay_kimligi']+'/1')]
    accept=event('GOREV.KABUL_ETTIM',{},target,'K004');send(accept);wait(accept)
    e=event('GOREV.TAMAMLADIM',{},target,'K004');send(e);wait(e)
    second=event('GOREV.TAMAMLADIM',{},target,'K004');send(second);wait(second,'INCELEME_GEREKIYOR')
    assert receipt(e)=='TAMAMLANDI';assert receipt(second,'K001')=='BULUNAMADI'
    # Yeni ikinci talebi engelleme bu yamanın kapsamı değil; yanlış başarı yok.
    return {'ilk_teslim':'TAMAMLANDI','ikinci_teslim':'INCELEME_GEREKIYOR'}
def future():
    e=note('Gelecek tanıklık');now=datetime.fromisoformat(e['oldugu_an']);e['oldugu_an']=(now+timedelta(seconds=5)).isoformat()
    send(e);wait(e,'ZAMANI_BEKLIYOR')
    assert not sqlrun("SELECT 1 FROM public.notlar WHERE anahtar=%s",(e['olay_kimligi'],))
    # Dakikalık saat işinin görevi değişmedi; ileri saat yalnız TEST kapısı.
    d=db.driver()
    try:
        later=(now+timedelta(seconds=6)).isoformat();d.saat({'simdi':later,'gercek':later,'demo':False});d._cagir('SELECT motor.saat_isi()',kontrol=True)
        wait(e)
    finally:
        # Gerçek saatin önüne olay bırakma; test kapısının korumasını aşma.
        while sqlrun('SELECT saat.simdi()>clock_timestamp()')[0][0]:time.sleep(.1)
        d._cagir('SELECT test.saat_birak()',kontrol=True);d.kapat()
    return {'erken_basari':False}
def invalidated():
    e=event('MESAI.GIRDIM',{},person='K017');send(e);wait(e,('TAMAMLANDI','INCELEME_GEREKIYOR'))
    inv=event('KAYIT.GECERSIZ_SAYDIM',{'hedef':e['olay_kimligi'],'gerekce':'Yalnız otomatik test'})
    inv['duzelttigi_olay']=e['olay_kimligi'];send(inv);wait(inv);assert receipt(e)=='GECERSIZ'
def rebuild():
    before=sqlrun('SELECT nokta_butcesi,saniye_butcesi FROM motor.durum')[0]
    d=db.driver();now=sqlrun('SELECT saat.kodla(son_yayin_ani) FROM motor.durum')[0][0]
    try:
        active(False);d.saat({'simdi':now,'gercek':now,'demo':False});db.drain()
        initial=d.dok();sqlrun('UPDATE motor.durum SET nokta_butcesi=12')
        d._cagir('SELECT motor.yeniden_kur()',kontrol=True);assert db.pending()
        count=sqlrun('SELECT count(*) FROM motor.olcumler WHERE olay IS NULL')[0][0];active(True)
        start=time.monotonic()
        while db.pending() and time.monotonic()-start<90:time.sleep(.2)
        assert not db.pending();after=d.dok()
        if initial!=after:
            from test.oynatici.hakem import karsilastirici
            differences=karsilastirici().farklar(initial,after)
            (OUT/'parcali_yeniden_fark.json').write_text(json.dumps(differences,ensure_ascii=False,default=str,indent=2))
            raise AssertionError(('Parçalı yeniden hesap son hali değiştirdi',differences[:2]))
        assert sqlrun('SELECT bakimda FROM motor.durum')[0][0] is False
        parts=sqlrun('SELECT count(*) FROM motor.olcumler WHERE olay IS NULL')[0][0]-count
        assert parts>1;return {'parca':parts,'tam_son_hal_esit':True}
    finally:
        sqlrun('UPDATE motor.durum SET nokta_butcesi=%s,saniye_butcesi=%s',before)
        d._cagir('SELECT test.saat_birak()',kontrol=True);d.kapat();active(True)

def writers():
    events=[note('Eşzamanlı tanıklık '+str(i)) for i in range(8)]
    before=sqlrun('SELECT count(*) FROM public.olaylar')[0][0]
    with ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(send,events))
    for e in events:wait(e)
    assert sqlrun('SELECT count(*) FROM public.olaylar')[0][0]-before==8
    assert len({e['olay_kimligi'] for e in events})==8
    return {'es_zamanli_yazan':8,'kaynak_olay':8,'bekleyen_yanit':sum(r['hesap']=='BEKLIYOR' for r in responses)}

def restart():
    import subprocess
    e=note('Sunucu yeniden başlatma');pending(e);active(True)
    data=Path(sqlrun('SHOW data_directory')[0][0]).resolve()
    assert data==Path('/tmp/irp_motor_yama/pgdata').resolve()
    subprocess.run(['/opt/homebrew/opt/postgresql@17/bin/pg_ctl','-D',str(data),'-l',str(OUT/'postgres.log'),'restart','-m','fast'],check=True,stdout=subprocess.DEVNULL)
    seconds=wait(e);assert seconds<8
    assert sqlrun('SELECT count(*) FROM public.olaylar WHERE olay_kimligi=%s',(e['olay_kimligi'],))[0][0]==1
    return {'yeniden_baslatma_sonrasi_s':seconds,'olay_kaybi':0}

def schedules():
    from urun.kur import zamanlayici
    # Kurulum tekrarlandığında iş çoğalmaz, kapatma bütün yeni işleri kapatır.
    first=zamanlayici(DSN);second=zamanlayici(DSN);assert first==second and len(second)==3
    assert zamanlayici(DSN,False)==[]
    assert len(zamanlayici(DSN))==3
    sqlrun("UPDATE cron.job SET active=false WHERE jobname='irp-motor-saat'")
    # Log temizliği yalnız kendi bitmiş eski izine dokunur.
    ids=dict(sqlrun('SELECT jobname,jobid FROM cron.job'))
    old=sqlrun("INSERT INTO cron.job_run_details(jobid,runid,status,end_time) VALUES(%s,nextval('cron.runid_seq'),'succeeded',now()-interval '25 hours') RETURNING runid",(ids['irp-motor-bekleyen'],))[0][0]
    other=sqlrun("INSERT INTO cron.job_run_details(jobid,runid,status,end_time) VALUES(%s,nextval('cron.runid_seq'),'succeeded',now()-interval '25 hours') RETURNING runid",(ids['irp-motor-saat'],))[0][0]
    sqlrun(sqlrun("SELECT command FROM cron.job WHERE jobname='irp-motor-log-temizle'")[0][0])
    assert not sqlrun('SELECT 1 FROM cron.job_run_details WHERE runid=%s',(old,))
    assert sqlrun('SELECT 1 FROM cron.job_run_details WHERE runid=%s',(other,))
    return {'tekil_is':3,'eski_iz_silindi':True,'diger_ise_dokunulmadi':True}

try:
    sqlrun("UPDATE cron.job SET active=false WHERE jobname='irp-motor-saat'")
    selected=os.environ.get('IRP_MOTOR_TEST_CASES','').split(',')
    for name,fn in [('Yetki',permissions),('Boşta Hesap Yok',idle),('Kilit ve Hızlı Devam',nonblocking),('24 İşçi ve Aynı Olay',parallel),('Yayın Kesintisi ve Kurtarma',crash),('Teslim ve Şüpheli Sonuç',suspect),('Gelecek Olay',future),('Geçersiz Olay',invalidated),('Parçalı Yeniden Kurma',rebuild),('8 Eşzamanlı Yazan',writers),('Sunucu Yeniden Başlatma',restart),('Zamanlayıcı ve İz Temizliği',schedules)]:
        if selected==[''] or name in selected:check(name,fn)
finally:
    sqlrun('DROP TRIGGER IF EXISTS yama_test_kes ON motor.durum')
    sqlrun("UPDATE cron.job SET active=true WHERE jobname IN ('irp-motor-saat','irp-motor-bekleyen')")
    db.dump('sql_trace')
