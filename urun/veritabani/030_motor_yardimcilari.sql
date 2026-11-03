SET ROLE irp_sahibi;
CREATE FUNCTION irp.sabit(a text) RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT hal FROM irp.sozluk WHERE ad=a $$;
CREATE FUNCTION irp.dizi(x jsonb) RETURNS text[] LANGUAGE sql IMMUTABLE AS $$ SELECT coalesce(array_agg(value ORDER BY n),'{}') FROM jsonb_array_elements_text(coalesce(nullif(x,'null'),'[]')) WITH ORDINALITY z(value,n) $$;
CREATE FUNCTION motor.bosalt(d text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE a text; v jsonb;
BEGIN
 DELETE FROM motor.calisma WHERE kip=d; DELETE FROM motor.anahtar_sirasi WHERE kip=d;
 FOR a,v IN SELECT * FROM jsonb_each(irp.sabit('bos_hal')) LOOP PERFORM motor.yaz(d,a,v); END LOOP;
END $$;
-- motor.py:22 takvim, 32 is_gunu, 36 sabit_molada, 39 ayar.
CREATE FUNCTION motor.takvim(d text,tarih text,kisi text DEFAULT NULL,birim text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE tanim jsonb; uygun jsonb; esik timestamptz;
BEGIN
 tanim=motor.kayit(d,'gun_tanimlari',saat.gun(tarih)::text);
 IF irp.dogru(tanim) AND (tanim->>'tur')<>'TATIL' THEN RETURN tanim||jsonb_build_object('calisma_gunleri',jsonb_build_array(extract(isodow FROM saat.gun(tarih)))); END IF;
 uygun=takvim.birim_takvimi(d,tarih,kisi,birim); IF uygun IS NOT NULL THEN RETURN uygun; END IF;
 esik=CASE WHEN position('T' IN tarih)>0 THEN saat.an(tarih) ELSE saat.gun_ani(saat.gun(tarih),'08:00') END;
 SELECT value INTO uygun FROM jsonb_array_elements(motor.oku(d,'takvimler','[]')) WHERE saat.an((value->>'gecerli_baslangic'))<=esik ORDER BY (value->>'gecerli_baslangic') DESC LIMIT 1;
 RETURN coalesce(uygun,motor.oku(d,'varsayilan_takvim'));
END $$;
CREATE FUNCTION motor.is_gunu(d text,tarih text,kisi text DEFAULT NULL,birim text DEFAULT NULL) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT (motor.takvim(d,tarih,kisi,birim)->'calisma_gunleri') @> to_jsonb(extract(isodow FROM saat.gun(tarih))::int)
 AND NOT motor.oku(d,'tatiller','[]') ? saat.gun(tarih)::text $$;
CREATE FUNCTION motor.sabit_molada(d text,t timestamptz,kisi text DEFAULT NULL) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT motor.is_gunu(d,saat.kodla(t),kisi) AND EXISTS(SELECT FROM jsonb_array_elements(motor.takvim(d,saat.kodla(t),kisi)->'sabit_molalar') x
 WHERE saat.gun_ani(saat.gun(saat.kodla(t)),(x->>'bas'))<=t AND t<saat.gun_ani(saat.gun(saat.kodla(t)),(x->>'bit'))) $$;
CREATE FUNCTION motor.ayar(d text,a text,t timestamptz,varsayilan jsonb) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT (x->'deger') FROM jsonb_array_elements(motor.oku(d,'ayarlar','[]')) x WHERE (x->>'anahtar')=a AND saat.an((x->>'gecerli_baslangic'))<=t
 ORDER BY (x->>'gecerli_baslangic') DESC,(x->>'doguran_olay') COLLATE "C" DESC LIMIT 1),varsayilan) $$;
-- motor.py:43 supheli, 46 bildir, 51 sonuc.
CREATE FUNCTION motor.supheli(d text,e jsonb,neden text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 PERFORM motor.kaydet(d,'supheliler',(e->>'olay_kimligi'),jsonb_build_object('olay',(e->>'olay_kimligi'),'kural','R10','gerekce',neden)); END $$;
CREATE FUNCTION motor.bildir(d text,e jsonb,kural text,alici text,t timestamptz,kisi text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 IF NOT irp.dogru(e) OR alici IS NULL OR alici='' THEN RETURN; END IF;
 PERFORM motor.kaydet(d,'bildirimler',(e->>'olay_kimligi')||':'||kural||':'||alici,jsonb_build_object('doguran_olay',(e->>'olay_kimligi'),'kural',kural,'alici',alici,'an',saat.kodla(t),'metin',kisi,'gecerli',true,'olusma_ani',saat.kodla(saat.gercek()),'gorulme_ani',NULL)); END $$;
CREATE FUNCTION motor.sonuc(d text,e jsonb,kural text,nesne text,onceki text,yeni text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 BEGIN
 IF onceki IS DISTINCT FROM yeni THEN PERFORM motor.kaydet(d,'sonuclar',(e->>'olay_kimligi')||':'||kural||':'||nesne,jsonb_build_object('doguran_olay',(e->>'olay_kimligi'),'kural',kural,'kural_versiyonu',1,'nesne_kimlik',nesne,'onceki_durum',onceki,'yeni_durum',yeni,'an',(e->'oldugu_an'))); END IF; END $$;
-- yetki_v6.py:54 istihdamda, 61 simdi, 65 yoneticiler, 71 birim_ustleri, 80 ustler.
CREATE FUNCTION yetki_v6.istihdamda(d text,k text,t timestamptz) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
 DECLARE p jsonb; BEGIN
 p=motor.kayit(d,'kisiler',k); RETURN EXISTS(SELECT FROM jsonb_array_elements(coalesce((p->'istihdam_donemleri'),jsonb_build_array(jsonb_build_object('giris',(p->'giris_tarihi'),'ayrilis',(p->'ayrilis_tarihi'))))) x
 WHERE irp.dogru((x->'giris')) AND ((x->>'giris'))::date<=saat.gun(saat.kodla(t)) AND (NOT irp.dogru((x->'ayrilis')) OR saat.gun(saat.kodla(t))<=((x->>'ayrilis'))::date)); END $$;
CREATE FUNCTION yetki_v6.simdi(d text) RETURNS timestamptz LANGUAGE sql STABLE AS $$ SELECT coalesce(saat.an(motor.oku(d,'_an','null')#>>'{}'),saat.simdi()) $$;
CREATE FUNCTION yetki_v6.yoneticiler(d text,b text) RETURNS text[] LANGUAGE sql STABLE AS $$
 SELECT coalesce(array_agg(DISTINCT k COLLATE "C" ORDER BY k COLLATE "C"),'{}') FROM (
 SELECT motor.kayit(d,'birimler',b)->>'basi' k UNION SELECT anahtar FROM motor.satirlar(d,'kisiler') WHERE (hal->>'birim')=b AND (hal->'roller') ? 'EKIP_LIDERI') z
 WHERE k IS NOT NULL AND yetki_v6.istihdamda(d,k,yetki_v6.simdi(d)) $$;
CREATE FUNCTION yetki_v6.birim_ustleri(d text,birim text) RETURNS text[] LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE b text; gezilen text[]='{}'; sonuc text[]='{}'; BEGIN
 b=motor.kayit(d,'birimler',birim)->>'ust_birim';
 WHILE b IS NOT NULL AND b<>'' AND NOT b=ANY(gezilen) LOOP gezilen=array_append(gezilen,b); sonuc=sonuc||yetki_v6.yoneticiler(d,b); b=motor.kayit(d,'birimler',b)->>'ust_birim'; END LOOP;
 RETURN ARRAY(SELECT DISTINCT x COLLATE "C" FROM unnest(sonuc) x ORDER BY 1); END $$;
CREATE FUNCTION yetki_v6.ustler(d text,k text) RETURNS text[] LANGUAGE sql STABLE AS $$
 SELECT ARRAY(SELECT DISTINCT x COLLATE "C" FROM unnest(yetki_v6.yoneticiler(d,motor.kayit(d,'kisiler',k)->>'birim')||yetki_v6.birim_ustleri(d,motor.kayit(d,'kisiler',k)->>'birim')) x WHERE x<>k ORDER BY 1) $$;
-- kurallar_v6.py:10 kod_aktif, 93 ana_veri.
CREATE FUNCTION k6.kod_aktif(d text,liste text,k text) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT irp.dogru(motor.kayit(d,'kod_listesi',liste||':'||k)->'aktif') $$;
CREATE FUNCTION k6.ana_veri(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); t text=saat.kodla(saat.an((e->>'oldugu_an'))); p jsonb; rs jsonb; r jsonb; k text; a text;
BEGIN
 IF kod='KOD.TANIMLADIM' THEN PERFORM motor.kaydet(d,'kod_listesi',(g->>'liste')||':'||(g->>'kod'),g);
 ELSIF kod='YETKI.TANIMLADIM' THEN
  rs='[]'; FOR r IN SELECT value FROM jsonb_array_elements(motor.oku(d,'yetki_kurallari','[]')) LOOP
   IF (r->>'eylem_kodu')=(g->>'eylem_kodu') AND NOT irp.dogru((r->'gecerli_bitis')) THEN r=r||jsonb_build_object('gecerli_bitis',t); END IF;
   rs=rs||jsonb_build_array(r); END LOOP;
  PERFORM motor.yaz(d,'yetki_kurallari',rs||jsonb_build_array(g||jsonb_build_object('gecerli_baslangic',t,'gecerli_bitis',NULL,'doguran_olay',(e->'olay_kimligi'))));
 ELSIF kod='KURULUM.TAMAMLADIM' THEN PERFORM motor.yaz(d,'kurulum_kaynagi',(e->'olay_kimligi'));
 ELSIF kod='TATIL.KALDIRDIM' THEN NULL;
 ELSIF kod='KISI.EKLEDIM' THEN
  k=(g->>'kod'); p=motor.kayit(d,'kisiler',k); rs=coalesce((p->'istihdam_donemleri'),'[]')||jsonb_build_array(jsonb_build_object('giris',(g->'giris_tarihi'),'ayrilis',NULL));
  IF irp.dogru(p) THEN PERFORM motor.yaz(d,'kisi_gecmisi',(SELECT coalesce(jsonb_agg(CASE WHEN (x->>'kisi')=k AND (x->'gecerli_bitis')='null' THEN x||jsonb_build_object('gecerli_bitis',(g->'giris_tarihi')) ELSE x END ORDER BY n),'[]') FROM jsonb_array_elements(motor.oku(d,'kisi_gecmisi','[]')) WITH ORDINALITY z(x,n))); END IF;
  PERFORM motor.kaydet(d,'kisiler',k,g||jsonb_build_object('ayrilis_tarihi',NULL,'istihdam_donemleri',rs));
  PERFORM motor.ekle(d,'kisi_gecmisi',g||jsonb_build_object('kisi',k,'gecerli_baslangic',(g->'giris_tarihi'),'gecerli_bitis',NULL));
  IF (e->>'giris_sekli')<>'AKTARIM' THEN FOREACH a IN ARRAY yetki_v6.yoneticiler(d,(g->>'birim')) LOOP IF a<>k THEN PERFORM motor.bildir(d,e,'R28',a,saat.an(t),k); END IF; END LOOP; END IF;
 ELSIF kod='KISI.AYRILDI' THEN
  k=(g->>'kisi'); p=motor.kayit(d,'kisiler',k); r=CASE WHEN irp.dogru((g->'iptal')) THEN 'null'::jsonb ELSE (g->'ayrilis_tarihi') END;
  p=jsonb_set(p||jsonb_build_object('ayrilis_tarihi',r),ARRAY['istihdam_donemleri',(jsonb_array_length((p->'istihdam_donemleri'))-1)::text,'ayrilis'],r);
  PERFORM motor.kaydet(d,'kisiler',k,p);
  IF (e->>'giris_sekli')<>'AKTARIM' THEN FOR a IN SELECT DISTINCT x COLLATE "C" FROM (SELECT unnest(yetki_v6.yoneticiler(d,(p->>'birim'))) x UNION SELECT anahtar FROM motor.satirlar(d,'kisiler') WHERE (hal->'roller') ? 'YETKILI' AND yetki_v6.istihdamda(d,anahtar,saat.an(t))) z ORDER BY 1 LOOP PERFORM motor.bildir(d,e,'R29',a,saat.an(t),k); END LOOP; END IF;
 ELSE RETURN false; END IF; RETURN true;
END $$;
-- motor.py:66 ana_veri_isle; her dal kendi tablo değişikliğini kaydeder.
CREATE FUNCTION motor.ana_veri_isle(d text,e jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE kod text=(e->>'eylem_kodu'); g jsonb=(e->'girdiler'); a text; k text; p jsonb; ks text[]; n integer=0;
BEGIN
 IF k6.ana_veri(d,e) THEN RETURN; END IF;
 a=CASE kod WHEN 'BIRIM.TANIMLADIM' THEN 'birimler' WHEN 'PROJE.ACTIM' THEN 'projeler' WHEN 'TEZGAH.TANIMLADIM' THEN 'tezgahlar' END;
 IF a IS NOT NULL THEN p=motor.kayit(d,a,(g->>'kod'))||g; IF a IN ('projeler','tezgahlar') THEN p=jsonb_build_object('aktif',true)||p; END IF; PERFORM motor.kaydet(d,a,(g->>'kod'),p);
 ELSIF kod='PROJE.DEGISTIRDIM' THEN k=(kapi.hedefler(e,'PROJE'))[1]; PERFORM motor.kaydet(d,'projeler',k,motor.kayit(d,'projeler',k)||(g->'degisenler'));
 ELSIF kod='PROJE.KAPATTIM' THEN k=(kapi.hedefler(e,'PROJE'))[1]; PERFORM motor.kaydet(d,'projeler',k,motor.kayit(d,'projeler',k)||jsonb_build_object('aktif',false,'kapanis_ani',saat.kodla(saat.an((e->>'oldugu_an')))));
 ELSIF kod='ETAP.DEGISTIRDIM' THEN k=(kapi.hedefler(e,'ETAP'))[1]; PERFORM motor.kaydet(d,'etaplar',k,motor.kayit(d,'etaplar',k)||(g->'degisenler'));
 ELSIF kod='KISI.DEGISTIRDIM' THEN
  k=(g->>'kisi'); p=motor.kayit(d,'kisiler',k); IF NOT irp.dogru(p) THEN RETURN; END IF; p=p||(g->'degisenler'); PERFORM motor.kaydet(d,'kisiler',k,p);
  PERFORM motor.yaz(d,'kisi_gecmisi',(SELECT coalesce(jsonb_agg(CASE WHEN (x->>'kisi')=k AND (x->'gecerli_bitis')='null' THEN x||jsonb_build_object('gecerli_bitis',coalesce((g->'gecerli_baslangic'),(e->'oldugu_an'))) ELSE x END ORDER BY n),'[]') FROM jsonb_array_elements(motor.oku(d,'kisi_gecmisi','[]')) WITH ORDINALITY z(x,n)));
  PERFORM motor.ekle(d,'kisi_gecmisi',(p-'istihdam_donemleri'-'ayrilis_tarihi')||jsonb_build_object('kisi',k,'gecerli_baslangic',coalesce((g->'gecerli_baslangic'),(e->'oldugu_an')),'gecerli_bitis',NULL));
 ELSIF kod='AYAR.YONLENDIRDIM' THEN PERFORM motor.kaydet(d,'yonlendirme',(g->>'birim'),(g->'kisiler'));
 ELSIF kod='ETAP.TANIMLADIM' THEN PERFORM motor.kaydet(d,'etaplar',(e->>'olay_kimligi'),g||jsonb_build_object('kimlik',(e->'olay_kimligi'),'doguran_olay',(e->'olay_kimligi')));
 ELSIF kod='NOT.YAZDIM' THEN
  k=(e->>'olay_kimligi'); p=g||jsonb_build_object('kimlik',k,'neyin_ustunde',(e->'neyin_ustunde'),'kanit',(e->'kanit'),'yazan',(e->'kim'),'an',(e->'oldugu_an')); PERFORM motor.kaydet(d,'notlar',k,p);
  FOR a IN SELECT DISTINCT x COLLATE "C" FROM jsonb_array_elements_text(coalesce((g->'etiketler'),'[]')) b CROSS JOIN LATERAL jsonb_array_elements_text(motor.kayit(d,'yonlendirme',b,'[]')) x ORDER BY 1 LOOP
   n=n+1; IF NOT irp.dogru(motor.kayit(d,'kisiler',a)) OR irp.dogru(motor.kayit(d,'kisiler',a)->'ayrilis_tarihi') OR k6.not_alicisi_ayrilmis(d,a,e) THEN
    p=p||jsonb_build_object('atlanan_alicilar',coalesce((p->'atlanan_alicilar'),'[]')||jsonb_build_array(a)); PERFORM motor.kaydet(d,'notlar',k,p); CONTINUE; END IF;
   PERFORM gorev.gorev_dogur(d,e,jsonb_build_object('ad',(g->'metin'),'kisi',a,'kaynak',k,'zaman_degeri',0,'teslim_tarihi',NULL),k||'/'||n,'NOT'); END LOOP;
 ELSIF kod IN ('TAKVIM.TANIMLADIM','TATIL.EKLEDIM','AYAR.ONAY_ORANI','AYAR.MAAS_PAYDASI','AYAR.PARCA_KODU_DESENI','MAAS.GUNCELLEDIM','AYAR.SAAT_KAYDIRDIM','KAYIT.GECERSIZ_SAYDIM') THEN NULL;
 END IF;
END $$;
CREATE FUNCTION k6.not_alicisi_ayrilmis(d text,k text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE x jsonb; ayrildi boolean=false; esira bigint; BEGIN
 IF (e->>'giris_sekli')='AKTARIM' THEN RETURN irp.dogru(motor.kayit(d,'kisiler',k)->'ayrilis_tarihi'); END IF;
 SELECT kabul_no INTO esira FROM public.olaylar WHERE olay_kimligi=(e->>'olay_kimligi');
 FOR x IN SELECT icerik FROM public.olaylar WHERE (bulut_ulasma_ani,kabul_no)<(saat.an(coalesce((e->>'bulut_ulasma_ani'),(e->>'oldugu_an'))),esira)
 AND ((eylem_kodu='KISI.EKLEDIM' AND (icerik#>>'{girdiler,kod}')=k) OR (eylem_kodu='KISI.AYRILDI' AND (icerik#>>'{girdiler,kisi}')=k)) ORDER BY bulut_ulasma_ani,kabul_no LOOP ayrildi=(x->>'eylem_kodu')='KISI.AYRILDI' AND NOT irp.dogru((x#>'{girdiler,iptal}')); END LOOP;
 RETURN ayrildi; END $$;
-- liste.py:4 yerlestir; JSON dizisini aynı sıra ile döndürür.
CREATE FUNCTION liste.yerlestir(l jsonb,k text,sira integer) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column

DECLARE a jsonb; n integer; BEGIN a=(SELECT coalesce(jsonb_agg(x ORDER BY s),'[]') FROM jsonb_array_elements(l) WITH ORDINALITY z(x,s) WHERE x<>to_jsonb(k)); n=greatest(0,least(jsonb_array_length(a),sira-1));
 RETURN (SELECT coalesce(jsonb_agg(x ORDER BY s),'[]') FROM (SELECT x,s*2 s FROM jsonb_array_elements(a) WITH ORDINALITY z(x,s) UNION ALL SELECT to_jsonb(k),n*2+1) q); END $$;
CREATE FUNCTION liste.cikar(d text,k text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE a text; l jsonb; BEGIN
 FOR a,l IN SELECT * FROM motor.satirlar(d,'listeler') LOOP IF l ? k THEN PERFORM motor.kaydet(d,'listeler',a,(SELECT coalesce(jsonb_agg(x ORDER BY n),'[]') FROM jsonb_array_elements(l) WITH ORDINALITY z(x,n) WHERE x<>to_jsonb(k))); END IF; END LOOP; END $$;
RESET ROLE;
