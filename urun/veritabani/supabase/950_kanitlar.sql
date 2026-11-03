-- Yalnız Supabase'te (T17 › 9). Özel kanitlar kovası; yol <olay_kimligi>/<n>-<ad>, dosya kimliği F-<olay>/<n>.
-- Yazma: oturumdaki kişinin kendi olay kimliğiyle başlayan yol (olay kimliği kişi koduyla başlar; dosya
-- olaydan sonra yüklenir ama olayın buluta varmasını beklemez). Okuma: DOSYA görme kuralı (T16 › 5) ya da
-- kişinin kendi yüklediği. Yardımcılar plpgsql: okuma katmanı (100–149) gövdeye çağrı anında bağlanır.
INSERT INTO storage.buckets(id,name,public) VALUES('kanitlar','kanitlar',false) ON CONFLICT(id) DO NOTHING;
SET ROLE irp_sahibi;
CREATE OR REPLACE FUNCTION public.kanit_kisisi() RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
BEGIN RETURN (SELECT kisi FROM public.kisi_hesaplari WHERE auth_kimligi=auth.uid()); END $$;
CREATE OR REPLACE FUNCTION public.kanit_yazabilir(yol text) RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
DECLARE k text=public.kanit_kisisi(); BEGIN
 RETURN k IS NOT NULL AND position('/' IN yol)>0 AND starts_with(split_part(yol,'/',1), k||'-');
END $$;
CREATE OR REPLACE FUNCTION public.kanit_gorebilir(yol text) RETURNS boolean LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
DECLARE k text=public.kanit_kisisi(); dosya text; BEGIN
 IF k IS NULL OR position('/' IN yol)=0 THEN RETURN false; END IF;
 IF starts_with(split_part(yol,'/',1), k||'-') THEN RETURN true; END IF;
 dosya='F-'||split_part(yol,'/',1)||'/'||split_part(split_part(yol,'/',2),'-',1);
 RETURN okuma.gorebilir(k,'DOSYA',dosya);
END $$;
REVOKE ALL ON FUNCTION public.kanit_kisisi(),public.kanit_yazabilir(text),public.kanit_gorebilir(text) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.kanit_yazabilir(text),public.kanit_gorebilir(text) TO authenticated;
RESET ROLE;
DROP POLICY IF EXISTS irp_kanit_yaz ON storage.objects;
DROP POLICY IF EXISTS irp_kanit_oku ON storage.objects;
CREATE POLICY irp_kanit_yaz ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id='kanitlar' AND public.kanit_yazabilir(name));
CREATE POLICY irp_kanit_oku ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id='kanitlar' AND public.kanit_gorebilir(name));
