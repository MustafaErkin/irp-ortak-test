-- Olay akışı (Mustafa, 30 Ekim): gösteride "her basış bir satır" ve hata ayıklama için web'de canlı liste.
-- Yalnız açıkça açılmış ortamda çalışır (irp.sozluk 'olay_akisi_acik' = true; Supabase test kurulumu açar),
-- gerçek kullanımda kapalıdır. Oturum gerekir. Hassas ekler (maaş tutarları) hiç dönmez; MAAS.* olaylarının
-- girdileri de boş döner. Reddedilen denemeler kaynakta tutulmadığı için listede yoktur.
SET ROLE irp_sahibi;
CREATE FUNCTION public.olay_akisi(sonra bigint DEFAULT 0, adet int DEFAULT 200) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kisiler jsonb; r jsonb; BEGIN
 IF coalesce((SELECT hal FROM irp.sozluk WHERE ad='olay_akisi_acik'),'false'::jsonb)<>'true'::jsonb THEN
  RAISE EXCEPTION 'IRP|YETKI|Olay akisi kapali';
 END IF;
 PERFORM kapi.oturum_kisi();
 adet=least(greatest(coalesce(adet,200),1),500);
 kisiler=okuma.tablo('kisiler');
 SELECT coalesce(jsonb_agg(x ORDER BY (x->>'sira')::bigint DESC),'[]') INTO r FROM (
  SELECT jsonb_build_object(
   'sira',o.kabul_no,'an',saat.kodla(o.oldugu_an),'ulasma',saat.kodla(o.bulut_ulasma_ani),
   'kim',o.kim,'ad',kisiler->o.kim->>'ad','adina',o.icerik->>'adina','eylem',o.eylem_kodu,
   'cihaz',o.icerik->>'cihaz','neyin_ustunde',coalesce(o.icerik->'neyin_ustunde','[]'),
   'girdiler',CASE WHEN o.eylem_kodu LIKE 'MAAS.%' THEN '{}'::jsonb ELSE coalesce(o.icerik->'girdiler','{}') END,
   'olay',o.olay_kimligi,
   'hata',EXISTS(SELECT FROM public.isleme_hatalari h WHERE h.hal->>'olay'=o.olay_kimligi
                 AND NOT coalesce((h.hal->>'cozuldu')::boolean,false))) x
  FROM public.olaylar o WHERE o.kabul_no>coalesce(sonra,0) ORDER BY o.kabul_no DESC LIMIT adet) t;
 RETURN jsonb_build_object('olaylar',r,'son',(SELECT coalesce(max(kabul_no),0) FROM public.olaylar));
END $$;
REVOKE ALL ON FUNCTION public.olay_akisi(bigint,int) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.olay_akisi(bigint,int) TO authenticated;
RESET ROLE;
