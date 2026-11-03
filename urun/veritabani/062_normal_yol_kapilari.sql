SET ROLE irp_sahibi;
-- kapilar_v3.dongusuz: yaprakları çıkarma aynı yönlü grafın çevrimini sınar.
CREATE FUNCTION kapilar_v3.dongusuz(graf jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE kalan jsonb=graf; sil text[]; BEGIN
 WHILE kalan<>'{}' LOOP SELECT array_agg(key) INTO sil FROM jsonb_each(kalan) x WHERE NOT EXISTS(SELECT FROM jsonb_array_elements_text(x.value) p WHERE kalan ? p);
  IF cardinality(sil) IS NULL THEN RETURN false; END IF; kalan=kalan-sil;
 END LOOP; RETURN true; END $$;
CREATE FUNCTION kapilar_v3.on_kosul_kapisi(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; oid text=e->>'olay_kimligi'; graf jsonb='{}'; yeni jsonb='{}'; k text; v jsonb; s jsonb; ps jsonb; ss jsonb; n bigint; BEGIN
 IF kod NOT IN ('GOREV.ATADIM','GOREV.DEGISTIRDIM','IS.TANIMLADIM') THEN RETURN true; END IF;
 FOR k,v IN SELECT * FROM motor.satirlar(d,'gorevler') UNION ALL SELECT * FROM motor.satirlar(d,'isler') LOOP graf=graf||jsonb_build_object(k,coalesce(v->'on_kosul',v->'on_isler','[]')); END LOOP;
 IF kod='GOREV.DEGISTIRDIM' THEN IF NOT g->'degisenler' ? 'on_kosul' THEN RETURN true; END IF; yeni=jsonb_build_object((kapi.hedefler(e,'GOREV'))[1],g#>'{degisenler,on_kosul}');
 ELSE ss=CASE WHEN kod='GOREV.ATADIM' THEN g->'gorevler' ELSE g->'isler' END;
  FOR s,n IN SELECT * FROM jsonb_array_elements(ss) WITH ORDINALITY LOOP k=oid||CASE WHEN kod='GOREV.ATADIM' OR jsonb_array_length(ss)>1 THEN '/'||n ELSE '' END;
   SELECT coalesce(jsonb_agg(CASE WHEN jsonb_typeof(value)='object' THEN to_jsonb(oid||'/'||(value->>'satir')) ELSE value END),'[]') INTO ps FROM jsonb_array_elements(coalesce(s->'on_kosul',s->'on_isler','[]')); yeni=yeni||jsonb_build_object(k,ps);
  END LOOP;
 END IF; graf=graf||yeni;
 RETURN NOT EXISTS(SELECT FROM jsonb_each(yeni) z CROSS JOIN LATERAL jsonb_array_elements_text(z.value) p WHERE NOT graf ? p) AND kapilar_v3.dongusuz(graf); END $$;
CREATE FUNCTION kapilar_v3.ek_kapilar(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; t timestamptz=saat.an(e->>'oldugu_an'); v timestamptz; yarin timestamptz; ks text[]; k text; BEGIN
 IF NOT kapilar_v3.on_kosul_kapisi(d,e) THEN RETURN false; END IF;
 IF kod='AYAR.ONAY_ORANI' AND saat.an(coalesce(g->>'gecerli_baslangic',e->>'oldugu_an'))<t THEN RETURN false; END IF;
 IF kod='TAKVIM.TANIMLADIM' THEN yarin=saat.gun_ani(saat.gun(e->>'oldugu_an')+1); v=coalesce(saat.an(g->>'gecerli_baslangic'),yarin); IF v<yarin OR v<>saat.gun_ani(saat.gun(saat.kodla(v))) THEN RETURN false; END IF; END IF;
 IF kod='TATIL.EKLEDIM' AND (saat.gun_ani(saat.gun(g->>'tarih'))<saat.gun_ani(saat.gun(e->>'oldugu_an')+1) OR saat.an(coalesce(g->>'gecerli_baslangic',e->>'oldugu_an'))<t) THEN RETURN false; END IF;
 -- Modelin Motor kopyası kapanışları taşımaz; bu kapı Depo kabulünde geçerlidir.
 IF kod='MAAS.GUNCELLEDIM' AND NOT irp.dogru(motor.oku(d,'_an','null')) THEN k=date_trunc('month',saat.an(g->>'gecerli_baslangic') AT TIME ZONE 'Europe/Istanbul')::date::text; IF EXISTS(SELECT FROM public.ay_kapanislari WHERE starts_with(anahtar,k||':')) THEN RETURN false; END IF; END IF;
 IF kod='IS.ATADIM' THEN ks=CASE WHEN irp.dogru(g->'kisiler') THEN irp.dizi(g->'kisiler') ELSE ARRAY[g->>'kisi'] END;
  IF (SELECT count(DISTINCT x)<>count(*) FROM unnest(ks) x) THEN RETURN false; END IF;
  FOREACH k IN ARRAY ks LOOP IF NOT kapilar_v5.aktif_kisi(d,k) THEN RETURN false; END IF; END LOOP;
 END IF;
 IF kod='IS.SURE_EKLEDIM' AND irp.dogru(g->'is_bitti') AND EXISTS(SELECT FROM public.olaylar WHERE irp.sabit('taniklik') ? eylem_kodu AND kapi.hedefler(icerik,'IS')&&kapi.hedefler(e,'IS') AND oldugu_an>saat.an(g->>'bitis')) THEN RETURN false; END IF;
 RETURN true; END $$;
-- kurallar_v6.yetkili_kalir: gelecekteki bütün rol ve istihdam sınırlarını denetler.
CREATE FUNCTION k6.yetkili_kalir(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE roller jsonb='{}'; donemler jsonb='{}'; sinirlar timestamptz[]=ARRAY[yetki_v6.simdi(d)]; x jsonb; g jsonb; kod text; k text; ds jsonb; rs jsonb; t timestamptz; tarih date; sayi int; mevcut jsonb; BEGIN
 FOR x IN SELECT z FROM (SELECT icerik z FROM public.olaylar WHERE eylem_kodu LIKE 'KISI.%' AND olay_kimligi<>e->>'olay_kimligi' AND (NOT irp.dogru(motor.oku(d,'_an')) OR konum<motor.konum(saat.an(e->>'oldugu_an'),1,e->>'olay_kimligi') COLLATE "C") UNION ALL SELECT e) q ORDER BY saat.an(z->>'oldugu_an'),z->>'olay_kimligi' COLLATE "C" LOOP
  g=x->'girdiler'; kod=x->>'eylem_kodu'; k=coalesce(g->>'kisi',g->>'kod');
  IF kod='KISI.EKLEDIM' THEN ds=coalesce(donemler->k,'[]')||jsonb_build_array(jsonb_build_array(g->'giris_tarihi',NULL)); donemler=donemler||jsonb_build_object(k,ds);
   t=saat.an(g->>'giris_tarihi'); roller=roller||jsonb_build_object(k,coalesce(roller->k,'[]')||jsonb_build_array(jsonb_build_object('an',saat.kodla(t),'olay',x->'olay_kimligi','roller',g->'roller'))); sinirlar=array_append(sinirlar,t);
  ELSIF kod='KISI.AYRILDI' AND irp.dogru(donemler->k) THEN tarih=CASE WHEN NOT irp.dogru(g->'iptal') THEN saat.gun(g->>'ayrilis_tarihi') END; ds=donemler->k; ds=jsonb_set(ds,ARRAY[(jsonb_array_length(ds)-1)::text,'1'],coalesce(to_jsonb(tarih::text),'null')); donemler=donemler||jsonb_build_object(k,ds); IF tarih IS NOT NULL THEN sinirlar=array_append(sinirlar,saat.gun_ani(tarih+1)); END IF;
  ELSIF kod='KISI.DEGISTIRDIM' AND g->'degisenler' ? 'roller' THEN t=saat.an(g->>'gecerli_baslangic'); sinirlar=array_append(sinirlar,t); roller=roller||jsonb_build_object(k,coalesce(roller->k,'[]')||jsonb_build_array(jsonb_build_object('an',saat.kodla(t),'olay',x->'olay_kimligi','roller',g#>'{degisenler,roller}')));
  END IF;
 END LOOP;
 FOR t IN SELECT DISTINCT z FROM unnest(sinirlar) z WHERE z>=yetki_v6.simdi(d) ORDER BY z LOOP sayi=0;
  FOR k,rs IN SELECT * FROM jsonb_each(roller) LOOP SELECT value INTO mevcut FROM jsonb_array_elements(rs) WHERE saat.an(value->>'an')<=t ORDER BY saat.an(value->>'an') DESC,value->>'olay' COLLATE "C" DESC LIMIT 1;
   IF mevcut->'roller' ? 'YETKILI' AND EXISTS(SELECT FROM jsonb_array_elements(donemler->k) a WHERE saat.gun(a->>0)<=saat.gun(saat.kodla(t)) AND (a->>1 IS NULL OR saat.gun(saat.kodla(t))<=saat.gun(a->>1))) THEN sayi=sayi+1; END IF;
  END LOOP; IF sayi=0 THEN RETURN false; END IF;
 END LOOP; RETURN true; END $$;
CREATE FUNCTION k6.kapilar(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; t timestamptz=saat.an(e->>'oldugu_an'); s jsonb; p jsonb; k text; ss jsonb; BEGIN
 IF kod IN ('KISI.EKLEDIM','KISI.DEGISTIRDIM') THEN
  IF kod='KISI.EKLEDIM' THEN p=motor.kayit(d,'kisiler',g->>'kod'); IF irp.dogru(p) AND (NOT irp.dogru(p->'ayrilis_tarihi') OR saat.gun(p->>'ayrilis_tarihi')>=saat.gun(e->>'oldugu_an') OR saat.gun(g->>'giris_tarihi')<=saat.gun(p->>'ayrilis_tarihi')) THEN RETURN false; END IF; s=g;
  ELSE IF NOT kapilar_v5.aktif_kisi(d,g->>'kisi') OR saat.an(g->>'gecerli_baslangic')<t OR EXISTS(SELECT FROM jsonb_object_keys(g->'degisenler') a WHERE a<>ALL(ARRAY['ad','birim','yaka','roller'])) THEN RETURN false; END IF; s=motor.kayit(d,'kisiler',g->>'kisi')||(g->'degisenler'); IF g->'degisenler' ? 'roller' AND NOT k6.yetkili_kalir(d,e) THEN RETURN false; END IF; END IF;
  RETURN motor.oku(d,'birimler') ? (s->>'birim') AND s->>'yaka' IN ('MAVI','BEYAZ') AND irp.dogru(s->'roller') AND NOT EXISTS(SELECT FROM jsonb_array_elements_text(s->'roller') r WHERE NOT k6.kod_aktif(d,'ROL',r));
 ELSIF kod='KISI.AYRILDI' THEN k=g->>'kisi'; p=motor.kayit(d,'kisiler',k); IF NOT irp.dogru(p) THEN RETURN false; END IF;
  IF irp.dogru(p->'ayrilis_tarihi') THEN IF saat.gun(e->>'oldugu_an')>=saat.gun(p->>'ayrilis_tarihi') THEN RETURN false; END IF; IF irp.dogru(g->'iptal') THEN RETURN true; END IF; ELSIF irp.dogru(g->'iptal') THEN RETURN false; END IF;
  RETURN saat.gun(g->>'ayrilis_tarihi')>=greatest(saat.gun(e->>'oldugu_an'),saat.gun(p->>'giris_tarihi')) AND NOT irp.dogru(motor.kayit(d,'listeler',k,'[]')) AND NOT EXISTS(SELECT FROM motor.satirlar(d,'gorevler') WHERE hal->>'durum' NOT IN ('BITTI','IPTAL') AND k IN (hal->>'kisi',hal->>'onaylayan')) AND NOT EXISTS(SELECT FROM motor.satirlar(d,'birimler') WHERE hal->>'basi'=k) AND NOT EXISTS(SELECT FROM motor.satirlar(d,'yonlendirme') WHERE hal ? k) AND k6.yetkili_kalir(d,e);
 ELSIF kod='IS.BAGLANTI_DUZELTTIM' THEN p=motor.kayit(d,'isler',(kapi.hedefler(e,'IS'))[1]); s=p||(g->'degisenler'); RETURN irp.dogru(p) AND p->>'durum'<>'IPTAL' AND s->>'nereye' IN ('PROJE','PROJE_DISI') AND kapilar_v5.proje_etap(d,s) AND (s->>'nereye'<>'PROJE_DISI' OR k6.kod_aktif(d,'PD',s->>'kategori'));
 ELSIF kod='IS.IPTAL_ETTIM' THEN RETURN coalesce(motor.kayit(d,'isler',(kapi.hedefler(e,'IS'))[1])->>'durum'<>'IPTAL',false);
 ELSIF kod='TATIL.KALDIRDIM' THEN RETURN motor.oku(d,'tatiller','[]') ? (g->>'tarih') AND saat.gun(g->>'tarih')>saat.gun(e->>'oldugu_an');
 END IF; RETURN NULL; END $$;
CREATE FUNCTION kapilar_v5.ek_denetim(d text,e jsonb) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE kod text=e->>'eylem_kodu'; g jsonb=e->'girdiler'; t timestamptz=saat.an(e->>'oldugu_an'); s jsonb; i jsonb; x jsonb; graf jsonb='{}'; k text; altlar text[]; yeni boolean; v timestamptz; BEGIN
 IF kod='BIRIM.TANIMLADIM' THEN s=motor.kayit(d,'birimler',g->>'kod'); IF irp.dogru(s) AND s->'tur'<>g->'tur' THEN RETURN false; END IF;
  FOR k,x IN SELECT * FROM motor.satirlar(d,'birimler') LOOP graf=graf||jsonb_build_object(k,CASE WHEN irp.dogru(x->'ust_birim') THEN jsonb_build_array(x->'ust_birim') ELSE '[]'::jsonb END); END LOOP;
  graf=graf||jsonb_build_object(g->>'kod',CASE WHEN irp.dogru(g->'ust_birim') THEN jsonb_build_array(g->'ust_birim') ELSE '[]'::jsonb END); RETURN kapilar_v3.dongusuz(graf);
 END IF;
 IF kod='IS.DEGISTIRDIM' THEN i=motor.kayit(d,'isler',(kapi.hedefler(e,'IS'))[1]); s=g->'degisenler';
  IF NOT irp.dogru(i) OR i->>'durum' IN ('BITTI','IPTAL') OR EXISTS(SELECT FROM jsonb_object_keys(s) a WHERE a<>ALL(ARRAY['islem','tahmini_sure_dk','teslim_tarihi','tezgah','tezgah_rolu','on_isler','onay_gerekli','onay_beklet','yetkinlik'])) OR NOT kapilar_v5.is_basvurulari(d,i||s) OR i->>'durum'='ONAY_BEKLIYOR' AND s ?| ARRAY['onay_gerekli','onay_beklet'] THEN RETURN false; END IF;
  IF EXISTS(SELECT FROM motor.satirlar(d,'isler') WHERE hal->'ana_is'=i->'kimlik' AND hal->>'durum' IN ('BITTI','IPTAL','ONAY_BEKLIYOR')) THEN RETURN false; END IF;
  IF s ? 'on_isler' THEN SELECT array_agg(anahtar) INTO altlar FROM motor.satirlar(d,'isler') WHERE anahtar=i->>'kimlik' OR hal->'ana_is'=i->'kimlik'; yeni=NOT coalesce(i->'on_isler','[]') @> (s->'on_isler');
   IF yeni AND (EXISTS(SELECT FROM motor.satirlar(d,'kisi_durumu') WHERE hal->>'acik_is'=ANY(altlar)) OR EXISTS(SELECT FROM jsonb_array_elements(motor.oku(d,'araliklar','[]')) a WHERE a->>'is'=ANY(altlar) AND a->>'kova' IN ('CALISMA','YENIDEN_ISLEME'))) THEN RETURN false; END IF;
   FOR k,x IN SELECT * FROM motor.satirlar(d,'isler') LOOP graf=graf||jsonb_build_object(k,CASE WHEN k=ANY(altlar) THEN s->'on_isler' ELSE coalesce(x->'on_isler','[]') END); END LOOP;
   IF EXISTS(SELECT FROM jsonb_array_elements_text(s->'on_isler') p WHERE NOT graf ? p) OR NOT kapilar_v3.dongusuz(graf) THEN RETURN false; END IF;
  END IF;
 END IF;
 IF kod='GOREV.DEGISTIRDIM' THEN s=motor.kayit(d,'gorevler',(kapi.hedefler(e,'GOREV'))[1])||(g->'degisenler'); FOREACH k IN ARRAY ARRAY['kisi','onaylayan'] LOOP IF g->'degisenler' ? k AND irp.dogru(s->k) AND NOT kapilar_v5.aktif_kisi(d,s->>k) THEN RETURN false; END IF; END LOOP; END IF;
 IF kod='ETAP.DEGISTIRDIM' AND (NOT irp.dogru(motor.kayit(d,'etaplar',(kapi.hedefler(e,'ETAP'))[1])) OR EXISTS(SELECT FROM jsonb_object_keys(g->'degisenler') a WHERE a<>ALL(ARRAY['ad','baslangic','bitis','hedef_saat','sorumlu']))) THEN RETURN false; END IF;
 IF kod='AYAR.MAAS_PAYDASI' THEN v=coalesce(saat.an(g->>'gecerli_baslangic'),t); RETURN (g->>'deger')::numeric>0 AND extract(day FROM v AT TIME ZONE 'Europe/Istanbul')=1 AND v=saat.gun_ani(saat.gun(saat.kodla(v))) AND date_trunc('month',v AT TIME ZONE 'Europe/Istanbul')>date_trunc('month',t AT TIME ZONE 'Europe/Istanbul'); END IF;
 RETURN true; END $$;
RESET ROLE;
