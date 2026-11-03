SET ROLE irp_sahibi;
-- T16-8: yeniden kurma çalışma alanını silebilir. Okuma kipinin kaynağı
-- kalıcı son hal tabloları ve aynı yayında alınan özel yardımcı verilerdir.
CREATE TABLE okuma.yayin_yardimci(ad text PRIMARY KEY,hal jsonb NOT NULL);
CREATE TABLE okuma.yayin_sirasi(ad text NOT NULL,anahtar text NOT NULL,sira bigint,PRIMARY KEY(ad,anahtar));
CREATE FUNCTION okuma.yayini_sakla() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 DELETE FROM okuma.yayin_yardimci WHERE true;
 INSERT INTO okuma.yayin_yardimci SELECT ad,hal FROM motor.calisma WHERE kip='YAYIN';
 DELETE FROM okuma.yayin_sirasi WHERE true;
 INSERT INTO okuma.yayin_sirasi SELECT ad,anahtar,sira FROM motor.anahtar_sirasi WHERE kip='YAYIN';
 RETURN NULL;
END $$;
CREATE TRIGGER okuma_00_yayini_sakla AFTER UPDATE OF son_yayin_ani ON motor.durum
FOR EACH ROW EXECUTE FUNCTION okuma.yayini_sakla();
INSERT INTO okuma.yayin_yardimci SELECT ad,hal FROM motor.calisma WHERE kip='YAYIN';
INSERT INTO okuma.yayin_sirasi SELECT ad,anahtar,sira FROM motor.anahtar_sirasi WHERE kip='YAYIN';
-- Yalnız OKUMA yeni kiptir. MOTOR/YAYIN dahil mevcut kiplerin davranışı aynıdır.
CREATE OR REPLACE FUNCTION motor.oku(d text,a text,varsayilan jsonb DEFAULT '{}') RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE tur text; sonuc jsonb; BEGIN
 IF d<>'OKUMA' THEN
  RETURN coalesce((SELECT hal FROM motor.calisma WHERE kip=d AND ad=a),varsayilan);
 END IF;
 -- Tam tablo hesabında yayının JSON kopyası tekrar birleştirmeyi önler.
 SELECT y.hal INTO sonuc FROM okuma.yayin_yardimci y WHERE y.ad=a;
 IF FOUND THEN RETURN sonuc; END IF;
 SELECT y.tur INTO tur FROM motor.yayin_tablosu y WHERE y.ad=a;
 IF tur='array' THEN
  EXECUTE format('SELECT coalesce(jsonb_agg(hal ORDER BY sira),''[]''::jsonb) FROM public.%I',a) INTO sonuc;
 ELSIF tur='object' THEN
  EXECUTE format('SELECT coalesce(jsonb_object_agg(anahtar,hal),''{}''::jsonb) FROM public.%I',a) INTO sonuc;
 ELSE SELECT y.hal INTO sonuc FROM okuma.yayin_yardimci y WHERE y.ad=a;
 END IF;
 RETURN coalesce(sonuc,varsayilan);
END $$;
CREATE OR REPLACE FUNCTION motor.satirlar(d text,a text) RETURNS TABLE(anahtar text,hal jsonb) LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
 IF d='OKUMA' THEN
  IF EXISTS(SELECT FROM motor.yayin_tablosu y WHERE y.ad=a) THEN
   RETURN QUERY EXECUTE format('SELECT anahtar,hal FROM public.%I ORDER BY sira,anahtar COLLATE "C"',a);
  ELSE
   RETURN QUERY SELECT j.key,j.value FROM jsonb_each(motor.oku(d,a)) j LEFT JOIN okuma.yayin_sirasi s
    ON s.ad=a AND s.anahtar=j.key ORDER BY s.sira NULLS LAST,j.key COLLATE "C";
  END IF;
 ELSE
  RETURN QUERY SELECT j.key,j.value FROM jsonb_each(motor.oku(d,a)) j LEFT JOIN motor.anahtar_sirasi s
   ON s.kip=d AND s.ad=a AND s.anahtar=j.key ORDER BY s.sira NULLS LAST,j.key COLLATE "C";
 END IF;
END $$;
RESET ROLE;
