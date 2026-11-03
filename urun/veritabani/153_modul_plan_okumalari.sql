-- Karar 95/156: etap özeti ortak gerçekleşmeden; izinli ayrıntı ayrı süzülür.
-- Paket 1.1: isteğe bağlı PLAN.surumler ve GANTT.adlar eski cevap biçimini korur.
SET ROLE irp_sahibi;
CREATE OR REPLACE FUNCTION okuma.gantt(proje text,bas text,bit_ text DEFAULT NULL,cagiran text DEFAULT NULL) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE ab timestamptz[]=okuma.pencere(bas,bit_); r jsonb='[]'; satirlar jsonb='[]'; z record; x jsonb; pq timestamptz[]; u timestamptz; v timestamptz; plan jsonb; alt jsonb; gorunen jsonb; etkin jsonb; s jsonb; p timestamptz; q timestamptz; durum text; aralikta boolean; BEGIN
 IF cagiran IS NOT NULL AND NOT k9.proje_gorebilir('OKUMA',cagiran,proje) THEN RAISE EXCEPTION 'IRP|YETKI|Proje gorunurlugu'; END IF;
 FOR z IN SELECT * FROM (SELECT 'IS' AS tur,k,x FROM okuma.satirlar('isler') UNION ALL SELECT 'GOREV',k,x FROM okuma.satirlar('gorevler')) q0 ORDER BY tur DESC,k COLLATE "C" LOOP
  x=z.x; IF x->>'proje' IS DISTINCT FROM proje THEN CONTINUE; END IF;
  pq=okuma.plan_araligi(z.tur,x);
  IF z.tur='IS' THEN SELECT min(saat.an(e->>'oldugu_an')) INTO u FROM jsonb_array_elements(okuma.tablo('olaylar')) e WHERE e->>'eylem_kodu'='IS.BASLADIM' AND NOT okuma.tablo('supheliler') ? (e->>'olay_kimligi') AND z.k=ANY(kapi.hedefler(e,'IS'));
  ELSE u=saat.an(coalesce(x->>'ilk_kabul_ani',x->>'kabul_ani')); END IF;
  v=CASE WHEN x->>'durum'='BITTI' THEN saat.an(x->>'bitis_ani') END;
  s=jsonb_build_object('tur',z.tur,'kimlik',z.k,'etap',x->'etap','tezgah',x->'tezgah','kisi',x->'kisi','planlanan_baslangic',saat.kodla(pq[1]),'planlanan_bitis',saat.kodla(pq[2]),'gerceklesen_baslangic',saat.kodla(u),'gerceklesen_bitis',saat.kodla(v),'durum',x->'durum','ilerleme',CASE WHEN x->>'durum'='BITTI' THEN 100 ELSE 0 END,'sapma',okuma.sapma(x->>'durum',pq[1],pq[2],u,v))||okuma.gecikme_olculeri(z.tur,x);
  s=s||jsonb_build_object('_gorunur',cagiran IS NULL OR okuma.gorebilir(cagiran,z.tur,z.k)); satirlar=satirlar||jsonb_build_array(s);
 END LOOP;
 plan=coalesce(okuma.satir('plan_surumleri',proje)->-1->'etaplar','{}');
 FOR z IN SELECT k,x FROM okuma.satirlar('etaplar') WHERE x->>'proje'=proje ORDER BY k COLLATE "C" LOOP
  SELECT coalesce(jsonb_agg(x),'[]') INTO alt FROM jsonb_array_elements(satirlar) x WHERE x->>'etap'=z.k;
  SELECT coalesce(bool_or(okuma.gantt_aralikta(x,ab[1],ab[2])),false) INTO aralikta FROM jsonb_array_elements(alt) x;
  SELECT coalesce(jsonb_agg(x-'_gorunur'),'[]') INTO gorunen FROM jsonb_array_elements(alt) x WHERE (x->>'_gorunur')::boolean AND okuma.gantt_aralikta(x,ab[1],ab[2]);
  p=saat.an(plan->z.k->>'baslangic'); q=CASE WHEN plan ? z.k THEN saat.gun_ani(saat.gun(plan->z.k->>'bitis')+1) END;
  IF NOT aralikta AND NOT coalesce(p IS NOT NULL AND greatest(ab[1],p)<least(ab[2],q),false) THEN CONTINUE; END IF;
  SELECT coalesce(jsonb_agg(x),'[]') INTO etkin FROM jsonb_array_elements(alt) x WHERE x->>'durum'<>'IPTAL';
  SELECT min(saat.an(x->>'gerceklesen_baslangic')),CASE WHEN bool_and(x->>'gerceklesen_bitis' IS NOT NULL) THEN max(saat.an(x->>'gerceklesen_bitis')) END,
  CASE WHEN bool_and(x->>'durum'='BITTI') THEN 'BITTI' ELSE 'ACIK' END INTO u,v,durum FROM jsonb_array_elements(etkin) x;
  s=jsonb_build_object('tur','ETAP','kimlik',z.k,'etap',NULL,'tezgah',NULL,'kisi',NULL,'planlanan_baslangic',saat.kodla(p),'planlanan_bitis',saat.kodla(q),'gerceklesen_baslangic',saat.kodla(u),'gerceklesen_bitis',saat.kodla(v),'durum',durum,'ilerleme',okuma.etap_gostergesi(z.k)->'yuzde','sapma',okuma.sapma(durum,p,q,u,v),'gecikme_takvim_dk',NULL,'gecikme_mesai_dk',NULL);
  r=r||jsonb_build_array(s)||gorunen;
 END LOOP;
 SELECT r||coalesce(jsonb_agg(x-'_gorunur'),'[]') INTO r FROM jsonb_array_elements(satirlar) x WHERE (x->>'_gorunur')::boolean AND NOT coalesce(okuma.tablo('etaplar') ? (x->>'etap'),false) AND okuma.gantt_aralikta(x,ab[1],ab[2]);
 RETURN r; END $$;
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
 IF veri='PLAN' AND coalesce((g->>'surumler')::boolean,false) THEN
  deger=deger||jsonb_build_object('surumler',coalesce(okuma.satir('plan_surumleri',hedef),'[]'));
 END IF;
 IF veri='GANTT' AND coalesce((g->>'adlar')::boolean,false) THEN
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('ad',okuma.satir(CASE x->>'tur' WHEN 'ETAP' THEN 'etaplar' WHEN 'IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->'ad')),'[]') INTO deger
  FROM jsonb_array_elements(deger) x;
 END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;

RESET ROLE;
