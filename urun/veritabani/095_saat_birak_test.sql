-- Yalnız --test ile kurulur. Canlı verinin geçmişi test saatiyle yüklendikten sonra ürünün saati
-- gerçek saate bırakılır (T19 › 3); aradaki zamanı saat işi (pg_cron, motor.saat_isi) ilerletir.
SET ROLE irp_sahibi;
CREATE FUNCTION test.saat_birak() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 IF test.ortam()<>'TEST' THEN RAISE EXCEPTION 'Test ortami gerekli'; END IF;
 IF (SELECT simdi FROM saat.ayar WHERE tek) > statement_timestamp() THEN
  RAISE EXCEPTION 'Test saati gercek saatin ilerisinde; gelecek tarihli olay birakilmaz';
 END IF;
 UPDATE saat.ayar SET simdi=NULL,gercek=NULL,demo=false WHERE tek;
END $$;
REVOKE ALL ON FUNCTION test.saat_birak() FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
