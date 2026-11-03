-- T28: özel modül dosyasının ortak kimliği. Baytlar mevcut MVP webinin özel deposundadır.
-- Modül kendi rolüyle bu tabloyu okuyamaz; normal kullanıcı ve kaynak modülün izni geçitte doğrulanır.
SET ROLE irp_sahibi;
CREATE TABLE eklenti.dosyalar (
 kimlik text PRIMARY KEY,
 modul text NOT NULL REFERENCES eklenti.kurulumlar(kod),
 kayit jsonb NOT NULL,
 ad text NOT NULL,
 boyut integer NOT NULL CHECK(boyut BETWEEN 1 AND 1048576),
 tur text NOT NULL,
 parmak_izi text NOT NULL CHECK(parmak_izi ~ '^[0-9a-f]{64}$'),
 olusturan text NOT NULL,
 an timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON eklenti.dosyalar FROM PUBLIC,anon,authenticated,service_role;

-- Projesi henüz olmayan teklif bildirimi özel modül nesnesidir; sahte proje yaratılmaz.
CREATE OR REPLACE FUNCTION k10_1.alici_gorebilir(d text,kisi text,kayit jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE p text; row_ record; BEGIN
 IF NOT yetki_v6.istihdamda(d,kisi,yetki_v6.simdi(d)) OR motor.kayit(d,'kisiler',kisi)->'aktif'='false' THEN RETURN false; END IF;
 IF kayit->>'tur'='MODUL' THEN
  SELECT etkin,web INTO row_ FROM eklenti.kurulumlar WHERE kod=kayit->>'modul';
  RETURN FOUND AND row_.etkin AND (coalesce(row_.web->'kimler','[]')='[]' OR
    motor.kayit(d,'kisiler',kisi)->'roller' ?| irp.dizi(row_.web->'kimler'));
 END IF;
 FOREACH p IN ARRAY k9.bagli_projeler(d,kayit->>'tur',kayit->>'kimlik') LOOP
  IF NOT k9.proje_gorebilir(d,kisi,p) THEN RETURN false; END IF;
 END LOOP; RETURN true;
END $$;

CREATE OR REPLACE FUNCTION k10_1.modul_kapilari(servis text,g jsonb,birak boolean) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE m jsonb; k jsonb=g->'kayit'; t timestamptz; BEGIN
 IF (SELECT son_yayin_ani FROM motor.durum WHERE tek) IS DISTINCT FROM saat.simdi() THEN
  PERFORM motor.iste(); IF (SELECT bekleyen_sinir FROM motor.durum WHERE tek) IS NOT NULL THEN RETURN kapi.red('HESAP_BEKLIYOR','Hesap bekliyor'); END IF;
 END IF;
 m=motor.kayit('YAYIN','moduller',g->>'modul');
 IF NOT irp.dogru(m) OR m->>'servis_kimligi' IS DISTINCT FROM servis OR birak AND NOT irp.dogru(m->'aktif') THEN RETURN kapi.red('YETKI','Modul servis kimligi veya etkinligi'); END IF;
 IF jsonb_typeof(g->'kural') IS DISTINCT FROM 'string' OR trim(coalesce(g->>'kural',''))='' OR jsonb_typeof(k) IS DISTINCT FROM 'object' OR
  coalesce(k->>'tur','') NOT IN ('PROJE','IS','GOREV','NESNE','MODUL') OR jsonb_typeof(k->'kimlik') IS DISTINCT FROM 'string' OR trim(coalesce(k->>'kimlik',''))='' THEN RETURN kapi.red('BICIM','Modul bildirim kaydi'); END IF;
 IF irp.dogru(k->'modul_kaydi') AND jsonb_typeof(k->'modul_kaydi')<>'string' THEN RETURN kapi.red('BICIM','Modul kaydi metin'); END IF;
 IF k->>'tur'='MODUL' AND k->>'modul' IS DISTINCT FROM g->>'modul' THEN RETURN kapi.red('YETKI','Modul ozel nesnesi'); END IF;
 BEGIN t=saat.an(g->>'an'); IF t IS NULL THEN RAISE EXCEPTION 'Bildirim ani'; END IF; EXCEPTION WHEN OTHERS THEN RETURN kapi.red('BICIM','Bildirim ani'); END;
 IF t>saat.simdi() THEN RETURN kapi.red('BICIM','Bildirim ani gelecekte olamaz'); END IF;
 IF k->>'tur'<>'MODUL' AND NOT irp.dogru(kapi.nesne('YAYIN',k->>'tur',k->>'kimlik')) THEN RETURN kapi.red('DURUM','Bildirim kaydi yok'); END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION okuma.not_alicilari(kim text,not_kimligi text) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE liste jsonb; adet integer; BEGIN
 IF okuma.satir('notlar',not_kimligi) IS NULL OR NOT okuma.gorebilir(kim,'NOT',not_kimligi) THEN
  RAISE EXCEPTION 'IRP|YETKI|Not gorunurlugu'; END IF;
 SELECT count(*) INTO adet FROM okuma.satirlar('gorevler') WHERE x->>'tur'='NOT' AND x->>'kaynak'=not_kimligi;
 SELECT coalesce(jsonb_agg(jsonb_build_object('gorev',k,'kisi',x->'kisi','durum',x->'durum',
   'gordu',x->>'durum'='BITTI','kabul_ani',x->'kabul_ani') ORDER BY k COLLATE "C"),'[]') INTO liste
 FROM okuma.satirlar('gorevler') WHERE x->>'tur'='NOT' AND x->>'kaynak'=not_kimligi AND okuma.gorebilir(kim,'GOREV',k);
 RETURN jsonb_build_object('alicilar',liste,'liste_tam',jsonb_array_length(liste)=adet);
END $$;

-- Normal okumaların mevcut izin ve cevap biçimi korunur.
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
 IF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
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
