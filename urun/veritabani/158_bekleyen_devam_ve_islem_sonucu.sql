SET ROLE irp_sahibi;

-- Dakikalık saat işi korunur. Bu kapı yalnız zaten bekleyen hesabı sürdürür;
-- boşta yayın üretmez, başka işlemin kilidinde kuyruk oluşturmaz.
CREATE FUNCTION motor.bekleyen_isi() RETURNS integer LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM motor.durum WHERE tek AND bekleyen_sinir IS NOT NULL) THEN RETURN 0; END IF;
 IF NOT pg_try_advisory_xact_lock(202620,1) THEN RETURN 0; END IF;
 RETURN motor.arka_plan_calistir();
END $$;
REVOKE ALL ON FUNCTION motor.bekleyen_isi() FROM PUBLIC,anon,authenticated,service_role;

-- Kabul makbuzu tek başına tamamlanma değildir. Yalnız yayımlanmış kopyadaki
-- kendi olayının sonucunu oku; çalışma alanına, başka kişinin olayına bakma.
CREATE FUNCTION public.islem_sonucu(olay_kimligi text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE oturum_kim text; e public.olaylar; d motor.durum; durum text;
BEGIN
 oturum_kim=kapi.oturum_kisi();
 IF oturum_kim IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 SELECT * INTO e FROM public.olaylar o WHERE o.olay_kimligi=$1 AND o.kim=oturum_kim;
 -- Yok ve başkasına ait aynı yanıttır; olay varlığını sızdırma.
 IF NOT FOUND THEN RETURN jsonb_build_object('durum','BULUNAMADI'); END IF;
 SELECT * INTO d FROM motor.durum WHERE tek;
 IF e.kabul_no>d.okuma_kabul_no THEN durum='BEKLIYOR';
 ELSIF e.oldugu_an>d.son_yayin_ani THEN durum='ZAMANI_BEKLIYOR';
 ELSIF okuma.satir('olay_nesneleri',$1) IS NOT NULL THEN
  durum=CASE WHEN okuma.satir('supheliler',$1) IS NOT NULL THEN 'INCELEME_GEREKIYOR' ELSE 'TAMAMLANDI' END;
 ELSIF EXISTS(SELECT FROM jsonb_array_elements(okuma.tablo('olaylar')) x
             WHERE x->>'eylem_kodu'='KAYIT.GECERSIZ_SAYDIM' AND x#>>'{girdiler,hedef}'=$1) THEN durum='GECERSIZ';
 ELSE durum='BEKLIYOR';
 END IF;
 RETURN jsonb_build_object('durum',durum,'yayin_ani',d.son_yayin_ani);
END $$;
REVOKE ALL ON FUNCTION public.islem_sonucu(text) FROM PUBLIC,anon,service_role;
GRANT EXECUTE ON FUNCTION public.islem_sonucu(text) TO authenticated;
NOTIFY pgrst,'reload schema';
RESET ROLE;
