-- T20: İş ekranlarının seçim ve listeleri. İş kuralları değişmez; aynı okuma kapısı.
SET ROLE irp_sahibi;
CREATE FUNCTION okuma.web_oku(kim text,veri text,hedef text,g jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; x jsonb; k text; a text; rows jsonb; roller jsonb=okuma.satir('kisiler',kim)->'roller'; yonetilen jsonb; yetkili boolean=coalesce(roller ? 'YETKILI',false);
BEGIN
 IF NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi()) THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') INTO yonetilen FROM okuma.satirlar('birimler') WHERE okuma.birim_gorebilir(kim,k);
 CASE veri
 WHEN 'WEB_BAGLAM' THEN
  SELECT coalesce(jsonb_agg(x ORDER BY k),'[]') INTO rows FROM okuma.satirlar('nesne_turleri');
  r=jsonb_build_object('yonetilen_birimler',yonetilen,'nesne_turleri',rows,'moduller',okuma.tablo('moduller'));
  SELECT coalesce(jsonb_agg(DISTINCT v->>'eylem_kodu'),'[]') INTO rows FROM jsonb_array_elements(coalesce(okuma.tablo('yetki_kurallari'),'[]')) v
   WHERE NOT irp.dogru(v->'gecerli_bitis') AND (yetki_v6.tablo_izni('OKUMA',kim,v->>'eylem_kodu',NULL)
    OR EXISTS(SELECT FROM jsonb_array_elements_text(yonetilen) b(value) WHERE yetki_v6.tablo_izni('OKUMA',kim,v->>'eylem_kodu',b.value)));
  r=r||jsonb_build_object('islem_izinleri',rows);
  SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') INTO rows FROM okuma.satirlar('kisiler') WHERE okuma.gorebilir(kim,'GUN',k);
  RETURN r||jsonb_build_object('gorulebilen_kisiler',rows);
 WHEN 'WEB_ISLER','WEB_GOREVLER' THEN
  a=CASE WHEN veri='WEB_ISLER' THEN 'isler' ELSE 'gorevler' END;
  SELECT coalesce(jsonb_agg(x ORDER BY x->>'teslim_tarihi',k),'[]') INTO rows FROM okuma.satirlar(a)
   WHERE okuma.gorebilir(kim,CASE WHEN veri='WEB_ISLER' THEN 'IS' ELSE 'GOREV' END,k)
    AND (coalesce(g->>'proje','')='' OR x->>'proje'=g->>'proje')
    AND (coalesce(g->>'birim','')='' OR coalesce(x->>'birim',okuma.satir('kisiler',x->>'kisi')->>'birim')=g->>'birim')
    AND (coalesce(g->>'kisi','')='' OR x->>'kisi'=g->>'kisi');
  RETURN rows;
 WHEN 'WEB_DOSYALAR','WEB_NOTLAR' THEN
  IF coalesce(g->>'tur','') NOT IN ('IS','GOREV','NESNE','PROJE') OR NOT okuma.gorebilir(kim,g->>'tur',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Nesne ekleri'; END IF;
  IF veri='WEB_NOTLAR' THEN
   SELECT coalesce(jsonb_agg(x ORDER BY k),'[]') INTO rows FROM okuma.satirlar('notlar')
    WHERE x->'neyin_ustunde' @> jsonb_build_array(jsonb_build_object('tur',g->>'tur','kimlik',hedef)) AND okuma.gorebilir(kim,'NOT',k);
  ELSE
   SELECT coalesce(jsonb_agg(d.x||jsonb_build_object('kimlik',d.k) ORDER BY d.k),'[]') INTO rows FROM okuma.satirlar('dosyalar') d
    JOIN public.olaylar e ON e.olay_kimligi=d.x->>'doguran_olay'
    WHERE e.icerik->'neyin_ustunde' @> jsonb_build_array(jsonb_build_object('tur',g->>'tur','kimlik',hedef)) AND okuma.gorebilir(kim,'DOSYA',d.k);
  END IF;
  RETURN rows;
 WHEN 'WEB_KISI' THEN
  IF NOT okuma.gorebilir(kim,'GUN',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Çalışan bilgisi'; END IF;
  RETURN okuma.satir('kisiler',hedef);
 WHEN 'WEB_KAYNAKLAR' THEN
  -- İK, onaylaması gereken izinleri görebilir (karar 85, T18 İ-2).
  SELECT coalesce(jsonb_agg(x-'olay' ORDER BY k),'[]') INTO rows FROM okuma.satirlar('izinler')
   WHERE (x->>'kisi'=kim OR okuma.gorebilir(kim,'GUN',x->>'kisi') OR roller ? 'IK')
    AND (hedef IS NULL OR x->>'kisi'=hedef);
  r=jsonb_build_object('izinler',rows);
  SELECT coalesce(jsonb_agg(x ORDER BY k),'[]') INTO rows FROM okuma.satirlar('ek_mesai_planlari') WHERE okuma.gorebilir(kim,'GUN',x->>'kisi') AND (hedef IS NULL OR x->>'kisi'=hedef);
  r=r||jsonb_build_object('ek_mesai',rows,'bakimlar',okuma.tablo('bakimlar'),'tezgah_duruslari',okuma.tablo('tezgah_duruslari'),
   'duruslar',okuma.tablo('duruslar'),'gun_tanimlari',okuma.tablo('gun_tanimlari'),'tatiller',okuma.tablo('tatiller'),
   'takvim',motor.takvim('OKUMA',saat.kodla(saat.simdi()),kim),'tezgah_takvimleri',okuma.tablo('tezgah_takvimleri'));
  RETURN r;
 WHEN 'WEB_SORUMLULUK' THEN
  rows='[]'; FOR k,x IN SELECT * FROM okuma.satirlar('sorumluluklar') LOOP
   IF yetkili OR (x->>'tur'='KISI' AND okuma.gorebilir(kim,'GUN',x->>'kimlik')) OR (x->>'tur'='BIRIM' AND okuma.birim_gorebilir(kim,x->>'kimlik')) THEN rows=rows||jsonb_build_array(x); END IF;
  END LOOP;
  r=jsonb_build_object('sorumluluklar',rows);
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('kimlik',k)),'[]') INTO rows FROM okuma.satirlar('itirazlar')
   WHERE EXISTS(SELECT FROM jsonb_array_elements(r->'sorumluluklar') s WHERE s->>'satir'=x->>'sorumluluk');
  RETURN r||jsonb_build_object('itirazlar',rows);
 WHEN 'WEB_FIRMA' THEN
  IF NOT yetkili THEN RAISE EXCEPTION 'IRP|YETKI|Firma yönetimi'; END IF;
  RETURN jsonb_build_object('ayarlar',okuma.tablo('ayarlar'),'yetkiler',okuma.tablo('yetki_kurallari'),
   'gun_onay_ayarlari',okuma.tablo('gun_onay_ayarlari'),'yonlendirme',okuma.tablo('yonlendirme'),
   'nesne_turleri',okuma.tablo('nesne_turleri'),'moduller',okuma.tablo('moduller'),'kodlar',okuma.tablo('kod_listesi'));
 WHEN 'WEB_HESAPLAR' THEN
  IF NOT yetkili THEN RAISE EXCEPTION 'IRP|YETKI|Hesap yönetimi'; END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_object('kisi',s.k,'ad',s.x->'ad','hesap_var',EXISTS(SELECT FROM public.kisi_hesaplari h WHERE h.kisi=s.k)) ORDER BY s.k),'[]') INTO rows FROM okuma.satirlar('kisiler') s;
  RETURN rows;
 ELSE RAISE EXCEPTION 'IRP|BICIM|TANIMSIZ_VERI';
 END CASE;
END $$;
REVOKE ALL ON FUNCTION okuma.web_oku(text,text,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
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
 IF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
