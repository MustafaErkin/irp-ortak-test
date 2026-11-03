SET ROLE irp_sahibi;
CREATE FUNCTION okuma.maliyet_izi_ekle(izler jsonb,tur text,k text,p text,tarih text,sa numeric,alan text,tutar numeric,emek boolean) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
#variable_conflict use_column
DECLARE key text=jsonb_build_array(tur,k,p,tarih)::text; x jsonb; BEGIN
 x=coalesce(izler->key,jsonb_build_object('tur',tur,'kimlik',k,'proje',p,'gun',tarih,'emek_saat',0,'iscilik',0,'tezgah',0,'maas',0));
 IF emek THEN x=okuma.ekle(x,'emek_saat',sa); END IF;
 IF tutar IS NULL OR x->>alan='VERI_EKSIK' THEN x=x||jsonb_build_object(alan,'VERI_EKSIK'); ELSE x=okuma.ekle(x,alan,tutar); END IF;
 RETURN izler||jsonb_build_object(key,x); END $$;
CREATE FUNCTION okuma.maliyet_izleri(bas text,bit_ text) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE r jsonb='{}'; a jsonb; g jsonb; m jsonb; paylar jsonb; maaslar jsonb='{}'; p timestamptz; q timestamptz; son timestamptz; sa numeric; oran numeric; alan text; t date; k text; kalem text; toplam numeric; BEGIN
 FOR a IN SELECT value FROM jsonb_array_elements(okuma.tablo('araliklar')) LOOP
  IF a->>'kova' NOT IN ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY','TEZGAH') OR a->>'is' IS NULL THEN CONTINUE; END IF;
  p=greatest(saat.an(a->>'baslangic'),saat.gun_ani(saat.gun(bas))); son=least(coalesce(saat.an(a->>'bitis'),saat.simdi()),saat.gun_ani(saat.gun(bit_)+1));
  WHILE p<son LOOP
   t=saat.gun(saat.kodla(p)); q=least(son,saat.gun_ani(t+1)); sa=extract(epoch FROM q-p)/3600; alan=CASE WHEN a->>'kova'='TEZGAH' THEN 'tezgah' ELSE 'iscilik' END;
   oran=CASE WHEN alan='tezgah' THEN okuma.tutar_bul(a->>'tezgah','SAAT_UCRETI',t::text,0) ELSE okuma.saat_maliyeti(a->>'kisi',t::text) END;
   r=okuma.maliyet_izi_ekle(r,'IS',a->>'is',a->>'proje',t::text,sa,alan,sa*oran,a->>'kova' IN ('CALISMA','YENIDEN_ISLEME')); p=q;
  END LOOP;
 END LOOP;
 FOR g IN SELECT x FROM okuma.satirlar('gorevler') LOOP
  kalem=coalesce(g->>'proje',g->>'kategori','BELIRSIZ'); IF g->>'durum'='IPTAL' THEN kalem='iptal:'||kalem; ELSIF g->>'tur'='REVIZYON' THEN kalem='revizyon:'||kalem; END IF;
  -- Aynı görevin bütün günleri bir kez hesaplanır; gün başına yeniden takvim taranmaz.
  paylar=CASE WHEN g->>'tur' IN ('NOT','ONAY') THEN '[]'::jsonb ELSE okuma.gorev_gunluk_paylar(g) END;
  FOR t IN SELECT okuma.gunler(bas,bit_) LOOP
   FOR k IN SELECT g->>'kisi' UNION SELECT x->>'kisi' FROM jsonb_array_elements(coalesce(g->'kisi_gecmisi','[]')) x LOOP
    IF g->>'tur' IN ('NOT','ONAY') THEN sa=okuma.gorev_payi(g,t::text,t::text,false,k);
    ELSE SELECT coalesce(sum((z->>'saat')::numeric),0) INTO sa FROM jsonb_array_elements(paylar) z WHERE z->>'gun'=t::text AND z->>'kisi'=k; END IF;
    IF sa=0 THEN CONTINUE; END IF;
    IF NOT maaslar ? k THEN maaslar=maaslar||jsonb_build_object(k,okuma.maas_dagilimi(k,bas)); END IF; m=maaslar->k; toplam=coalesce((m->'paylar'->>kalem)::numeric,0);
    oran=CASE WHEN m->'tutarlar'->>kalem='VERI_EKSIK' THEN NULL WHEN toplam=0 THEN 0 ELSE coalesce((m->'tutarlar'->>kalem)::numeric,0)*sa/toplam END;
    r=okuma.maliyet_izi_ekle(r,'GOREV',g->>'kimlik',g->>'proje',t::text,sa,'maas',oran,true);
   END LOOP;
  END LOOP;
 END LOOP;
 RETURN (SELECT coalesce(jsonb_agg(value ORDER BY value->>'tur' COLLATE "C",value->>'kimlik' COLLATE "C",coalesce(value->>'proje','None') COLLATE "C",value->>'gun'),'[]') FROM jsonb_each(r)); END $$;
RESET ROLE;
