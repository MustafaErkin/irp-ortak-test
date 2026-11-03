SET ROLE irp_sahibi;
-- model/irp/saat.py:6 an, 17 gun, 21 gun_ani; iş saatinin tek arayüzü.
CREATE OR REPLACE FUNCTION saat.an(x text) RETURNS timestamptz LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column

BEGIN
  IF x IS NULL THEN RETURN NULL; END IF;
  IF length(x)=10 THEN RETURN x::date::timestamp AT TIME ZONE 'Europe/Istanbul'; END IF;
  RETURN x::timestamptz;
EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION 'IRP|BICIM|Gecersiz an: %',x;
END $$;
CREATE OR REPLACE FUNCTION saat.gun(x text) RETURNS date LANGUAGE sql IMMUTABLE AS
$$ SELECT (saat.an(x) AT TIME ZONE 'Europe/Istanbul')::date $$;
CREATE OR REPLACE FUNCTION saat.gun_ani(x date, s text DEFAULT '00:00') RETURNS timestamptz LANGUAGE sql IMMUTABLE AS
$$ SELECT (x::timestamp + CASE WHEN s='24:00' THEN interval '1 day' ELSE s::time - time '00:00' END) AT TIME ZONE 'Europe/Istanbul' $$;
CREATE OR REPLACE FUNCTION saat.kodla(x timestamptz) RETURNS text LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN x IS NULL THEN NULL ELSE to_char(x AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD"T"HH24:MI:SS') ||
 CASE WHEN extract(microseconds FROM x)::bigint % 1000000=0 THEN '' ELSE '.'||to_char(x,'US') END || '+03:00' END $$;
CREATE OR REPLACE FUNCTION saat.simdi() RETURNS timestamptz LANGUAGE sql STABLE AS
$$ SELECT coalesce(simdi,statement_timestamp()) FROM saat.ayar WHERE tek $$;
CREATE OR REPLACE FUNCTION saat.gercek() RETURNS timestamptz LANGUAGE sql STABLE AS
$$ SELECT coalesce(gercek,statement_timestamp()) FROM saat.ayar WHERE tek $$;
CREATE OR REPLACE FUNCTION saat.demo() RETURNS boolean LANGUAGE sql STABLE AS
$$ SELECT demo FROM saat.ayar WHERE tek $$;
-- Yalnız ölçüm; hiçbir iş kararı ölçüm saatinden türetilmez.
CREATE OR REPLACE FUNCTION saat.olcum() RETURNS double precision LANGUAGE sql VOLATILE AS
$$ SELECT extract(epoch FROM clock_timestamp())::double precision $$;
-- T14 canlı hesap bütçesi, tarihsel fotoğraf ve yayın sırasında da geçerlidir.
-- Sınır oturumun yalnız bu işlemine aittir; arka plan çağrısı sınırı kaldırır.
CREATE FUNCTION motor.butce_denetle() RETURNS void LANGUAGE plpgsql AS $$
DECLARE son text=current_setting('irp.canli_bitis',true); BEGIN
 IF nullif(son,'') IS NOT NULL AND saat.olcum()>=son::double precision THEN RAISE EXCEPTION 'IRP_BUTCE'; END IF;
END $$;
CREATE OR REPLACE FUNCTION motor.konum(t timestamptz,tur integer,k text) RETURNS text LANGUAGE sql IMMUTABLE AS
$$ SELECT to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')||'|'||tur::text||'|'||k $$;
CREATE OR REPLACE FUNCTION irp.dogru(x jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS
$$ SELECT coalesce(x NOT IN ('null'::jsonb,'false'::jsonb,'0'::jsonb,'""'::jsonb,'[]'::jsonb,'{}'::jsonb),false) $$;
CREATE OR REPLACE FUNCTION irp.j(x text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT coalesce(to_jsonb(x),'null'::jsonb) $$;
CREATE OR REPLACE FUNCTION motor.oku(d text, a text, varsayilan jsonb DEFAULT '{}') RETURNS jsonb LANGUAGE sql STABLE AS
$$ SELECT coalesce((SELECT hal FROM motor.calisma WHERE kip=d AND ad=a),varsayilan) $$;
CREATE OR REPLACE FUNCTION motor.kayit(d text,a text,k text,varsayilan jsonb DEFAULT '{}') RETURNS jsonb LANGUAGE sql STABLE AS
$$ SELECT coalesce(motor.oku(d,a)->k,varsayilan) $$;
CREATE OR REPLACE FUNCTION motor.yaz(d text,a text,x jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

BEGIN
  INSERT INTO motor.calisma(kip,ad,hal) VALUES(d,a,coalesce(x,'null')) ON CONFLICT(kip,ad) DO UPDATE SET hal=excluded.hal;
END $$;
CREATE OR REPLACE FUNCTION motor.kaydet(d text,a text,k text,x jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

BEGIN
  INSERT INTO motor.anahtar_sirasi(kip,ad,anahtar) VALUES(d,a,k) ON CONFLICT DO NOTHING;
  PERFORM motor.yaz(d,a,motor.oku(d,a)||jsonb_build_object(k,x));
END $$;
CREATE OR REPLACE FUNCTION motor.sil(d text,a text,k text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

BEGIN
  PERFORM motor.yaz(d,a,motor.oku(d,a)-k);
  DELETE FROM motor.anahtar_sirasi WHERE kip=d AND ad=a AND anahtar=k;
END $$;
CREATE OR REPLACE FUNCTION motor.ekle(d text,a text,x jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

BEGIN PERFORM motor.yaz(d,a,motor.oku(d,a,'[]')||jsonb_build_array(x)); END $$;
CREATE OR REPLACE FUNCTION motor.satirlar(d text,a text) RETURNS TABLE(anahtar text,hal jsonb) LANGUAGE sql STABLE AS
$$ SELECT j.key,j.value FROM jsonb_each(motor.oku(d,a)) j LEFT JOIN motor.anahtar_sirasi s
   ON s.kip=d AND s.ad=a AND s.anahtar=j.key ORDER BY s.sira NULLS LAST,j.key COLLATE "C" $$;
CREATE OR REPLACE FUNCTION motor.zamanli_yaz(a text,k text,x jsonb,s bigint,konum text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE once motor.hal%ROWTYPE;
BEGIN
  SELECT * INTO once FROM motor.hal WHERE ad=a AND anahtar=k AND bit IS NULL;
  IF FOUND AND once.hal=x THEN RETURN; END IF;
  IF once.bas=konum THEN
    IF x IS NULL THEN DELETE FROM motor.hal WHERE ad=a AND anahtar=k AND bas=konum;
    ELSE UPDATE motor.hal SET hal=x WHERE ad=a AND anahtar=k AND bas=konum; END IF;
    RETURN;
  END IF;
  UPDATE motor.hal SET bit=konum WHERE ad=a AND anahtar=k AND bit IS NULL;
  IF x IS NOT NULL THEN INSERT INTO motor.hal(ad,anahtar,sira,hal,bas) VALUES(a,k,coalesce(once.sira,s),x,konum); END IF;
END $$;
CREATE OR REPLACE FUNCTION motor.geri_sar(k text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

BEGIN
  DELETE FROM motor.hal WHERE bas>=k COLLATE "C";
  UPDATE motor.hal SET bit=NULL WHERE bit>=k COLLATE "C";
  DELETE FROM motor.baglam WHERE ad='_calisma_siniri';
  UPDATE motor.durum SET islenen_sinir=k WHERE tek;
END $$;
-- Modelin iş alanı temizliği; metin içindeki sayı/para tipleri korunur.
CREATE OR REPLACE FUNCTION surum.is_alanlari(x jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column

DECLARE r jsonb; k text; v jsonb;
BEGIN
  IF jsonb_typeof(x)='object' THEN
    r='{}'; FOR k,v IN SELECT * FROM jsonb_each(x) LOOP
      IF k NOT IN ('surum','son_hesap_ani','son_olay','olusma_ani','kural_versiyonu') THEN r=r||jsonb_build_object(k,surum.is_alanlari(v)); END IF;
    END LOOP; RETURN r;
  ELSIF jsonb_typeof(x)='array' THEN
    r='[]'; FOR v IN SELECT value FROM jsonb_array_elements(x) LOOP r=r||jsonb_build_array(surum.is_alanlari(v)); END LOOP; RETURN r;
  END IF;
  RETURN x;
END $$;
CREATE OR REPLACE FUNCTION surum.ozet(x jsonb) RETURNS text LANGUAGE sql IMMUTABLE AS
$$ SELECT encode(sha256(convert_to(x::text,'UTF8')),'hex') $$;
CREATE OR REPLACE FUNCTION kapi.hedefler(e jsonb,tur text) RETURNS text[] LANGUAGE sql IMMUTABLE AS
$$ SELECT coalesce(array_agg((x->>'kimlik') ORDER BY n),'{}') FROM jsonb_array_elements((e->'neyin_ustunde')) WITH ORDINALITY t(x,n) WHERE (x->>'tur')=tur $$;
CREATE OR REPLACE FUNCTION kapi.red(kod text,neden text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS
$$ SELECT jsonb_build_object('sonuc','REDDEDILDI','kod',kod,'neden',neden) $$;
RESET ROLE;
