-- T30 / Tur 1: ileri göç. Eski olayları silmez, tanıklık kapılarını değiştirmez.
SET ROLE irp_sahibi;

ALTER FUNCTION k7.takvim_yetki(text,jsonb) RENAME TO takvim_yetki_154;
CREATE FUNCTION k7.takvim_yetki(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN
 IF e->>'eylem_kodu'='IZIN.TALEP_ETTIM' THEN
  RETURN coalesce(e->>'kim'=e#>>'{girdiler,kisi}' AND NOT irp.dogru(e->'adina')
   AND yetki_v6.istihdamda(m,e->>'kim',yetki_v6.simdi(m)),false);
 END IF;
 RETURN k7.takvim_yetki_154(m,e);
END $$;

-- Telefon, firma/birim takvimi + tatil/özel gün + onaylı izin + ek mesaiyi
-- aynı motor işlevleriyle alır. Sabit mola mesai dışı değildir.
ALTER FUNCTION okuma.ek_oku(text,text,text,jsonb) RENAME TO ek_oku_154;
-- PL/pgSQL parametresinin örtük blok adı işlev adıyla değişir.
-- Eski göçteki nitelikli kim referansını yeni ada taşı; aksi halde
-- BUGUNKU_KIMLIKLER ilk cihaz bağlantısında UndefinedTable üretir.
DO $migration$
BEGIN
 EXECUTE replace(pg_get_functiondef('okuma.ek_oku_154(text,text,text,jsonb)'::regprocedure),
                 'ek_oku.kim','ek_oku_154.kim');
END $migration$;
CREATE FUNCTION okuma.ek_oku(kim text,veri text,hedef text,g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE r jsonb; gun date=saat.gun(saat.kodla(saat.simdi())); mesai jsonb='[]'; calisma jsonb='[]'; ek jsonb;
BEGIN
 r=okuma.ek_oku_154(kim,veri,hedef,g);
 IF veri='TELEFON' THEN
  IF yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN
   ek=takvim.ekler('OKUMA',kim,gun);
   mesai=takvim.cikar(takvim.birlesim(takvim.normal('OKUMA',gun,false,kim)||ek),takvim.izinler('OKUMA',kim));
   calisma=takvim.cikar(takvim.birlesim(takvim.normal('OKUMA',gun,true,kim)||ek),takvim.izinler('OKUMA',kim));
  END IF;
  r=r||jsonb_build_object('calisma_penceresi',jsonb_build_object('gun',gun::text,'mesai',mesai,'calisma',calisma,'kaynak_ani',saat.kodla(saat.simdi())));
 END IF;
 RETURN r;
END $$;

CREATE FUNCTION k7.is_bildirimi(m text,e jsonb,tur text,x jsonb,alici text,asama text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kural text='U_'||asama||'_'||md5(x->>'kimlik'); anahtar text; baslik text; metin text; b jsonb;
BEGIN
 IF alici IS NULL OR alici='' THEN RETURN; END IF;
 baslik=CASE asama WHEN 'ATAMA' THEN 'Yeni İş Ataması' WHEN 'TESLIM' THEN 'Teslim Onayı Bekleniyor' WHEN 'ONAY' THEN 'Tesliminiz Onaylandı' ELSE 'İşiniz Düzeltmeye Gönderildi' END;
 metin=coalesce(x->>'ad',x->>'islem',x->>'is_tanimi','İş')||' — '||CASE asama WHEN 'ATAMA' THEN 'Size atandı.' WHEN 'TESLIM' THEN 'Teslim edildi; onayınız bekleniyor.' WHEN 'ONAY' THEN 'Tesliminiz onaylandı.' ELSE coalesce(nullif(e#>>'{girdiler,not}',''),'Düzeltme isteniyor.') END;
 -- Atölye tesliminin mevcut R05 bildirimi varsa ikinci bildirim doğurma.
 IF asama='TESLIM' AND tur='IS' AND motor.oku(m,'bildirimler') ? ((e->>'olay_kimligi')||':R05:'||alici) THEN kural='R05'; END IF;
 anahtar=(e->>'olay_kimligi')||':'||kural||':'||alici;
 PERFORM motor.bildir(m,e,kural,alici,saat.an(e->>'oldugu_an'),metin);
 b=motor.kayit(m,'bildirimler',anahtar)||jsonb_build_object('baslik',baslik,'metin',metin,'is_akisi',asama,'hedef_tur',tur,'hedef',x->'kimlik','yapan',e->'kim');
 PERFORM motor.kaydet(m,'bildirimler',anahtar,b);
END $$;

ALTER FUNCTION k7.sonra(text,jsonb) RENAME TO sonra_154;
CREATE FUNCTION k7.sonra(m text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; oid text=e->>'olay_kimligi'; tur text; tablo text; x jsonb; hedef text; alici text; ids jsonb;
BEGIN
 PERFORM k7.sonra_154(m,e);
 IF kod='GOREV.ATADIM' THEN
  FOR x IN SELECT hal FROM motor.satirlar(m,'gorevler') WHERE hal->>'doguran_olay'=oid AND hal->>'tur'<>'ONAY' LOOP
   PERFORM k7.is_bildirimi(m,e,'GOREV',x,x->>'kisi','ATAMA');
  END LOOP;
 END IF;
 IF kod IN ('IS.ATADIM','IS.DEVRETTIM') THEN
  FOR x IN SELECT hal FROM motor.satirlar(m,'isler') WHERE anahtar=ANY(kapi.hedefler(e,'IS')) OR hal->>'ana_is'=ANY(kapi.hedefler(e,'IS')) LOOP
   IF irp.dogru(x->'kisi') THEN PERFORM k7.is_bildirimi(m,e,'IS',x,x->>'kisi','ATAMA'); END IF;
  END LOOP;
 END IF;
 IF kod IN ('GOREV.TAMAMLADIM','GOREV.ONAYLADIM','GOREV.REDDETTIM','IS.TAMAMLADIM','IS.ONAYLADIM','IS.REDDETTIM') THEN
  tur=split_part(kod,'.',1);tablo=CASE tur WHEN 'GOREV' THEN 'gorevler' ELSE 'isler' END;
  FOREACH hedef IN ARRAY kapi.hedefler(e,tur) LOOP
   x=motor.kayit(m,tablo,hedef);
   IF kod LIKE '%.TAMAMLADIM' AND x->>'durum'='ONAY_BEKLIYOR' THEN
    alici=CASE tur WHEN 'GOREV' THEN x->>'onaylayan' ELSE x->>'atayan' END;
    PERFORM k7.is_bildirimi(m,e,tur,x,alici,'TESLIM');
   ELSIF kod LIKE '%.ONAYLADIM' AND x->>'durum'='BITTI' OR kod LIKE '%.REDDETTIM' AND x->>'durum' IN ('REDDEDILDI','REVIZYONDA') THEN
    alici=CASE tur WHEN 'GOREV' THEN x->>'kisi' ELSE coalesce(x->>'tamamlayan',x->>'kisi') END;
    PERFORM k7.is_bildirimi(m,e,tur,x,alici,CASE WHEN kod LIKE '%.ONAYLADIM' THEN 'ONAY' ELSE 'RET' END);
   END IF;
  END LOOP;
 END IF;
 IF kod='GOREV.KABUL_ETTIM' THEN
  SELECT coalesce(jsonb_agg(anahtar),'[]') INTO ids FROM motor.satirlar(m,'bildirimler') b
   WHERE b.hal->>'is_akisi'='ATAMA' AND b.hal->>'alici'=e->>'kim'
    AND b.hal->>'hedef'=ANY(kapi.hedefler(e,'GOREV'))
    AND motor.kayit(m,'gorevler',b.hal->>'hedef')->>'kabul_ani'=e->>'oldugu_an';
  -- Görülme izdüşümü gerçek kabul olayına bağlıdır; insan adına yeni olay yoktur.
  IF jsonb_array_length(ids)>0 THEN PERFORM motor.kaydet(m,'bildirim_gorulmeleri',oid||'/atama',jsonb_build_object('kim',e->'kim','an',e->'oldugu_an','bildirimler',ids)); END IF;
 END IF;
END $$;

ALTER FUNCTION k9.gorulmeleri_yansit(text) RENAME TO gorulmeleri_yansit_154;
CREATE FUNCTION k9.gorulmeleri_yansit(m text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE k text; b jsonb;
BEGIN
 PERFORM k9.gorulmeleri_yansit_154(m);
 FOR k,b IN SELECT anahtar,hal FROM motor.satirlar(m,'bildirimler') LOOP
  IF NOT irp.dogru(b->'gorulme_ani') AND (b->>'yapan'=b->>'alici' OR EXISTS(
   SELECT FROM jsonb_array_elements(motor.oku(m,'olaylar','[]')) e WHERE e->>'olay_kimligi'=b->>'doguran_olay' AND e->>'kim'=b->>'alici')) THEN
   PERFORM motor.kaydet(m,'bildirimler',k,b||jsonb_build_object('gorulme_ani',b->'an'));
  END IF;
 END LOOP;
END $$;
-- 153/154 ortak okuma genişletilirken düşen 151 maaş ayrıntısını geri bağla.
-- PLAN/GANTT/NOT_ALICILARI dalları ve tutar yetkisi korunur.
CREATE OR REPLACE FUNCTION public.oku(veri text,hedef text DEFAULT NULL,g jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text; deger jsonb;
BEGIN
 IF g IS NULL OR jsonb_typeof(g)<>'object' THEN RAISE EXCEPTION 'IRP|BICIM|Okuma parametreleri'; END IF;
 IF g ? 'kim' THEN
  IF coalesce(current_setting('role',true),'')<>'service_role' OR auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'IRP|YETKI|g.kim yalniz cekirdek servis rolune aittir'; END IF;
  kim=g->>'kim';
 ELSE kim=kapi.oturum_kisi(); END IF;
 IF kim IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 IF veri='WEB_KISI' THEN deger=okuma.web_kisi_ayrintisi(kim,hedef);
 ELSIF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 IF veri='PLAN' AND coalesce((g->>'surumler')::boolean,false) THEN
  deger=deger||jsonb_build_object('surumler',coalesce(okuma.satir('plan_surumleri',hedef),'[]'));
 END IF;
 IF veri='GANTT' AND coalesce((g->>'adlar')::boolean,false) THEN
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('ad',okuma.satir(CASE x->>'tur' WHEN 'ETAP' THEN 'etaplar' WHEN 'IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->'ad')),'[]') INTO deger
  FROM jsonb_array_elements(deger) x;
 END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
