SET ROLE irp_sahibi;
-- Önceki dönemin yeniden hesaplanması yayın işidir. Sıradan okuma yalnız
-- yayınla aynı işlemde hazırlanan sonucu okur; firma kilidi almaz.
CREATE TABLE okuma.duzeltme_ozeti(tek boolean PRIMARY KEY DEFAULT true CHECK(tek),deger jsonb NOT NULL);
ALTER FUNCTION okuma.onceki_donem_duzeltmeleri() RENAME TO duzeltmeleri_hesapla;
ALTER FUNCTION okuma.duzeltmeleri_hesapla() VOLATILE;
CREATE FUNCTION okuma.onceki_donem_duzeltmeleri() RETURNS jsonb LANGUAGE sql STABLE AS
$$ SELECT coalesce((SELECT deger FROM okuma.duzeltme_ozeti WHERE tek),'[]') $$;
CREATE FUNCTION okuma.duzeltme_yayini() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE eski text=current_setting('irp.duzeltme_hesaplaniyor',true); r jsonb; BEGIN
 IF eski='evet' THEN RETURN NULL; END IF;
 PERFORM set_config('irp.duzeltme_hesaplaniyor','evet',true);
 IF EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar LIKE '%:DEFTER_V7')
 AND EXISTS(SELECT FROM public.ay_kapanislari WHERE hal ? 'kapanis_ani') THEN
  r=okuma.duzeltmeleri_hesapla();
 ELSE r='[]'; END IF;
 INSERT INTO okuma.duzeltme_ozeti VALUES(true,r) ON CONFLICT(tek) DO UPDATE SET deger=excluded.deger;
 PERFORM set_config('irp.duzeltme_hesaplaniyor',coalesce(eski,''),true);
 RETURN NULL; END $$;
CREATE TRIGGER okuma_duzeltme_yayini AFTER UPDATE OF son_yayin_ani ON motor.durum
FOR EACH ROW EXECUTE FUNCTION okuma.duzeltme_yayini();

-- Dört sonuç tablosu için kapanışın ek fotoğrafı. Kaynak kapanışlar değişmez.
CREATE TABLE okuma.kapanis_sonuclari(ay date NOT NULL,proje text NOT NULL,maliyet jsonb NOT NULL,
 iscilik_birim jsonb NOT NULL,iscilik_yetkinlik jsonb NOT NULL,PRIMARY KEY(ay,proje));
CREATE FUNCTION okuma.kapanis_fotografi() RETURNS trigger LANGUAGE plpgsql AS $$
#variable_conflict use_column
<<fotograf_baglami>>
DECLARE ay date=left(NEW.anahtar,10)::date; son date=(ay+interval '1 month - 1 day')::date;
 p text; m jsonb; b jsonb; y jsonb; BEGIN
 IF coalesce(current_setting('irp.gecmis_okuma',true),'')='evet'
 OR coalesce(current_setting('irp.duzeltme_hesaplaniyor',true),'')='evet' THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT FROM public.ay_kapanislari WHERE anahtar=ay::text||':GOREV_PAYLARI') THEN RETURN NULL; END IF;
 FOR p IN SELECT k FROM okuma.satirlar('projeler') LOOP
  IF EXISTS(SELECT FROM okuma.kapanis_sonuclari s WHERE s.ay=fotograf_baglami.ay AND s.proje=p) THEN CONTINUE; END IF;
  m=okuma.proje_maliyeti(p,ay::text);
  b=okuma.proje_isciligi(p,ay::text,son::text,'BIRIM');
  y=okuma.proje_isciligi(p,ay::text,son::text,'YETKINLIK');
  INSERT INTO okuma.kapanis_sonuclari VALUES(ay,p,m,b,y);
 END LOOP; RETURN NULL; END $$;
-- Kapanışın bütün parçaları yazıldıktan sonra, commit öncesinde bir kez.
CREATE CONSTRAINT TRIGGER okuma_kapanis_fotografi AFTER INSERT ON public.ay_kapanislari
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION okuma.kapanis_fotografi();
RESET ROLE;
