from .ortak import Duzenek,t,is_id,yaz,s1

def isaret(f,hedef,kim='K009',zaman=None,gerekce='Yanlis basildi'):
    return f.olay(kim,'KAYIT.GECERSIZ_SAYDIM',zaman or t(22,'11:44'),girdiler={'hedef':hedef,'gerekce':gerekce},duzelttigi_olay=hedef)

def iki_kisi():
    f=Duzenek()
    g=f.olay('K004','IS.TANIMLADIM',t(22,'08:00'),girdiler={'isler':[{'islem':'Govde kaynagi','parca_kodu':'2509084_07_04-70','proje':'2509084','nereye':'PROJE','birim':'IMALAT','etap':f.etap['E-IML'],'tur':'SURELI','tahmini_sure_dk':180,'kisi_sayisi':2,'onay_gerekli':True}]})
    f.olay('K009','IS.ATADIM',t(22,'08:05'),g,{'kisiler':['K017','K023'],'sira':1})
    for kisi,alt,bas,bit in [('K017',g+'/k1','08:10','11:40'),('K023',g+'/k2','08:12','12:45')]:
        f.is_olay('MESAI.GIRDIM','07:58',kisi=kisi)
        f.is_olay('BASLADIM',bas,alt,kisi); f.is_olay('DEVAM_ETTIM','10:15',alt,kisi)
        if kisi=='K023': f.is_olay('DEVAM_ETTIM','12:31',alt,kisi)
        f.is_olay('TAMAMLADIM',bit,alt,kisi)
    f.is_olay('ONAYLADIM','12:50',g+'/k1','K009'); f.is_olay('ONAYLADIM','12:55',g+'/k2','K009')
    return f,g

def iptal_gorev():
    f=Duzenek(); g=f.gorev_ata(t(26,'09:00'),ad='Montaj resmi seti',teslim_tarihi='2026-10-30',zaman_degeri=20,zorluk=3,onay_gerekli=True,onaylayan='K012')
    f.gorev_olay('KABUL_ETTIM',t(26,'09:30'),g); o=f.gorev_olay('TAMAMLADIM',t(28,'10:00'),g)
    f.gorev_olay('IPTAL_ETTIM',t(28,'11:00'),g,'K012')
    return f,g,o

def s12_veri():
    f=Duzenek()
    for saat,kabul,teslim,proje,kat in [(81,1,'2026-10-30','2509084',None),(12,5,'2026-10-09','2509091',None),(60,22,'2026-11-05','2509091',None),(16,12,'2026-10-16',None,'PD.IDARI_MALI')]:
        g=f.gorev_ata(t(kabul,'08:00'),zaman_degeri=saat,teslim_tarihi=teslim,proje=proje,kategori=kat,nereye='PROJE' if proje else 'PROJE_DISI')
        f.gorev_olay('KABUL_ETTIM',t(kabul,'09:00'),g)
    return f

def kisi_degisim():
    f=Duzenek(); g=f.gorev_ata(proje='2509091',teslim_tarihi='2026-11-05',zaman_degeri=60,zorluk=5)
    f.gorev_olay('KABUL_ETTIM',t(22,'08:05'),g)
    f.gorev_olay('DEGISTIRDIM',t(28,'09:00'),g,'K012',degisenler={'kisi':'K044'})
    f.gorev_olay('KABUL_ETTIM',t(28,'10:00'),g,'K044')
    return f,g
