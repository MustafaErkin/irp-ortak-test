SET ROLE irp_sahibi;
-- T16-3: imzada başlangıç yok. Kurulum özel sütunu doldurabilir; aksi halde
-- gösterinin ilk olay anı kullanılır. Bu ayar istemciye açılmaz.
ALTER TABLE saat.ayar ADD COLUMN gosteri_baslangici timestamptz;
CREATE FUNCTION public.gosteri_sifirla() RETURNS jsonb LANGUAGE plpgsql VOLATILE
SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text=kapi.oturum_kisi(); bas timestamptz; BEGIN
 IF NOT saat.demo() OR NOT yetki_v6.istihdamda('OKUMA',kim,saat.simdi())
 OR NOT coalesce(okuma.satir('kisiler',kim)->'roller' ? 'YETKILI',false) THEN
  RAISE EXCEPTION 'IRP|YETKI|Yalniz gosteride yetkili';
 END IF;
 PERFORM pg_advisory_xact_lock(202620,1);
 SELECT coalesce(gosteri_baslangici,(SELECT min(oldugu_an) FROM public.olaylar),saat.simdi()) INTO bas FROM saat.ayar WHERE tek;
 -- Auth eşlemesi ve cihaz eşitlemeleri modelde olduğu gibi korunur.
 ALTER TABLE public.olaylar DISABLE TRIGGER olaylar_degismez;
 TRUNCATE public.hassas_ekler,public.olaylar,public.ay_kapanislari,public.isleme_hatalari,
 public.modul_bildirimleri,motor.hal,motor.baglam,motor.calisma,motor.anahtar_sirasi,
 motor.yayin,motor.noktalar,motor.olcumler,motor.arka_plan_isleri,
 okuma.yayin_yardimci,okuma.yayin_sirasi,okuma.kapanis_sonuclari,okuma.duzeltme_ozeti,okuma.sinyal_kuyrugu,okuma.sinyal_tekil,
 okuma.ana_veri_ozeti,public.degisim_sinyalleri RESTART IDENTITY;
 ALTER TABLE public.olaylar ENABLE TRIGGER olaylar_degismez;
 DELETE FROM motor.durum WHERE true; INSERT INTO motor.durum(tek) VALUES(true);
 UPDATE saat.ayar SET simdi=bas WHERE tek;
 PERFORM motor.bosalt('MOTOR');
 PERFORM motor.yaz('MOTOR','kod_listesi',irp.sabit('kodlar9'));
 PERFORM motor.yaz('MOTOR','yetki_kurallari',irp.sabit('yetkiler9'));
 PERFORM motor.iste('');
 RETURN jsonb_build_object('sonuc','BASARILI','simdi',saat.kodla(saat.simdi()));
END $$;
REVOKE ALL ON FUNCTION public.gosteri_sifirla() FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.gosteri_sifirla() TO authenticated;
RESET ROLE;
