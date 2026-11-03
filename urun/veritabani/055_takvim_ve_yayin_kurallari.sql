SET ROLE irp_sahibi;
-- Tarihli takvim işlevleri 057_tarihli_takvim.sql içinde tanımlanır.
-- kurallar_v9.py:344 isle (proje ve görülme dalları).
CREATE FUNCTION k9.isle(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); oid text=(e->>'olay_kimligi'); t text=saat.kodla(saat.an((e->>'oldugu_an'))); p text; x jsonb; h jsonb;
BEGIN
 IF kod='PROJE.ACTIM' THEN p=coalesce((g->>'kimlik'),(g->>'kod')); x='{"ana_proje":null,"sorumlu":null,"baslangic_tarihi":null,"kesin_kabul_tarihi":null}'::jsonb||g||jsonb_build_object('kimlik',p,'ek',coalesce((g->>'ek'),''),'aktif',true,'kod_gecmisi',jsonb_build_array(jsonb_build_object('kod',(g->'kod'),'ek',coalesce((g->>'ek'),''),'baslangic',t,'bitis',NULL))); PERFORM motor.kaydet(m,'projeler',p,x);
 ELSIF kod='PROJE.KOD_DEGISTIRDIM' THEN p=coalesce((g->>'proje'),(kapi.hedefler(e,'PROJE'))[1]); x=motor.kayit(m,'projeler',p); h=(x->'kod_gecmisi'); h=jsonb_set(h,ARRAY[(jsonb_array_length(h)-1)::text,'bitis'],to_jsonb(t));
  x=x||jsonb_build_object('kod',(g->'kod'),'ek',coalesce((g->>'ek'),''),'kod_gecmisi',h||jsonb_build_array(jsonb_build_object('kod',(g->'kod'),'ek',coalesce((g->>'ek'),''),'baslangic',t,'bitis',NULL))); PERFORM motor.kaydet(m,'projeler',p,x);
 ELSIF kod='BILDIRIM.GORDUM' THEN PERFORM motor.kaydet(m,'bildirim_gorulmeleri',oid,g||jsonb_build_object('kim',(e->'kim'),'an',t));
 ELSIF kod LIKE 'PROJE.ERISIM_%' THEN PERFORM motor.kaydet(m,'proje_erisimleri',oid,g||jsonb_build_object('kimlik',oid,'an',t,'yazan',e->'kim','acik',kod='PROJE.ERISIM_VERDIM')); PERFORM motor.bildir(m,e,'R42',g->>'kisi',saat.an(t),g->>'proje');
 ELSIF kod='GUN_ONAYI.AYARLADIM' THEN PERFORM motor.kaydet(m,'gun_onay_ayarlari',oid,g||jsonb_build_object('kimlik',oid,'an',t));
 ELSIF kod LIKE 'GUN_SONU.%' THEN PERFORM k9.gun_sonu_isle(m,e);
 ELSIF kod='PLAN.ONAYLADIM' THEN PERFORM k7.plan_isle(m,e);
 ELSIF kod='GECIKME.DEGERLENDIRDIM' OR kod LIKE 'SORUMLULUK.%' THEN PERFORM k9.sorumluluk_isle(m,e);
 ELSE RETURN false; END IF; RETURN true;
END $$;
-- kurallar_v7.py:158 satir_ustleri; 228 bildirim.
CREATE FUNCTION k7.satir_ustleri(m text,x jsonb) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 BEGIN
 IF (x->>'tur')='KISI' THEN RETURN yetki_v6.ustler(m,(x->>'kimlik')); END IF;
 IF (x->>'tur')='BIRIM' THEN RETURN yetki_v6.birim_ustleri(m,(x->>'kimlik')); END IF;
 RETURN '{}'; END $$;
CREATE FUNCTION k7.bildirim(m text,e jsonb,kural text,alicilar text[],kisi text DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; BEGIN
 FOREACH k IN ARRAY alicilar LOOP PERFORM motor.bildir(m,e,kural,k,saat.an((e->>'oldugu_an')),coalesce(kisi,'')); END LOOP; END $$;
-- kurallar_v7.py:335 sonra; desteklenmeyen bağlar açık hata verir.
CREATE FUNCTION k7.sonra(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); oid text=(e->>'olay_kimligi'); ss jsonb; s jsonb; n bigint; k text; x jsonb; ks text[]; u text[]; a text; iz jsonb; aday jsonb; BEGIN
 IF kod IN ('IS.REDDETTIM','GOREV.REDDETTIM') AND NOT motor.oku(m,'supheliler') ? oid THEN
  ss=coalesce((g->'sorumlular'),CASE WHEN irp.dogru((g->'sebep_olan')) THEN jsonb_build_array(jsonb_build_object('tur','KISI','kimlik',(g->'sebep_olan'),'yuzde',100)) ELSE '[]'::jsonb END);
  FOR s,n IN SELECT * FROM jsonb_array_elements(ss) WITH ORDINALITY LOOP k=oid||'/'||n; x=s||jsonb_build_object('satir',k,'ret',oid,'an',(e->'oldugu_an'),'dogrulandi',false,'itirazda',false,'kanit',(e->'kanit'),'hedef',(e->'neyin_ustunde')); u=k7.satir_ustleri(m,x);
   x=x||jsonb_build_object('dogrulandi',((e->>'kim'))<>((x->>'kimlik')) AND ((e->>'kim'))=ANY(u)); PERFORM motor.kaydet(m,'sorumluluklar',k,x); IF NOT irp.dogru((x->'dogrulandi')) THEN PERFORM k7.bildirim(m,e,'R38',u); END IF; END LOOP;
 END IF;
 IF kod IN ('IS.ATADIM','IS.DEVRETTIM','GOREV.ATADIM') THEN
  IF kod='GOREV.ATADIM' THEN SELECT array_agg((x->>'kisi')) INTO ks FROM jsonb_array_elements((g->'gorevler')) x; ELSE ks=coalesce(irp.dizi((g->'kisiler')),ARRAY[coalesce((g->>'kime'),(g->>'kisi'))]); IF cardinality(ks)=0 THEN ks=ARRAY[coalesce((g->>'kime'),(g->>'kisi'))]; END IF; END IF;
  FOREACH k IN ARRAY ks LOOP x=motor.kayit(m,'kisiler',k); IF irp.dogru(x) AND (x->>'birim') IS DISTINCT FROM motor.kayit(m,'kisiler',(e->>'kim'))->>'birim' THEN PERFORM k7.bildirim(m,e,'R30',yetki_v6.yoneticiler(m,(x->>'birim')),k); END IF; END LOOP;
 END IF;
 IF kod IN ('IS.TANIMLADIM','GOREV.ATADIM','IS.BAGLANTI_DUZELTTIM') THEN
  k=(kapi.hedefler(e,'NESNE'))[1]; IF k IS NOT NULL THEN FOREACH a IN ARRAY ARRAY['isler','gorevler'] LOOP FOR x IN SELECT hal FROM motor.satirlar(m,a) WHERE (hal->>'doguran_olay')=oid OR (hal->>'kimlik')=ANY(kapi.hedefler(e,'IS')) LOOP PERFORM motor.kaydet(m,a,(x->>'kimlik'),x||jsonb_build_object('nesne',k)); END LOOP; END LOOP; END IF;
 END IF;
 IF kod IN ('IS.ATADIM','GOREV.ATADIM','IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM') THEN
  FOR iz IN SELECT hal FROM motor.satirlar(m,'izinler') WHERE hal->>'durum'='ONAYLI' LOOP
   FOR aday IN SELECT hal FROM motor.satirlar(m,'gorevler') WHERE hal->>'kisi'=iz->>'kisi' AND irp.dogru(hal->'teslim_tarihi') AND saat.gun(hal->>'teslim_tarihi') BETWEEN saat.gun(iz->>'baslangic') AND saat.gun(iz->>'bitis') AND hal->>'durum' NOT IN ('BITTI','IPTAL')
   UNION ALL SELECT motor.kayit(m,'isler',z) FROM jsonb_array_elements_text(motor.kayit(m,'listeler',iz->>'kisi','[]')) z WHERE motor.kayit(m,'isler',z)->>'durum' IN ('SIRADA','ON_IS_BEKLIYOR') LOOP
    PERFORM k7.bildirim(m,e,'R37',array_remove(ARRAY[iz->>'onaylayan',coalesce(aday->>'veren',aday->>'atayan')],NULL),iz->>'kisi');
   END LOOP;
  END LOOP;
 END IF;
END $$;
-- kurallar_v9.py:398 sonra.
CREATE FUNCTION k9.sonra(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); k text; x jsonb; alici text; s jsonb; gecmis jsonb; BEGIN
 IF kod IN ('NESNE.ACTIM','NESNE.GUNCELLEDIM') THEN k=CASE WHEN kod='NESNE.ACTIM' THEN e->>'olay_kimligi' ELSE g->>'hedef' END; x=motor.kayit(m,'nesneler',k);
  IF irp.dogru(x) THEN gecmis=coalesce(x->'kod_gecmisi','[]'); s=CASE WHEN kod='NESNE.ACTIM' THEN g ELSE g->'degisenler' END;
   IF s ? 'kod' THEN IF jsonb_array_length(gecmis)>0 THEN gecmis=jsonb_set(gecmis,ARRAY[(jsonb_array_length(gecmis)-1)::text,'bitis'],to_jsonb(saat.kodla(saat.an(e->>'oldugu_an')))); END IF;
    IF irp.dogru(s->'kod') THEN gecmis=gecmis||jsonb_build_array(jsonb_build_object('kod',s->'kod','baslangic',saat.kodla(saat.an(e->>'oldugu_an')),'bitis',NULL)); END IF;
   END IF; PERFORM motor.kaydet(m,'nesneler',k,x||jsonb_build_object('kod_gecmisi',gecmis));
  END IF;
 END IF;
 IF kod='GOREV.TAMAMLADIM' THEN FOREACH k IN ARRAY kapi.hedefler(e,'GOREV') LOOP x=motor.kayit(m,'gorevler',k);
  IF (x->>'tur') IN ('NORMAL','DEGISIKLIK') AND (x->'ilk_teslim_ani')=(e->'oldugu_an') AND saat.an((x->>'ilk_teslim_ani'))>gorev.son_teslim_ani(x,m) THEN
   x=x||jsonb_build_object('gecikme_nedeni',coalesce(nullif((g->>'gecikme_nedeni'),''),CASE WHEN length(trim(coalesce((g->>'gecikme_aciklamasi'),'')))>0 THEN 'BELIRTILMEDI' ELSE 'GIRILMEDI' END)); IF irp.dogru((g->'gecikme_aciklamasi')) THEN x=x||jsonb_build_object('gecikme_aciklamasi',(g->'gecikme_aciklamasi')); END IF;
   PERFORM motor.kaydet(m,'gorevler',k,x); FOREACH alici IN ARRAY yetki_v6.yoneticiler(m,motor.kayit(m,'kisiler',(x->>'kisi'))->>'birim') LOOP IF alici<>(x->>'kisi') THEN PERFORM motor.bildir(m,e,'R40',alici,saat.an((e->>'oldugu_an')),k); END IF; END LOOP; END IF; END LOOP; END IF;
 IF kod IN ('GOREV.ATADIM','IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') THEN PERFORM k9.degisiklik_sonra(m,e); END IF;
 IF kod='IS.TAMAMLADIM' AND irp.dogru((g->'makine_bitis_ani')) THEN FOREACH k IN ARRAY kapi.hedefler(e,'IS') LOOP x=motor.kayit(m,'isler',k); IF (x->>'durum')='BITTI' THEN PERFORM motor.kaydet(m,'isler',k,x||jsonb_build_object('makine_bitis_ani',saat.kodla(saat.an((g->>'makine_bitis_ani'))))); END IF; END LOOP; END IF;
 IF kod='IZIN.ONAYLADIM' THEN x=motor.kayit(m,'izinler',g->>'hedef');
  IF irp.dogru(motor.ayar(m,'izin_ik_onayi',saat.an(e->>'oldugu_an'),'{}')->(x->>'tur')) THEN
   PERFORM motor.yaz(m,'bildirimler',motor.oku(m,'bildirimler')-((e->>'olay_kimligi')||':R36:'||(x->>'kisi')));
   FOR k IN SELECT anahtar FROM motor.satirlar(m,'kisiler') WHERE hal->'roller' ? 'IK' AND yetki_v6.istihdamda(m,anahtar,saat.an(e->>'oldugu_an')) LOOP PERFORM motor.bildir(m,e,'R41',k,saat.an(e->>'oldugu_an'),x->>'kisi'); END LOOP;
  END IF;
 END IF;
END $$;
-- is_.py:14 tezgah_saati_hesapla. Doğum satırındaki parça bağı korunur.
CREATE FUNCTION is_.dogum_parcasi(m text,i jsonb) RETURNS text LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 DECLARE e jsonb; ss jsonb; n int; BEGIN
 SELECT x INTO e FROM jsonb_array_elements(motor.oku(m,'olaylar','[]')) x WHERE (x->>'olay_kimligi')=(i->>'doguran_olay') AND (x->>'eylem_kodu') IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') LIMIT 1;
 ss=coalesce((e#>'{girdiler,isler}'),jsonb_build_array(coalesce((e->'girdiler'),'{}'))); n=CASE WHEN jsonb_array_length(ss)>1 THEN substring((i->>'kimlik') FROM '[^/]+$')::int-1 ELSE 0 END;
 RETURN coalesce((ss->n)->>'parca_kodu',i->>'parca_kodu'); END $$;
CREATE FUNCTION is_.tezgah_saati_hesapla(m text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE sonuc jsonb='[]'; i jsonb; bas timestamptz; bit timestamptz; BEGIN
 FOR i IN SELECT hal FROM motor.satirlar(m,'isler') WHERE (hal->>'tezgah_rolu')='AL' AND coalesce((hal->>'bitis_ani'),(hal->>'iptal_oncesi_bitis_ani')) IS NOT NULL LOOP
  bit=saat.an(coalesce((i->>'bitis_ani'),(i->>'iptal_oncesi_bitis_ani')));
  SELECT max(saat.an(coalesce((hal->>'bitis_ani'),(hal->>'iptal_oncesi_bitis_ani')))) INTO bas FROM motor.satirlar(m,'isler') WHERE (hal->>'tezgah_rolu')='BASLAT' AND (hal->'tezgah')=(i->'tezgah') AND is_.dogum_parcasi(m,hal) IS NOT DISTINCT FROM is_.dogum_parcasi(m,i) AND saat.an(coalesce((hal->>'bitis_ani'),(hal->>'iptal_oncesi_bitis_ani')))<=bit;
  IF bas<bit THEN sonuc=sonuc||jsonb_build_array(jsonb_build_object('kisi',NULL,'gun',saat.gun(saat.kodla(bas))::text,'is',(i->'kimlik'),'proje',(i->'proje'),'kategori',(i->'kategori'),'tezgah',(i->'tezgah'),'kova','TEZGAH','baslangic',saat.kodla(bas),'bitis',coalesce((i->>'makine_bitis_ani'),saat.kodla(bit)),'elle',false,'plansiz',false,'sistem_kapatti',false,'acan_kural','R11','kapatan_kural','R11')); END IF;
 END LOOP; RETURN sonuc; END $$;
-- kurallar_v6.py:121 baglantilari_yansit; kurallar_v7.py:366 tamamla; v9.py:433 tamamla.
CREATE FUNCTION k6.baglantilari_yansit(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE a jsonb; i jsonb; rs jsonb='[]'; k text; BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) LOOP i=motor.kayit(m,'isler',(a->>'is')); IF irp.dogru(i) THEN a=a||jsonb_build_object('proje',(i->'proje'),'kategori',(i->'kategori'),'parca_kodu',(i->'parca_kodu'),'is_iptal',(i->>'durum')='IPTAL'); END IF; rs=rs||jsonb_build_array(a); END LOOP; PERFORM motor.yaz(m,'araliklar',rs);
 FOR k,i IN SELECT * FROM motor.satirlar(m,'gorevler') LOOP IF irp.dogru((i->'teslim_tarihi')) AND NOT irp.dogru((i->'teslim_saati')) THEN PERFORM motor.kaydet(m,'gorevler',k,i||jsonb_build_object('takvim_teslim_saati',motor.takvim(m,(i->>'teslim_tarihi'),(i->>'kisi'))->'mesai_bitis')); END IF; END LOOP; END $$;
CREATE FUNCTION k7.tamamla(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; g jsonb; rs jsonb; a jsonb; tablo text; bag text; engeller jsonb; p jsonb; BEGIN
 rs='[]'; FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) LOOP
  IF a->>'kova'<>'TEZGAH' THEN rs=rs||jsonb_build_array(a); CONTINUE; END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_array(hal->'baslangic',coalesce(nullif(hal->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))))),'[]') INTO engeller FROM (
   SELECT hal FROM motor.satirlar(m,'duruslar') WHERE takvim.birim_kapsamda(m,motor.kayit(m,'tezgahlar',a->>'tezgah')->>'birim',hal->'kapsam')
   UNION ALL SELECT hal FROM motor.satirlar(m,'tezgah_duruslari') WHERE hal->>'tezgah'=a->>'tezgah') z;
  FOR p IN SELECT value FROM jsonb_array_elements(takvim.cikar(jsonb_build_array(jsonb_build_array(a->'baslangic',coalesce(nullif(a->'bitis','null'),to_jsonb(saat.kodla(saat.simdi()))))),engeller)) LOOP rs=rs||jsonb_build_array(a||jsonb_build_object('baslangic',p->0,'bitis',p->1)); END LOOP;
 END LOOP; PERFORM motor.yaz(m,'araliklar',rs);
 FOR k,g IN SELECT * FROM motor.satirlar(m,'gorevler') WHERE (hal->>'tur')='REVIZYON' LOOP g=g||jsonb_build_object('sorumlulugu_dogrulandi',EXISTS(SELECT FROM motor.satirlar(m,'sorumluluklar') s WHERE (s.hal->'ret')=(g->'doguran_olay') AND (s.hal->>'tur')='KISI' AND (s.hal->'kimlik')=(g->'kisi') AND ((s.hal->>'yuzde'))::numeric>0 AND irp.dogru((s.hal->'dogrulandi')) AND NOT irp.dogru((s.hal->'itirazda')))); g=g||jsonb_build_object('is_puani',gorev.puan(g)); PERFORM motor.kaydet(m,'gorevler',k,g); END LOOP;
 FOREACH tablo IN ARRAY ARRAY['isler','gorevler'] LOOP FOR k,g IN SELECT * FROM motor.satirlar(m,tablo) LOOP SELECT anahtar INTO bag FROM motor.satirlar(m,'nesneler') WHERE hal->>'tur'='PARCA' AND hal->'ad'=g->'parca_kodu' AND hal->>'proje' IS NOT DISTINCT FROM g->>'proje' LIMIT 1; IF bag IS NOT NULL THEN PERFORM motor.kaydet(m,tablo,k,g||jsonb_build_object('nesne',bag)); END IF; END LOOP; END LOOP;
END $$;
CREATE FUNCTION k9.gorulmeleri_yansit(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; s jsonb; x jsonb; h text; BEGIN
 FOR k,s IN SELECT * FROM motor.satirlar(m,'bildirimler') LOOP PERFORM motor.kaydet(m,'bildirimler',k,s||'{"gorulme_ani":null}'); END LOOP;
 FOR x IN SELECT hal FROM motor.satirlar(m,'bildirim_gorulmeleri') ORDER BY (hal->>'an') LOOP
  FOREACH h IN ARRAY irp.dizi((x->'bildirimler')) LOOP
   s=k9.bildirim_bul(m,h);
   -- Modül kaynağının kalıcı görülmesi k10_1.modul_gorulmeleri_yansit'tadır.
   IF coalesce(s->>'kaynak','CEKIRDEK')<>'CEKIRDEK' THEN CONTINUE; END IF;
   IF irp.dogru((s->'gecerli')) AND (s->'alici')=(x->'kim') AND saat.an((s->>'an'))<=saat.an((x->>'an')) AND NOT irp.dogru((s->'gorulme_ani')) THEN
    k=concat_ws(':',s->>'doguran_olay',s->>'kural',s->>'alici'); PERFORM motor.kaydet(m,'bildirimler',k,s||jsonb_build_object('gorulme_ani',(x->'an')));
   END IF;
  END LOOP;
 END LOOP; END $$;
CREATE FUNCTION k9.tamamla(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; x jsonb; tablo text; bag text; BEGIN
 FOR k,x IN SELECT * FROM motor.satirlar(m,'etaplar') LOOP PERFORM motor.kaydet(m,'etaplar',k,'{"sorumlu":null}'::jsonb||x); END LOOP;
 FOR k,x IN SELECT * FROM motor.satirlar(m,'gorevler') LOOP
  x='{"oncelik":"NORMAL","degisiklik_kaynagi":null,"gecikme_nedeni":null}'::jsonb||x;
  IF x->>'tur'='DEGISIKLIK' THEN
   x=x||jsonb_build_object('sorumlulugu_dogrulandi',EXISTS(SELECT FROM motor.satirlar(m,'sorumluluklar') WHERE hal->'ret'=x->'kimlik' AND hal->>'tur'='KISI' AND hal->'kimlik'=x->'kisi' AND irp.dogru(hal->'dogrulandi') AND NOT irp.dogru(hal->'itirazda') AND (hal->>'yuzde')::numeric>0));
   x=x||jsonb_build_object('is_puani',gorev.puan(x));
  END IF; PERFORM motor.kaydet(m,'gorevler',k,x);
 END LOOP;
 FOR k,x IN SELECT * FROM motor.satirlar(m,'kod_listesi') LOOP PERFORM motor.kaydet(m,'kod_listesi',k,'{"ust":null}'::jsonb||x); END LOOP;
 FOREACH tablo IN ARRAY ARRAY['isler','gorevler'] LOOP FOR k,x IN SELECT * FROM motor.satirlar(m,tablo) LOOP IF NOT irp.dogru(x->'parca_kodu') THEN CONTINUE; END IF;
  SELECT anahtar INTO bag FROM motor.satirlar(m,'nesneler') WHERE hal->>'tur'='PARCA' AND hal->>'proje' IS NOT DISTINCT FROM x->>'proje' AND EXISTS(SELECT FROM jsonb_array_elements(coalesce(hal->'kod_gecmisi','[]')) h WHERE h->'kod'=x->'parca_kodu') LIMIT 1;
  IF bag IS NOT NULL THEN PERFORM motor.kaydet(m,tablo,k,x||jsonb_build_object('nesne',bag)); END IF;
 END LOOP; END LOOP;
 PERFORM k9.gorulmeleri_yansit(m); END $$;
RESET ROLE;
