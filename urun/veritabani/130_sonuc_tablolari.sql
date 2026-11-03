SET ROLE irp_sahibi;
-- T12 hesapları; tutar alanları iki ondalıklı metin, eksik tutar VERI_EKSIK.
CREATE FUNCTION okuma.toplam_para(xs jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE n numeric=0; x jsonb; BEGIN
 FOR x IN SELECT value FROM jsonb_array_elements(xs) LOOP
  IF x='"VERI_EKSIK"' OR x='null' THEN RETURN '"VERI_EKSIK"'; END IF; n=n+(x#>>'{}')::numeric;
 END LOOP; RETURN okuma.para(n); END $$;
CREATE FUNCTION okuma.proje_isciligi(proje text,bas text,bit_ text,kirilim text DEFAULT 'BIRIM') RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
<<iscilik_baglami>>
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); gruplar jsonb='{}'; x jsonb; i jsonb; s jsonb; ic jsonb; key text; alan text; p timestamptz; q timestamptz; u timestamptz; v timestamptz; t date; sa numeric; tutar numeric; saat_top numeric=0; paralar jsonb='[]'; r jsonb='[]'; donmus jsonb; ay date=date_trunc('month',saat.gun(bas))::date; BEGIN
 IF kirilim NOT IN ('BIRIM','YETKINLIK') THEN RAISE EXCEPTION 'IRP|BICIM|Iscilik kirilimi'; END IF;
 IF EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar=ay::text||':GOREV_PAYLARI') THEN
  SELECT CASE WHEN kirilim='BIRIM' THEN s.iscilik_birim ELSE s.iscilik_yetkinlik END INTO donmus FROM okuma.kapanis_sonuclari s WHERE s.ay=iscilik_baglami.ay AND s.proje=proje_isciligi.proje;
  IF donmus IS NOT NULL THEN
   IF ab<>ARRAY[saat.gun_ani(ay),saat.gun_ani((ay+interval '1 month')::date)] THEN RAISE EXCEPTION 'IRP|BICIM|Kapanmis ay yalniz tam ay sorgulanir'; END IF;
   RETURN donmus;
  END IF;
 END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) WHERE value->>'proje'=proje AND value->>'kisi' IS NOT NULL AND value->>'kova' IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY') LOOP
  i=okuma.satir('isler',x->>'is'); IF i->>'durum'='IPTAL' THEN CONTINUE; END IF;
  p=greatest(ab[1],saat.an(x->>'baslangic')); q=least(ab[2],coalesce(saat.an(x->>'bitis'),saat.simdi())); IF p>=q THEN CONTINUE; END IF;
  key=coalesce(CASE WHEN kirilim='BIRIM' THEN i->>'birim' ELSE i->>'yetkinlik' END,'belirtilmemiş');
  s=coalesce(gruplar->key,'{"saat":0,"tutar":0,"icinde":{"yeniden_isleme":{"saat":0,"tutar":0},"plansiz":{"saat":0,"tutar":0},"bekleme":{"saat":0,"tutar":0}}}');
  FOR t IN SELECT okuma.gunler(saat.kodla(p),saat.kodla(q-interval '1 microsecond')) LOOP
   u=greatest(p,saat.gun_ani(t)); v=least(q,saat.gun_ani(t+1)); sa=extract(epoch FROM v-u)/3600; tutar=sa*okuma.saat_maliyeti(x->>'kisi',t::text);
   s=okuma.ekle(s,'saat',sa)||jsonb_build_object('tutar',CASE WHEN tutar IS NULL OR s->>'tutar'='VERI_EKSIK' THEN '"VERI_EKSIK"'::jsonb ELSE to_jsonb((s->>'tutar')::numeric+tutar) END);
   FOREACH alan IN ARRAY ARRAY['yeniden_isleme','plansiz','bekleme'] LOOP
    IF (alan='yeniden_isleme' AND x->>'kova'='YENIDEN_ISLEME') OR (alan='plansiz' AND irp.dogru(i->'plansiz')) OR (alan='bekleme' AND x->>'kova' LIKE 'BEKLEME_%') THEN
     ic=s->'icinde'->alan; ic=okuma.ekle(ic,'saat',sa)||jsonb_build_object('tutar',CASE WHEN tutar IS NULL OR ic->>'tutar'='VERI_EKSIK' THEN '"VERI_EKSIK"'::jsonb ELSE to_jsonb((ic->>'tutar')::numeric+tutar) END);
     s=jsonb_set(s,ARRAY['icinde',alan],ic);
    END IF;
   END LOOP;
  END LOOP; gruplar=gruplar||jsonb_build_object(key,s);
 END LOOP;
 FOR key,s IN SELECT * FROM jsonb_each(gruplar) ORDER BY key COLLATE "C" LOOP
  saat_top=saat_top+(s->>'saat')::numeric; paralar=paralar||jsonb_build_array(s->'tutar');
  IF s->>'tutar'<>'VERI_EKSIK' THEN s=s||jsonb_build_object('tutar',okuma.para((s->>'tutar')::numeric)); END IF;
  FOREACH alan IN ARRAY ARRAY['yeniden_isleme','plansiz','bekleme'] LOOP ic=s->'icinde'->alan; IF ic->>'tutar'<>'VERI_EKSIK' THEN s=jsonb_set(s,ARRAY['icinde',alan,'tutar'],okuma.para((ic->>'tutar')::numeric)); END IF; END LOOP;
  r=r||jsonb_build_array(s||jsonb_build_object('kimlik',key));
 END LOOP; RETURN jsonb_build_object('proje',proje,'kirilim',kirilim,'satirlar',r,'toplam_saat',saat_top,'toplam_tutar',okuma.toplam_para(paralar)); END $$;
CREATE FUNCTION okuma.proje_maliyeti(proje text,ay text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE a date=date_trunc('month',saat.gun(ay))::date; b date=(a+interval '1 month - 1 day')::date; maliyet jsonb; emek jsonb; m jsonb; k text; x jsonb; key text;
 masa_saat numeric=0; makine_saat numeric; masalar jsonb='[]'; primler jsonb='[]'; duzeltmeler jsonb='[]'; onaylar jsonb='[]'; masa jsonb; prim jsonb; duzeltme jsonb; toplam jsonb; iptal jsonb; BEGIN
 IF EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar=a::text||':GOREV_PAYLARI') THEN
  SELECT s.maliyet INTO maliyet FROM okuma.kapanis_sonuclari s WHERE s.ay=a AND s.proje=proje_maliyeti.proje;
  IF maliyet IS NOT NULL THEN RETURN maliyet; END IF;
 END IF;
 maliyet=okuma.iscilik_maliyeti(proje,a::text,b::text); emek=okuma.proje_isciligi(proje,a::text,b::text);
 FOR k IN SELECT s.k FROM okuma.satirlar('kisiler') s WHERE s.x->>'yaka'='BEYAZ' LOOP
  m=okuma.maas_dagilimi(k,a::text);
  FOREACH key IN ARRAY ARRAY[proje,'revizyon:'||proje] LOOP
   masa_saat=masa_saat+coalesce((m->'paylar'->>key)::numeric,0); masalar=masalar||jsonb_build_array(coalesce(m->'tutarlar'->key,'"0.00"'));
  END LOOP;
  onaylar=onaylar||jsonb_build_array(okuma.bekleyen_maliyet(a::text,b::text,proje,k,true));
 END LOOP;
 SELECT coalesce(sum(extract(epoch FROM least(saat.gun_ani(b+1),coalesce(saat.an(x->>'bitis'),saat.simdi()))-greatest(saat.gun_ani(a),saat.an(x->>'baslangic')))/3600),0) INTO makine_saat FROM jsonb_array_elements(okuma.tablo('araliklar')) x
 WHERE x->>'proje'=proje AND x->>'kova'='TEZGAH' AND okuma.satir('isler',x->>'is')->>'durum' IS DISTINCT FROM 'IPTAL' AND greatest(saat.gun_ani(a),saat.an(x->>'baslangic'))<least(saat.gun_ani(b+1),coalesce(saat.an(x->>'bitis'),saat.simdi()));
 -- Donuk defter varsa prim de kapanış fotoğrafından okunur.
 SELECT hal INTO x FROM public.ay_kapanislari WHERE anahtar=a::text||':DEFTER_V7';
 IF x IS NOT NULL THEN SELECT coalesce(jsonb_agg(value->'tutar'),'[]') INTO primler FROM jsonb_each(x) WHERE value->>'proje'=proje AND value->>'kaynak_kalem'='FAZLA_MESAI_PRIMI';
 ELSE SELECT coalesce(jsonb_agg(x->'prim'),'[]') INTO primler FROM jsonb_array_elements(okuma.fazla_mesai_kayitlari()) x WHERE x->>'proje'=proje AND saat.gun(x->>'tarih') BETWEEN a AND b; END IF;
 SELECT hal INTO x FROM public.ay_kapanislari WHERE anahtar=a::text||':DUZELTMELER';
 IF x IS NULL THEN x=okuma.onceki_donem_duzeltmeleri(); END IF;
 SELECT coalesce(jsonb_agg(z->'tutar'),'[]') INTO duzeltmeler FROM jsonb_array_elements(x) z WHERE z->>'proje'=proje AND z->>'ay'=a::text;
 masa=okuma.toplam_para(masalar); prim=okuma.toplam_para(primler); duzeltme=okuma.toplam_para(duzeltmeler);
 toplam=okuma.toplam_para(jsonb_build_array(maliyet->'iscilik',maliyet->'tezgah',masa,prim,duzeltme));
 iptal=okuma.iptal_edilenler(proje,a::text,b::text);
 RETURN jsonb_build_object('proje',proje,'ay',a,'atolye_saat',emek->'toplam_saat','tezgah_saat',makine_saat,'masa_basi_saat',masa_saat,
 'atolye',maliyet->'iscilik','tezgah',maliyet->'tezgah','masa_basi',masa,'prim',prim,'duzeltme',duzeltme,'toplam',toplam,
 'onay_bekleyen',jsonb_build_object('tutar',okuma.toplam_para(onaylar||jsonb_build_array(coalesce(maliyet->'onay_bekleyen','"0.00"')))),
 'iptal_edilen',iptal,'eksik_veri',toplam='"VERI_EKSIK"'); END $$;
CREATE FUNCTION okuma.tahmin_gercek(proje text,bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; k text; x jsonb; gercek numeric; tahmin numeric; kisiler jsonb;
 ab timestamptz[]=okuma.pencere(bas,bit_); dogus timestamptz; BEGIN
 -- Çok kişili işin ana satırı tekrar sayılmaz; yapraklar birer satırdır.
 FOR k,x IN SELECT * FROM okuma.satirlar('isler') WHERE x->>'proje'=proje AND x->>'durum'<>'IPTAL' AND coalesce((x->>'kisi_sayisi')::int,1)=1 ORDER BY k COLLATE "C" LOOP
  SELECT oldugu_an INTO dogus FROM public.olaylar WHERE olay_kimligi=x->>'doguran_olay';
  -- Aralık, o dönemde mevcut işleri seçer. Gerçek sütunu T12 gereği işin
  -- emek değeridir; dönem sınırında kesilmiş ikinci bir emek hesabı değildir.
  IF coalesce(dogus,'-infinity'::timestamptz)>=ab[2]
   OR (x->>'durum'='BITTI' AND saat.an(x->>'bitis_ani')<ab[1]) THEN CONTINUE; END IF;
  gercek=okuma.emek(k); tahmin=(x->>'tahmini_sure_dk')::numeric;
  SELECT coalesce(jsonb_agg(z ORDER BY z COLLATE "C"),'[]') INTO kisiler FROM (SELECT DISTINCT z FROM (
   SELECT x->>'kisi' z UNION SELECT a->>'kisi' FROM jsonb_array_elements(okuma.tablo('araliklar')) a WHERE a->>'is'=k) q WHERE z IS NOT NULL) q;
  r=r||jsonb_build_array(jsonb_build_object('kimlik',k,'surum',x->'surum','parca',coalesce(nullif(x->'nesne','null'),x->'parca_kodu'),'islem',x->'islem','kisiler',kisiler,'tezgah',x->'tezgah','durum',x->'durum','tahmin_dk',tahmin,'gercek_dk',gercek,
   'fark',CASE WHEN tahmin>0 THEN to_jsonb((gercek-tahmin)/tahmin) ELSE '"Hesaplanamaz"'::jsonb END,'suruyor',x->>'durum'<>'BITTI'));
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.personel_dagilimi(bas text,bit_ text,cagiran text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE gruplar jsonb='{}'; paylar jsonb; p text; v jsonb; toplam numeric; r jsonb='[]'; BEGIN
 FOR paylar IN SELECT value FROM jsonb_each(okuma.saat_nereye_gitti(bas,bit_,cagiran)) LOOP
  FOR p,v IN SELECT * FROM jsonb_each(paylar) LOOP gruplar=okuma.ekle(gruplar,p,(v#>>'{}')::numeric); END LOOP;
 END LOOP;
 SELECT coalesce(sum((value#>>'{}')::numeric),0) INTO toplam FROM jsonb_each(gruplar);
 FOR p,v IN SELECT * FROM jsonb_each(gruplar) ORDER BY key COLLATE "C" LOOP r=r||jsonb_build_array(jsonb_build_object('kalem',p,'saat',v,'yuzde',CASE WHEN toplam<>0 THEN (v#>>'{}')::numeric/toplam*100 END)); END LOOP;
 RETURN jsonb_build_object('satirlar',r,'toplam_saat',toplam); END $$;
CREATE FUNCTION okuma.sonuc_tutarlarini_ayikla(j jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; k text; v jsonb; BEGIN
 IF jsonb_typeof(j)='object' THEN r='{}'; FOR k,v IN SELECT * FROM jsonb_each(j) LOOP
  IF k NOT IN ('atolye','tezgah','masa_basi','prim','duzeltme','toplam','tutar','tutarlar','toplam_tutar','maliyet','iscilik','maas') THEN r=r||jsonb_build_object(k,okuma.sonuc_tutarlarini_ayikla(v)); END IF;
 END LOOP; RETURN r;
 ELSIF jsonb_typeof(j)='array' THEN SELECT coalesce(jsonb_agg(okuma.sonuc_tutarlarini_ayikla(value)),'[]') INTO r FROM jsonb_array_elements(j); RETURN r;
 END IF; RETURN j; END $$;
RESET ROLE;
