SET ROLE irp_sahibi;
-- modul_bildirimi.py: kimlik ve görünür alıcı çözümü. Kalıcı tablo motor tarihçesine girmez.
CREATE FUNCTION irp.url_parcasi(v text) RETURNS text LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE b bytea=convert_to(v,'UTF8'); i int; c int; sonuc text=''; BEGIN
 FOR i IN 0..length(b)-1 LOOP c=get_byte(b,i); IF c BETWEEN 48 AND 57 OR c BETWEEN 65 AND 90 OR c BETWEEN 97 AND 122 OR c IN (45,46,95,126) THEN sonuc=sonuc||chr(c); ELSE sonuc=sonuc||'%'||upper(lpad(to_hex(c),2,'0')); END IF; END LOOP; RETURN sonuc; END $$;
CREATE FUNCTION k10_1.alici_gorebilir(d text,kisi text,kayit jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE p text; BEGIN
 IF NOT yetki_v6.istihdamda(d,kisi,yetki_v6.simdi(d)) OR motor.kayit(d,'kisiler',kisi)->'aktif'='false' THEN RETURN false; END IF;
 FOREACH p IN ARRAY k9.bagli_projeler(d,kayit->>'tur',kayit->>'kimlik') LOOP IF NOT k9.proje_gorebilir(d,kisi,p) THEN RETURN false; END IF; END LOOP; RETURN true; END $$;
CREATE FUNCTION k10_1.modul_kapilari(servis text,g jsonb,birak boolean) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE m jsonb; k jsonb=g->'kayit'; t timestamptz; BEGIN
 IF (SELECT son_yayin_ani FROM motor.durum WHERE tek) IS DISTINCT FROM saat.simdi() THEN PERFORM motor.iste(); IF (SELECT bekleyen_sinir FROM motor.durum WHERE tek) IS NOT NULL THEN RETURN kapi.red('HESAP_BEKLIYOR','Hesap bekliyor'); END IF; END IF;
 m=motor.kayit('YAYIN','moduller',g->>'modul');
 IF NOT irp.dogru(m) OR m->>'servis_kimligi' IS DISTINCT FROM servis OR birak AND NOT irp.dogru(m->'aktif') THEN RETURN kapi.red('YETKI','Modul servis kimligi veya etkinligi'); END IF;
 IF jsonb_typeof(g->'kural') IS DISTINCT FROM 'string' OR trim(coalesce(g->>'kural',''))='' OR jsonb_typeof(k) IS DISTINCT FROM 'object' OR coalesce(k->>'tur','') NOT IN ('PROJE','IS','GOREV','NESNE') OR jsonb_typeof(k->'kimlik') IS DISTINCT FROM 'string' OR trim(coalesce(k->>'kimlik',''))='' THEN RETURN kapi.red('BICIM','Modul bildirim kaydi'); END IF;
 IF irp.dogru(k->'modul_kaydi') AND jsonb_typeof(k->'modul_kaydi')<>'string' THEN RETURN kapi.red('BICIM','Modul kaydi metin'); END IF;
 BEGIN t=saat.an(g->>'an'); IF t IS NULL THEN RAISE EXCEPTION 'Bildirim ani'; END IF; EXCEPTION WHEN OTHERS THEN RETURN kapi.red('BICIM','Bildirim ani'); END;
 IF t>saat.simdi() THEN RETURN kapi.red('BICIM','Bildirim ani gelecekte olamaz'); END IF;
 IF NOT irp.dogru(kapi.nesne('YAYIN',k->>'tur',k->>'kimlik')) THEN RETURN kapi.red('DURUM','Bildirim kaydi yok'); END IF; RETURN NULL; END $$;
CREATE FUNCTION k10_1.alicilari_coz(d text,alicilar jsonb) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sonuc text[]='{}'; a jsonb; key text; k text; p jsonb; BEGIN
 IF jsonb_typeof(alicilar) IS DISTINCT FROM 'array' OR alicilar='[]' THEN PERFORM kapi.bicim_hatasi('Alici tanimi gerekli'); END IF;
 FOR a IN SELECT value FROM jsonb_array_elements(alicilar) LOOP
  IF jsonb_typeof(a)<>'object' OR jsonb_typeof(a->'kimlik') IS DISTINCT FROM 'string' OR trim(coalesce(a->>'kimlik',''))='' THEN PERFORM kapi.bicim_hatasi('Alici bicimi'); END IF; key=a->>'kimlik';
  CASE a->>'tur'
   WHEN 'KISI' THEN sonuc=array_append(sonuc,key);
   WHEN 'BIRIM_YONETICILERI' THEN sonuc=sonuc||yetki_v6.yoneticiler(d,key);
   WHEN 'ROL' THEN FOR k,p IN SELECT * FROM motor.satirlar(d,'kisiler') WHERE hal->'roller' ? key LOOP sonuc=array_append(sonuc,k); END LOOP;
   WHEN 'PROJEDE_YETKILILER' THEN FOR k IN SELECT anahtar FROM motor.satirlar(d,'kisiler') WHERE k10.projede_yetkili(d,anahtar,key) LOOP sonuc=array_append(sonuc,k); END LOOP;
   WHEN 'NESNE_SORUMLUSU' THEN sonuc=array_append(sonuc,motor.kayit(d,'nesneler',key)->>'sorumlu');
   ELSE PERFORM kapi.bicim_hatasi('Alici turu');
  END CASE;
 END LOOP; RETURN ARRAY(SELECT z FROM (SELECT DISTINCT z FROM unnest(sonuc) z WHERE z IS NOT NULL) q ORDER BY z COLLATE "C"); END $$;
CREATE FUNCTION k10_1.modul_birak(servis text,g jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE hata jsonb; adaylar text[]; ks text[]='{}'; k text; key text; x jsonb; p jsonb; araliklar jsonb; suzulenler jsonb='[]'; neden text; yeni int=0; simdi text=saat.kodla(saat.simdi()); zaman text; kayit jsonb=g->'kayit'; BEGIN
 hata=k10_1.modul_kapilari(servis,g,true); IF hata IS NOT NULL THEN RETURN hata; END IF;
 IF jsonb_typeof(g->'metin') IS DISTINCT FROM 'string' OR trim(coalesce(g->>'metin',''))='' OR coalesce(g->>'onem','') NOT IN ('BILGI','UYARI') THEN RETURN kapi.red('BICIM','Bildirim metni veya onemi'); END IF;
 BEGIN adaylar=k10_1.alicilari_coz('YAYIN',g->'alicilar'); EXCEPTION WHEN raise_exception THEN IF SQLERRM NOT LIKE 'IRP|BICIM|%' THEN RAISE; END IF; RETURN kapi.red('BICIM',substring(SQLERRM FROM 11)); END;
 FOREACH k IN ARRAY adaylar LOOP IF k10_1.alici_gorebilir('YAYIN',k,kayit) THEN ks=array_append(ks,k); ELSE
  p=motor.kayit('YAYIN','kisiler',k); neden=CASE WHEN p->'aktif'='false' OR irp.dogru(p->'ayrilis_tarihi') AND saat.gun(p->>'ayrilis_tarihi')<saat.gun(simdi) THEN 'AYRILDI' WHEN NOT yetki_v6.istihdamda('YAYIN',k,saat.simdi()) THEN 'ISTIHDAM_DISI' ELSE 'PROJEYI_GOREMEZ' END;
  suzulenler=suzulenler||jsonb_build_array(jsonb_build_object('kisi',k,'neden',neden)); END IF; END LOOP;
 zaman=saat.kodla(saat.an(g->>'an'));
 FOREACH k IN ARRAY ks LOOP key=irp.url_parcasi(g->>'modul')||'/'||irp.url_parcasi(g->>'kural')||'/'||irp.url_parcasi((kayit->>'tur')||':'||(kayit->>'kimlik'))||'/'||irp.url_parcasi(k);
  SELECT hal INTO x FROM public.modul_bildirimleri WHERE anahtar=key;
  IF NOT FOUND THEN yeni=yeni+1; x=jsonb_build_object('kimlik',key,'kaynak',g->'modul','kural',g->'kural','kayit',kayit,'alici',k,'an',zaman,'birakma_ani',simdi,'gorulme_ani',NULL,'gecerli',false,'etkinlik_araliklari','[]'::jsonb); END IF;
  IF NOT irp.dogru(x->'gecerli') THEN x=x||jsonb_build_object('etkinlik_araliklari',(x->'etkinlik_araliklari')||jsonb_build_array(jsonb_build_object('bas',simdi,'bit',NULL))); END IF;
  x=x||jsonb_build_object('metin',g->'metin','onem',g->'onem','gecerli',true,'guncelleme_ani',simdi,'son_kaynak_ani',zaman,'alici_tanimlari',g->'alicilar','cozulmus_alicilar',to_jsonb(ks),'kayit',kayit);
  INSERT INTO public.modul_bildirimleri VALUES(key,x) ON CONFLICT(anahtar) DO UPDATE SET hal=excluded.hal;
 END LOOP;
 RETURN jsonb_build_object('sonuc','BASARILI','alici_kalmadi',cardinality(ks)=0,'alicilar',to_jsonb(ks),'yeni',yeni,'guncellenen',cardinality(ks)-yeni,'suzulenler',suzulenler); END $$;
CREATE FUNCTION k10_1.modul_kaldir(servis text,g jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE hata jsonb; k text; x jsonb; a jsonb; sayi int=0; BEGIN
 hata=k10_1.modul_kapilari(servis,g,false); IF hata IS NOT NULL THEN RETURN hata; END IF;
 FOR k,x IN SELECT anahtar,hal FROM public.modul_bildirimleri WHERE hal->'kaynak'=g->'modul' AND hal->'kural'=g->'kural' AND hal#>'{kayit,tur}'=g#>'{kayit,tur}' AND hal#>'{kayit,kimlik}'=g#>'{kayit,kimlik}' LOOP
  IF irp.dogru(x->'gecerli') THEN sayi=sayi+1; a=x->'etkinlik_araliklari'; a=jsonb_set(a,ARRAY[(jsonb_array_length(a)-1)::text,'bit'],to_jsonb(saat.kodla(saat.simdi())));
   UPDATE public.modul_bildirimleri SET hal=x||jsonb_build_object('etkinlik_araliklari',a,'gecerli',false,'kaldirma_ani',saat.kodla(saat.simdi()),'son_kaynak_ani',saat.kodla(saat.an(g->>'an'))) WHERE anahtar=k;
  END IF;
 END LOOP; RETURN jsonb_build_object('sonuc','BASARILI','kaldirilan',sayi); END $$;
CREATE FUNCTION k10_1.modul_gorulmeleri_yansit(d text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE e jsonb; k text; x jsonb; BEGIN
 FOR e IN SELECT hal FROM motor.satirlar(d,'bildirim_gorulmeleri') ORDER BY hal->>'an' LOOP
  FOREACH k IN ARRAY irp.dizi(e->'bildirimler') LOOP SELECT hal INTO x FROM public.modul_bildirimleri WHERE anahtar=k;
   IF NOT FOUND OR e->'kim' IS DISTINCT FROM x->'alici' THEN CONTINUE; END IF;
   IF NOT EXISTS(SELECT FROM jsonb_array_elements(x->'etkinlik_araliklari') a WHERE saat.an(a->>'bas')<=saat.an(e->>'an') AND (a->>'bit' IS NULL OR saat.an(e->>'an')<=saat.an(a->>'bit'))) THEN CONTINUE; END IF;
   IF NOT irp.dogru(x->'gorulme_ani') OR saat.an(e->>'an')<saat.an(x->>'gorulme_ani') THEN UPDATE public.modul_bildirimleri SET hal=x||jsonb_build_object('gorulme_ani',e->'an') WHERE anahtar=k; END IF;
  END LOOP;
 END LOOP; END $$;
CREATE FUNCTION k9.bildirim_bul(d text,k text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE x jsonb; a text; BEGIN
 SELECT hal INTO x FROM public.modul_bildirimleri WHERE anahtar=k; IF x IS NOT NULL THEN RETURN x; END IF;
 -- kurallar_v9.bildirim_bul / bildirim_kimligi: iç anahtar ve dış kimlik.
 FOR a,x IN SELECT * FROM motor.satirlar(d,'bildirimler') LOOP
  IF a=k OR concat_ws('/',x->>'doguran_olay',x->>'kural',x->>'alici')=k THEN RETURN x; END IF;
 END LOOP; RETURN '{}'; END $$;
CREATE FUNCTION public.modul_bildirimi_birak(g jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
BEGIN PERFORM pg_advisory_xact_lock(202620,1); IF auth.role()<>'service_role' THEN RETURN kapi.red('YETKI','Modul servis kimligi veya etkinligi'); END IF; RETURN k10_1.modul_birak(kapi.oturum(),g); END $$;
CREATE FUNCTION public.modul_bildirimi_kaldir(g jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
BEGIN PERFORM pg_advisory_xact_lock(202620,1); IF auth.role()<>'service_role' THEN RETURN kapi.red('YETKI','Modul servis kimligi veya etkinligi'); END IF; RETURN k10_1.modul_kaldir(kapi.oturum(),g); END $$;
GRANT EXECUTE ON FUNCTION public.modul_bildirimi_birak(jsonb),public.modul_bildirimi_kaldir(jsonb) TO authenticated,service_role;
RESET ROLE;
