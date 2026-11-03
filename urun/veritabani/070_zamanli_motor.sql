SET ROLE irp_sahibi;
CREATE TABLE motor.noktalar(konum text COLLATE "C" PRIMARY KEY,an timestamptz NOT NULL,tur int NOT NULL,anahtar text COLLATE "C" NOT NULL,olay jsonb);
CREATE TABLE motor.olcumler(sira bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,olay text,nokta int,gec boolean,saniye double precision,yayin_saniye double precision);
-- motor.py:115 yurut hazırlığı. Bütün bilinen olaylardan hazırlanan bağlam geçmişe sürümlenmez.
CREATE FUNCTION motor.hazirla_kaynak(m text,kaynak jsonb) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE es jsonb; e jsonb; g jsonb; kod text; a text; rs jsonb='[]'; ts jsonb='[]'; tat jsonb='[]'; gun date; tak jsonb; x jsonb; t timestamptz; k text;
BEGIN
 SELECT coalesce(jsonb_agg(x ORDER BY saat.an(x->>'oldugu_an'),(x->>'olay_kimligi') COLLATE "C"),'[]') INTO es
 FROM jsonb_array_elements(kaynak) x WHERE saat.an(x->>'oldugu_an')<=saat.simdi()
 AND x->>'olay_kimligi' NOT IN (SELECT y#>>'{girdiler,hedef}' FROM jsonb_array_elements(kaynak) y WHERE saat.an(y->>'oldugu_an')<=saat.simdi() AND y->>'eylem_kodu'='KAYIT.GECERSIZ_SAYDIM');
 PERFORM motor.yaz(m,'olaylar',es);
 FOR e IN SELECT value FROM jsonb_array_elements(es) LOOP
  PERFORM motor.butce_denetle(); g=(e->'girdiler'); kod=(e->>'eylem_kodu');
  a=CASE kod WHEN 'AYAR.ONAY_ORANI' THEN 'onay_orani' WHEN 'AYAR.MAAS_PAYDASI' THEN 'maas_paydasi_saat' WHEN 'AYAR.PARCA_KODU_DESENI' THEN 'parca_kodu_deseni' WHEN 'AYAR.DEGISTIRDIM' THEN (g->>'anahtar') END;
  IF a IS NOT NULL THEN rs=rs||jsonb_build_array(g||jsonb_build_object('gecerli_baslangic',coalesce(nullif((g->>'gecerli_baslangic'),''),(e->>'oldugu_an')),'anahtar',a,'doguran_olay',(e->'olay_kimligi'))); END IF;
  IF kod='TAKVIM.TANIMLADIM' THEN ts=ts||jsonb_build_array(g||jsonb_build_object('gecerli_baslangic',coalesce((g->>'gecerli_baslangic'),saat.kodla(saat.gun_ani(saat.gun((e->>'oldugu_an'))+1))))); END IF;
  IF kod='TATIL.EKLEDIM' AND NOT tat ? ((g->>'tarih')) THEN tat=tat||jsonb_build_array((g->'tarih')); END IF;
  IF kod='TATIL.KALDIRDIM' THEN tat=(SELECT coalesce(jsonb_agg(value),'[]') FROM jsonb_array_elements(tat) WHERE value<>(g->'tarih')); END IF;
 END LOOP;
 PERFORM motor.yaz(m,'ayarlar',rs); PERFORM motor.yaz(m,'takvimler',ts); PERFORM motor.yaz(m,'tatiller',tat);
 PERFORM takvim.hazirla(m,es);
 IF m='MOTOR' THEN
  INSERT INTO motor.baglam SELECT ad,hal FROM motor.calisma WHERE kip=m AND ad IN ('olaylar','ayarlar','takvimler','tatiller','gun_tanimlari','izinler','ek_mesai_planlari','_v9_birim_takvimleri','_v9_kisi_birimleri') ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal;
 END IF;
 DELETE FROM motor.noktalar WHERE true;
 FOR e IN SELECT value FROM jsonb_array_elements(es) LOOP
  PERFORM motor.butce_denetle();
  t=saat.an((e->>'oldugu_an')); k=(e->>'olay_kimligi'); g=(e->'girdiler'); kod=(e->>'eylem_kodu');
  INSERT INTO motor.noktalar VALUES(motor.konum(t,1,k),t,1,k,e);
  IF kod='KISI.YETKINLIK_TANIMLADIM' AND saat.an(g->>'gecerli_baslangic')>t AND saat.an(g->>'gecerli_baslangic')<=saat.simdi() THEN
   INSERT INTO motor.noktalar VALUES(motor.konum(saat.an(g->>'gecerli_baslangic'),0,'YETKINLIK_GECERLI:'||k),saat.an(g->>'gecerli_baslangic'),0,'YETKINLIK_GECERLI:'||k,e); END IF;
  IF kod='KISI.DEGISTIRDIM' AND saat.an((g->>'gecerli_baslangic'))>t AND saat.an((g->>'gecerli_baslangic'))<=saat.simdi() THEN
   t=saat.an((g->>'gecerli_baslangic')); k='KISI_GECERLI:'||k; INSERT INTO motor.noktalar VALUES(motor.konum(t,0,k),t,0,k,e); END IF;
  IF kod='IS.SURE_EKLEDIM' AND irp.dogru((g->'is_bitti')) THEN
   t=saat.an((g->>'bitis')); k='ELLE_BITIS:'||((e->>'olay_kimligi')); INSERT INTO motor.noktalar VALUES(motor.konum(t,0,k),t,0,k,e||jsonb_build_object('eylem_kodu','ELLE_BITIS','oldugu_an',(g->'bitis'))); END IF;
 END LOOP;
 PERFORM takvim.sistem_noktalari(m,es);
END $$;
-- T14: kayıt başına tarihçe; dizinin sırası ayrı saklanır.
CREATE FUNCTION motor.hazirla(m text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE es jsonb; anahtar jsonb; BEGIN
 -- Kaynak olaylar değişmezdir. Aynı kaynak ve saatte devam eden arka plan
 -- parçası, bir önceki parçanın bağlamını ve nokta listesini kullanabilir.
 SELECT jsonb_build_array(count(*),max(kabul_no),saat.kodla(saat.simdi())) INTO anahtar FROM public.olaylar;
 IF m='MOTOR' AND anahtar=(SELECT hal FROM motor.baglam WHERE ad='_hazirlik_anahtari')
  AND EXISTS(SELECT FROM motor.noktalar) THEN RETURN; END IF;
 SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]') INTO es FROM public.olaylar;
 PERFORM motor.hazirla_kaynak(m,es);
 IF m='MOTOR' THEN INSERT INTO motor.baglam VALUES('_hazirlik_anahtari',anahtar) ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal; END IF;
END $$;
CREATE FUNCTION motor.kaydet_tarihce(k text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE r record; x record; s bigint; BEGIN
 FOR r IN SELECT ad,hal,sira FROM motor.calisma WHERE kip='MOTOR' AND ad NOT IN ('olaylar','ayarlar','takvimler','tatiller','gun_tanimlari','izinler','ek_mesai_planlari','_v9_birim_takvimleri','_v9_kisi_birimleri','_an','yakinsama_turlari') LOOP
  PERFORM motor.butce_denetle();
  IF jsonb_typeof(r.hal)='object' THEN
   FOR x IN SELECT z.key,z.value,coalesce(a.sira,0) sira FROM jsonb_each(r.hal) z LEFT JOIN motor.anahtar_sirasi a ON a.kip='MOTOR' AND a.ad=r.ad AND a.anahtar=z.key LOOP PERFORM motor.zamanli_yaz(r.ad,x.key,x.value,x.sira,k); END LOOP;
   FOR x IN SELECT anahtar FROM motor.hal WHERE ad=r.ad AND bit IS NULL AND NOT r.hal ? anahtar LOOP PERFORM motor.zamanli_yaz(r.ad,x.anahtar,NULL,0,k); END LOOP;
  ELSIF jsonb_typeof(r.hal)='array' THEN
   FOR x IN SELECT value,ordinality FROM jsonb_array_elements(r.hal) WITH ORDINALITY LOOP PERFORM motor.zamanli_yaz(r.ad,lpad(x.ordinality::text,12,'0'),x.value,x.ordinality,k); END LOOP;
   FOR x IN SELECT anahtar FROM motor.hal WHERE ad=r.ad AND bit IS NULL AND sira>jsonb_array_length(r.hal) LOOP PERFORM motor.zamanli_yaz(r.ad,x.anahtar,NULL,0,k); END LOOP;
  ELSE PERFORM motor.zamanli_yaz(r.ad,'',r.hal,0,k); END IF;
 END LOOP; END $$;
CREATE FUNCTION motor.halden_yukle(d text,k text DEFAULT NULL) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE a text; v jsonb; rs jsonb; r record; BEGIN
 PERFORM motor.bosalt(d);
 FOR a,v IN SELECT * FROM jsonb_each(irp.sabit('bos_hal')) LOOP
  PERFORM motor.butce_denetle();
  IF jsonb_typeof(v)='object' THEN
   FOR r IN SELECT * FROM motor.hal WHERE ad=a AND ((k IS NULL AND bit IS NULL) OR (k IS NOT NULL AND bas<k COLLATE "C" AND (bit IS NULL OR bit>=k COLLATE "C"))) ORDER BY sira,anahtar COLLATE "C" LOOP
    PERFORM motor.kaydet(d,a,r.anahtar,r.hal); END LOOP;
  ELSIF jsonb_typeof(v)='array' THEN SELECT coalesce(jsonb_agg(hal ORDER BY sira),'[]') INTO rs FROM motor.hal WHERE ad=a AND ((k IS NULL AND bit IS NULL) OR (k IS NOT NULL AND bas<k COLLATE "C" AND (bit IS NULL OR bit>=k COLLATE "C"))); PERFORM motor.yaz(d,a,rs);
  ELSE SELECT hal INTO rs FROM motor.hal WHERE ad=a AND ((k IS NULL AND bit IS NULL) OR (k IS NOT NULL AND bas<k COLLATE "C" AND (bit IS NULL OR bit>=k COLLATE "C"))) LIMIT 1; IF rs IS NOT NULL THEN PERFORM motor.yaz(d,a,rs); END IF;
  END IF;
 END LOOP;
 IF NOT EXISTS(SELECT FROM motor.hal WHERE ad='kod_listesi' AND (k IS NULL OR bas<k COLLATE "C")) AND NOT EXISTS(SELECT FROM public.olaylar WHERE eylem_kodu='KURULUM.TAMAMLADIM' AND oldugu_an<=saat.simdi()) THEN
  PERFORM motor.yaz(d,'kod_listesi',irp.sabit('kodlar9')); PERFORM motor.yaz(d,'yetki_kurallari',irp.sabit('yetkiler9')); END IF;
 FOR r IN SELECT * FROM motor.baglam WHERE ad NOT IN ('_hazirlik_anahtari','_calisma_siniri') LOOP PERFORM motor.yaz(d,r.ad,r.hal); END LOOP;
END $$;
-- motor.py:160–200 bir noktanın yürütülmesi; nokta sırası değişmez.
CREATE FUNCTION motor.nokta_isle(m text,n motor.noktalar) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE e jsonb=n.olay; kod text=(e->>'eylem_kodu'); oid text=(e->>'olay_kimligi'); dosya jsonb; refs jsonb;
BEGIN
 PERFORM motor.yaz(m,'_an',to_jsonb(saat.kodla(n.an)));
 IF n.tur=0 AND e IS NOT NULL THEN IF n.anahtar LIKE 'KISI_GECERLI:%' THEN PERFORM motor.ana_veri_isle(m,e); ELSIF n.anahtar LIKE 'YETKINLIK_GECERLI:%' THEN PERFORM k10_2.yetkinlik_isle(m,e); ELSE PERFORM kg.atolye_isle(m,e); END IF; RETURN; END IF;
 IF e IS NULL THEN PERFORM takvim.sistem_isle(m,n.anahtar,n.an); RETURN; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_array(t,k) ORDER BY t COLLATE "C",k COLLATE "C"),'[]') INTO refs FROM (
 SELECT DISTINCT (x->>'tur') t,(x->>'kimlik') k FROM jsonb_array_elements((e->'neyin_ustunde')) x UNION SELECT 'KISI',e#>>ARRAY['girdiler',a] FROM unnest(ARRAY['kisi','kimden','kime']) a WHERE irp.dogru(e#>ARRAY['girdiler',a]) UNION SELECT 'KISI',(e->>'adina') WHERE irp.dogru((e->'adina'))) z;
 PERFORM motor.kaydet(m,'olay_nesneleri',oid,refs);
 FOR dosya IN SELECT value FROM jsonb_array_elements((e->'kanit')) LOOP PERFORM motor.kaydet(m,'dosyalar',(dosya->>'dosya_kimligi'),dosya||jsonb_build_object('doguran_olay',oid)); END LOOP;
 IF kod='KISI.YETKINLIK_TANIMLADIM' THEN PERFORM k10_2.yetkinlik_isle(m,e); PERFORM k7.sonra(m,e); PERFORM k9.sonra(m,e); RETURN; END IF;
 IF k10_1.isle(m,e) OR k9.isle(m,e) OR k7.takvim_isle(m,e) OR k7.nesne_isle(m,e) THEN PERFORM k7.sonra(m,e); PERFORM k9.sonra(m,e); RETURN; END IF;
 IF NOT irp.sabit('taniklik') ? kod AND (e->>'giris_sekli')<>'AKTARIM' AND kod NOT IN ('IS.SURE_EKLEDIM','KAYIT.GECERSIZ_SAYDIM') AND NOT kapi.durum(m,e) THEN PERFORM motor.supheli(m,e,'Kabul edilmis karar yeniden hesapta duruma uymuyor'); RETURN; END IF;
 IF kod='KISI.DEGISTIRDIM' AND saat.an((e#>>'{girdiler,gecerli_baslangic}'))>n.an THEN RETURN; END IF;
 IF kod LIKE 'IS.%' OR kod LIKE 'MESAI.%' THEN PERFORM kg.atolye_isle(m,e); ELSIF kod LIKE 'GOREV.%' THEN PERFORM gorev.gorev_isle(m,e); ELSE PERFORM motor.ana_veri_isle(m,e); END IF;
 PERFORM k7.sonra(m,e); PERFORM k9.sonra(m,e); PERFORM gorev.bekletme_kayitlari(m,n.an);
END $$;
-- motor.py:201–219 bitirme geçişleri; yalnız YAYIN kopyasında çalışır.
CREATE FUNCTION motor.bitir(m text) RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column
 DECLARE k text; d jsonb; BEGIN
 FOR k,d IN SELECT * FROM motor.satirlar(m,'kisi_durumu') LOOP
  PERFORM motor.butce_denetle(); IF irp.dogru((d->'kova')) AND irp.dogru((d->'baslangic')) THEN PERFORM takvim.aralik_ekle(m,k,d,NULL); END IF;
  PERFORM motor.kaydet(m,'kisi_durumu',k,d||jsonb_build_object('son_hesap_ani',saat.kodla(saat.simdi()))); END LOOP;
 PERFORM gorev.bagimliliklari_hesapla(m); PERFORM kg.elle_uygula(m); PERFORM gorev.bekletme_kayitlari(m,saat.simdi()); PERFORM kg.ana_isleri_guncelle(m); PERFORM motor.yaz(m,'araliklar',kg.birlestir(motor.oku(m,'araliklar','[]')));
 FOR k,d IN SELECT * FROM motor.satirlar(m,'kisi_durumu') LOOP PERFORM motor.kaydet(m,'kisi_durumu',k,d||jsonb_build_object('aktif_is',(d->'acik_is'))); END LOOP;
 PERFORM motor.yaz(m,'araliklar',motor.oku(m,'araliklar','[]')||is_.tezgah_saati_hesapla(m));
 PERFORM motor.yaz(m,'araliklar',(SELECT coalesce(jsonb_agg(x ORDER BY coalesce((x->>'kisi'),'') COLLATE "C",(x->>'baslangic'),(x->>'kova') COLLATE "C",n),'[]') FROM jsonb_array_elements(motor.oku(m,'araliklar','[]')) WITH ORDINALITY z(x,n)));
 PERFORM k6.baglantilari_yansit(m); PERFORM k7.tamamla(m); PERFORM k9.tamamla(m); PERFORM motor.yaz(m,'_an','null');
END $$;
CREATE FUNCTION motor.yayinla() RETURNS void LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE r record; a text; k text; x jsonb; once jsonb; bas double precision=saat.olcum(); no bigint;
 fotograf_ani text=coalesce(current_setting('irp.yayin_fotografi_ani',true),''); BEGIN
 DELETE FROM motor.calisma WHERE kip='YAYIN'; DELETE FROM motor.anahtar_sirasi WHERE kip='YAYIN';
 INSERT INTO motor.calisma(kip,ad,hal) SELECT 'YAYIN',ad,hal FROM motor.calisma WHERE kip='MOTOR';
 INSERT INTO motor.anahtar_sirasi(kip,ad,anahtar,sira) SELECT 'YAYIN',ad,anahtar,sira FROM motor.anahtar_sirasi WHERE kip='MOTOR';
 PERFORM motor.bitir('YAYIN');
 PERFORM motor.butce_denetle();
 PERFORM set_config('irp.yayin_fotografi_ani',saat.kodla(saat.simdi()),true);
 FOR r IN SELECT * FROM motor.yayin WHERE ad='bildirimler' LOOP
  x=motor.kayit('YAYIN','bildirimler',r.anahtar); IF irp.dogru(x) THEN x=x||jsonb_build_object('olusma_ani',(r.hal->'olusma_ani')); ELSE x=r.hal||'{"gecerli":false}'; END IF; PERFORM motor.kaydet('YAYIN','bildirimler',r.anahtar,x); END LOOP;
 FOREACH a IN ARRAY ARRAY['isler','gorevler','kisiler','birimler','etaplar','projeler','notlar','tezgahlar','kisi_durumu','bildirimler','supheliler','sonuclar','bekletmeler','dosyalar'] LOOP
  FOR k,x IN SELECT * FROM motor.satirlar('YAYIN',a) LOOP PERFORM motor.kaydet('YAYIN',a,k,x||jsonb_build_object('surum',surum.ozet(surum.is_alanlari(x)))); END LOOP; END LOOP;
 FOR k,x IN SELECT * FROM motor.satirlar('YAYIN','gun_sonu_raporlari') LOOP
  PERFORM motor.butce_denetle();
  PERFORM motor.kaydet('YAYIN','gun_sonu_raporlari',k,k7.gun_sonu_raporu('YAYIN',x->>'kisi',saat.gun(x->>'gun')));
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(k9.hatirlatmalar('YAYIN')) LOOP
  k='GUN_SONU:'||(x->>'kisi')||':'||(x->>'gun');
  PERFORM motor.kaydet('YAYIN','bildirimler',k||':'||(x->>'kural')||':'||(x->>'alici'),
   x||jsonb_build_object('doguran_olay',k,'gecerli',true,'metin',x->'kisi','olusma_ani',saat.kodla(saat.gercek())));
 END LOOP;
 PERFORM k9.gorulmeleri_yansit('YAYIN');
 PERFORM k10_1.modul_gorulmeleri_yansit('YAYIN');
 FOR k,x IN SELECT * FROM motor.satirlar('YAYIN','bildirimler') LOOP PERFORM motor.kaydet('YAYIN','bildirimler',k,'{"kaynak":"CEKIRDEK","onem":"BILGI"}'::jsonb||x); END LOOP;
 FOREACH a IN ARRAY ARRAY['nesneler','nesne_turleri','gun_sonu_raporlari'] LOOP FOR k,x IN SELECT * FROM motor.satirlar('YAYIN',a) LOOP PERFORM motor.kaydet('YAYIN',a,k,x||jsonb_build_object('surum',surum.ozet(surum.is_alanlari(x)))); END LOOP; END LOOP;
 -- Yayın iş alanı değişmediyse fiziksel satır güncellemesi yapılmaz.
 FOR r IN SELECT c.ad,c.hal FROM motor.calisma c WHERE kip='YAYIN' AND jsonb_typeof(c.hal)='object' LOOP
  FOR k,x IN SELECT * FROM jsonb_each(r.hal) LOOP SELECT sira INTO no FROM motor.anahtar_sirasi WHERE kip='YAYIN' AND ad=r.ad AND anahtar=k;
   INSERT INTO motor.yayin(ad,anahtar,sira,hal,surum) VALUES(r.ad,k,coalesce(no,0),x,surum.ozet(surum.is_alanlari(x))) ON CONFLICT(ad,anahtar) DO UPDATE SET hal=excluded.hal,surum=excluded.surum,sira=excluded.sira WHERE motor.yayin.hal IS DISTINCT FROM excluded.hal;
  END LOOP;
  DELETE FROM motor.yayin WHERE ad=r.ad AND NOT r.hal ? anahtar;
 END LOOP;
 PERFORM motor.son_hal_yaz();
 PERFORM motor.butce_denetle();
 PERFORM set_config('irp.yayin_fotografi_ani',fotograf_ani,true);
 UPDATE motor.durum SET son_yayin_ani=saat.simdi(),kurulum_tamamlandi=irp.dogru(motor.oku('YAYIN','kurulum_kaynagi','null')),yayin_saniye=saat.olcum()-bas WHERE tek;
END $$;
-- T14 §5: canlı bütçesi alt işlemde geri alınır; kaynak olay dış işlemde korunur.
CREATE FUNCTION motor.calistir(k text DEFAULT NULL,arka_plan boolean DEFAULT false) RETURNS boolean LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE n motor.noktalar; sinir text; bas double precision=saat.olcum(); sayi int=0; nb int; sb double precision;
 onceki_butce text=coalesce(current_setting('irp.canli_bitis',true),''); BEGIN
 SELECT islenen_sinir,nokta_butcesi,saniye_butcesi INTO sinir,nb,sb FROM motor.durum WHERE tek;
 -- Tek kapıda kilit ve kabul denetiminde geçen süre de canlı çağrının
 -- bütçesindedir. Kuyrukta beklemiş olay yeni bir tam bütçe başlatmaz.
 IF NOT arka_plan THEN bas=least(bas,extract(epoch FROM statement_timestamp())::double precision); END IF;
 PERFORM set_config('irp.canli_bitis',CASE WHEN arka_plan THEN '' ELSE (bas+sb)::text END,true);
 PERFORM motor.butce_denetle();
 IF k IS NOT NULL AND k<sinir COLLATE "C" THEN PERFORM motor.geri_sar(k); sinir=k; END IF;
 -- Ham çalışma kopyası yayın bitirme geçişlerinde değiştirilmez. Kaydedilmiş
 -- sınır aynıysa tarihçeden aynı kopyayı yeniden yazmak gerekmez. Geri sarma
 -- ve baştan kurma bu işareti siler; yayın kopyası hiçbir zaman kullanılmaz.
 IF to_jsonb(sinir) IS DISTINCT FROM (SELECT hal FROM motor.baglam WHERE ad='_calisma_siniri')
  OR NOT EXISTS(SELECT FROM motor.calisma WHERE kip='MOTOR') THEN PERFORM motor.halden_yukle('MOTOR'); END IF;
 PERFORM motor.hazirla('MOTOR');
 -- Arka planda hazırlık tamamlandıktan sonra parça bütçesi başlar. En az bir
 -- nokta işlenir; aksi halde pahalı hazırlık sonsuz sıfır ilerleme doğururdu.
 IF arka_plan THEN bas=saat.olcum(); END IF;
 FOR n IN SELECT * FROM motor.noktalar WHERE konum>=sinir COLLATE "C" AND an<=saat.simdi() ORDER BY konum COLLATE "C" LOOP
  IF (sayi>=nb OR saat.olcum()-bas>=sb) AND (NOT arka_plan OR sayi>0) THEN
   IF NOT arka_plan THEN RAISE EXCEPTION 'IRP_BUTCE'; END IF;
   UPDATE motor.durum SET islenen_sinir=n.konum,bekleyen_sinir=n.konum,islenen_nokta=islenen_nokta+sayi WHERE tek;
   INSERT INTO motor.baglam VALUES('_calisma_siniri',to_jsonb(n.konum)) ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal;
   PERFORM set_config('irp.canli_bitis',onceki_butce,true); RETURN false;
  END IF;
  PERFORM motor.nokta_isle('MOTOR',n); PERFORM motor.kaydet_tarihce(n.konum); sayi=sayi+1;
 END LOOP;
 IF NOT arka_plan AND (sayi>=nb OR saat.olcum()-bas>=sb) THEN RAISE EXCEPTION 'IRP_BUTCE'; END IF;
 PERFORM motor.yayinla();
 UPDATE motor.durum SET islenen_sinir=motor.konum(saat.simdi(),3,''),bekleyen_sinir=NULL,islenen_nokta=islenen_nokta+sayi,son_gec_nokta=CASE WHEN k IS NOT NULL THEN sayi ELSE 0 END WHERE tek;
 INSERT INTO motor.baglam VALUES('_calisma_siniri',to_jsonb(motor.konum(saat.simdi(),3,''))) ON CONFLICT(ad) DO UPDATE SET hal=excluded.hal;
 PERFORM set_config('irp.canli_bitis',onceki_butce,true);
 RETURN true;
END $$;
CREATE FUNCTION motor.iste(k text DEFAULT NULL,oid text DEFAULT NULL) RETURNS text LANGUAGE plpgsql AS $$
#variable_conflict use_column

DECLARE bas double precision=saat.olcum(); oldu boolean; bek text; n int; yp double precision; once int; BEGIN
 SELECT islenen_nokta INTO once FROM motor.durum WHERE tek;
 SELECT bekleyen_sinir INTO bek FROM motor.durum WHERE tek;
 IF bek IS NOT NULL THEN k=least(k,bek); END IF;
 BEGIN oldu=motor.calistir(k,false);
 EXCEPTION WHEN raise_exception THEN IF SQLERRM<>'IRP_BUTCE' THEN RAISE; END IF; oldu=false; END;
 IF NOT oldu THEN UPDATE motor.durum SET bekleyen_sinir=least(coalesce(k,islenen_sinir),coalesce(bekleyen_sinir,coalesce(k,islenen_sinir))) WHERE tek;
  IF NOT EXISTS(SELECT FROM motor.arka_plan_isleri WHERE durum='BEKLIYOR') THEN INSERT INTO motor.arka_plan_isleri(tur) VALUES('HESAP'); END IF;
 END IF;
 SELECT CASE WHEN oldu THEN islenen_nokta-once END,CASE WHEN oldu THEN yayin_saniye END INTO n,yp FROM motor.durum WHERE tek;
 INSERT INTO motor.olcumler(olay,nokta,gec,saniye,yayin_saniye) VALUES(oid,n,k IS NOT NULL,saat.olcum()-bas,yp);
 RETURN CASE WHEN oldu THEN 'GUNCEL' ELSE 'BEKLIYOR' END;
END $$;
-- T14 §5.3 etki zamanı; bağlamı etkileyen tarihler en erken noktaya döndürür.
CREATE FUNCTION motor.etki_ani(e jsonb) RETURNS timestamptz LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column

DECLARE t timestamptz=saat.an((e->>'oldugu_an')); g jsonb=(e->'girdiler'); a text; kod text=(e->>'eylem_kodu'); x timestamptz; s jsonb; BEGIN
 FOREACH a IN ARRAY ARRAY['gecerli_baslangic','takvim_gecerli','giris_tarihi','ayrilis_tarihi','tarih','baslangic'] LOOP IF irp.dogru(g->a) THEN t=least(t,CASE WHEN (g->>a) ~ '^[0-9]{2}:[0-9]{2}$' THEN saat.gun_ani(saat.gun(g->>'tarih'),g->>a) ELSE saat.an(g->>a) END); END IF; END LOOP;
 FOR s IN SELECT value FROM jsonb_array_elements(coalesce(g->'gorevler',g->'isler',jsonb_build_array(g))) LOOP IF irp.dogru(s#>'{ek_mesai,tarih}') THEN t=least(t,saat.an(s#>>'{ek_mesai,tarih}')); END IF; END LOOP;
 IF kod IN ('KAYIT.GECERSIZ_SAYDIM','IZIN.ONAYLADIM','IZIN.REDDETTIM','IZIN.IK_ONAYLADIM','IZIN.IPTAL_ETTIM','EK_MESAI.IPTAL_ETTIM','TEZGAH.BAKIM_IPTAL_ETTIM') THEN SELECT etki_ani INTO x FROM public.olaylar WHERE olay_kimligi=(g->>'hedef'); t=least(t,x); END IF;
 -- T14-1: hazır izin bağlamı önceki atamaların R37 bildirimini de değiştirir.
 -- Y109 D5 farkıyla doğrulandı; izin tarihinden eski atamalar da yeniden oynatılır.
 IF kod LIKE 'IZIN.%' THEN SELECT min(oldugu_an) INTO x FROM public.olaylar WHERE eylem_kodu IN ('IS.ATADIM','GOREV.ATADIM'); t=least(t,x); END IF;
 IF kod='KURULUM.TAMAMLADIM' THEN SELECT min(etki_ani) INTO x FROM public.olaylar; t=least(t,x); END IF;
 IF kod IN ('MESAI.GIRDIM','MESAI.CIKTIM') AND NOT EXISTS(SELECT FROM public.olaylar WHERE eylem_kodu IN ('MESAI.GIRDIM','MESAI.CIKTIM') AND saat.gun(saat.kodla(oldugu_an))=saat.gun((e->>'oldugu_an'))) THEN t=least(t,saat.gun_ani(saat.gun((e->>'oldugu_an')))); END IF;
 RETURN t;
END $$;
RESET ROLE;
