"""Yeni Sibernetik kurulumu için veri; eski kurulumlar otomatik değiştirilmez."""


def parca_turu():
    asamalar = ['SIPARIS_VERILMELI','SIPARISTE','FASONDA','GELDI','ISLEMDE','KALITE_ONAYLI','MONTAJA_HAZIR','MONTAJDA']
    by = ['BEYAZ_YAKA','YONETICI']; ey = ['EKIP_LIDERI','YONETICI']; eby = ['EKIP_LIDERI','BEYAZ_YAKA','YONETICI']
    yollar = [('SIPARIS_VERILMELI','SIPARISTE',by),('SIPARISTE','GELDI',by),
              ('GELDI','ISLEMDE',['EKIP_LIDERI']),('ISLEMDE','KALITE_ONAYLI',['EKIP_LIDERI']),
              ('KALITE_ONAYLI','MONTAJA_HAZIR',ey),('MONTAJA_HAZIR','MONTAJDA',['EKIP_LIDERI']),
              ('SIPARIS_VERILMELI','MONTAJA_HAZIR',['YONETICI']),
              ('SIPARIS_VERILMELI','ISLEMDE',ey),('SIPARIS_VERILMELI','FASONDA',by),
              ('FASONDA','GELDI',by),('ISLEMDE','FASONDA',eby),('FASONDA','ISLEMDE',eby)]
    return dict(kod='PARCA',ad='Parça',asamalar=[dict(kod=k,son=k=='MONTAJDA') for k in asamalar],
                baslangic_asamasi=asamalar[0],gecisler=[dict(den=a,e=b,kimler=r,kapsam='FIRMA') for a,b,r in yollar],
                baglanabilir_turler=['PROJE','NESNE'],acabilenler=dict(kimler=by,kapsam='FIRMA'))


SIBERNETIK_EKLERI = {
    'rol_katalogu': {'MALIYET': 'Tezgâh saat ücretini görür. Maaş ve kişi bazında tutar görmez.'},
    'birim_rolleri': {'PLANLAMA': {'ekip_yoneticisi': ['MALIYET']}},
    'kod_listeleri': {'YETKINLIK': []},
}
