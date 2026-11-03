-- T27 / karar 125, 129, 157: modül kimliği ve dar servis kapıları.
-- Modül rolü JWT iddiasından alınmaz; gerçek veritabanı giriş rolü doğrulanır.
CREATE SCHEMA IF NOT EXISTS eklenti AUTHORIZATION irp_sahibi;
SET ROLE irp_sahibi;
REVOKE ALL ON SCHEMA eklenti FROM PUBLIC,anon,authenticated,service_role;
CREATE TABLE IF NOT EXISTS eklenti.kurulumlar (
 kod text PRIMARY KEY, rol name NOT NULL UNIQUE, kunye jsonb NOT NULL,
 ozet text NOT NULL, surum text NOT NULL, etkin boolean NOT NULL DEFAULT false,
 web jsonb NOT NULL DEFAULT '{}',
 kuruldu timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS eklenti.gocler (
 kod text NOT NULL REFERENCES eklenti.kurulumlar(kod), ad text NOT NULL, ozet text NOT NULL,
 PRIMARY KEY(kod,ad)
);
CREATE TABLE IF NOT EXISTS eklenti.kullanim (
 kod text NOT NULL, kapi text NOT NULL, dakika timestamptz NOT NULL, sayi int NOT NULL,
 PRIMARY KEY(kod,kapi,dakika)
);
REVOKE ALL ON ALL TABLES IN SCHEMA eklenti FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION eklenti.kimlik(pasif_olabilir boolean DEFAULT false) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE k jsonb; m jsonb; etkin boolean; BEGIN
 SELECT kunye,kurulumlar.etkin INTO k,etkin FROM eklenti.kurulumlar WHERE rol=session_user::name;
 IF k IS NULL OR NOT etkin AND NOT pasif_olabilir THEN RAISE EXCEPTION 'IRP|YETKI|Modul servis kimligi'; END IF;
 m=motor.kayit('YAYIN','moduller',k->>'kod');
 IF m IS NULL OR m->>'servis_kimligi' IS DISTINCT FROM k->>'servis_kimligi'
    OR NOT pasif_olabilir AND NOT coalesce((m->>'aktif')::boolean,false) THEN
  RAISE EXCEPTION 'IRP|YETKI|Modul etkin degil';
 END IF;
 RETURN k;
END $$;
REVOKE ALL ON FUNCTION eklenti.kimlik(boolean) FROM PUBLIC,anon,authenticated,service_role;

CREATE FUNCTION eklenti.kota(k jsonb,kapisi text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE sinir int=(k#>>ARRAY['sinirlar',kapisi])::int; sayi_ int; dakika_ timestamptz=date_trunc('minute',clock_timestamp()); BEGIN
 IF sinir IS NULL OR sinir<1 THEN RAISE EXCEPTION 'IRP|YETKI|Kapi kunyede yok'; END IF;
 INSERT INTO eklenti.kullanim AS u VALUES(k->>'kod',kapisi,dakika_,1)
 ON CONFLICT(kod,kapi,dakika) DO UPDATE SET sayi=u.sayi+1 RETURNING sayi INTO sayi_;
 IF sayi_>sinir THEN RAISE EXCEPTION 'IRP|SINIR|Modul istek siniri'; END IF;
 DELETE FROM eklenti.kullanim WHERE dakika<dakika_-interval '2 minutes';
END $$;

CREATE FUNCTION public.modul_oturum(modul text DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE kisi text; roller jsonb; r jsonb; BEGIN
 kisi=kapi.oturum_kisi();
 IF kisi IS NULL OR NOT yetki_v6.istihdamda('YAYIN',kisi,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 roller=motor.kayit('YAYIN','kisiler',kisi)->'roller';
 SELECT coalesce(jsonb_agg(jsonb_build_object('kod',e.kod,'ad',coalesce(e.web->>'ad',e.kunye->>'ad'),
  'surum',e.surum,'yol',e.web->>'yol','ekran',e.web->>'ekran','kimler',e.web->'kimler') ORDER BY e.kod),'[]') INTO r
 FROM eklenti.kurulumlar e WHERE e.etkin AND coalesce((motor.kayit('YAYIN','moduller',e.kod)->>'aktif')::boolean,false)
  AND (modul IS NULL AND (coalesce(e.web->'kimler','[]')='[]' OR roller ?| irp.dizi(e.web->'kimler')) OR e.kod=modul);
 RETURN jsonb_build_object('kisi',kisi,'roller',roller,'moduller',r);
END $$;
REVOKE ALL ON FUNCTION public.modul_oturum(text) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.modul_oturum(text) TO authenticated;

CREATE FUNCTION eklenti.alanlar(x jsonb,alanlar text[]) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce(jsonb_object_agg(key,value),'{}') FROM jsonb_each(coalesce(x,'{}')) WHERE key=ANY(alanlar)
$$;

CREATE FUNCTION public.servis_oku(veri text,hedef text DEFAULT NULL,g jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE k jsonb; r jsonb; x jsonb; a text; alanlar text[]; tablo text; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 PERFORM motor.iste();
 k=eklenti.kimlik();
 IF g IS NULL OR jsonb_typeof(g)<>'object' OR g ?| ARRAY['kim','cagiran','oturum','servis_kimligi'] THEN
  RAISE EXCEPTION 'IRP|YETKI|Servis kisi adina okuyamaz'; END IF;
 IF NOT coalesce(k#>'{kapilar,servis_okumalari}','[]') ? veri THEN RAISE EXCEPTION 'IRP|YETKI|Servis okumasi kunyede yok'; END IF;
 PERFORM eklenti.kota(k,'servis_okuma_dakika');
 CASE veri
 WHEN 'PROJE','PROJELER' THEN
  tablo='projeler'; alanlar=ARRAY['kimlik','kod','ad','sorumlu','aktif','ana_proje','baslangic_tarihi','teslim_tarihi','kesin_kabul_tarihi','surum'];
 WHEN 'ETAP','ETAPLAR' THEN
  tablo='etaplar'; alanlar=ARRAY['kimlik','ad','proje','birim','sorumlu','baslangic','bitis','hedef_saat','surum'];
 WHEN 'KISILER' THEN
  tablo='kisiler'; alanlar=ARRAY['kimlik','birim','yaka','roller','aktif','surum'];
 WHEN 'BIRIMLER' THEN
  tablo='birimler'; alanlar=ARRAY['kimlik','kod','ad','ust_birim','basi','surum'];
 WHEN 'NESNE','NESNELER' THEN
  tablo='nesneler'; alanlar=ARRAY['kimlik','tur','kod','ad','proje','asama','sorumlu','baglar','asama_ani','surum'];
 WHEN 'TEZGAHLAR' THEN
  tablo='tezgahlar'; alanlar=ARRAY['kimlik','kod','ad','birim','aktif','surum'];
 WHEN 'KODLAR' THEN
  tablo='kod_listesi'; alanlar=ARRAY['kimlik','liste','kod','ad','ust','aktif','surum'];
 WHEN 'GECERLI_SURUM' THEN
  r=eklenti.alanlar(okuma.gecerli_surum(coalesce(g->>'nesne',hedef)),ARRAY['nesne','surum_no','surum_adi','durum','dosyalar','eklenme_ani','onay_ani']);
 WHEN 'TOP_KIMDE' THEN r=okuma.top_kimde(coalesce(g->>'nesne',hedef));
 WHEN 'TEZGAH_GOSTERGESI' THEN r=okuma.tezgah_gostergesi(hedef,g->>'bas',g->>'bit');
 WHEN 'TEZGAH_UYGUNLUK' THEN r=okuma.tezgah_uygun_mu(hedef,g->>'bas',g->>'bit');
 ELSE RAISE EXCEPTION 'IRP|YETKI|Servis kisisel veya parasal veri okuyamaz';
 END CASE;
 IF tablo IS NOT NULL THEN
  IF veri IN ('PROJE','ETAP','NESNE') THEN
   x=okuma.satir(tablo,hedef);
   r=CASE WHEN x IS NULL THEN NULL ELSE eklenti.alanlar(x||jsonb_build_object('kimlik',hedef),alanlar) END;
  ELSE
   SELECT coalesce(jsonb_agg(eklenti.alanlar(x||jsonb_build_object('kimlik',a),alanlar) ORDER BY a),'[]') INTO r
   FROM okuma.satirlar(tablo) z(a,x)
   WHERE (veri<>'ETAPLAR' OR x->>'proje'=coalesce(g->>'proje',hedef))
    AND (veri<>'NESNELER' OR coalesce(g->>'proje',hedef,'')='' OR x->>'proje'=coalesce(g->>'proje',hedef))
    AND (veri<>'KISILER' OR coalesce(g->>'birim',hedef,'')='' OR x->>'birim'=coalesce(g->>'birim',hedef))
    AND (veri<>'KODLAR' OR hedef IS NULL OR x->>'liste'=hedef);
  END IF;
 END IF;
 RETURN jsonb_build_object('deger',r,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,
  'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
REVOKE ALL ON FUNCTION public.servis_oku(text,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.modul_bildirimi_birak(g jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
DECLARE k jsonb; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 -- Eski çekirdek sınamaları/işletim yolu korunur; modüle service_role verilmez.
 IF auth.role()='service_role' AND coalesce(current_setting('role',true),'')='service_role' THEN
  RETURN k10_1.modul_birak(kapi.oturum(),g);
 END IF;
 PERFORM motor.iste(); k=eklenti.kimlik();
 PERFORM eklenti.kota(k,'bildirim_dakika');
 IF g->>'modul' IS DISTINCT FROM k->>'kod' THEN RAISE EXCEPTION 'IRP|YETKI|Baska modul bildirimi'; END IF;
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(k#>'{kapilar,bildirimler}') b WHERE b->>'kural'=g->>'kural'
  AND b->'kayit_turleri' ? (g#>>'{kayit,tur}')
  AND NOT EXISTS(SELECT FROM jsonb_array_elements(g->'alicilar') a WHERE NOT b->'alici_turleri' ? (a->>'tur'))) THEN
  RAISE EXCEPTION 'IRP|YETKI|Bildirim kunyede yok'; END IF;
 RETURN k10_1.modul_birak(k->>'servis_kimligi',g);
END $$;
CREATE OR REPLACE FUNCTION public.modul_bildirimi_kaldir(g jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
DECLARE k jsonb; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 IF auth.role()='service_role' AND coalesce(current_setting('role',true),'')='service_role' THEN
  RETURN k10_1.modul_kaldir(kapi.oturum(),g);
 END IF;
 PERFORM motor.iste(); k=eklenti.kimlik(true);
 PERFORM eklenti.kota(k,'bildirim_dakika');
 IF g->>'modul' IS DISTINCT FROM k->>'kod' OR NOT EXISTS(
  SELECT FROM jsonb_array_elements(k#>'{kapilar,bildirimler}') b WHERE b->>'kural'=g->>'kural') THEN
  RAISE EXCEPTION 'IRP|YETKI|Bildirim kunyede yok'; END IF;
 RETURN k10_1.modul_kaldir(k->>'servis_kimligi',g);
END $$;
-- Dar modül rollerine EXECUTE haklarını kurulum verir. Normal kullanıcı servis kapısına giremez.
RESET ROLE;
