SET ROLE irp_sahibi;
CREATE TABLE motor.yayin_tablosu(ad text PRIMARY KEY,tur text NOT NULL);
-- T14 §2.2: model adlı gerçek son hal tabloları. İç çalışma alanı ayrı kalır.
DO $$ DECLARE a text; x jsonb; BEGIN
 FOR a,x IN SELECT key,value FROM jsonb_each((SELECT hal FROM irp.sozluk WHERE ad='bos_hal'))
 WHERE key NOT IN ('olaylar','ayarlar','takvimler','tatiller','elle_olaylar','retler','motor_hatalari','yakinsama_turlari','varsayilan_takvim','yonlendirme','olay_nesneleri') AND jsonb_typeof(value) IN ('object','array') LOOP
  INSERT INTO motor.yayin_tablosu VALUES(a,jsonb_typeof(x));
  EXECUTE format('CREATE TABLE public.%I (anahtar text COLLATE "C" PRIMARY KEY,sira bigint NOT NULL,hal jsonb NOT NULL,surum text NOT NULL,kisi text GENERATED ALWAYS AS (hal->>''kisi'') STORED,proje text GENERATED ALWAYS AS (hal->>''proje'') STORED,birim text GENERATED ALWAYS AS (hal->>''birim'') STORED,durum text GENERATED ALWAYS AS (hal->>''durum'') STORED)',a);
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',a);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC,anon,authenticated,service_role',a);
 END LOOP;
END $$;
CREATE FUNCTION motor.son_hal_yaz() RETURNS void LANGUAGE plpgsql AS $$
DECLARE r record; x record; j jsonb; s bigint; BEGIN
 FOR r IN SELECT * FROM motor.yayin_tablosu LOOP
  j=motor.oku('YAYIN',r.ad,CASE WHEN r.tur='array' THEN '[]'::jsonb ELSE '{}'::jsonb END);
  IF r.tur='object' THEN
   FOR x IN SELECT z.key,z.value,coalesce(a.sira,0) sira FROM jsonb_each(j) z LEFT JOIN motor.anahtar_sirasi a ON a.kip='YAYIN' AND a.ad=r.ad AND a.anahtar=z.key LOOP
    EXECUTE format('INSERT INTO public.%I(anahtar,sira,hal,surum) VALUES($1,$2,$3,$4) ON CONFLICT(anahtar) DO UPDATE SET sira=excluded.sira,hal=excluded.hal,surum=excluded.surum WHERE surum.is_alanlari(%I.hal) IS DISTINCT FROM surum.is_alanlari(excluded.hal)',r.ad,r.ad) USING x.key,x.sira,x.value,surum.ozet(surum.is_alanlari(x.value));
   END LOOP;
   EXECUTE format('DELETE FROM public.%I WHERE NOT $1 ? anahtar',r.ad) USING j;
  ELSE
   FOR x IN SELECT value,ordinality FROM jsonb_array_elements(j) WITH ORDINALITY LOOP
    EXECUTE format('INSERT INTO public.%I(anahtar,sira,hal,surum) VALUES($1,$2,$3,$4) ON CONFLICT(anahtar) DO UPDATE SET hal=excluded.hal,surum=excluded.surum WHERE surum.is_alanlari(%I.hal) IS DISTINCT FROM surum.is_alanlari(excluded.hal)',r.ad,r.ad) USING lpad(x.ordinality::text,12,'0'),x.ordinality,x.value,surum.ozet(surum.is_alanlari(x.value));
   END LOOP;
   EXECUTE format('DELETE FROM public.%I WHERE sira>$1',r.ad) USING jsonb_array_length(j);
  END IF;
 END LOOP;
END $$;
RESET ROLE;
