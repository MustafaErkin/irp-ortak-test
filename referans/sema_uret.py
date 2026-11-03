"""T2/T3/T4 v4 olay sozlesmesini ve kanonik ozet orneklerini dondurur."""
import json
from pathlib import Path
from copy import deepcopy
from irp.olay import EYLES, kodla
from irp.kabul import TANIKLIK
from irp.yetki_v6 import varsayilan_yetkiler
from irp.surum import is_alanlari, ozet

KOK=Path(__file__).resolve().parent
P=KOK/'cevap_anahtari'

def yaz(ad,x): (P/ad).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n','utf-8')

def uret():
    metin={'type':'string'}; bos_metin={'type':['string','null']}
    tarih={'type':'string','format':'date'}; an={'type':'string','format':'date-time'}
    kisi={'type':'string','pattern':'^K[0-9]{3}$'}
    mantik={'type':'boolean'}; poz={'type':'integer','minimum':1}
    zaman={'type':['string','null'],'description':'ISO 8601 + saat dilimi; tarih tek basina ise yerel 00:00. Bos AYAR icin olay ani, TAKVIM icin ertesi gun 00:00.'}
    onkosul={'type':'array','items':{'oneOf':[metin,{'type':'object','required':['satir'],'properties':{'satir':poz},'additionalProperties':False}]}}
    alan={k:deepcopy(metin) for k in ('ad','kod','birim','basi','ust_birim','tur','nereye','proje','etap','kategori','islem','is_tanimi','parca_kodu','tezgah','tezgah_rolu','neden','hedef','gerekce','metin','not','aciklama')}
    for k in ('kisi','kimden','kime','onaylayan','sebep_olan'): alan[k]=kisi
    for k in ('onay_gerekli','onay_beklet','dosya_gerekli','is_bitti','revizyon_ver','sorun_kaynakli','aktif'): alan[k]=mantik
    for k in ('sira','yeni_sira','kime_sira','kisi_sayisi','zaman_degeri'): alan[k]=poz
    for k in ('tarih','teslim_tarihi','yeni_teslim_tarihi','giris_tarihi','ayrilis_tarihi'): alan[k]=tarih
    for k in ('baslangic','bitis'): alan[k]={'type':'string','description':'Etapta YYYY-MM-DD; elle surede saat dilimli ISO 8601 an.'}
    alan.update(gecerli_baslangic=zaman,teslim_saati=bos_metin,degisenler={'type':'object'},
                tahmini_sure_dk={'type':'integer','minimum':0},hedef_saat={'type':'integer','minimum':0},
                zorluk={'type':'integer','minimum':1,'maximum':5},deger={'type':'number','minimum':0,'maximum':1},
                kisiler={'type':'array','minItems':1,'items':kisi},
                roller={'type':'array','uniqueItems':True,'items':metin},
                kimler={'type':'array','uniqueItems':True,'items':metin},
                kapsam={'enum':['BIRIM','FIRMA']},liste={'enum':['ARIZA','MOLA','PD','ROL']},
                eylem_kodu={'enum':sorted(EYLES)},iptal=mantik,
                yaka={'enum':['MAVI','BEYAZ']},etiketler={'type':'array','items':metin},
                on_isler=onkosul,on_kosul=onkosul,kimden_yeni_is=metin,
                mesai_baslangic=metin,mesai_bitis=metin,
                calisma_gunleri={'type':'array','items':{'type':'integer','minimum':1,'maximum':7}},
                sabit_molalar={'type':'array','items':{'type':'object','required':['ad','bas','bit'],'properties':{'ad':metin,'bas':metin,'bit':metin}}})
    gorev_zor=['ad','nereye','teslim_tarihi','zaman_degeri','zorluk','kisi','onay_gerekli','dosya_gerekli']
    satir_alanlari=('ad nereye proje etap kategori islem is_tanimi parca_kodu tur tezgah tezgah_rolu tahmini_sure_dk teslim_tarihi teslim_saati kisi_sayisi onay_gerekli on_isler birim zaman_degeri zorluk kisi onaylayan dosya_gerekli on_kosul sorun_kaynakli').split()
    satir={'type':'object','properties':{k:alan[k] for k in satir_alanlari},'additionalProperties':True,
           'allOf':[{'if':{'properties':{'nereye':{'const':'PROJE_DISI'}},'required':['nereye']},'then':{'required':['kategori']}}]}
    gorev=deepcopy(satir); gorev['required']=gorev_zor
    gorev['allOf'].append({'if':{'properties':{'onay_gerekli':{'const':True}},'required':['onay_gerekli']},'then':{'required':['onaylayan']}})
    satir['properties']['onay_beklet']=mantik
    satir['allOf'].append({'if':{'properties':{'onay_gerekli':{'const':True}},'required':['onay_gerekli']},'then':{'required':['onay_beklet']}})
    alan['isler']={'type':'array','minItems':1,'items':satir}
    alan['gorevler']={'type':'array','minItems':1,'items':gorev}
    eylem_alanlari={
        'IS.ATADIM':'kisi kisiler sira kisi_sayisi','IS.SIRALADIM':'kisi yeni_sira',
        'IS.DEVRETTIM':'kimden kime kime_sira kimden_yeni_is',
        'IS.PLANSIZ_TANIMLADIM':'nereye proje etap kategori is_tanimi tur onay_gerekli onay_beklet kisi sira birim tahmini_sure_dk teslim_tarihi',
        'IS.ARIZA_BILDIRDIM':'neden not','IS.SURE_EKLEDIM':'baslangic bitis aciklama is_bitti',
        'GOREV.REDDETTIM':'not sebep_olan revizyon_ver yeni_teslim_tarihi zaman_degeri kime',
        'GOREV.DEGISTIRDIM':'degisenler gerekce','NOT.YAZDIM':'metin etiketler',
        'AYAR.ONAY_ORANI':'deger gecerli_baslangic',
        'TAKVIM.TANIMLADIM':'gecerli_baslangic mesai_baslangic mesai_bitis calisma_gunleri sabit_molalar',
        'TATIL.EKLEDIM':'tarih ad gecerli_baslangic','BIRIM.TANIMLADIM':'kod ad tur basi ust_birim',
        'PROJE.ACTIM':'kod ad teslim_tarihi musteri aktif',
        'TEZGAH.TANIMLADIM':'kod ad birim aktif',
        'AYAR.MAAS_PAYDASI':'deger gecerli_baslangic',
        'AYAR.PARCA_KODU_DESENI':'deger gecerli_baslangic',
        'KISI.AYRILDI':'kisi ayrilis_tarihi iptal',
    }
    alan['musteri']=metin
    semalar={}
    for kod,zor in EYLES.items():
        isimler=eylem_alanlari.get(kod,' '.join(zor)).split()
        girdi={'type':'object','properties':{k:deepcopy(alan.get(k,metin)) for k in isimler},'additionalProperties':True}
        if zor: girdi['required']=list(zor)
        if kod=='AYAR.SAAT_KAYDIRDIM': girdi['properties']['hedef']=an
        if kod=='AYAR.MAAS_PAYDASI': girdi['properties']['deger']={'type':'number','exclusiveMinimum':0}
        if kod=='AYAR.PARCA_KODU_DESENI': girdi['properties']['deger']={'type':'string'}
        if kod=='BIRIM.TANIMLADIM':
            girdi['properties']['basi']=bos_metin; girdi['properties']['ust_birim']=bos_metin
        if kod=='IS.PLANSIZ_TANIMLADIM':
            girdi['allOf']=[{'if':{'properties':{'onay_gerekli':{'const':True}},'required':['onay_gerekli']},'then':{'required':['onay_beklet']}}]
        if kod=='MAAS.GUNCELLEDIM': girdi['properties']['kisi']=dict(metin,description='Kisi ya da tezgah kodu; tutar hassas ekte.')
        if kod=='KISI.AYRILDI':
            girdi['oneOf']=[{'required':['ayrilis_tarihi'],'not':{'properties':{'iptal':{'const':True}},'required':['iptal']}},
                            {'required':['iptal'],'properties':{'iptal':{'const':True}},'not':{'required':['ayrilis_tarihi']}}]
        if kod=='IS.BAGLANTI_DUZELTTIM':
            girdi['properties']['degisenler']={'type':'object','minProperties':1,'properties':{k:alan[k] for k in ('nereye','proje','etap','parca_kodu','kategori')},'additionalProperties':False}
            for k in ('proje','etap','parca_kodu','kategori'): girdi['properties']['degisenler']['properties'][k]=bos_metin
        if kod=='IS.DEGISTIRDIM':
            girdi['properties']['degisenler']={'type':'object','minProperties':1,'not':{'anyOf':[{'required':[k]} for k in ('nereye','proje','etap','parca_kodu','kategori')]}}
        if kod=='IS.ATADIM': girdi['anyOf']=[{'required':['kisi']},{'required':['kisiler']}]
        if kod=='GOREV.REDDETTIM':
            girdi['allOf']=[{'if':{'properties':{'revizyon_ver':{'const':True}}},'then':{'required':['yeni_teslim_tarihi','zaman_degeri','kime']}}]
        hedef='IS' if kod.startswith('IS.') and kod not in ('IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM') else 'GOREV' if kod.startswith('GOREV.') and kod!='GOREV.ATADIM' else None
        if kod in ('PROJE.DEGISTIRDIM','PROJE.KAPATTIM'): hedef='PROJE'
        if kod=='ETAP.DEGISTIRDIM': hedef='ETAP'
        semalar[kod]={'eylem_versiyonu':1,'sinif':'TANIKLIK' if kod in TANIKLIK else 'YONETIM',
                      'yazabilen':'T3 v5: sabit iliski VEYA olay anindaki yetki tablosu VEYA birim zincirinden miras; sabit guvenceler her zaman uygulanir.',
                      'girdi_semasi':girdi,'zorunlu_hedef_turu':hedef,
                      'tek_gorev_hedefi':kod in ('GOREV.TAMAMLADIM','GOREV.REDDETTIM','GOREV.DEGISTIRDIM','GOREV.IPTAL_ETTIM')}
    from sema_v7 import genislet
    genislet(semalar,alan)
    from sema_v9 import genislet as v9
    v9(semalar,alan)
    from sema_v10 import genislet as v10
    v10(semalar)
    from sema_v10_1 import genislet as v101, kapi_semasi
    v101(semalar)
    from sema_v10_2 import genislet as v102, kapi_semasi
    v102(semalar)
    yaz('modul_bildirimi_semasi.json',kapi_semasi())
    turler=['IS','GOREV','NOT','PARCA','PROJE','ETAP','KISI','TEZGAH','BIRIM','LISTE','NESNE']
    olay={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'IRP T11 / başvuru v10.2 olay girişi',
          'type':'object','required':['olay_kimligi','eylem_kodu','eylem_versiyonu','neyin_ustunde','giris_sekli','kim','cihaz','uygulama_surumu','oldugu_an','saat_dilimi','bildigi_son_hal_ani','girdiler','kanit','yol'],
          'properties':{
              'olay_kimligi':{'type':'string','pattern':'^K[0-9]{3}-[0-9]{10}-[A-Z]$'},
              'eylem_kodu':{'enum':sorted(EYLES)},'eylem_versiyonu':{'const':1},
              'neyin_ustunde':{'type':'array','items':{'type':'object','required':['tur','kimlik'],
                  'properties':{'tur':{'enum':turler},'kimlik':metin,'surum':{'type':['string','null'],'pattern':'^[0-9a-f]{64}$'}}}},
              'giris_sekli':{'enum':['QR','LISTE','ELLE','AKTARIM']},'kim':kisi,'adina':{'type':['string','null']},
              'cihaz':metin,'uygulama_surumu':metin,'oldugu_an':an,'saat_dilimi':{'const':'+03:00'},
              'bildigi_son_hal_ani':an,'girdiler':{'type':'object'},
              'kanit':{'type':'array','items':{'type':'object','required':['dosya_kimligi','parmak_izi'],'properties':{'dosya_kimligi':metin,'parmak_izi':metin}}},
              'duzelttigi_olay':bos_metin,'yol':{'enum':['ATOLYE','DISARIDA']},'pc_ulasma_ani':bos_metin,
              'bulut_ulasma_ani':dict(an,readOnly=True,description='Sunucu gercek saati yazar; istemciden gelen deger ezilir.'),
              'kabul_sirasi':{'type':'integer','minimum':1,'readOnly':True,'description':'T10 olaylarinda sunucu atar; ayni andaki kabul sirasi.'},
              'nesne_surum_no':{'type':'integer','minimum':1,'readOnly':True,'description':'NESNE.SURUM_EKLEDIM kabulunde sunucu atar; yeniden hesapta degismez.'}},
          'eylem_semalari':semalar,'siniflar':{'TANIKLIK':{'cevrimdisi':True,'durum_uyusmazligi':'SUPHELI'},'YONETIM':{'cevrimdisi':False,'durum_uyusmazligi':'RED_DURUM','bayat_surumu':'RED_BAYAT'}},
          'varsayilan_yetki_tablosu':varsayilan_yetkiler(),
          'anlamsal_kurallar':[
              'JSON Schema bicimi denetler; rol, olay anindaki atama, durum, hafta ve liste surumu model/kabul.py ile denetlenir.',
              'Tanıklik yetkisi olay anina, yonetim yetkisi guncel hale gore. AKTARIM yalniz servis; tarihsel aktarimda durum/yetki kapisi uygulanmaz.',
              'LISTE kimligi kisi kodu; surumu sirali is kimlikleri dizisinin SHA-256 ozetidir. Devir iki listeyi tasir.',
              'Takvim ertesi gunun basindan veya sonraki gun basindan; tatil en erken yarin. Ayar bos gecerlilikte olay anindan.',
              'MAAS.GUNCELLEDIM tutari olayda bulunmaz; hassas_ek kabuluyla birlikte verilir.',
              'KAYIT.GECERSIZ_SAYDIM girdiler.hedef ile duzelttigi_olay esit olmalidir.'
              ,'Kurulumun son olayi KURULUM.TAMAMLADIM; rol listesi ve yetki tablosu olaylari zorunlu. Canlida kurulum sonrasi AKTARIM kapali.'
              ,'Kimse kendi isini/gorevini onaylayamaz. Maas ve yetki tablosu yalniz YETKILI; son yetkili kaldirilamaz.'
              ,'Rol kodlari ROL listesinden gelir. Bos kimler eylem-kapsam satirini kapatir; sabit iliskileri silmez.'
          ],'allOf':[]}
    for kod,s in semalar.items():
        sonra={'properties':{'girdiler':{'$ref':'#/eylem_semalari/'+kod+'/girdi_semasi'}}}
        if s['zorunlu_hedef_turu']:
            n={'contains':{'properties':{'tur':{'const':s['zorunlu_hedef_turu']}},'required':['tur']},'minContains':1}
            if s['tek_gorev_hedefi']: n['maxContains']=1
            sonra['properties']['neyin_ustunde']=n
        olay['allOf'].append({'if':{'properties':{'eylem_kodu':{'const':kod}},'required':['eylem_kodu']},'then':sonra})
    olay['allOf'].append({'if':{'properties':{'eylem_kodu':{'const':'NOT.YAZDIM'}},'required':['eylem_kodu']},
        'then':{'properties':{'neyin_ustunde':{'contains':{'properties':{'tur':{'enum':['PARCA','GOREV','PROJE','NESNE']}},'required':['tur']}}}}})
    olay['anlamsal_kurallar'].append('T11: yönetim kararı AKTARIM dahil dayandığı etkin kayıttan önce sıralanırsa RED(BAYAT, SIRA).')
    yaz('olay_semasi.json',olay)
    # Artik eski v2 eylem envanteri de yanlis zorunlu gecerlilik gostermesin.
    (KOK/'eylem_semalari.json').write_text(json.dumps(semalar,ensure_ascii=False,indent=2,sort_keys=True)+'\n','utf-8')
    ornekler=[[],['A','B'],{'ad':'İmalat','surum':'x','son_olay':'A','kural_versiyonu':4},
              {'ad':'Görev','zaman_degeri':20,'onay_gerekli':False,'kabul_ani':'2026-10-26T09:30:00+03:00','son_hesap_ani':'y'}]
    yaz('kanonik_ornekler.json',[{'girdi':x,'is_alanlari':is_alanlari(x),'kanonik_json':kodla(is_alanlari(x)),
                                'sha256':ozet(is_alanlari(x))} for x in ornekler])

if __name__=='__main__': uret()
