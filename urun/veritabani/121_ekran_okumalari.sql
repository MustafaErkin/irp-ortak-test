SET ROLE irp_sahibi;
CREATE FUNCTION okuma.atama_uyarilari(satirlar jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='[]'; n bigint; s jsonb; aday jsonb; teslim date; a date; b date; kisi text; yeni numeric; toplam int; donem int; BEGIN
 FOR s,n IN SELECT * FROM jsonb_array_elements(satirlar) WITH ORDINALITY LOOP
  teslim=saat.gun(s->>'teslim_tarihi'); kisi=s->>'kisi'; a=teslim-(extract(isodow FROM teslim)::int-1); b=a+6; yeni=0;
  IF teslim>saat.gun(okuma.satir('etaplar',s->>'etap')->>'bitis') THEN r=r||jsonb_build_array(jsonb_build_object('satir',n,'kural','R24','metin','Teslim etabin bitisini asiyor')); END IF;
  FOR aday IN SELECT value FROM jsonb_array_elements(satirlar) WHERE value->>'kisi'=kisi LOOP
   SELECT count(*),count(*) FILTER(WHERE t BETWEEN a AND b) INTO toplam,donem FROM okuma.gunler(saat.kodla(saat.simdi()),aday->>'teslim_tarihi') t WHERE motor.is_gunu('OKUMA',t::text,kisi);
   IF toplam>0 THEN yeni=yeni+(aday->>'zaman_degeri')::numeric*donem/toplam; END IF;
  END LOOP;
  IF okuma.yuk(kisi,a::text,b::text)+yeni>okuma.kapasite(kisi,a::text,b::text) THEN r=r||jsonb_build_array(jsonb_build_object('satir',n,'kural','R23','metin','Teslim haftasi kapasite asiliyor')); END IF;
 END LOOP; RETURN r; END $$;
CREATE FUNCTION okuma.ek_oku(kim text,veri text,hedef text,g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; x jsonb; h jsonb; i jsonb; k text; key text; b text=g->>'bas'; e text=g->>'bit'; birim text=coalesce(g->>'birim',hedef); tarih text=coalesce(g->>'tarih',saat.gun(saat.kodla(saat.simdi()))::text); liste jsonb; isler jsonb; kayitlar jsonb; BEGIN
 CASE veri
 WHEN 'TELEFON' THEN
  IF hedef IS NOT NULL AND hedef<>kim THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  h=coalesce(okuma.satir('kisi_durumu',kim),kg.bos_hal()); liste=coalesce(okuma.satir('listeler',kim),'[]');
  SELECT coalesce(jsonb_object_agg(k,x),'{}') INTO isler FROM okuma.satirlar('isler') WHERE (liste ? k OR k IN (h->>'acik_is',h->>'aralik_is')) AND okuma.gorebilir(kim,'IS',k);
  SELECT coalesce(jsonb_agg(value),'[]') INTO liste FROM jsonb_array_elements(liste) WHERE isler ? (value#>>'{}');
  RETURN jsonb_build_object('kisi',okuma.satir('kisiler',kim),'son_hal',h,'liste',liste,'isler',isler,'takvim',motor.takvim('OKUMA',tarih,kim));
 WHEN 'HAVUZ','EKIP' THEN
  IF NOT okuma.birim_gorebilir(kim,birim) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  IF veri='HAVUZ' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('isler') WHERE x->>'birim'=birim AND NOT irp.dogru(x->'kisi') AND x->>'durum' NOT IN ('BITTI','IPTAL') AND okuma.gorebilir(kim,'IS',k); RETURN r; END IF;
  r='[]'; FOR k,x IN SELECT * FROM okuma.satirlar('kisiler') WHERE x->>'birim'=birim LOOP
   IF NOT okuma.gorebilir(kim,'GUN',k) THEN CONTINUE; END IF;
   h=coalesce(okuma.satir('kisi_durumu',k),kg.bos_hal()); i=okuma.satir('isler',coalesce(h->>'acik_is',h->>'aralik_is'));
   IF i IS NOT NULL AND NOT okuma.gorebilir(kim,'IS',i->>'kimlik') THEN i=NULL; END IF;
   r=r||jsonb_build_array(jsonb_build_object('kisi',k,'surum',x->'surum','ad',x->'ad','hal',h,'is_',i,'calisma_dk',coalesce(okuma.kisinin_gunu(k,tarih)#>'{kovalar,CALISMA}','0')));
  END LOOP; RETURN r;
 WHEN 'ONAY_LISTESI' THEN
  IF hedef IS NOT NULL AND hedef<>kim THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM jsonb_array_elements(okuma.onay_listesi(kim)) x WHERE okuma.gorebilir(kim,CASE WHEN okuma.tablo('isler') ? (x->>'kimlik') THEN 'IS' ELSE 'GOREV' END,x->>'kimlik'); RETURN r;
 WHEN 'KISININ_GUNU' THEN
  IF NOT okuma.gorebilir(kim,'GUN',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  r=okuma.kisinin_gunu(hedef,tarih);
  SELECT coalesce(jsonb_object_agg(k,x),'{}') INTO isler FROM okuma.satirlar('isler') WHERE x->>'kisi'=hedef AND okuma.gorebilir(kim,'IS',k);
  SELECT coalesce(jsonb_agg(jsonb_build_object('kimlik',olay_kimligi,'eylem',eylem_kodu,'an',icerik->'oldugu_an') ORDER BY kabul_no),'[]') INTO kayitlar FROM public.olaylar WHERE coalesce(icerik->>'adina',icerik->>'kim')=hedef AND saat.gun(icerik->>'oldugu_an')=saat.gun(tarih) AND (eylem_kodu LIKE 'IS.%' OR eylem_kodu LIKE 'MESAI.%');
  RETURN r||jsonb_build_object('isler',isler,'kayitlar',kayitlar);
 WHEN 'BIRIM_DOLULUGU' THEN IF NOT okuma.gorebilir(kim,'UYGUNLUK') THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.birim_dolulugu(b,e);
 WHEN 'MAAS_DAGILIMI' THEN IF NOT okuma.gorebilir(kim,'MAAS',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.maas_dagilimi(hedef,g->>'ay');
 WHEN 'GUN_ISLERI' THEN IF NOT okuma.gorebilir(kim,'GUN',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.ic('gun_isleri',g||jsonb_build_object('kisi',hedef));
 WHEN 'GECIKME_RAPORU' THEN RETURN okuma.gecikme_raporu(b,e,coalesce(g->>'kirilim','sorumlu'),kim);
 WHEN 'ELLE_SURELER' THEN IF NOT okuma.gorebilir(kim,'BIRIM_PERFORMANS',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.ic('elle_sureler',g||jsonb_build_object('birim',hedef));
 WHEN 'ATAMA_UYARILARI' THEN IF NOT okuma.satir('kisiler',kim)->'roller' ?| ARRAY['YONETICI','EKIP_LIDERI','YETKILI'] THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.atama_uyarilari(g->'satirlar');
 WHEN 'YUK' THEN IF NOT okuma.gorebilir(kim,'IS',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN to_jsonb(okuma.yuk(hedef,b,e));
 WHEN 'PROJELER' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('projeler') WHERE k9.proje_gorebilir('OKUMA',kim,k); RETURN r;
 WHEN 'YONLENDIRME' THEN
  IF NOT (okuma.satir('kisiler',kim)->'roller' ? 'YETKILI' OR kim=ANY(yetki_v6.yoneticiler('OKUMA',birim))) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  RETURN coalesce(okuma.satir('yonlendirme',birim),'[]');
 WHEN 'SUPHELILER' THEN
  IF NOT okuma.satir('kisiler',kim)->'roller' ? 'YETKILI' THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  RETURN jsonb_build_object('supheliler',okuma.tablo('supheliler'),'isleme_hatalari',(SELECT coalesce(jsonb_agg(hal ORDER BY sira),'[]') FROM public.isleme_hatalari));
 WHEN 'KODLAR' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('kod_listesi') WHERE irp.dogru(x->'aktif') AND (hedef IS NULL OR x->>'liste'=hedef); RETURN r;
 WHEN 'BUGUNKU_KIMLIKLER' THEN
  IF hedef IS NULL OR length(hedef)<>1 THEN RAISE EXCEPTION 'IRP|BICIM|Cihaz harfi'; END IF;
  SELECT coalesce(jsonb_agg(olay_kimligi ORDER BY kabul_no),'[]') INTO r FROM public.olaylar WHERE public.olaylar.kim=ek_oku.kim AND starts_with(olay_kimligi,ek_oku.kim||'-'||to_char(saat.simdi() AT TIME ZONE 'Europe/Istanbul','YYMMDD')) AND right(olay_kimligi,1)=hedef; RETURN r;
 WHEN 'PROJE_MALIYETI','PROJE_ISCILIGI','TAHMIN_GERCEK' THEN
  IF NOT k9.proje_gorebilir('OKUMA',kim,hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
  r=CASE veri WHEN 'PROJE_MALIYETI' THEN okuma.proje_maliyeti(hedef,g->>'ay') WHEN 'PROJE_ISCILIGI' THEN okuma.proje_isciligi(hedef,b,e,coalesce(g->>'kirilim','BIRIM')) ELSE okuma.tahmin_gercek(hedef,b,e) END;
  RETURN CASE WHEN veri='TAHMIN_GERCEK' OR okuma.satir('kisiler',kim)->'roller' ? 'YETKILI' THEN r ELSE okuma.sonuc_tutarlarini_ayikla(r) END;
 WHEN 'PERSONEL_DAGILIMI' THEN IF NOT okuma.gorebilir(kim,'SAAT_NEREYE_GITTI') THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.personel_dagilimi(b,e,kim);
 ELSE RAISE EXCEPTION 'IRP|BICIM|TANIMSIZ_VERI'; END CASE;
END $$;
RESET ROLE;
