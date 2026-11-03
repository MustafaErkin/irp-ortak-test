"""T10 olayları ve ayrı modül kapısının JSON alan sözleşmesi."""
from copy import deepcopy


def genislet(s):
    metin={'type':'string'}; dolu=dict(metin,minLength=1); zaman=dict(metin,format='date-time')
    plan={k:dict(zaman,type=['string','null']) for k in ('planlanan_baslangic','planlanan_bitis')}
    for kod,alan in [('IS.TANIMLADIM','isler'),('GOREV.ATADIM','gorevler')]:
        s[kod]['girdi_semasi']['properties'][alan]['items']['properties'].update(deepcopy(plan))
    s['IS.PLANSIZ_TANIMLADIM']['girdi_semasi']['properties'].update(deepcopy(plan))
    s['NESNE_TURU.TANIMLADIM']['girdi_semasi']['properties']['surum_onaylayanlar']={
        'type':['object','null'],'properties':{'kimler':{'type':'array','uniqueItems':True,'items':dolu},'kapsam':{'enum':['BIRIM','FIRMA']}}}
    alanlar={
        'PLAN.TARIHLEDIM':dict(hedefler={'type':'array','minItems':1,'items':{'type':'object',
            'required':['tur','kimlik','planlanan_baslangic','planlanan_bitis'],
            'properties':dict(tur={'enum':['IS','GOREV']},kimlik=dolu,planlanan_baslangic=zaman,planlanan_bitis=zaman)}},kaynak=metin,gerekce=metin),
        'NESNE.SURUM_EKLEDIM':dict(hedef=dolu,dosyalar={'type':'array','minItems':1,'uniqueItems':True,'items':dolu},surum_adi={'type':['string','null']},aciklama=metin),
        'NESNE.SURUM_ONAYLADIM':dict(hedef=dolu,surum_no={'type':'integer','minimum':1},gerekce=metin),
        'NESNE.SURUM_GERI_CEKTIM':dict(hedef=dolu,surum_no={'type':'integer','minimum':1},gerekce=dolu),
        'MODUL.TANIMLADIM':dict(kod=dolu,ad=dolu,servis_kimligi=dolu,aktif={'type':'boolean'}),
    }
    for kod,props in alanlar.items():
        s[kod]['girdi_semasi']['properties']=props
        s[kod]['yazabilen']='T10: yetki tablosu ve sabit ilişkiler; canlı hedef sürümü zorunlu.'
        if kod.startswith('NESNE.SURUM_'): s[kod]['zorunlu_hedef_turu']='NESNE'


def kapi_semasi():
    metin={'type':'string','minLength':1}
    kayit={'type':'object','required':['tur','kimlik'],'properties':dict(tur={'enum':['PROJE','IS','GOREV','NESNE']},kimlik=metin,modul_kaydi={'type':'string'})}
    alici={'type':'object','required':['tur','kimlik'],'properties':dict(tur={'enum':['KISI','BIRIM_YONETICILERI','ROL','PROJEDE_YETKILILER','NESNE_SORUMLUSU']},kimlik=metin)}
    props=dict(servis_kimligi=metin,modul=metin,kural=metin,kayit=kayit,an={'type':'string','format':'date-time'})
    ortak=list(props)
    return dict(olay_degil=True,bicim_surumu=4,adim_turu='modul_bildirimi',
        birak=dict(type='object',required=ortak+['alicilar','metin','onem'],properties=dict(props,alicilar={'type':'array','minItems':1,'items':alici},metin=metin,onem={'enum':['BILGI','UYARI']})),
        kaldir=dict(type='object',required=ortak,properties=props))
