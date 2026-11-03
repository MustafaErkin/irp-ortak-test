-- Yalnız Supabase test projesinde (kur.py --hedef supabase-test --test). Supabase'te veritabanının adı
-- her zaman postgres; TEST denetimi bu yüzden kurulumun --onay ile yazdığı proje kimliğine de bakar.
SET ROLE irp_sahibi;
CREATE OR REPLACE FUNCTION test.ortam() RETURNS text LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN test_ortami AND (current_database() ILIKE '%test%'
   OR EXISTS(SELECT 1 FROM irp.sozluk WHERE ad='supabase_test_projesi')) THEN 'TEST' ELSE 'CANLI' END
 FROM saat.ayar WHERE tek $$;
REVOKE ALL ON FUNCTION test.ortam() FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
