SET ROLE irp_sahibi;
-- yasam_v5.py:8 listeden_cikar. Değişen iş ve eski liste başları birlikte döner.
CREATE FUNCTION yasam_v5.listeden_cikar(m text,i jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE sahipler jsonb='[]'; k text; l jsonb; BEGIN
 FOR k,l IN SELECT * FROM motor.satirlar(m,'listeler') LOOP IF l ? (i->>'kimlik') THEN sahipler=sahipler||jsonb_build_array(jsonb_build_array(k,l->0)); END IF; END LOOP;
 PERFORM liste.cikar(m,i->>'kimlik'); i=i||'{"kisi":null,"sira":null}'; PERFORM motor.kaydet(m,'isler',i->>'kimlik',i);
 RETURN jsonb_build_object('is',i,'sahipler',sahipler); END $$;
-- yasam_v5.py:21 isle; onay kararı ile kişisel beklemenin ayrılması.
CREATE FUNCTION yasam_v5.isle(m text,e jsonb) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; t timestamptz=saat.an(e->>'oldugu_an'); ids text[]=kapi.hedefler(e,'IS'); i jsonb; x jsonb; k text; h jsonb; once jsonb; sahip jsonb; cik jsonb; eski text; l jsonb; onceki jsonb='{}'; uygun boolean; alanlar jsonb;
BEGIN
 i=motor.kayit(m,'isler',ids[1]); IF NOT irp.dogru(i) THEN RETURN false; END IF;
 IF kod='IS.BAGLANTI_DUZELTTIM' THEN FOR k,x IN SELECT * FROM motor.satirlar(m,'isler') WHERE anahtar=ids[1] OR hal->>'ana_is'=ids[1] LOOP PERFORM motor.kaydet(m,'isler',k,x||(g->'degisenler')); END LOOP; RETURN true; END IF;
 IF kod='IS.IPTAL_ETTIM' THEN
  FOR x IN SELECT hal FROM motor.satirlar(m,'isler') WHERE anahtar=ids[1] OR hal->>'ana_is'=ids[1] LOOP
   IF x->>'durum'='IPTAL' THEN CONTINUE; END IF;
   x=x||jsonb_build_object('iptal_oncesi_durum',x->'durum','iptal_eden',e->'kim','iptal_oncesi_bitis_ani',x->'bitis_ani','durum','IPTAL','iptal_ani',saat.kodla(t),'iptal_gerekcesi',g->'gerekce','bitis_ani',NULL,'acik_ariza',NULL);
   cik=yasam_v5.listeden_cikar(m,x); x=cik->'is';
   FOR sahip IN SELECT value FROM jsonb_array_elements(cik->'sahipler') LOOP k=sahip->>0; eski=sahip->>1; h=motor.kayit(m,'kisi_durumu',k,kg.bos_hal()); once=CASE WHEN h->>'durum'='SABIT_MOLADA' THEN h->'mola_onceki' ELSE h END;
    IF once->>'durum'='ONAY_BEKLIYOR' AND once->'aralik_is'=x->'kimlik' THEN PERFORM kg.uygula(m,k,'IS.ONAYLADIM',t,e,x); IF NOT irp.dogru(motor.kayit(m,'listeler',k,'[]')) THEN PERFORM motor.bildir(m,e,'R08',x->>'atayan',t,k); END IF;
    ELSIF eski=x->>'kimlik' THEN PERFORM kg.uygula(m,k,'LISTE_DEGISTI',t,e,x); END IF; END LOOP;
  END LOOP; PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); PERFORM gorev.bagimliliklari_hesapla(m); RETURN true;
 END IF;
 IF kod='IS.DEGISTIRDIM' THEN
  FOR k,l IN SELECT * FROM motor.satirlar(m,'listeler') WHERE irp.dogru(hal) LOOP onceki=onceki||jsonb_build_object(k,coalesce(motor.kayit(m,'isler',l->>0)->'kilitli','false')); END LOOP;
  alanlar=g->'degisenler'; FOR k,x IN SELECT * FROM motor.satirlar(m,'isler') WHERE anahtar=ids[1] OR hal->>'ana_is'=ids[1] LOOP
   x=x||alanlar; IF k=ids[1] AND alanlar ? 'tahmini_sure_dk' AND EXISTS(SELECT FROM motor.satirlar(m,'isler') WHERE hal->>'ana_is'=k) THEN x=x||jsonb_build_object('tahmini_sure_dk',(x->>'tahmini_sure_dk')::int*(x->>'kisi_sayisi')::int); END IF; PERFORM motor.kaydet(m,'isler',k,x); END LOOP;
  PERFORM kg.isleri_guncelle(m,t,e); FOR k,h IN SELECT * FROM jsonb_each(onceki) LOOP x=motor.kayit(m,'isler',motor.kayit(m,'listeler',k,'[]')->>0); IF NOT irp.dogru(h) AND irp.dogru(x->'kilitli') THEN PERFORM kg.uygula(m,k,'LISTE_DEGISTI',t,e,x); END IF; END LOOP; RETURN true;
 END IF;
 IF irp.dogru(i->'onay_beklet') OR NOT irp.dogru(i->'onay_gerekli') THEN RETURN false; END IF;
 IF kod IN ('IS.TAMAMLADIM','ELLE_BITIS') THEN
  k=coalesce(e->>'adina',e->>'kim'); h=motor.kayit(m,'kisi_durumu',k,kg.bos_hal()); l=motor.kayit(m,'listeler',k,'[]'); uygun=kod='ELLE_BITIS' OR kg.kapi(h,kod,i,l->>0,motor.sabit_molada(m,t));
  IF NOT uygun THEN PERFORM motor.supheli(m,e,'Calisan kapisi kapali'); END IF;
  IF i->>'durum' NOT IN ('SIRADA','YARIM','CALISILIYOR','REDDEDILDI') THEN RETURN true; END IF;
  i=i||jsonb_build_object('durum','ONAY_BEKLIYOR','bitis_ani',NULL,'tamamlayan',k,'onay_bekleme_ani',saat.kodla(t),'acik_ariza',NULL);
  cik=yasam_v5.listeden_cikar(m,i); i=cik->'is';
  FOR sahip IN SELECT value FROM jsonb_array_elements(cik->'sahipler') LOOP h=motor.kayit(m,'kisi_durumu',sahip->>0,kg.bos_hal()); once=CASE WHEN h->>'durum'='SABIT_MOLADA' THEN h->'mola_onceki' ELSE h END;
   IF once->'acik_is'=i->'kimlik' OR uygun AND kod<>'ELLE_BITIS' AND sahip->1=i->'kimlik' THEN PERFORM kg.uygula(m,sahip->>0,'IS.TAMAMLADIM',t,e,i||'{"onay_gerekli":false}'); END IF;
   IF NOT irp.dogru(motor.kayit(m,'listeler',sahip->>0,'[]')) THEN PERFORM motor.bildir(m,e,'R08',i->>'atayan',t,sahip->>0); END IF;
  END LOOP;
  PERFORM motor.bildir(m,e,'R05',i->>'atayan',t,k); PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); RETURN true;
 ELSIF kod='IS.ONAYLADIM' THEN PERFORM motor.kaydet(m,'isler',ids[1],i||jsonb_build_object('durum','BITTI','bitis_ani',saat.kodla(t))); PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); RETURN true;
 ELSIF kod='IS.REDDETTIM' THEN
  i=i||'{"durum":"REDDEDILDI"}'; PERFORM motor.kaydet(m,'isler',ids[1],i); k=i->>'tamamlayan';
  IF k IS NOT NULL AND NOT irp.dogru(motor.kayit(m,'kisiler',k)->'ayrilis_tarihi') THEN l=motor.kayit(m,'listeler',k,'[]'); eski=l->>0; l=liste.yerlestir(l,i->>'kimlik',CASE WHEN irp.dogru(l) THEN 2 ELSE 1 END); PERFORM motor.kaydet(m,'listeler',k,l); IF eski IS DISTINCT FROM l->>0 THEN PERFORM kg.uygula(m,k,'LISTE_DEGISTI',t,e,i); END IF; END IF;
  PERFORM kg.isleri_guncelle(m,t,e); PERFORM kg.ana_isleri_guncelle(m); RETURN true;
 END IF;
 RETURN false;
END $$;
CREATE OR REPLACE FUNCTION kg.elle_uygula(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE e jsonb; g jsonb; kisi text; bas timestamptz; bit timestamptz; yeni jsonb; a jsonb; son timestamptz; x timestamptz; y timestamptz; i jsonb; BEGIN
 FOR e IN SELECT value FROM jsonb_array_elements(motor.oku(m,'elle_olaylar','[]')) LOOP
  g=e->'girdiler'; kisi=e->>'adina'; bas=saat.an(g->>'baslangic'); bit=least(saat.an(g->>'bitis'),saat.simdi());
  IF to_char(bas AT TIME ZONE 'Europe/Istanbul','IYYY-IW')<>to_char(saat.an(e->>'oldugu_an') AT TIME ZONE 'Europe/Istanbul','IYYY-IW') THEN PERFORM motor.supheli(m,e,'Ayni hafta disinda'); END IF;
  yeni='[]'; FOR a IN SELECT value FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) LOOP
   son=coalesce(saat.an(a->>'bitis'),saat.simdi()); x=greatest(saat.an(a->>'baslangic'),bas); y=least(son,bit);
   IF a->>'kisi' IS DISTINCT FROM kisi OR a->>'kova' NOT IN ('TANIMSIZ','GECIS') OR x>=y THEN yeni=yeni||jsonb_build_array(a); CONTINUE; END IF;
   IF saat.an(a->>'baslangic')<x THEN yeni=yeni||jsonb_build_array(a||jsonb_build_object('bitis',saat.kodla(x))); END IF;
   i=motor.kayit(m,'isler',(kapi.hedefler(e,'IS'))[1]); yeni=yeni||jsonb_build_array(a||jsonb_build_object('baslangic',saat.kodla(x),'bitis',saat.kodla(y),'kova','CALISMA','is_',NULL,'is',i->'kimlik','proje',i->'proje','kategori',i->'kategori','plansiz',coalesce(i->'plansiz','false'),'elle',true,'aciklama',g->'aciklama','yazan',e->'kim','acan_olay',e->'olay_kimligi'));
   IF y<son THEN yeni=yeni||jsonb_build_array(a||jsonb_build_object('baslangic',saat.kodla(y))); END IF;
  END LOOP; PERFORM motor.yaz(m,'araliklar',yeni);
 END LOOP; END $$;
RESET ROLE;
