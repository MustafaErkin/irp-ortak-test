SET ROLE irp_sahibi;
CREATE FUNCTION kapi.oturum() RETURNS text LANGUAGE sql STABLE AS $$ SELECT kisi FROM irp.kisiler_oturum WHERE oturum=auth.uid() $$;
-- kurallar_v10_2.py:104 cihaz_izni.
CREATE FUNCTION k10_2.cihaz_izni(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 DECLARE m jsonb; BEGIN
 SELECT hal INTO m FROM motor.satirlar(d,'moduller') WHERE (hal->>'cihaz_harfi')=right((e->>'olay_kimligi'),1) LIMIT 1;
 IF m IS NOT NULL THEN RETURN irp.dogru((m->'aktif')) AND (e->>'cihaz')='MODUL-'||((m->>'kod')); END IF;
 RETURN (e->>'cihaz') NOT LIKE 'MODUL-%'; END $$;
-- Karar sırası işlevleri 081_karar_sirasi.sql içinde tanımlanır.
CREATE FUNCTION kapi.ekle(e jsonb,hassas_ek jsonb DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kisi jsonb; oturum text=kapi.oturum(); servis boolean=auth.role()='service_role'; yd text='YAYIN'; kod text; kimlik text; kanonik jsonb; once jsonb; mevcut jsonb; x jsonb; k text; sonuc jsonb; hesap text; etki timestamptz; hata text; no bigint; bek text; ns int; serbest timestamptz;
BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 e=e-'kabul_sirasi'-'nesne_surum_no'; kod=(e->>'eylem_kodu'); kimlik=(e->>'olay_kimligi');
 BEGIN PERFORM kapi.bicim_kontrol('YAYIN',e); EXCEPTION WHEN OTHERS THEN
  IF SQLERRM LIKE 'IRP|BICIM|%' THEN RETURN kapi.red('BICIM',substring(SQLERRM FROM 11)); END IF; RAISE;
 END;
 IF (SELECT kurulum_tamamlandi FROM motor.durum WHERE tek) AND (e->>'giris_sekli')='AKTARIM' AND NOT saat.demo() THEN RETURN kapi.red('YETKI','Kurulum tamamlandi; normal yol gerekli'); END IF;
 IF kod='KURULUM.TAMAMLADIM' AND coalesce(current_setting('irp.kurulum',true),'')<>'evet' AND NOT saat.demo() THEN RETURN kapi.red('DURUM','Kurulum kapanisi yalniz atomik kurulum icinde'); END IF;
 IF irp.sabit('taniklik') ? kod AND (e->>'giris_sekli')<>'AKTARIM' AND kod<>'BILDIRIM.GORDUM' THEN
  yd='YETKI'; PERFORM motor.halden_yukle(yd,motor.konum(saat.an((e->>'oldugu_an')),1,kimlik)); PERFORM motor.yaz(yd,'_an',to_jsonb(saat.kodla(saat.an((e->>'oldugu_an'))))); END IF;
 kisi=motor.kayit(yd,'kisiler',coalesce(oturum,(e->>'kim')));
 IF (e->>'giris_sekli')='AKTARIM' AND NOT servis THEN RETURN kapi.red('YETKI','AKTARIM yalniz servis'); END IF;
 IF (e->>'kim') IS DISTINCT FROM oturum AND NOT (servis AND (e->>'giris_sekli')='AKTARIM') THEN RETURN kapi.red('YETKI','Kim oturumla ayni olmali'); END IF;
 IF NOT k10_2.cihaz_izni('YAYIN',e) THEN RETURN kapi.red('YETKI','Modul cihaz harfi'); END IF;
 IF NOT yetki_v6.yetkili_mi(yd,e,servis) THEN
  IF irp.dogru((e->'adina')) AND NOT coalesce((kisi->'roller') ? 'EKIP_LIDERI',false) AND NOT EXISTS(SELECT FROM jsonb_array_elements(motor.oku(yd,'yetki_kurallari','[]')) r WHERE irp.dogru((r->'doguran_olay'))) THEN RETURN kapi.red('YETKI','Adina yalniz ekip lideri'); END IF;
  RETURN kapi.red('YETKI','T3 yetki matrisi'); END IF;
 IF saat.demo() AND NOT servis AND kod<>'AYAR.SAAT_KAYDIRDIM' THEN RETURN kapi.red('YETKI','Demo yeni girdi almaz'); END IF;
 IF hassas_ek IS NOT NULL AND NOT servis AND NOT coalesce((kisi->'roller') ? 'YETKILI',false) THEN RETURN kapi.red('YETKI','Hassas ek'); END IF;
 IF kod='AYAR.SAAT_KAYDIRDIM' AND NOT saat.demo() THEN RETURN kapi.red('YETKI','Yalniz demo'); END IF;
 e=e-'bulut_ulasma_ani'; kanonik=e;
 SELECT o.kanonik INTO once FROM public.olaylar o WHERE olay_kimligi=kimlik;
 IF FOUND THEN
  IF once<>kanonik THEN INSERT INTO public.isleme_hatalari(hal) VALUES(jsonb_build_object('olay',kimlik,'hata','ayni kimlik, farkli icerik','an',saat.kodla(saat.gercek()),'cozuldu',false)); RETURN '{"sonuc":"CAKISMA","kod":"CAKISMA"}'; END IF;
  RETURN '{"sonuc":"BASARILI","tekrar":true}'; END IF;
 IF NOT irp.sabit('taniklik') ? kod AND (e->>'giris_sekli')<>'AKTARIM' THEN
  SELECT bekleyen_sinir INTO bek FROM motor.durum WHERE tek; IF bek IS NOT NULL OR (SELECT bakimda FROM motor.durum WHERE tek) THEN RETURN kapi.red('HESAP_BEKLIYOR','Hesap bekliyor'); END IF;
  IF k10_2.sira_siniri('YAYIN',e) IS NOT NULL THEN RETURN kapi.red('BAYAT','SIRA'); END IF;
  FOREACH k IN ARRAY kapilar_v3.liste_hedefleri(e) LOOP IF NOT k=ANY(kapi.hedefler(e,'LISTE')) THEN RETURN kapi.red('BAYAT','Hedef liste surumu eksik'); END IF; END LOOP;
  FOR x IN SELECT value FROM jsonb_array_elements((e->'neyin_ustunde')) LOOP
   mevcut=kapi.nesne('YAYIN',(x->>'tur'),(x->>'kimlik')); IF NOT irp.dogru(mevcut) THEN RETURN kapi.red('DURUM','Yonetim hedefi bulutta yok'); END IF;
   IF (x->'surum') IS DISTINCT FROM coalesce((mevcut->'surum'),'0') THEN RETURN kapi.red('BAYAT','Nesne surumu degisti')||jsonb_build_object('guncel',mevcut); END IF;
  END LOOP;
  IF NOT kapi.durum('YAYIN',e) THEN RETURN kapi.red('DURUM','Bulut kapisi kapali'); END IF;
 END IF;
 IF kod='BILDIRIM.GORDUM' AND NOT kapi.durum('YAYIN',e) THEN RETURN kapi.red('DURUM','Bildirim hic var olmadi'); END IF;
 IF kod='AYAR.SAAT_KAYDIRDIM' THEN
  IF saat.an((e#>>'{girdiler,hedef}'))<saat.simdi() THEN RETURN kapi.red('DURUM','Geri saat icin demo sifirla'); END IF;
  UPDATE saat.ayar SET simdi=saat.an((e#>>'{girdiler,hedef}')),gercek=CASE WHEN demo THEN gercek ELSE saat.an((e#>>'{girdiler,hedef}')) END WHERE tek;
 END IF;
 etki=motor.etki_ani(e); e=e||jsonb_build_object('bulut_ulasma_ani',saat.kodla(saat.gercek()));
 SELECT min(etki_ani) INTO serbest FROM public.olaylar WHERE oldugu_an>(SELECT son_yayin_ani FROM motor.durum WHERE tek) AND oldugu_an<=saat.simdi();
 IF irp.sabit('kabul_sirali') ? kod THEN SELECT count(*)+1 INTO no FROM public.olaylar; e=e||jsonb_build_object('kabul_sirasi',no); END IF;
 IF kod='NESNE.SURUM_EKLEDIM' THEN SELECT count(*)+1 INTO ns FROM motor.satirlar('YAYIN','nesne_surumleri') WHERE hal->'nesne'=e#>'{girdiler,hedef}'; e=e||jsonb_build_object('nesne_surum_no',ns); END IF;
 INSERT INTO public.olaylar(olay_kimligi,icerik,kanonik,eylem_kodu,kim,oldugu_an,konum,bulut_ulasma_ani,kabul_sirasi,nesne_surum_no,etki_ani)
 VALUES(kimlik,e,kanonik,kod,(e->>'kim'),saat.an((e->>'oldugu_an')),motor.konum(saat.an((e->>'oldugu_an')),1,kimlik),saat.gercek(),no,ns,etki);
 IF hassas_ek IS NOT NULL THEN INSERT INTO public.hassas_ekler VALUES(kimlik,hassas_ek||jsonb_build_object('olay',kimlik)); END IF;
 -- Atomik, boş firma kurulumunda aradaki yayın dışarıdan görülemez.
 -- İzinli paket yalnız ana veri taşır; her zarf yine aynı kabul kapısından geçer.
 IF current_setting('irp.kurulum_toplu',true)='evet' THEN
  UPDATE motor.durum SET bekleyen_sinir=least(coalesce(bekleyen_sinir,motor.konum(etki,0,'')),motor.konum(etki,0,'')),kurulum_tamamlandi=kurulum_tamamlandi OR kod='KURULUM.TAMAMLADIM' AND saat.an(e->>'oldugu_an')<=saat.simdi() WHERE tek;
  RETURN '{"sonuc":"BASARILI","tekrar":false,"hesap":"BEKLIYOR"}';
 END IF;
 BEGIN
  etki=least(etki,serbest);
  hesap=motor.iste(CASE WHEN motor.konum(etki,0,'')<=(SELECT islenen_sinir FROM motor.durum WHERE tek) COLLATE "C" THEN motor.konum(etki,0,'') END,kimlik);
 EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS hata=MESSAGE_TEXT;
  INSERT INTO public.isleme_hatalari(hal) VALUES(jsonb_build_object('olay',kimlik,'hata',hata,'cozuldu',false));
  UPDATE motor.durum SET bekleyen_sinir=least(coalesce(bekleyen_sinir,motor.konum(etki,0,'')),motor.konum(etki,0,'')) WHERE tek;
  hesap='HATA';
 END;
 RETURN jsonb_build_object('sonuc','BASARILI','tekrar',false,'hesap',hesap);
END $$;
CREATE FUNCTION public.olay_ekle(olay jsonb,hassas_ek jsonb DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
#variable_conflict use_column

DECLARE r jsonb; hesap text; BEGIN
 r=kapi.ekle(olay,hassas_ek); hesap=coalesce((r->>'hesap'),CASE WHEN (SELECT bekleyen_sinir FROM motor.durum WHERE tek) IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END);
 RETURN r||jsonb_build_object('alindi',(r->>'sonuc')='BASARILI','hesap',hesap); END $$;
-- depo.py:206 cihaz_esitle, 210 cihaz_kaydol.
CREATE FUNCTION public.cihaz_esitle(cihaz text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
#variable_conflict use_column

DECLARE kim text=kapi.oturum(); BEGIN
 IF NOT motor.oku('YAYIN','kisiler') ? kim THEN RAISE EXCEPTION 'IRP|YETKI|Cihaz oturumu'; END IF;
 INSERT INTO public.cihaz_esitlemeleri VALUES(cihaz,jsonb_build_object('kisi',kim,'son_esitleme',saat.kodla(saat.gercek()))) ON CONFLICT(anahtar) DO UPDATE SET hal=excluded.hal; RETURN NULL; END $$;
CREATE FUNCTION public.cihaz_kaydol(cihaz text) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
#variable_conflict use_column

DECLARE kim text=kapi.oturum(); k text; h text; i int; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 IF NOT yetki_v6.istihdamda('YAYIN',kim,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 k=kim||':'||cihaz; SELECT (hal#>>'{}') INTO h FROM public.cihaz_harfleri WHERE anahtar=k; IF FOUND THEN RETURN h; END IF;
 FOR i IN 1..26 LOOP h=substring('TUVWXYZABCDEFGHIJKLMNOPQRS' FROM i FOR 1);
  IF NOT EXISTS(SELECT FROM motor.satirlar('YAYIN','moduller') WHERE (hal->>'cihaz_harfi')=h) AND NOT EXISTS(SELECT FROM public.cihaz_harfleri WHERE starts_with(anahtar,kim||':') AND hal=to_jsonb(h)) AND NOT EXISTS(SELECT FROM public.olaylar o WHERE o.kim=kim AND right(olay_kimligi,1)=h) THEN INSERT INTO public.cihaz_harfleri VALUES(k,to_jsonb(h)); RETURN h; END IF;
 END LOOP; RAISE EXCEPTION 'IRP|TASMA|Cihaz harfleri doldu'; END $$;
CREATE FUNCTION irp.kaynak_degismez() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Olaylar yalniz eklenir'; END $$;
CREATE TRIGGER olaylar_degismez BEFORE UPDATE OR DELETE OR TRUNCATE ON public.olaylar FOR EACH STATEMENT EXECUTE FUNCTION irp.kaynak_degismez();
REVOKE ALL ON public.olaylar FROM anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.olay_ekle(jsonb,jsonb),public.cihaz_esitle(text),public.cihaz_kaydol(text) TO authenticated,service_role;
RESET ROLE;
