SET ROLE irp_sahibi;
-- depo.py:181 kurulum: başarısız paket alt işlemle bütünüyle geri alınır.
CREATE FUNCTION kapi.kurulum(olaylar jsonb,kod_listeleri jsonb) RETURNS jsonb LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE gerekli text[]=ARRAY['KOD.TANIMLADIM','YETKI.TANIMLADIM','KURULUM.TAMAMLADIM','AYAR.ONAY_ORANI','AYAR.MAAS_PAYDASI','AYAR.PARCA_KODU_DESENI','TAKVIM.TANIMLADIM','BIRIM.TANIMLADIM','KISI.EKLEDIM']; kodlar text[]; e jsonb; sonuc jsonb; p jsonb; b jsonb; k text; bid text; u uuid; once_jwt text=current_setting('request.jwt.claims',true); once_ayar text=current_setting('irp.kurulum',true); neden text;
BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 IF EXISTS(SELECT FROM public.olaylar) OR (SELECT kurulum_tamamlandi FROM motor.durum WHERE tek) THEN RETURN kapi.red('DURUM','Kurulum yalniz bos firmada'); END IF;
 IF jsonb_typeof(olaylar) IS DISTINCT FROM 'array' OR olaylar='[]' THEN RETURN kapi.red('BICIM','Kurulum olaylari eksik ya da kapsam disi'); END IF;
 SELECT array_agg(value->>'eylem_kodu') INTO kodlar FROM jsonb_array_elements(olaylar);
 IF NOT kodlar @> gerekli OR NOT kodlar <@ (gerekli||ARRAY['TATIL.EKLEDIM']) THEN RETURN kapi.red('BICIM','Kurulum olaylari eksik ya da kapsam disi'); END IF;
 IF jsonb_typeof(kod_listeleri) IS DISTINCT FROM 'object' OR EXISTS(SELECT FROM jsonb_each(kod_listeleri) WHERE jsonb_typeof(value)<>'array') THEN RETURN kapi.red('BICIM','Kod listeleri gerekli'); END IF;
 IF olaylar->-1->>'eylem_kodu'<>'KURULUM.TAMAMLADIM' THEN RETURN kapi.red('BICIM','Kurulumun son olayi eksik'); END IF;
 BEGIN
  INSERT INTO irp.kisiler_oturum VALUES('SERVIS',gen_random_uuid()) ON CONFLICT DO NOTHING; SELECT oturum INTO u FROM irp.kisiler_oturum WHERE kisi='SERVIS';
  PERFORM set_config('request.jwt.claims',jsonb_build_object('sub',u,'role','service_role')::text,true); PERFORM set_config('irp.kurulum','evet',true); PERFORM set_config('irp.kurulum_toplu','evet',true);
  FOR e IN SELECT value FROM jsonb_array_elements(olaylar) LOOP
   IF e->>'giris_sekli'<>'AKTARIM' THEN sonuc=kapi.red('BICIM','Kurulum AKTARIM olmali'); RAISE EXCEPTION USING ERRCODE='P0020',MESSAGE='Kurulum reddi',DETAIL=sonuc::text; END IF;
   sonuc=kapi.ekle(e); IF sonuc->>'sonuc'<>'BASARILI' THEN RAISE EXCEPTION USING ERRCODE='P0020',MESSAGE='Kurulum reddi',DETAIL=(sonuc-'hesap')::text; END IF;
  END LOOP;
  PERFORM set_config('irp.kurulum_toplu','',true);
  PERFORM motor.yeniden_kur(); WHILE motor.arka_plan_calistir()>0 LOOP NULL; END LOOP;
  IF EXISTS(SELECT FROM public.isleme_hatalari) OR (SELECT count(*) FROM motor.satirlar('YAYIN','kisiler'))<>1 OR (SELECT count(*) FROM motor.satirlar('YAYIN','birimler'))<>1 THEN sonuc=kapi.red('DURUM','Tek kok ve ilk yetkili gerekli');
  ELSE SELECT anahtar,hal INTO k,p FROM motor.satirlar('YAYIN','kisiler') LIMIT 1; SELECT anahtar,hal INTO bid,b FROM motor.satirlar('YAYIN','birimler') LIMIT 1;
   IF p->>'birim' IS DISTINCT FROM bid OR NOT p->'roller' ?& ARRAY['YETKILI','YONETICI'] OR b->>'basi' IS DISTINCT FROM k OR irp.dogru(b->'ust_birim') THEN sonuc=kapi.red('DURUM','Kurulum kok/yetkili baglantisi gecersiz');
   ELSIF EXISTS(SELECT FROM jsonb_array_elements_text(p->'roller') r WHERE NOT k6.kod_aktif('YAYIN','ROL',r)) THEN sonuc=kapi.red('DURUM','Kurulum rolleri eksik');
   ELSIF NOT (SELECT kurulum_tamamlandi FROM motor.durum WHERE tek) THEN sonuc=kapi.red('DURUM','Kurulum kapanmadi');
   ELSE sonuc='{"sonuc":"BASARILI","tekrar":false}'; END IF;
  END IF;
  IF sonuc->>'sonuc'<>'BASARILI' THEN RAISE EXCEPTION USING ERRCODE='P0020',MESSAGE='Kurulum reddi',DETAIL=sonuc::text; END IF;
  UPDATE motor.durum SET kod_listeleri=$2 WHERE tek;
  PERFORM set_config('request.jwt.claims',coalesce(once_jwt,''),true); PERFORM set_config('irp.kurulum',coalesce(once_ayar,''),true);
 EXCEPTION WHEN SQLSTATE 'P0020' THEN GET STACKED DIAGNOSTICS neden=PG_EXCEPTION_DETAIL; RETURN neden::jsonb;
 END;
 RETURN sonuc;
END $$;
RESET ROLE;
