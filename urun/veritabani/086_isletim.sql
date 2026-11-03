SET ROLE irp_sahibi;
-- T13 arka planı bir çağrıda bir parça işler; her zamanlayıcı çağrısı ayrı işlemdir.
CREATE FUNCTION motor.arka_plan_calistir() RETURNS integer LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE k text; b boolean; bas double precision=saat.olcum(); once int; sonra int; yp double precision; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 SELECT bekleyen_sinir,islenen_nokta INTO k,once FROM motor.durum WHERE tek; IF k IS NULL THEN RETURN 0; END IF;
 b=motor.calistir(k,true);
 SELECT islenen_nokta,CASE WHEN b THEN yayin_saniye END INTO sonra,yp FROM motor.durum WHERE tek;
 INSERT INTO motor.olcumler(olay,nokta,gec,saniye,yayin_saniye) VALUES(NULL,sonra-once,true,saat.olcum()-bas,yp);
 UPDATE motor.arka_plan_isleri SET durum=CASE WHEN b THEN 'BITTI' ELSE durum END,deneme=deneme+1 WHERE durum='BEKLIYOR';
 IF b THEN UPDATE motor.durum SET bakimda=false WHERE tek; END IF;
 RETURN 1;
END $$;
CREATE FUNCTION motor.saat_isi() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
DECLARE k text; BEGIN
 PERFORM pg_advisory_xact_lock(202620,1);
 IF (SELECT bekleyen_sinir IS NOT NULL FROM motor.durum WHERE tek) THEN PERFORM motor.arka_plan_calistir(); RETURN; END IF;
 SELECT min(motor.konum(etki_ani,0,'')) COLLATE "C" INTO k FROM public.olaylar WHERE oldugu_an>(SELECT son_yayin_ani FROM motor.durum WHERE tek) AND oldugu_an<=saat.simdi();
 PERFORM motor.iste(k);
END $$;
CREATE FUNCTION motor.yeniden_kur() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
BEGIN
 PERFORM pg_advisory_xact_lock(202620,1); UPDATE motor.durum SET bakimda=true WHERE tek;
 TRUNCATE motor.hal,motor.baglam,motor.calisma,motor.anahtar_sirasi,motor.noktalar RESTART IDENTITY;
 UPDATE motor.durum SET islenen_sinir='',bekleyen_sinir='' WHERE tek;
 PERFORM motor.iste('');
 UPDATE motor.durum SET bakimda=bekleyen_sinir IS NOT NULL WHERE tek;
END $$;
-- Yalnız veritabanı yönetim rolü çalıştırır; istemci/servis rolüne verilmez.
REVOKE ALL ON FUNCTION motor.arka_plan_calistir(),motor.saat_isi(),motor.yeniden_kur() FROM PUBLIC,anon,authenticated,service_role;
RESET ROLE;
