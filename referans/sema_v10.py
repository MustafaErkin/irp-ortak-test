"""Karar 91–92 olay alanları. İlişkisel kapılar modelde denetlenir."""
def genislet(s):
    def g(k): return s[k]['girdi_semasi']
    g('IS.ARIZA_BILDIRDIM')['properties'].update(neden={'type':'string'},not_={'type':'string'})
    g('IS.ARIZA_BILDIRDIM')['properties'].pop('not_',None)
    g('IS.ARIZA_BILDIRDIM')['properties']['not']={'type':'string'}
    g('IS.ARIZA_BILDIRDIM')['anyOf']=[{'required':['neden']},{'required':['not']}]
    g('ETAP.TANIMLADIM')['properties']['sorumlu']={'type':['string','null']}
    g('ETAP.DEGISTIRDIM')['properties']['degisenler'].setdefault('properties',{})['sorumlu']={'type':['string','null']}
    a=g('AYAR.DEGISTIRDIM')['properties']['anahtar']
    if 'enum' in a and 'sessiz_kabul_is_gunu' not in a['enum']: a['enum'].append('sessiz_kabul_is_gunu')
    for k in ('ETAP.TANIMLADIM','ETAP.DEGISTIRDIM'):
        s[k]['yazabilen']='YETKILI ve kök yönetimi; yetki tablosuyla PROJE_SORUMLUSU veya rol devri. UYELER ise olay anında proje yetkisi de gerekli.'
    s['PLAN.ONAYLADIM']['yazabilen']='Yeni kurulum: proje sorumlusu/üstleri veya YETKILI. Eski ortak veri v9 tablosuna sabittir.'
    for k in ('PROJE.ERISIM_VERDIM','PROJE.ERISIM_KALDIRDIM'):
        s[k]['yazabilen']='UYELER: projede_yetkili sabit ilişkisi. Ek erişim yönetim yetkisi değildir.'
