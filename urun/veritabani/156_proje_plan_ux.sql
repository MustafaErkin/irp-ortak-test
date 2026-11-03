-- Proje/etap kabul kuralları değişmez; kesin ret nedenlerini arayüze taşır.
SET ROLE irp_sahibi;
CREATE FUNCTION kapi.proje_alan_hatasi(e jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE code text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; s jsonb; p jsonb; pid text; path text=''; msg text; prefix text=''; BEGIN
 IF code NOT IN ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM','PROJE.DEGISTIRDIM','PROJE.KAPATTIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM','PLAN.ONAYLADIM') THEN RETURN '{}'; END IF;
 IF code IN ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM') THEN
  IF EXISTS(SELECT FROM motor.satirlar('YAYIN','projeler') p CROSS JOIN LATERAL jsonb_array_elements(p.hal->'kod_gecmisi') h WHERE h->'kod'=g->'kod' AND coalesce(h->>'ek','')=coalesce(g->>'ek','')) THEN path='kod';msg='Bu proje kodu daha önce kullanılmış. Başka bir kod girin.'; END IF;
 END IF;
 IF code LIKE 'ETAP.%' THEN
  s=CASE WHEN code='ETAP.TANIMLADIM' THEN g ELSE motor.kayit('YAYIN','etaplar',(kapi.hedefler(e,'ETAP'))[1])||(g->'degisenler') END;
  pid=s->>'proje';prefix=CASE WHEN code='ETAP.DEGISTIRDIM' THEN 'degisenler.' ELSE '' END;
  IF saat.an(s->>'baslangic')>saat.an(s->>'bitis') THEN path=prefix||'bitis';msg='Bitiş tarihi başlangıçtan önce olamaz.';
  ELSIF NOT motor.oku('YAYIN','birimler') ? (s->>'birim') THEN path=prefix||'birim';msg='Bu birim artık kullanılamıyor. Geçerli bir birim seçin.';
  ELSIF irp.dogru(s->'sorumlu') AND NOT kapilar_v5.aktif_kisi('YAYIN',s->>'sorumlu') THEN path=prefix||'sorumlu';msg='Etap sorumlusu aktif bir çalışan olmalı.'; END IF;
 ELSE pid=coalesce(g->>'proje',(kapi.hedefler(e,'PROJE'))[1]); END IF;
 p=motor.kayit('YAYIN','projeler',pid);
 IF pid IS NOT NULL AND code NOT IN ('PROJE.ACTIM','PROJE.KOD_DEGISTIRDIM') AND NOT irp.dogru(p->'aktif') THEN path=CASE WHEN code='ETAP.TANIMLADIM' THEN 'proje' ELSE '' END;msg='Bu proje kapalı veya artık kullanılamıyor. İşlem yapılamaz.'; END IF;
 IF code='PROJE.KAPATTIM' AND irp.dogru(p->'aktif') THEN path='';msg='Proje kapatılamıyor. Önce açık iş ve görevleri tamamlayın veya iptal edin.'; END IF;
 IF code='PLAN.ONAYLADIM' AND irp.dogru(p->'aktif') AND NOT EXISTS(SELECT FROM motor.satirlar('YAYIN','etaplar') WHERE hal->>'proje'=pid) THEN path='';msg='Planı onaylamak için önce en az bir etap oluşturun.'; END IF;
 IF code='PROJE.ACTIM' AND msg IS NULL AND irp.dogru(g->'sorumlu') AND NOT kapilar_v5.aktif_kisi('YAYIN',g->>'sorumlu') THEN path='sorumlu';msg='Proje sorumlusu aktif bir çalışan olmalı.'; END IF;
 IF msg IS NULL THEN RETURN '{}'; END IF;
 RETURN jsonb_build_object('mesaj',msg,'alan_hatalari',jsonb_build_array(jsonb_build_object('path',path,'message',msg)));
END $$;
CREATE OR REPLACE FUNCTION public.olay_ekle(olay jsonb,hassas_ek jsonb DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
#variable_conflict use_column
DECLARE r jsonb; hesap text; BEGIN
 r=kapi.ekle(olay,hassas_ek);
 -- Yalnız yetki/biçim kontrolünden geçmiş kesin durum reddini açıkla.
 IF r->>'kod'='DURUM' THEN r=r||kapi.proje_alan_hatasi(olay); END IF;
 hesap=coalesce(r->>'hesap',CASE WHEN (SELECT bekleyen_sinir FROM motor.durum WHERE tek) IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END);
 RETURN r||jsonb_build_object('alindi',r->>'sonuc'='BASARILI','hesap',hesap);
END $$;

-- 155 okuma/yetki yolları aynen korunur; proje ek erişimi isteğe bağlıdır.
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
 IF veri='WEB_KISI' THEN deger=okuma.web_kisi_ayrintisi(kim,hedef);
 ELSIF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 IF veri='PLAN' AND coalesce((g->>'surumler')::boolean,false) THEN
  deger=deger||jsonb_build_object('surumler',coalesce(okuma.satir('plan_surumleri',hedef),'[]'));
 END IF;
 IF veri='GANTT' AND coalesce((g->>'adlar')::boolean,false) THEN
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('ad',okuma.satir(CASE x->>'tur' WHEN 'ETAP' THEN 'etaplar' WHEN 'IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->'ad')),'[]') INTO deger
  FROM jsonb_array_elements(deger) x;
 END IF;
 IF veri='PROJE' AND coalesce((g->>'ekip')::boolean,false) AND deger IS NOT NULL THEN
  -- Ana oku çağrısı proje görünürlüğünü denetledi. Yalnız güncel ek erişim listesi.
  deger=deger||jsonb_build_object('ek_erisim',coalesce((SELECT jsonb_agg(k) FROM okuma.satirlar('kisiler') WHERE k10.ek_erisim('OKUMA',k,hedef)),'[]'::jsonb));
 END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
