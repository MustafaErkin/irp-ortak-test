-- Yalnız Supabase'te, göçlerden önce (T19-1). auth şemasının sahibi supabase_admin; postgres'in
-- orada yetki verme hakkı yok, 001'deki GRANT USAGE ON SCHEMA auth yalnız uyarı verir ve
-- irp_sahibi auth.uid()'i göremez. postgres, anon rolünü verebilir; anon'un auth'ta yalnız USAGE'ı
-- ve auth.uid()/jwt()/role() hakkı var. irp_sahibi her tablonun sahibi olduğundan satır kuralları
-- ve anon'un başka hakları ona bir şey katmaz.
DO $$ BEGIN
  IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='irp_sahibi') THEN CREATE ROLE irp_sahibi NOLOGIN; END IF;
END $$;
GRANT anon TO irp_sahibi;
