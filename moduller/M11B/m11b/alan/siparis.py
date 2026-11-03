"""M11A sağlayıcılarından gerçek başlangıç planı ve teknik girdi devri. T28/I05."""
from psycopg.types.json import Jsonb
import base64
from irp_sozlesme.baglanti import CekirdekHatasi
from . import yetki
from .hatalar import ModulHatasi


def kaynak(b, proje):
    with b.vt.islem() as c:
        return c.execute('SELECT * FROM mod_m11b.siparis_kaynagi WHERE proje=%s', (proje,)).fetchone()


def al(b, proje):
    """Donmuş kaynağı değiştirmez; tekrar aynı kaynağı döndürür. Kaynaksız proje devir olabilir."""
    p=b.proje(proje)
    yetki.gerek(yetki.sorumlu_ya_da_yetkili(b,p), 'Sipariş girdilerini proje sorumlusu veya yetkili aktarır.')
    if old:=kaynak(b,proje):
        return {'durum':'AKTARILDI','kaynak':old['kaynak'],'tekrar':True}
    try:
        plan=b.oku('M11A.BASLANGIC_PLANI',proje)
        girdiler=b.oku('M11A.TEKLIF_GIRDILERI',proje)
    except CekirdekHatasi as error:
        if error.tur=='BILGI_YOK':
            return {'durum':'KAYNAK_YOK','mesaj':'Bu proje için siparişten gelen teklif planı bulunmuyor.'}
        if error.tur=='SAGLAYICI_YOK':
            return {'durum':'SAGLAYICI_KAPALI','mesaj':'Sipariş bilgisi şu an alınamıyor; teklif planı aktarılmadı.'}
        raise
    if plan.get('proje')!=proje or girdiler.get('proje')!=proje or plan.get('kaynak')!=girdiler.get('kaynak'):
        raise ModulHatasi(409,'KAYNAK_DEGISTI','Sipariş planı ve teknik girdiler aynı kaynaktan gelmiyor.')
    if not isinstance(plan.get('etaplar'),list) or not plan.get('kaynak'):
        raise ModulHatasi(422,'KAYNAK_EKSIK','Sipariş planının kaynak bilgisi veya etapları eksik.')
    if girdiler.get('dosya_aktarimi_tamam') is False:
        raise ModulHatasi(409,'DOSYA_AKTARIMI_BEKLIYOR','Siparişin teknik dosya aktarımı henüz tamamlanmadı.')
    from . import dosya
    for document in girdiler.get('dosyalar',[]):
        ref=document['konum']
        with b.vt.islem() as c:
            if c.execute('SELECT 1 FROM mod_m11b.kaynak_dosyalari WHERE proje=%s AND kaynak=%s',(proje,ref)).fetchone():continue
        target={k:document.get(k) for k in ('ad','konum','parmak_izi')}
        if ref.startswith('irp-dosya:'):
            physical=b.oturum.dosya_oku(ref.removeprefix('irp-dosya:'))
            if document.get('parmak_izi')!=physical['parmak_izi']:raise ModulHatasi(409,'DOSYA_DEGISTI','Teknik dosyanın kaynağı doğrulanamadı.')
            uploaded=b.oturum.dosya_yukle({'tur':'PROJE','kimlik':proje},physical['ad'],
                base64.b64decode(physical['icerik_base64']),physical['tur'])
            target.update({k:uploaded[k] for k in ('ad','konum','parmak_izi')})
        with b.vt.islem() as c:
            c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(proje+':'+ref,))
            if c.execute('SELECT 1 FROM mod_m11b.kaynak_dosyalari WHERE proje=%s AND kaynak=%s',(proje,ref)).fetchone():continue
            local=dosya.dosya_ekle(b,proje,{'tur':'TASARIM_GIRDISI',**target},c=c)
            c.execute('INSERT INTO mod_m11b.kaynak_dosyalari VALUES(%s,%s,%s)',(proje,ref,local['kimlik']))
    with b.vt.islem() as c:
        c.execute('INSERT INTO mod_m11b.siparis_kaynagi VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(proje) DO NOTHING',
                  (proje,plan['kaynak'],Jsonb(plan),Jsonb(girdiler),b.kisi,b.simdi()))
    return {'durum':'AKTARILDI','kaynak':plan['kaynak'],'tekrar':False}


def gorunum(b,proje):
    b.proje(proje)
    row=kaynak(b,proje)
    if not row:
        return {'durum':'AKTARILMADI','plan':None,'girdiler':None}
    return {'durum':'AKTARILDI','kaynak':row['kaynak'],'plan':row['plan'],'girdiler':row['girdiler']}


def oneri(b,proje,sablon):
    row=kaynak(b,proje)
    if row is None:
        return None
    templates={s['kod']:s for s in sablon}
    heads={r['kimlik']:r.get('basi') for r in b.birimler}
    result=[]
    for stage in row['plan']['etaplar']:
        template=templates.get(stage.get('etap_kodu'),{})
        unit=template.get('varsayilan_birim')
        result.append({'islem':'TANIMLA','etap':None,'okunan_surum':None,'ad':stage['ad'],
          'birim':unit,'baslangic':stage['baslangic'],'bitis':stage['bitis'],'hedef_saat':0,
          'sorumlu':heads.get(unit),'sablon_kodu':template.get('kod'),
          'paralel_grup':stage.get('paralel_grup'),'tasarim_kapisi':bool(template.get('tasarim_kapisi'))})
    return result
