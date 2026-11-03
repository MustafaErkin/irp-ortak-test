SET ROLE irp_sahibi;
-- İç sorgu izin listesi test.sorgu'dadır. Bu işlev istemci rollerine açılmaz.
CREATE FUNCTION okuma.ic(ad text,g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb; x jsonb; k text; b text=g->>'bas'; e text=g->>'bit'; kisi text=g->>'kisi'; c text=g->>'cagiran'; BEGIN
 IF g->>'t' IS NOT NULL AND ad IN ('proje_kaydi','proje_gorebilir_mi','proje_uyeleri','gecmis_gorunumu','gecerli_surum','gun_isleri') THEN
  IF ad='gecerli_surum' AND c IS NOT NULL AND NOT okuma.gorebilir(c,'NESNE',g->>'nesne') THEN RETURN NULL; END IF;
  IF ad<>'gun_isleri' OR saat.an(g->>'t')<>saat.simdi() THEN RETURN okuma.gecmis(g->>'t',ad,g); END IF;
 END IF;
 CASE ad
 WHEN 'proje_kaydi' THEN IF c IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',c,g->>'proje') THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF; RETURN okuma.satir('projeler',g->>'proje');
 WHEN 'proje_gorebilir_mi' THEN RETURN to_jsonb(k9.proje_gorebilir('OKUMA',g->>'kim',g->>'proje'));
 WHEN 'proje_uyeleri' THEN RETURN to_jsonb(k9.proje_uyeleri('OKUMA',g->>'proje'));
 WHEN 'gorebilir_mi' THEN RETURN to_jsonb(okuma.gorebilir(g->>'kim',g->>'veri',g->>'hedef'));
 WHEN 'emek' THEN RETURN to_jsonb(okuma.emek(g->>'kimlik'));
 WHEN 'kapasite' THEN RETURN to_jsonb(okuma.kapasite(kisi,b,e));
 WHEN 'is_gunleri' THEN SELECT coalesce(jsonb_agg(t),'[]') INTO r FROM okuma.gunler(b,e) t WHERE motor.is_gunu('OKUMA',t::text,kisi); RETURN r;
 WHEN 'gun_agirligi' THEN RETURN to_jsonb(okuma.gun_agirligi(g->>'tarih',kisi));
 WHEN 'gorev_payi' THEN RETURN to_jsonb(okuma.gorev_payi(g->'g',b,e,coalesce((g->>'yuk')::boolean,false),kisi));
 WHEN 'gorev_gunluk_paylar' THEN RETURN okuma.gorev_gunluk_paylar(g->'g',coalesce((g->>'yuk')::boolean,false));
 WHEN 'yuk' THEN RETURN to_jsonb(okuma.yuk(kisi,b,e));
 WHEN 'kisinin_gunu' THEN RETURN okuma.kisinin_gunu(kisi,g->>'tarih');
 WHEN 'maas_dagilimi' THEN RETURN okuma.maas_dagilimi(kisi,g->>'ay',coalesce((g->>'canli')::boolean,false));
 WHEN 'iscilik_maliyeti' THEN RETURN okuma.iscilik_maliyeti(g->>'proje',b,e,coalesce((g->>'canli')::boolean,false),coalesce((g->>'iptal')::boolean,false));
 WHEN 'etap_gostergesi' THEN RETURN okuma.etap_gostergesi(g->>'etap',g->>'t');
 WHEN 'proje_gostergesi' THEN RETURN okuma.proje_gostergesi(g->>'proje',c);
 WHEN 'adil_performans' THEN RETURN okuma.adil_performans(kisi,b,e,c);
 WHEN 'gorev_isaretleri' THEN RETURN okuma.gorev_isaretleri(g->'gorev',g->>'ay');
 WHEN 'fazla_mesai_kayitlari' THEN RETURN okuma.fazla_mesai_kayitlari();
 WHEN 'gun_sonu_raporu' THEN RETURN okuma.gun_sonu_raporu(kisi,g->>'tarih');
 WHEN 'gun_ozeti' THEN RETURN okuma.gun_ozeti(kisi,g->>'tarih');
 WHEN 'hatirlatmalar' THEN RETURN okuma.hatirlatmalar();
 WHEN 'gun_isleri' THEN RETURN okuma.gun_isleri(kisi);
 WHEN 'okunmamis_bildirimler' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM jsonb_array_elements(okuma.bildirim_kutusu(kisi)) x WHERE x->>'gorulme_ani' IS NULL; RETURN r;
 WHEN 'bildirim_kutusu' THEN RETURN okuma.bildirim_kutusu(kisi,c);
 WHEN 'onay_listesi' THEN RETURN okuma.onay_listesi(kisi);
 WHEN 'gorev_listesi' THEN SELECT coalesce(jsonb_agg(x ORDER BY CASE x->>'oncelik' WHEN 'ACIL' THEN 0 WHEN 'YUKSEK' THEN 1 ELSE 2 END,coalesce(x->>'teslim_tarihi','9999'),x->>'kimlik' COLLATE "C"),'[]') INTO r FROM okuma.satirlar('gorevler') WHERE x->>'kisi'=kisi AND x->>'durum' NOT IN ('BITTI','IPTAL'); RETURN r;
 WHEN 'elle_sureler' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM jsonb_array_elements(okuma.tablo('araliklar')) x WHERE irp.dogru(x->'elle') AND saat.gun(x->>'gun') BETWEEN saat.gun(b) AND saat.gun(e) AND okuma.satir('kisiler',x->>'kisi')->>'birim'=g->>'birim'; RETURN r;
 WHEN 'kisi_uygun_mu' THEN RETURN okuma.kisi_uygun_mu(kisi,b,e,c);
 WHEN 'tezgah_uygun_mu' THEN RETURN okuma.tezgah_uygun_mu(g->>'tezgah',b,e);
 WHEN 'tezgah_gostergesi' THEN RETURN okuma.tezgah_gostergesi(g->>'tezgah',b,e);
 WHEN 'top_kimde' THEN RETURN okuma.top_kimde(g->>'kimlik');
 WHEN 'surumler' THEN RETURN okuma.surumler(g->>'nesne',c);
 WHEN 'gecerli_surum' THEN RETURN okuma.gecerli_surum(g->>'nesne',c);
 WHEN 'gantt' THEN RETURN okuma.gantt(g->>'proje',b,e,c);
 WHEN 'plan_cakismalari' THEN RETURN okuma.plan_cakismalari(g->'kaynak',b,e,c);
 WHEN 'plan_karsilastir' THEN RETURN okuma.plan_karsilastir(g->>'proje');
 WHEN 'iptal_edilenler' THEN RETURN okuma.iptal_edilenler(g->>'proje',b,e);
 WHEN 'gecikme_raporu' THEN RETURN okuma.gecikme_raporu(b,e,coalesce(g->>'kirilim','sorumlu'),c);
 WHEN 'sorumluluk_ekleri' THEN RETURN okuma.sorumluluk_ekleri(kisi,b,e,coalesce(g->>'tur','KISI'));
 WHEN 'degisiklik_gecmisi' THEN RETURN okuma.degisiklik_gecmisi(g->>'kaynak',c);
 WHEN 'proje_degisiklikleri' THEN RETURN okuma.proje_degisiklikleri(g->>'proje',b,e,c);
 WHEN 'proje_erisim_gecmisi' THEN RETURN okuma.proje_erisim_gecmisi(g->>'proje',c);
 WHEN 'onceki_donem_duzeltmeleri' THEN RETURN okuma.onceki_donem_duzeltmeleri();
 WHEN 'liste_surumu' THEN RETURN kapi.nesne('OKUMA','LISTE',kisi)->'surum';
 ELSE RAISE EXCEPTION 'IRP|BICIM|Bilinmeyen sorgu'; END CASE;
END $$;
CREATE FUNCTION okuma.oku(kim text,veri text,hedef text,g jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
<<okuma_baglami>>
DECLARE r jsonb; x jsonb; k text; a text; b text=g->>'bas'; e text=g->>'bit'; key text; t text; toplam jsonb; ab timestamptz[]; BEGIN
 IF veri NOT IN ('GANTT','PLAN_CAKISMALARI','SURUMLER','GECERLI_SURUM','BILDIRIMLER','PROJE','ETAP','NOT','DOSYA','PLAN','KIM_NEREDE','SAAT_NEREYE_GITTI','PERFORMANS','GUN','MAAS','SAAT_MALIYETI','IZIN','IZIN_DETAY','HAM_OLAY','FAZLA_MESAI','NESNE','UYGUNLUK','BIRIM_PERFORMANS','PROJE_DURUM','ETAP_DURUM','GOREV','IS','KISILER','BIRIMLER','TEZGAHLAR','TAKVIM','ETAPLAR','NESNELER','TOP_KIMDE','KAPASITE','TEZGAH_UYGUNLUK','TEZGAH_GOSTERGESI','TEZGAH_UCRETI','ISCILIK_MALIYETI','LISTE','KAYNAK_YUKU',
 'TELEFON','EKIP','HAVUZ','ONAY_LISTESI','KISININ_GUNU','BIRIM_DOLULUGU','MAAS_DAGILIMI','GUN_ISLERI','GECIKME_RAPORU','ELLE_SURELER','ATAMA_UYARILARI','YUK','PROJELER','YONLENDIRME','SUPHELILER','KODLAR','BUGUNKU_KIMLIKLER','PROJE_MALIYETI','PROJE_ISCILIGI','TAHMIN_GERCEK','PERSONEL_DAGILIMI') THEN RAISE EXCEPTION 'IRP|BICIM|TANIMSIZ_VERI'; END IF;
 -- Modelin eski özel kapıları kendi görme denetimlerini yapar.
 CASE veri
 WHEN 'GANTT' THEN RETURN okuma.gantt(hedef,b,e,kim);
 WHEN 'PLAN_CAKISMALARI' THEN RETURN okuma.plan_cakismalari(to_jsonb(hedef),b,e,kim);
 WHEN 'SURUMLER' THEN RETURN okuma.surumler(hedef,kim);
 WHEN 'GECERLI_SURUM' THEN RETURN okuma.ic('gecerli_surum',g||jsonb_build_object('nesne',hedef,'cagiran',kim));
 WHEN 'BILDIRIMLER' THEN RETURN okuma.bildirim_kutusu(hedef,kim);
 ELSE NULL; END CASE;
 IF NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 CASE veri
 WHEN 'KISILER' THEN SELECT coalesce(jsonb_agg(jsonb_build_object('kimlik',k,'surum',x->'surum','ad',x->'ad','birim',x->'birim','yaka',x->'yaka','roller',x->'roller','aktif',yetki_v6.istihdamda('OKUMA',k,saat.simdi()) AND coalesce((x->>'aktif')::boolean,true),'yetkinlikler',coalesce(x->'yetkinlikler','[]')) ORDER BY k COLLATE "C"),'[]') INTO r FROM okuma.satirlar('kisiler') WHERE coalesce(g->>'birim',hedef,'')='' OR x->>'birim'=coalesce(g->>'birim',hedef); RETURN r;
 WHEN 'BIRIMLER' THEN SELECT coalesce(jsonb_agg(jsonb_build_object('kimlik',k,'surum',x->'surum','ad',x->'ad','ust',x->'ust_birim','basi',x->'basi','yoneticileri',yetki_v6.yoneticiler('OKUMA',k),'takvim',motor.takvim('OKUMA',saat.kodla(saat.simdi()),NULL,k)) ORDER BY k COLLATE "C"),'[]') INTO r FROM okuma.satirlar('birimler'); RETURN r;
 WHEN 'TEZGAHLAR' THEN
  r='[]'; FOR k,x IN SELECT * FROM okuma.satirlar('tezgahlar') ORDER BY k COLLATE "C" LOOP
   IF coalesce(g->>'birim',hedef,'')<>'' AND x->>'birim'<>coalesce(g->>'birim',hedef) THEN CONTINUE; END IF;
   SELECT s.x->'vardiyalar' INTO toplam FROM okuma.satirlar('tezgah_takvimleri') s WHERE s.x->>'tezgah'=okuma_baglami.k AND saat.gun(s.x->>'gecerli_baslangic')<=saat.gun(saat.kodla(saat.simdi())) ORDER BY s.x->>'gecerli_baslangic' DESC,s.x->>'kimlik' COLLATE "C" DESC LIMIT 1;
   r=r||jsonb_build_array(jsonb_build_object('kod',k,'surum',x->'surum','ad',x->'ad','birim',x->'birim','aktif',coalesce(x->'aktif','true'),'vardiyalar',coalesce(toplam,'[]')));
  END LOOP; RETURN r;
 WHEN 'TAKVIM' THEN RETURN okuma.takvim(kim,g->>'tur',coalesce(g->>'kimlik',hedef),b,e);
 WHEN 'KAYNAK_YUKU' THEN RETURN okuma.kaynak_yuku(kim,g->>'tur',coalesce(g->>'kimlik',hedef),b,e,coalesce((g->>'kapasite_dahil')::boolean,false));
 WHEN 'ETAPLAR' THEN key=coalesce(g->>'proje',hedef); IF NOT k9.proje_gorebilir('OKUMA',kim,key) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF; SELECT coalesce(jsonb_agg(x ORDER BY k COLLATE "C"),'[]') INTO r FROM okuma.satirlar('etaplar') WHERE x->>'proje'=key; RETURN r;
 WHEN 'NESNELER' THEN SELECT coalesce(jsonb_agg(x ORDER BY k COLLATE "C"),'[]') INTO r FROM okuma.satirlar('nesneler') WHERE (coalesce(g->>'proje',hedef,'')='' OR x->>'proje'=coalesce(g->>'proje',hedef)) AND (coalesce(g->>'tur','')='' OR x->>'tur'=g->>'tur') AND (coalesce(g->>'kod','')='' OR x->>'kod'=g->>'kod') AND okuma.gorebilir(kim,'NESNE',k); RETURN r;
 WHEN 'TOP_KIMDE' THEN key=coalesce(g->>'nesne',hedef); IF NOT okuma.gorebilir(kim,'NESNE',key) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.top_kimde(key);
 WHEN 'KAPASITE' THEN key=coalesce(g->>'kisi',hedef); ab=okuma.pencere(b,e); IF NOT coalesce(okuma.tablo('kisiler') ? key,false) THEN RAISE EXCEPTION 'IRP|BICIM|Kisi'; END IF; RETURN to_jsonb(okuma.kapasite_araligi(key,ab[1],ab[2]));
 WHEN 'TEZGAH_UYGUNLUK' THEN ab=okuma.pencere(b,e); RETURN okuma.tezgah_uygun_mu(coalesce(g->>'tezgah',hedef),saat.kodla(ab[1]),saat.kodla(ab[2]));
 WHEN 'TEZGAH_GOSTERGESI' THEN RETURN okuma.tezgah_gostergesi(coalesce(g->>'tezgah',hedef),b,e);
 WHEN 'TEZGAH_UCRETI' THEN IF NOT okuma.satir('kisiler',kim)->'roller' ?| ARRAY['YETKILI','MALIYET'] THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN coalesce(okuma.kodlu_tutar(okuma.tutar_bul(coalesce(g->>'tezgah',hedef),'SAAT_UCRETI',g->>'gun')),'"VERI_EKSIK"');
 WHEN 'ISCILIK_MALIYETI' THEN key=coalesce(g->>'proje',hedef); IF NOT okuma.gorebilir(kim,'TUTAR') OR NOT k9.proje_gorebilir('OKUMA',kim,key) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF; RETURN okuma.iscilik_maliyeti(key,b,e);
 WHEN 'LISTE' THEN key=coalesce(g->>'kisi',hedef); IF NOT okuma.gorebilir(kim,'IS',key) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
  SELECT coalesce(jsonb_agg(okuma.satir('isler',value)),'[]') INTO r FROM jsonb_array_elements_text(coalesce(okuma.satir('listeler',key),'[]')) WHERE okuma.gorebilir(kim,'IS',value);
  RETURN jsonb_build_object('isler',r,'surum',kapi.nesne('OKUMA','LISTE',key)->'surum');
 ELSE NULL; END CASE;
 IF veri IN ('TELEFON','EKIP','HAVUZ','ONAY_LISTESI','KISININ_GUNU','BIRIM_DOLULUGU','MAAS_DAGILIMI','GUN_ISLERI','GECIKME_RAPORU','ELLE_SURELER','ATAMA_UYARILARI','YUK','PROJELER','YONLENDIRME','SUPHELILER','KODLAR','BUGUNKU_KIMLIKLER','PROJE_MALIYETI','PROJE_ISCILIGI','TAHMIN_GERCEK','PERSONEL_DAGILIMI') THEN RETURN okuma.ek_oku(kim,veri,hedef,g); END IF;
 IF NOT okuma.gorebilir(kim,veri,hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorunurluk'; END IF;
 CASE veri
 WHEN 'PROJE' THEN RETURN okuma.satir('projeler',hedef);
 WHEN 'ETAP' THEN RETURN okuma.satir('etaplar',hedef);
 WHEN 'NOT' THEN RETURN okuma.satir('notlar',hedef);
 WHEN 'DOSYA' THEN RETURN okuma.satir('dosyalar',hedef);
 WHEN 'PLAN' THEN RETURN okuma.plan_karsilastir(hedef);
 WHEN 'KIM_NEREDE' THEN RETURN okuma.kim_nerede(b,e,kim);
 WHEN 'SAAT_NEREYE_GITTI' THEN RETURN okuma.saat_nereye_gitti(b,e,kim);
 WHEN 'PERFORMANS' THEN RETURN okuma.adil_performans(hedef,b,e,kim);
 WHEN 'GUN' THEN RETURN okuma.gun_sonu_raporu(hedef,g->>'gun')-'gecmis';
 WHEN 'MAAS' THEN RETURN okuma.aylik_maliyet_ozeti(hedef,g->>'ay');
 WHEN 'SAAT_MALIYETI' THEN RETURN coalesce(okuma.kodlu_tutar(okuma.saat_maliyeti(hedef,g->>'gun')),'"VERI_EKSIK"');
 WHEN 'IZIN','IZIN_DETAY' THEN SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar('izinler') WHERE x->>'kisi'=hedef; RETURN r;
 WHEN 'HAM_OLAY' THEN SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]') INTO r FROM public.olaylar WHERE (public.olaylar.kim=hedef OR okuma.satir('kisiler',oku.kim)->'roller' ? 'YETKILI') AND okuma.surum_olayi_gorebilir(oku.kim,icerik); RETURN r;
 WHEN 'FAZLA_MESAI' THEN SELECT coalesce(jsonb_agg(CASE WHEN okuma.gorebilir(kim,'TUTAR') THEN x ELSE x-'prim' END),'[]') INTO r FROM jsonb_array_elements(okuma.fazla_mesai_kayitlari()) x WHERE x->>'kisi'=hedef; RETURN r;
 WHEN 'NESNE' THEN RETURN okuma.satir('nesneler',hedef);
 WHEN 'UYGUNLUK' THEN RETURN okuma.kisi_uygun_mu(hedef,b,e,kim);
 WHEN 'BIRIM_PERFORMANS' THEN
  toplam='{"teslim":0,"zamaninda":0,"kalite_ret":0,"sebep_olunan_gecikme":0}';
  FOR k IN SELECT s.k FROM okuma.satirlar('kisiler') s WHERE s.x->>'birim'=hedef LOOP x=okuma.adil_performans(k,b,e); FOREACH a IN ARRAY ARRAY['teslim','zamaninda','kalite_ret','sebep_olunan_gecikme'] LOOP toplam=okuma.ekle(toplam,a,(x->>a)::numeric); END LOOP; END LOOP;
  x=okuma.sorumluluk_performansi(hedef,b,e,'BIRIM'); FOREACH a IN ARRAY ARRAY['kalite_ret','sebep_olunan_gecikme'] LOOP toplam=okuma.ekle(toplam,a,(x->>a)::numeric); END LOOP; RETURN toplam;
 WHEN 'PROJE_DURUM','ETAP_DURUM' THEN r=CASE WHEN veri='PROJE_DURUM' THEN okuma.proje_gostergesi(hedef,kim) ELSE okuma.etap_gostergesi(hedef) END; RETURN CASE WHEN okuma.gorebilir(kim,'TUTAR') THEN r ELSE okuma.ayikla(r) END;
 WHEN 'IS','GOREV' THEN a=CASE WHEN veri='IS' THEN 'isler' ELSE 'gorevler' END; IF okuma.tablo(a) ? hedef THEN RETURN okuma.satir(a,hedef); END IF;
  SELECT coalesce(jsonb_agg(x),'[]') INTO r FROM okuma.satirlar(a) WHERE x->>'kisi'=hedef AND okuma.gorebilir(kim,veri,x->>'kimlik'); RETURN r;
 ELSE RAISE EXCEPTION 'IRP|BICIM|Tanimli gorunum gerekli'; END CASE;
END $$;
RESET ROLE;
