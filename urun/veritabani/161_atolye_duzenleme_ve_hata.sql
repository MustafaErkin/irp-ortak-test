-- Tur 3.1: iş açıklaması düzenlenebilir; ret nedenleri alanıyla açıklanır.
-- Durum/sıra/önkoşul/yetki/maliyet kuralları mevcut denetimden geçmeye devam eder.
SET ROLE irp_sahibi;

ALTER FUNCTION kapilar_v5.ek_denetim(text,jsonb) RENAME TO ek_denetim_160;
CREATE FUNCTION kapilar_v5.ek_denetim(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN
 IF e->>'eylem_kodu'='IS.DEGISTIRDIM' AND e->'girdiler'->'degisenler' ? 'is_tanimi' THEN
  IF jsonb_typeof(e#>'{girdiler,degisenler,is_tanimi}') NOT IN ('string','null') THEN RETURN false; END IF;
  -- Yalnız yeni açıklama alanını eski izinli alan denetiminden ayır.
  -- Motor gerçek olaydaki açıklamayı diğer değişikliklerle birlikte uygular.
  RETURN kapilar_v5.ek_denetim_160(d,jsonb_set(e,'{girdiler,degisenler}',(e#>'{girdiler,degisenler}')-'is_tanimi'));
 END IF;
 RETURN kapilar_v5.ek_denetim_160(d,e);
END $$;

CREATE FUNCTION kapi.is_alan_hatasi(e jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE code text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; i jsonb; s jsonb; h jsonb; l jsonb;
 k text; v jsonb; path text=''; msg text; prefix text=''; n int; satir int=0; ids text[]; graf jsonb='{}';
BEGIN
 IF code NOT LIKE 'IS.%' THEN RETURN '{}'; END IF;
 i=motor.kayit('YAYIN','isler',(kapi.hedefler(e,'IS'))[1]);
 IF code NOT IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') THEN
  IF NOT irp.dogru(i) THEN msg='İş artık bulunamıyor. İş listesini yenileyin.';
  ELSIF i->>'durum'='IPTAL' THEN msg='Bu iş iptal edilmiş. İptal edilen işte bu işlem yapılamaz.';
  ELSIF i->>'durum'='BITTI' AND code NOT IN ('IS.IPTAL_ETTIM','IS.BAGLANTI_DUZELTTIM','IS.SURE_EKLEDIM') THEN msg='Bu iş tamamlanmış. Tamamlanan işte bu işlem yapılamaz.';
  END IF;
 END IF;
 IF msg IS NULL AND code='IS.DEGISTIRDIM' THEN
  s=g->'degisenler';prefix='degisenler.';
  IF s ? 'is_tanimi' AND jsonb_typeof(s->'is_tanimi') NOT IN ('string','null') THEN path=prefix||'is_tanimi';msg='İş açıklamasını metin olarak girin.';
  ELSIF EXISTS(SELECT FROM jsonb_object_keys(s) a WHERE a<>ALL(ARRAY['islem','is_tanimi','tahmini_sure_dk','teslim_tarihi','tezgah','tezgah_rolu','on_isler','onay_gerekli','onay_beklet','yetkinlik'])) THEN msg='İşin birimi, türü ve kişi sayısı bu düzenleme ekranından değiştirilemez. Proje ve etap için Proje ve Parça Bağını Düzelt işlemini kullanın.';
  ELSIF i->>'durum'='ONAY_BEKLIYOR' AND s ?| ARRAY['onay_gerekli','onay_beklet'] THEN path=prefix||'onay_gerekli';msg='İş teslim edilmiş ve onay bekliyor. Teslim sonucu verilmeden onay koşulları değiştirilemez.';
  ELSIF EXISTS(SELECT FROM motor.satirlar('YAYIN','isler') WHERE hal->'ana_is'=i->'kimlik' AND hal->>'durum' IN ('BITTI','IPTAL','ONAY_BEKLIYOR')) THEN msg='Bu çok kişili işin teslim edilmiş, tamamlanmış veya iptal edilmiş bir alt işi var. Ortak iş tanımı artık değiştirilemez.';
  ELSIF s ? 'on_isler' THEN
   SELECT array_agg(anahtar) INTO ids FROM motor.satirlar('YAYIN','isler') WHERE anahtar=i->>'kimlik' OR hal->'ana_is'=i->'kimlik';
   IF NOT coalesce(i->'on_isler','[]') @> (s->'on_isler') AND
    (EXISTS(SELECT FROM motor.satirlar('YAYIN','kisi_durumu') WHERE hal->>'acik_is'=ANY(ids)) OR
     EXISTS(SELECT FROM jsonb_array_elements(motor.oku('YAYIN','araliklar','[]')) a WHERE a->>'is'=ANY(ids) AND a->>'kova' IN ('CALISMA','YENIDEN_ISLEME'))) THEN
    path=prefix||'on_isler';msg='Çalışmaya başlanmış işe yeni önkoşul eklenemez. Mevcut önkoşulları kaldırabilirsiniz.';
   ELSE
    FOR k,v IN SELECT * FROM motor.satirlar('YAYIN','isler') LOOP graf=graf||jsonb_build_object(k,CASE WHEN k=ANY(ids) THEN s->'on_isler' ELSE coalesce(v->'on_isler','[]') END); END LOOP;
    IF EXISTS(SELECT FROM jsonb_array_elements_text(s->'on_isler') p WHERE NOT graf ? p) THEN path=prefix||'on_isler';msg='Seçilen ön işlerden biri bulunamıyor. Önce bitmesi gereken işleri yeniden seçin.';
    ELSIF NOT kapilar_v3.dongusuz(graf) THEN path=prefix||'on_isler';msg='Bu önkoşul işleri birbirini bekler hale getiriyor. Ön iş seçimini değiştirin.'; END IF;
   END IF;
  END IF;
 END IF;
 IF msg IS NULL AND code IN ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM','IS.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') THEN
  FOR s IN SELECT value FROM jsonb_array_elements(CASE WHEN code='IS.TANIMLADIM' THEN g->'isler' WHEN code IN ('IS.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') THEN jsonb_build_array(i||(g->'degisenler')) ELSE jsonb_build_array(g) END) LOOP
   prefix=CASE WHEN code='IS.TANIMLADIM' THEN 'isler.'||satir||'.' WHEN code IN ('IS.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') THEN 'degisenler.' ELSE '' END;satir=satir+1;
   IF s->>'nereye'='PROJE' AND coalesce(s->>'proje','')='' THEN path=prefix||'proje';msg='İşin bağlı olduğu projeyi seçin.';
   ELSIF irp.dogru(s->'proje') AND NOT coalesce((motor.kayit('YAYIN','projeler',s->>'proje')->>'aktif')::boolean,false) THEN path=prefix||'proje';msg='İşin bağlı olduğu proje kapalı veya bulunamıyor. Açık bir proje seçin.';
   ELSIF irp.dogru(s->'etap') AND motor.kayit('YAYIN','etaplar',s->>'etap')->>'proje' IS DISTINCT FROM s->>'proje' THEN path=prefix||'etap';msg='Seçilen etap bu projeye ait değil. Projenin etabını veya Etap Dışı seçeneğini seçin.';
   ELSIF motor.kayit('YAYIN','birimler',s->>'birim')->>'tur' IS DISTINCT FROM 'ATOLYE' THEN path=prefix||'birim';msg='Saat ölçülen iş için atölye veya saha birimini seçin.';
   ELSIF s->>'nereye'='PROJE_DISI' AND NOT k6.kod_aktif('YAYIN','PD',s->>'kategori') THEN path=prefix||'kategori';msg='Kullanılabilir bir proje dışı faaliyet seçin.';
   ELSIF irp.dogru(s->'tezgah') AND NOT coalesce((motor.kayit('YAYIN','tezgahlar',s->>'tezgah')->>'aktif')::boolean,false) THEN path=prefix||'tezgah';msg='Seçilen tezgâh kullanılamıyor. Aktif bir tezgâh seçin.';
   END IF;
   EXIT WHEN msg IS NOT NULL;
  END LOOP;
 END IF;
 IF msg IS NULL AND code IN ('IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM') THEN
  FOREACH k IN ARRAY kapilar_v3.liste_hedefleri(e) LOOP
   IF NOT kapilar_v5.aktif_kisi('YAYIN',k) THEN path=CASE WHEN code='IS.DEVRETTIM' THEN 'kime' ELSE 'kisi' END;msg='Seçilen çalışan aktif değil. Başka bir çalışan seçin.';EXIT; END IF;
   l=motor.kayit('YAYIN','listeler',k,'[]');h=motor.kayit('YAYIN','isler',l->>0);
   n=coalesce((g->>'sira')::int,(g->>'yeni_sira')::int,(g->>'kime_sira')::int,1);
   IF h->>'durum'='ONAY_BEKLIYOR' AND irp.dogru(h->'onay_beklet') AND
    ((code='IS.DEVRETTIM' AND k=g->>'kimden' AND i->'kimlik'=l->0) OR
     (NOT(code='IS.DEVRETTIM' AND k=g->>'kimden') AND ((i->'kimlik'=l->0 AND n<>1) OR (i->'kimlik' IS DISTINCT FROM l->0 AND n=1)))) THEN
    path=CASE code WHEN 'IS.SIRALADIM' THEN 'yeni_sira' WHEN 'IS.DEVRETTIM' THEN 'kime_sira' ELSE 'sira' END;msg='İlk iş onay bekliyor. Sonuç gelmeden bu işin önüne geçilemez veya ilk iş başka sıraya taşınamaz.';EXIT;
   END IF;
  END LOOP;
  IF msg IS NULL THEN
   IF code='IS.ATADIM' AND (i->>'durum' NOT IN ('HAVUZDA','REDDEDILDI') OR EXISTS(SELECT FROM motor.satirlar('YAYIN','listeler') WHERE hal ? (i->>'kimlik'))) THEN msg='Bu iş zaten bir çalışanın listesinde. Sırasını değiştirin veya başka çalışana devredin.';
   ELSIF code='IS.ATADIM' AND coalesce((i->>'kisi_sayisi')::int,1)>1 AND jsonb_array_length(coalesce(g->'kisiler','[]'))<>(i->>'kisi_sayisi')::int THEN path='kisiler';msg='Bu iş için '||(i->>'kisi_sayisi')||' çalışan seçin.';
   ELSIF code='IS.SIRALADIM' AND NOT motor.kayit('YAYIN','listeler',g->>'kisi','[]') ? (i->>'kimlik') THEN msg='İş artık bu çalışanın listesinde değil. İş listesini yenileyin.';
   ELSIF code='IS.DEVRETTIM' AND g->>'kimden'=g->>'kime' THEN path='kime';msg='İşi devralacak farklı bir çalışan seçin.';
   ELSIF code='IS.DEVRETTIM' AND i->>'durum'='ONAY_BEKLIYOR' THEN msg='İş onay bekliyor. Onay veya düzeltme sonucu gelmeden devredilemez.';
   ELSIF code='IS.DEVRETTIM' AND NOT motor.kayit('YAYIN','listeler',g->>'kimden','[]') ? (i->>'kimlik') THEN msg='İş artık devreden çalışanın listesinde değil. İş listesini yenileyin.';
   END IF;
  END IF;
 END IF;
 IF msg IS NULL AND code IN ('IS.ONAYLADIM','IS.REDDETTIM') AND i->>'durum'<>'ONAY_BEKLIYOR' THEN msg='Bu iş teslim onayı beklemiyor. Onaylar listesini yenileyin.'; END IF;
 IF msg IS NULL AND code='IS.DEVAM_ONAYLADIM' THEN msg='Çalışan bu iş için duruştan devam izni beklemiyor. Ekip Takibi ekranını yenileyin.'; END IF;
 IF msg IS NULL THEN msg='İşlem uygulanamadı. İşin ayrıntılarını yenileyip seçtiğiniz bilgileri kontrol edin.';path=''; END IF;
 RETURN jsonb_build_object('mesaj',msg,'alan_hatalari',CASE WHEN path='' THEN '[]'::jsonb ELSE jsonb_build_array(jsonb_build_object('path',path,'message',msg)) END);
END $$;

CREATE OR REPLACE FUNCTION public.olay_ekle(olay jsonb,hassas_ek jsonb DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,irp AS $$
#variable_conflict use_column
DECLARE r jsonb; hesap text;
BEGIN
 r=kapi.ekle(olay,hassas_ek);
 -- DURUM ancak yetki/biçim denetiminden sonra gelir. Yetki reddinde veri açıklama.
 IF r->>'kod'='DURUM' THEN r=r||kapi.proje_alan_hatasi(olay)||kapi.is_alan_hatasi(olay); END IF;
 hesap=coalesce(r->>'hesap',CASE WHEN (SELECT bekleyen_sinir FROM motor.durum WHERE tek) IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END);
 RETURN r||jsonb_build_object('alindi',r->>'sonuc'='BASARILI','hesap',hesap);
END $$;
RESET ROLE;
