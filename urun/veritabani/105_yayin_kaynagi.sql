SET ROLE irp_sahibi;
-- Hassas ekler kaynak tablodadır. Yayın beklerken yeni kabul edilmiş ücret,
-- eski YAYIN satırlarıyla karışmaz; sınır yayınla aynı işlemde değişir.
ALTER TABLE motor.durum ADD COLUMN okuma_kabul_no bigint NOT NULL DEFAULT 0;
UPDATE motor.durum SET okuma_kabul_no=CASE WHEN bekleyen_sinir IS NULL
 THEN (SELECT coalesce(max(kabul_no),0) FROM public.olaylar)
 ELSE (SELECT coalesce(max(e.kabul_no),0) FROM public.olaylar e
       JOIN jsonb_array_elements(okuma.tablo('olaylar')) x ON x->>'olay_kimligi'=e.olay_kimligi)
 END WHERE tek;
CREATE FUNCTION okuma.yayin_kabul_siniri() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 SELECT coalesce(max(kabul_no),0) INTO NEW.okuma_kabul_no FROM public.olaylar;
 RETURN NEW;
END $$;
CREATE TRIGGER okuma_yayin_kabul_siniri BEFORE UPDATE OF son_yayin_ani ON motor.durum
FOR EACH ROW EXECUTE FUNCTION okuma.yayin_kabul_siniri();
RESET ROLE;
