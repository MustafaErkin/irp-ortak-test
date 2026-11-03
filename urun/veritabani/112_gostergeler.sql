SET ROLE irp_sahibi;
CREATE FUNCTION okuma.etap_gostergesi(etap text,t text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE sim timestamptz=coalesce(saat.an(t),saat.simdi()); e jsonb=okuma.satir('etaplar',etap); g jsonb; key text; tur text; sa numeric;
 planli numeric=0; tamam numeric=0; gorev_saati numeric=0; atolye numeric=0; rev numeric=0; hedef numeric=(e->>'hedef_saat')::numeric;
 kategoriler jsonb='{"tamamlandi":0,"onay_bekliyor":0,"revizyonda":0,"geride":0}'; teslim timestamptz; alan text; isler text[]='{}'; BEGIN
 FOR tur,key,g IN SELECT 'GOREV',k,x FROM okuma.satirlar('gorevler') UNION ALL SELECT 'IS',k,x FROM okuma.satirlar('isler') LOOP
  IF g->>'etap' IS DISTINCT FROM etap OR g->>'durum'='IPTAL' THEN CONTINUE; END IF;
  IF tur='GOREV' THEN
   sa=okuma.gorev_payi(g,e->>'baslangic',saat.gun(saat.kodla(sim))::text); gorev_saati=gorev_saati+sa;
   IF g->>'tur'='REVIZYON' THEN rev=rev+sa; END IF;
   IF g->>'tur' NOT IN ('NORMAL','DEGISIKLIK') THEN CONTINUE; END IF; sa=(g->>'zaman_degeri')::numeric;
  ELSE
   IF coalesce((g->>'kisi_sayisi')::int,1)<>1 THEN CONTINUE; END IF;
   isler=array_append(isler,key); atolye=atolye+okuma.emek(key)/60; sa=(g->>'tahmini_sure_dk')::numeric/60;
  END IF;
  planli=planli+sa; IF g->>'durum'='BITTI' THEN tamam=tamam+sa; END IF;
  teslim=gorev.son_teslim_ani(g,'OKUMA'); IF teslim IS NULL OR teslim>sim THEN CONTINUE; END IF;
  alan=CASE WHEN g->>'durum'='BITTI' THEN 'tamamlandi' WHEN g->>'durum'='ONAY_BEKLIYOR' THEN 'onay_bekliyor' WHEN g->>'durum' IN ('REDDEDILDI','REVIZYONDA') THEN 'revizyonda' ELSE 'geride' END;
  kategoriler=okuma.ekle(kategoriler,alan,sa);
 END LOOP;
 SELECT rev+coalesce(sum(extract(epoch FROM coalesce(saat.an(a->>'bitis'),sim)-saat.an(a->>'baslangic'))/3600),0) INTO rev
 FROM jsonb_array_elements(okuma.tablo('araliklar')) a WHERE a->>'kova'='YENIDEN_ISLEME' AND a->>'is'=ANY(isler);
 RETURN jsonb_build_object('planli_toplam',planli,'tamamlanan',tamam,'hedef',hedef,'yuzde',CASE WHEN hedef<>0 THEN to_jsonb(tamam/hedef*100) ELSE '"Hesaplanamaz"'::jsonb END,
 'dort_kategori',kategoriler,'harcanan_emek',gorev_saati+atolye,'butce_tuketimi',CASE WHEN hedef<>0 THEN to_jsonb((gorev_saati+atolye)/hedef*100) ELSE '"Hesaplanamaz"'::jsonb END,'revizyon_maliyeti_saat',rev);
END $$;
CREATE FUNCTION okuma.proje_emegi(proje text) RETURNS numeric LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT sum(okuma.gorev_payi(x,'1900-01-01',saat.kodla(saat.simdi()))) FROM okuma.satirlar('gorevler') WHERE x->>'proje'=proje AND x->>'durum'<>'IPTAL'),0)
 +coalesce((SELECT sum(okuma.emek(k)/60) FROM okuma.satirlar('isler') WHERE x->>'proje'=proje AND x->>'durum'<>'IPTAL' AND coalesce((x->>'kisi_sayisi')::int,1)=1),0) $$;
CREATE FUNCTION okuma.iptal_edilenler(proje text,bas text DEFAULT NULL,bit_ text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a date; b date=coalesce(saat.gun(bit_),saat.gun(saat.kodla(saat.simdi()))); ay date; son date; izler jsonb; x jsonb; secilen jsonb='{}'; tutarlar jsonb='{"iscilik":0,"tezgah":0,"maas":0}'; sa numeric=0; alan text; k text; BEGIN
 SELECT coalesce(saat.gun(bas),date_trunc('month',coalesce(min(saat.an(e->>'oldugu_an')),saat.simdi()) AT TIME ZONE 'Europe/Istanbul')::date) INTO a FROM jsonb_array_elements(okuma.tablo('olaylar')) e;
 FOR k,x IN SELECT k,x FROM okuma.satirlar('isler') WHERE x->>'proje'=proje AND x->>'durum'='IPTAL' AND coalesce((x->>'kisi_sayisi')::int,1)=1 LOOP secilen=secilen||jsonb_build_object('IS:'||k,true); END LOOP;
 FOR k,x IN SELECT k,x FROM okuma.satirlar('gorevler') WHERE x->>'proje'=proje AND x->>'durum'='IPTAL' AND x->>'tur'<>'ONAY' LOOP secilen=secilen||jsonb_build_object('GOREV:'||k,true); END LOOP;
 IF secilen='{}' THEN RETURN '{"sayi":0,"isler":[],"gorevler":[],"emek_saat":0,"maliyet":{"iscilik":"0.00","tezgah":"0.00","maas":"0.00"}}'; END IF;
 ay=date_trunc('month',a)::date;
 WHILE ay<=b LOOP
  son=(ay+interval '1 month - 1 day')::date; SELECT hal INTO izler FROM public.ay_kapanislari WHERE anahtar=ay::text||':MALIYET_IZLERI';
  izler=coalesce(izler,okuma.maliyet_izleri(ay::text,son::text));
  FOR x IN SELECT value FROM jsonb_array_elements(izler) LOOP
   IF x->>'proje' IS DISTINCT FROM proje OR (x->>'gun')::date NOT BETWEEN a AND b THEN CONTINUE; END IF;
   IF okuma.satir(CASE WHEN x->>'tur'='IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->>'durum' IS DISTINCT FROM 'IPTAL' THEN CONTINUE; END IF;
   secilen=secilen||jsonb_build_object((x->>'tur')||':'||(x->>'kimlik'),true); sa=sa+(x->>'emek_saat')::numeric;
   FOREACH alan IN ARRAY ARRAY['iscilik','tezgah','maas'] LOOP
    IF x->>alan='VERI_EKSIK' OR tutarlar->>alan='VERI_EKSIK' THEN tutarlar=tutarlar||jsonb_build_object(alan,'VERI_EKSIK');
    ELSE tutarlar=okuma.ekle(tutarlar,alan,(x->>alan)::numeric); END IF;
   END LOOP;
  END LOOP; ay=son+1;
 END LOOP;
 FOREACH alan IN ARRAY ARRAY['iscilik','tezgah','maas'] LOOP IF tutarlar->>alan<>'VERI_EKSIK' THEN tutarlar=tutarlar||jsonb_build_object(alan,okuma.para((tutarlar->>alan)::numeric)); END IF; END LOOP;
 RETURN jsonb_build_object('sayi',(SELECT count(*) FROM jsonb_object_keys(secilen)),
 'isler',(SELECT coalesce(jsonb_agg(substr(key,4) ORDER BY key COLLATE "C"),'[]') FROM jsonb_each(secilen) WHERE key LIKE 'IS:%'),
 'gorevler',(SELECT coalesce(jsonb_agg(substr(key,7) ORDER BY key COLLATE "C"),'[]') FROM jsonb_each(secilen) WHERE key LIKE 'GOREV:%'),'emek_saat',sa,'maliyet',tutarlar);
END $$;
CREATE FUNCTION okuma.proje_gostergesi(proje text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE etaplar jsonb='{}'; k text; x jsonb; bagli text[]; tamam numeric=0; hedef numeric=0; son jsonb; r jsonb; bas text; df jsonb; maliyet numeric=0; alt numeric=0; ex boolean=false; ex_alt boolean=false; BEGIN
 FOR k IN SELECT s.k FROM okuma.satirlar('etaplar') s WHERE s.x->>'proje'=proje LOOP
  x=okuma.etap_gostergesi(k); etaplar=etaplar||jsonb_build_object(k,x); tamam=tamam+(x->>'tamamlanan')::numeric; hedef=hedef+(x->>'hedef')::numeric;
 END LOOP;
 SELECT coalesce(array_agg(s.k ORDER BY s.k COLLATE "C"),'{}') INTO bagli FROM okuma.satirlar('projeler') s WHERE s.x->>'ana_proje'=proje;
 SELECT jsonb_build_object('emek_saat',coalesce(sum(okuma.proje_emegi(p)),0)) INTO son FROM unnest(bagli) p;
 r=jsonb_build_object('bagli_projeler',bagli,'harcanan_emek',okuma.proje_emegi(proje));
 IF cagiran IS NOT NULL AND okuma.gorebilir(cagiran,'TUTAR') THEN
  SELECT coalesce(min(saat.gun(e->>'oldugu_an')),saat.gun(saat.kodla(saat.simdi())))::text INTO bas FROM jsonb_array_elements(okuma.tablo('olaylar')) e;
  df=okuma.donem_defteri(bas,saat.kodla(saat.simdi()));
  FOR x IN SELECT value FROM jsonb_each(df) LOOP
   IF x->>'proje'=proje THEN IF x->>'tutar'='VERI_EKSIK' THEN ex=true; ELSE maliyet=maliyet+(x->>'tutar')::numeric; END IF; END IF;
   IF x->>'proje'=ANY(bagli) THEN IF x->>'tutar'='VERI_EKSIK' THEN ex_alt=true; ELSE alt=alt+(x->>'tutar')::numeric; END IF; END IF;
  END LOOP;
  son=son||jsonb_build_object('maliyet',CASE WHEN ex_alt THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(alt) END);
  r=r||jsonb_build_object('maliyet',CASE WHEN ex THEN '"VERI_EKSIK"'::jsonb ELSE okuma.para(maliyet) END);
 END IF;
 RETURN r||jsonb_build_object('bitis_sonrasi',son,'iptal_edilenler',okuma.iptal_edilenler(proje),'etaplar',etaplar,'tamamlanan',tamam,'hedef',hedef,'yuzde',CASE WHEN hedef<>0 THEN to_jsonb(tamam/hedef*100) ELSE '"Hesaplanamaz"'::jsonb END);
END $$;
CREATE FUNCTION okuma.pano_projeleri(paylar jsonb,cagiran text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; p text; v jsonb; ad text; BEGIN
 FOR p,v IN SELECT * FROM jsonb_each(paylar) LOOP
  ad=CASE WHEN okuma.tablo('projeler') ? p AND NOT k9.proje_gorebilir('OKUMA',cagiran,p) THEN 'erişim dışı proje' ELSE p END;
  r=okuma.ekle(r,ad,(v#>>'{}')::numeric);
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.kim_nerede(bas text,bit_ text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; sonuc jsonb='{}'; a jsonb; g jsonb; t date; key text; p text; pay numeric; BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) WHERE value->>'kisi' IS NOT NULL AND saat.gun(value->>'gun') BETWEEN saat.gun(bas) AND saat.gun(bit_) AND value->>'kova' IN ('CALISMA','YENIDEN_ISLEME') LOOP
  key=(a->>'kisi')||':'||(a->>'gun'); p=coalesce(a->>'proje',a->>'kategori','BELIRSIZ');
  pay=extract(epoch FROM coalesce(saat.an(a->>'bitis'),saat.simdi())-saat.an(a->>'baslangic'))/3600;
  r=r||jsonb_build_object(key,okuma.ekle(coalesce(r->key,'{}'),p,pay));
 END LOOP;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') LOOP
  FOR a IN SELECT value FROM jsonb_array_elements(okuma.gorev_paylari(g)) WHERE (value->>'gun')::date BETWEEN saat.gun(bas) AND saat.gun(bit_) LOOP
   t=(a->>'gun')::date; pay=(a->>'saat')::numeric; IF pay=0 THEN CONTINUE; END IF;
   key=okuma.gorevin_kisisi(g,t)||':'||t; p=coalesce(g->>'proje',g->>'kategori','BELIRSIZ'); r=r||jsonb_build_object(key,okuma.ekle(coalesce(r->key,'{}'),p,pay));
  END LOOP;
 END LOOP;
 IF cagiran IS NULL THEN RETURN r; END IF;
 FOR key,a IN SELECT * FROM jsonb_each(r) LOOP IF okuma.gorebilir(cagiran,'GUN',split_part(key,':',1)) THEN sonuc=sonuc||jsonb_build_object(key,okuma.pano_projeleri(a,cagiran)); END IF; END LOOP;
 RETURN sonuc; END $$;
CREATE FUNCTION okuma.saat_nereye_gitti(bas text,bit_ text,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; key text; x jsonb; b text; p text; pay jsonb; kap numeric; toplam numeric; BEGIN
 IF cagiran IS NOT NULL AND NOT okuma.gorebilir(cagiran,'UYGUNLUK') THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 FOR key,x IN SELECT * FROM jsonb_each(okuma.kim_nerede(bas,bit_)) LOOP
  b=okuma.satir('kisiler',split_part(key,':',1))->>'birim';
  FOR p,pay IN SELECT * FROM jsonb_each(x) LOOP r=r||jsonb_build_object(b,okuma.ekle(coalesce(r->b,'{}'),p,(pay#>>'{}')::numeric)); END LOOP;
 END LOOP;
 FOR b IN SELECT k FROM okuma.satirlar('birimler') LOOP
  SELECT coalesce(sum(okuma.kapasite(k,bas,bit_)),0) INTO kap FROM okuma.satirlar('kisiler') WHERE x->>'birim'=b;
  SELECT coalesce(sum((value#>>'{}')::numeric),0) INTO toplam FROM jsonb_each(coalesce(r->b,'{}'));
  r=r||jsonb_build_object(b,coalesce(r->b,'{}')||jsonb_build_object('KAYDEDILMEYEN',kap-toplam));
 END LOOP;
 IF cagiran IS NOT NULL THEN FOR b,x IN SELECT * FROM jsonb_each(r) LOOP r=r||jsonb_build_object(b,okuma.pano_projeleri(x,cagiran)); END LOOP; END IF;
 RETURN r; END $$;
CREATE FUNCTION okuma.birim_dolulugu(bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; b text; kap numeric; plan numeric; BEGIN
 FOR b IN SELECT k FROM okuma.satirlar('birimler') LOOP
  SELECT coalesce(sum(okuma.kapasite(k,bas,bit_)),0),coalesce(sum(okuma.yuk(k,bas,bit_)),0) INTO kap,plan FROM okuma.satirlar('kisiler') WHERE x->>'birim'=b;
  r=r||jsonb_build_object(b,jsonb_build_object('kapasite',kap,'planli',plan,'bos',kap-plan));
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.onay_listesi(kisi text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; tur text; k text; x jsonb; e jsonb; BEGIN
 FOR tur,k,x IN SELECT 'IS',s.k,s.x FROM okuma.satirlar('isler') s UNION ALL SELECT 'GOREV',s.k,s.x FROM okuma.satirlar('gorevler') s LOOP
  IF x->>'durum'<>'ONAY_BEKLIYOR' OR coalesce((x->>'kisi_sayisi')::int,1)<>1 THEN CONTINUE; END IF;
  e=jsonb_build_object('kim',kisi,'eylem_kodu',tur||'.ONAYLADIM','girdiler','{}'::jsonb,'giris_sekli','LISTE','neyin_ustunde',jsonb_build_array(jsonb_build_object('tur',tur,'kimlik',k)));
  IF yetki_v6.yetkili_mi('OKUMA',e) THEN r=r||jsonb_build_array(x); END IF;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.gorev_isaretleri(gorev jsonb,ay text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE g jsonb=CASE WHEN jsonb_typeof(gorev)='string' THEN okuma.satir('gorevler',gorev#>>'{}') ELSE gorev END; r text[]='{}'; teslim timestamptz; bit_ date; sinir timestamptz; BEGIN
 teslim=gorev.son_teslim_ani(g,'OKUMA');
 IF saat.an(g->>'ilk_teslim_ani')>teslim THEN r=array_append(r,'GEC_TESLIM'); END IF;
 IF teslim<saat.simdi() AND g->>'ilk_teslim_ani' IS NULL AND g->>'durum' NOT IN ('BITTI','IPTAL') THEN r=array_append(r,'GECIKTI'); END IF;
 IF ay IS NOT NULL THEN bit_=(date_trunc('month',saat.gun(ay))+interval '1 month - 1 day')::date;
  sinir=saat.gun_ani(bit_,motor.takvim('OKUMA',bit_::text,okuma.gorevin_kisisi(g,bit_))->>'mesai_bitis');
  IF saat.an(g->>'kabul_ani')<=sinir AND (g->>'bitis_ani' IS NULL OR saat.an(g->>'bitis_ani')>sinir) AND g->>'durum'<>'IPTAL' THEN r=array_append(r,'SUREN'); END IF;
 END IF; RETURN to_jsonb(ARRAY(SELECT x FROM unnest(r) x ORDER BY x COLLATE "C")); END $$;
RESET ROLE;
