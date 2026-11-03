-- Tur 2: görev ekranı için yayımlanmış durum, teslim notu ve ret gerekçesi.
-- Yeni yazma yetkisi veya motor kuralı yok. Ham olay listesi istemciye verilmez.
SET ROLE irp_sahibi;
CREATE FUNCTION okuma.gorev_ayrintisi(kim text,hedef text) RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE task jsonb; history jsonb; notes jsonb; requests jsonb; BEGIN
 task=okuma.satir('gorevler',hedef);
 IF task IS NULL OR NOT okuma.gorebilir(kim,'GOREV',hedef) THEN RAISE EXCEPTION 'IRP|YETKI|Gorev gorunurlugu'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('an',s.x->'an','kim',e.icerik->'kim','eylem',e.icerik->'eylem_kodu',
  'baslik',CASE e.icerik->>'eylem_kodu' WHEN 'GOREV.KABUL_ETTIM' THEN 'Kabul Edildi' WHEN 'GOREV.TAMAMLADIM' THEN 'Teslim Edildi'
  WHEN 'GOREV.ONAYLADIM' THEN 'Teslim Onaylandı' WHEN 'GOREV.REDDETTIM' THEN CASE WHEN e.icerik->'girdiler'->>'revizyon_ver'='true' THEN 'Ayrı Revizyon Açıldı' ELSE 'Düzeltmeye Gönderildi' END
  WHEN 'GOREV.IPTAL_ETTIM' THEN 'İptal Edildi' ELSE 'Görev Güncellendi' END,
  'not',CASE WHEN e.icerik->>'eylem_kodu' IN ('GOREV.TAMAMLADIM','GOREV.REDDETTIM','GOREV.IPTAL_ETTIM') THEN e.icerik->'girdiler'->'not' END) ORDER BY s.x->>'an',e.kabul_no),'[]') INTO history
 FROM okuma.satirlar('sonuclar') s JOIN public.olaylar e ON e.olay_kimligi=s.x->>'doguran_olay'
 WHERE s.x->>'kural'='R15' AND s.x->>'nesne_kimlik'=hedef;
 history=jsonb_build_array(jsonb_build_object('an',task->'atama_ani','kim',task->'veren','baslik','Görev Atandı'))||history;
 notes=okuma.web_oku(kim,'WEB_NOTLAR',hedef,'{"tur":"GOREV"}');
 -- Gönderen kendi isteğinin toplam sonucunu görür. Başkasının görev kimliği/kişisi açılmaz.
 SELECT coalesce(jsonb_object_agg(n->>'kimlik',okuma.not_alicilari(kim,n->>'kimlik') ||
  CASE WHEN n->>'yazan'=kim THEN jsonb_build_object('ozet',(SELECT jsonb_build_object(
   'toplam',count(*),'kabul',count(*) FILTER (WHERE x->>'durum'='BITTI'),
   'bekleyen',count(*) FILTER (WHERE x->>'durum' NOT IN ('BITTI','IPTAL')),
   'iptal',count(*) FILTER (WHERE x->>'durum'='IPTAL'))
   FROM okuma.satirlar('gorevler') WHERE x->>'tur'='NOT' AND x->>'kaynak'=n->>'kimlik')) ELSE '{}'::jsonb END),'{}')
 INTO requests FROM jsonb_array_elements(notes) n;
 RETURN jsonb_build_object('gorev',task,'gecmis',history,'notlar',notes,'istekler',requests,
  'dosyalar',okuma.web_oku(kim,'WEB_DOSYALAR',hedef,'{"tur":"GOREV"}'));
END $$;
REVOKE ALL ON FUNCTION okuma.gorev_ayrintisi(text,text) FROM PUBLIC,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.oku(veri text,hedef text DEFAULT NULL,g jsonb DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
#variable_conflict use_column
DECLARE kim text; deger jsonb;
BEGIN
 IF g IS NULL OR jsonb_typeof(g)<>'object' THEN RAISE EXCEPTION 'IRP|BICIM|Okuma parametreleri'; END IF;
 IF g ? 'kim' THEN
  IF coalesce(current_setting('role',true),'')<>'service_role' OR auth.role() IS DISTINCT FROM 'service_role' THEN RAISE EXCEPTION 'IRP|YETKI|g.kim yalniz cekirdek servis rolune aittir'; END IF;
  kim=g->>'kim';
 ELSE kim=kapi.oturum_kisi(); END IF;
 IF kim IS NULL THEN RAISE EXCEPTION 'IRP|YETKI|Oturum'; END IF;
 IF veri='GOREV_AYRINTISI' THEN deger=okuma.gorev_ayrintisi(kim,hedef);
 ELSIF veri='WEB_KISI' THEN deger=okuma.web_kisi_ayrintisi(kim,hedef);
 ELSIF veri='NOT_ALICILARI' THEN deger=okuma.not_alicilari(kim,hedef);
 ELSIF veri LIKE 'WEB\_%' ESCAPE '\' THEN deger=okuma.web_oku(kim,veri,hedef,g-'kim');
 ELSE deger=okuma.oku(kim,veri,hedef,g-'kim'); END IF;
 IF veri='WEB_BAGLAM' THEN
  deger=deger||jsonb_build_object('sorumlu_adaylari',(SELECT jsonb_object_agg(kod,adaylar) FROM (
   SELECT kod,(SELECT coalesce(jsonb_agg(k ORDER BY k),'[]') FROM okuma.satirlar('kisiler') WHERE yetki_v6.sorumlu_atayabilir('OKUMA',kim,k,kod)) adaylar
   FROM unnest(ARRAY['PROJE.ACTIM','PROJE.DEGISTIRDIM','ETAP.TANIMLADIM','ETAP.DEGISTIRDIM']) kod) q));
 END IF;
 IF veri='PLAN' AND coalesce((g->>'surumler')::boolean,false) THEN
  deger=deger||jsonb_build_object('surumler',coalesce(okuma.satir('plan_surumleri',hedef),'[]'));
 END IF;
 IF veri='GANTT' AND coalesce((g->>'adlar')::boolean,false) THEN
  SELECT coalesce(jsonb_agg(x||jsonb_build_object('ad',okuma.satir(CASE x->>'tur' WHEN 'ETAP' THEN 'etaplar' WHEN 'IS' THEN 'isler' ELSE 'gorevler' END,x->>'kimlik')->'ad')),'[]') INTO deger
  FROM jsonb_array_elements(deger) x;
 END IF;
 IF veri='PROJE' AND coalesce((g->>'ekip')::boolean,false) AND deger IS NOT NULL THEN
  -- Ana oku çağrısı proje görünürlüğünü denetledi. Yalnız güncel ek erişim listesi.
  deger=deger||jsonb_build_object('ek_erisim',coalesce((SELECT jsonb_agg(k) FROM okuma.satirlar('kisiler') WHERE k10.ek_erisim('OKUMA',k,hedef)),'[]'::jsonb));
 END IF;
 RETURN jsonb_build_object('deger',deger,'hesap',CASE WHEN bekleyen_sinir IS NULL THEN 'GUNCEL' ELSE 'BEKLIYOR' END,'hesap_ani',saat.kodla(son_yayin_ani)) FROM motor.durum WHERE tek;
END $$;
RESET ROLE;
