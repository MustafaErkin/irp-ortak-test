-- Olay akışına okunur etiketler (30 Ekim): hedeflerin adı (iş: işlem ve parça; görev, parça/belge, proje,
-- etap, kişi, tezgâh, birim: ad), girdideki kişinin ve hedefin adı. 146'nın yerine geçer; davranış aynı.
SET ROLE irp_sahibi;
CREATE OR REPLACE FUNCTION okuma.akis_etiketi(tur text,k text,t jsonb) RETURNS text LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE tur
  WHEN 'IS' THEN nullif(concat_ws(' · ',t->'isler'->k->>'islem',t->'isler'->k->>'parca_kodu'),'')
  WHEN 'GOREV' THEN t->'gorevler'->k->>'ad'
  WHEN 'NESNE' THEN t->'nesneler'->k->>'ad'
  WHEN 'PROJE' THEN t->'projeler'->k->>'ad'
  WHEN 'ETAP' THEN t->'etaplar'->k->>'ad'
  WHEN 'KISI' THEN t->'kisiler'->k->>'ad'
  WHEN 'LISTE' THEN (t->'kisiler'->k->>'ad')||' listesi'
  WHEN 'TEZGAH' THEN t->'tezgahlar'->k->>'ad'
  WHEN 'BIRIM' THEN t->'birimler'->k->>'ad'
 END $$;
CREATE OR REPLACE FUNCTION public.olay_akisi(sonra bigint DEFAULT 0, adet int DEFAULT 200) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE t jsonb; r jsonb; BEGIN
 IF coalesce((SELECT hal FROM irp.sozluk WHERE ad='olay_akisi_acik'),'false'::jsonb)<>'true'::jsonb THEN
  RAISE EXCEPTION 'IRP|YETKI|Olay akisi kapali';
 END IF;
 PERFORM kapi.oturum_kisi();
 adet=least(greatest(coalesce(adet,200),1),500);
 SELECT jsonb_object_agg(a,okuma.tablo(a)) INTO t
 FROM unnest(ARRAY['kisiler','isler','gorevler','nesneler','projeler','etaplar','tezgahlar','birimler']) a;
 SELECT coalesce(jsonb_agg(x ORDER BY (x->>'sira')::bigint DESC),'[]') INTO r FROM (
  SELECT jsonb_build_object(
   'sira',o.kabul_no,'an',saat.kodla(o.oldugu_an),'ulasma',saat.kodla(o.bulut_ulasma_ani),
   'kim',o.kim,'ad',t->'kisiler'->o.kim->>'ad','adina',o.icerik->>'adina','eylem',o.eylem_kodu,
   'cihaz',o.icerik->>'cihaz',
   'neyin_ustunde',coalesce((SELECT jsonb_agg(n||jsonb_build_object('etiket',okuma.akis_etiketi(n->>'tur',n->>'kimlik',t)))
                             FROM jsonb_array_elements(o.icerik->'neyin_ustunde') n),'[]'),
   'girdiler',CASE WHEN o.eylem_kodu LIKE 'MAAS.%' THEN '{}'::jsonb ELSE coalesce(o.icerik->'girdiler','{}') END,
   'kisi_ad',t->'kisiler'->(o.icerik->'girdiler'->>'kisi')->>'ad',
   'hedef_etiket',coalesce(t->'nesneler'->(o.icerik->'girdiler'->>'hedef')->>'ad',
                           t->'isler'->(o.icerik->'girdiler'->>'hedef')->>'islem'),
   'olay',o.olay_kimligi,
   'hata',EXISTS(SELECT FROM public.isleme_hatalari h WHERE h.hal->>'olay'=o.olay_kimligi
                 AND NOT coalesce((h.hal->>'cozuldu')::boolean,false))) x
  FROM public.olaylar o WHERE o.kabul_no>coalesce(sonra,0) ORDER BY o.kabul_no DESC LIMIT adet) z;
 RETURN jsonb_build_object('olaylar',r,'son',(SELECT coalesce(max(kabul_no),0) FROM public.olaylar));
END $$;
REVOKE ALL ON FUNCTION okuma.akis_etiketi(text,text,jsonb) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.olay_akisi(bigint,int) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.olay_akisi(bigint,int) TO authenticated;
RESET ROLE;
