"""Ürün kaynakları ve açık kapsamlı test kanıtından yetenek envanteri üretir.

Eski paket kataloğunu veya donmuş referansı değiştirmez. Bir kapının kodda
bulunması, işlevin bütünüyle kabul edildiği anlamına gelmez.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
EVIDENCE=ROOT/'codex/sonuclar/cekirdek_yetenekleri/sql_kaniti.json'
LABELS={'DOGRULANDI':'Çalıştığı Doğrulandı','DOGRULANACAK':'Doğrulanacak / Sınırı Var','HENUZ_YOK':'Henüz Yapılmadı'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    reads={}; functions={}; dispatches={}
    for path in sorted((ROOT/'urun/veritabani').glob('[0-9][0-9][0-9]_*.sql')):
        source=path.read_text()
        for match in re.finditer(r'CREATE(?: OR REPLACE)? FUNCTION\s+([\w.]+)\(.*?AS \$\$(.*?)\$\$;',source,re.S):
            function,body=match.groups()
            location={'dosya':str(path.relative_to(ROOT)),'satir':source.count('\n',0,match.start())+1}
            if function.startswith('public.'):
                functions[function]=location
            if function=='public.oku':
                for name in re.findall(r"IF veri='([A-Z_]+)' THEN",body):
                    reads[name]={**location,'islev':function}
            if function not in ('okuma.oku','okuma.ek_oku','okuma.web_oku'):
                continue
            dispatches[function]=(body,location)
    for function,(body,location) in dispatches.items():
        for branch in re.finditer(r"WHEN\s+((?:'[^']+'\s*,?\s*)+)THEN",body):
            for name in re.findall(r"'([A-Z][A-Z0-9_]*)'",branch[1]):
                reads[name]={**location,'islev':function}
    return reads,functions


def evidence_matches(evidence, root=ROOT):
    """Yeni, eksik veya değiştirilmiş SQL ile eski kanıtı kullanma."""
    migrations=evidence.get('gocler',{})
    current={p.name:sha(p) for p in (root/'urun/veritabani').glob('[0-9][0-9][0-9]_*.sql')}
    focused=evidence.get('odak_kontrolleri',[])
    return bool(current and evidence.get('gocler_kaynakla_ayni') is True
                and migrations==current and focused and all(r.get('eslesti') is True for r in focused)
                and all(r.get('hata')==0 for r in evidence.get('web_okumalari',{}).values()))


def inventory():
    reads,functions=sources()
    old=json.loads((HERE/'cekirdek_katalogu.json').read_text())
    schemas=json.loads((ROOT/'referans/eylem_semalari.json').read_text())
    evidence=json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    available=evidence_matches(evidence)
    module_path=ROOT/'codex/sonuclar/modul_ortak_baglanti.json'
    module=json.loads(module_path.read_text()) if module_path.exists() else {}
    module_ok=available and module.get('durum')=='GECTI' and module.get('gocler')==evidence.get('gocler')
    triple_path=ROOT/'codex/sonuclar/moduller_mvp.json'
    triple=json.loads(triple_path.read_text()) if triple_path.exists() else {}
    triple_ok=available and triple.get('durum')=='GECTI' and triple.get('gocler')==evidence.get('gocler')
    checked=evidence.get('web_okumalari',{}) if available else {}
    focused={r['ad']:r for r in evidence.get('odak_kontrolleri',[]) if r['eslesti']} if available else {}
    rows=[]
    for name,source in sorted(reads.items()):
        observation=checked.get(name,{})
        called=bool(observation.get('cagri',0)>observation.get('hata',0) or focused.get(name,{}).get('sonuc')=='OK')
        rows.append({'ad':name,'kodda_mevcut':True,'kaynak':source,
                     'erisim':'cekirdek_web' if name.startswith('WEB_') else 'kullanici_okumasi',
                     'sql_kapi_cevabi_dogrulandi':called,
                     'kanit':str(EVIDENCE.relative_to(ROOT)) if called else None,
                     'eski_paket_katmani':old['okumalar'].get(name,{}).get('katman'),
                     'modul_islevi_kabul_edildi':False})
    action_rows=[]
    for name,schema in sorted(schemas.items()):
        action_rows.append({'ad':name,'sinif':schema.get('sinif'),
                            'surum':schema.get('eylem_versiyonu',1),
                            'semada_tanimli':True,
                            'sql_sozlugunde_dogrulandi':name in evidence.get('tanimli_eylemler',[]) if available else False,
                            'bu_kosuda_basarili_is_olayi':evidence.get('basarili_olaylar',{}).get(name,0) if available else 0,
                            'paket_modulden_yazmayi_yasakliyor':name in old['kurulum_eylemleri'] or any(
                                name==pattern or pattern.endswith('.*') and name.startswith(pattern[:-1])
                                for pattern in old['cekirdek_ekrani']+old['mavi_yaka_dugmeleri'])})
    capabilities=json.loads((HERE/'yetenek_tanimlari.json').read_text())
    for row in capabilities:
        if row['durum'] not in LABELS or not set(row.get('okumalar',[]))<=set(reads):
            raise ValueError('Geçersiz yetenek tanımı: '+row['kod'])
        if (not available or row['kod'] in ('C14','C15','C20','C21') and not module_ok or
                row['kod'] in ('C19','C22','C24') and not triple_ok) and row['durum']=='DOGRULANDI':
            row['durum']='DOGRULANACAK'
            row['kapsam']+=' Güncel SQL kanıtı yok; önceki sonuç mevcut ürün için yeniden doğrulanmalı.'
        row['temel_sql_okumasi_kaniti']=[r['ad'] for r in rows if r['ad'] in row.get('okumalar',[]) and r['sql_kapi_cevabi_dogrulandi']]
    source_paths=['tasarim/00_kararlar.md','tasarim/18_modul_sozlesmesi.md','tasarim/16_okumalar.md',
                  'referans/eylem_semalari.json','modul_kiti/cekirdek_katalogu.json',
                  'modul_kiti/yetenek_tanimlari.json','modul_kiti/yetenek_denetle.py',
                  'istemci/web/erp.js','istemci/web/test/tarayici.py','istemci/web/test/yerel_api.py',
                  *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'urun/veritabani').rglob('*.sql'))]]
    source_paths=sorted(set(source_paths)|{name for row in capabilities for name in row['kaynaklar'] if (ROOT/name).exists()})
    return {'bicim_surumu':1,'uretildi':datetime.now().isoformat(timespec='seconds'),
            'urun_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'kaynak_sirasi':['Mustafa ve müşteri kararları / şartname: gereken davranış',
                            'Ortak iskeletin üç sunumu: işleyiş niyeti; sonraki kararlarla birlikte',
                            'Mevcut sözleşme: sınırlar ve sahiplik','Ürün SQL ve istemci kodu: uygulanmış yol',
                            'Gerçek SQL / canlı test kanıtı: doğrulanmış kapsam','Eski katalog ve modül istekleri: karşılaştırılacak beyan'],
            'uyari':'Bu envanter ürünün tamamının veya gelen modüllerin kabul belgesi değildir. SQL kapısı ve işlev kabulü ayrıdır.',
            'sql_kaniti_kaynakla_eslesiyor':bool(available),
            'modul_pilotu_sql_kaynagiyla_eslesiyor':bool(module_ok),
            'modul_pilotu_kaniti':str(module_path.relative_to(ROOT)) if module_ok else None,
            'sql_kaniti_ozeti':{'web_okuma_turu':len(checked),
                               'basarili_olay_turu':len(evidence.get('basarili_olaylar',{})) if available else 0,
                               'odak_kontrolu':len(evidence.get('odak_kontrolleri',[])) if available else 0,
                               'gantt':focused.get('GANTT'), 'plan':focused.get('PLAN')},
            'kaynak_ozetleri':{name:sha(ROOT/name) for name in source_paths},
            'yetenekler':capabilities,'okumalar':rows,'eylemler':action_rows,
            'public_kod_kapilari':functions,'test_public_kapilari':evidence.get('public_kapilar',[]) if available else [],
            'eski_katalog_farki':{'urun_yonlendirmesinde_olup_katalogda_olmayan':sorted(set(reads)-set(old['okumalar'])),
                                  'katalogda_olup_urun_yonlendirmesinde_olmayan':sorted(set(old['okumalar'])-set(reads))},
            'gelen_moduller':{p.name:{'kunye_sha256':sha(p/'kunye.json'),
                           'cekirdek_okumalari':[n for n in json.loads((p/'kunye.json').read_text())['kapilar']['okumalar'] if n in reads],
                           'moduller_arasi_okumalari':[n for n in json.loads((p/'kunye.json').read_text())['kapilar']['okumalar'] if '.' in n]}
                              for p in sorted((ROOT/'disaridan_moduller/Modules').glob('m*')) if (p/'kunye.json').exists()}}


def document(data):
    counts=Counter(r['durum'] for r in data['yetenekler'])
    lines=['# Çekirdeğin Gerçek Yetenek Durumu','',
           data['uretildi'][:10]+' · Modül standardı güncel envanteri · Ürün kaynağı: `'+data['urun_commit'][:7]+'`','',
           '**Kaynak:** Önce Mustafa/müşteri kararları ve mevcut sözleşme; uygulama için ürün SQL/istemci kodu; '
           'kanıt için ayrı gerçek PostgreSQL firması ve kapsamı belirtilen önceki canlı sınamalar. '
           'Eski katalog ve gelen modül notları uygulamanın kanıtı sayılmaz.','',
           '**Durumların anlamı:** “Doğrulandı” yalnız satırda belirtilen davranış içindir. '
           '“Doğrulanacak” çalışan temel yolun yanında açık sınır veya kabul ihtiyacı olduğunu da kapsar. '
           '“Henüz yapılmadı” ortak ürün yolunun bulunmadığı anlamına gelir; kaynak kodda adı geçmesi yeterli değildir.','',
           f"**Sonuç:** {counts['DOGRULANDI']} doğrulanmış, {counts['DOGRULANACAK']} doğrulanacak/sınırı olan, {counts['HENUZ_YOK']} henüz yapılmamış yetenek başlığı.",'',
           f"Üründe **{len(data['okumalar'])} okuma yönlendirmesi**, sözleşmede **{len(data['eylemler'])} eylem** var. "
           'Bunlar tamamının bu turda kabul edildiği anlamına gelmez. Webe özel okumalar modül sözleşmesine kendiliğinden eklenmez.','',
           f"Yeni gerçek SQL gözlemi: **{data['sql_kaniti_ozeti']['web_okuma_turu']} web okuma türü**, "
           f"**{data['sql_kaniti_ozeti']['basarili_olay_turu']} başarılı iş olayı türü**, "
           f"**{data['sql_kaniti_ozeti']['odak_kontrolu']} odak kontrolü**. "
           'Beklenen retler de kontrol kapsamındadır; iş kuralının bütün dallarının kabulü anlamına gelmez.','',
           '| Yetenek | Durum | Doğrulanan Kapsam / Açık Nokta |','|---|---|---|']
    for row in data['yetenekler']:
        lines.append('| '+row['kod']+' · '+row['ad']+' | '+LABELS[row['durum']]+' | '+row['kapsam'].replace('|','/')+' |')
    gantt=data['sql_kaniti_ozeti']['gantt'] or {}
    plan=data['sql_kaniti_ozeti']['plan'] or {}
    lines+=['','## Gantt Konusunda Kesin Ayrım','',
            'Üründe GANTT okuma kapısı vardır. '
            f"Güncel kanıttaki satır: {gantt.get('eleman','kanıt yok')}; plan tarihli: {gantt.get('planli_satir','—')}; "
            f"gerçekleşme başlangıcı dolu: {gantt.get('gerceklesen_satir','—')}. İki küme örtüşebilir. "
            'Bu, M11B modülünün tamamının kabul edildiğini veya farklı rollerin etap toplamlarının '
            'doğru olduğunu tek başına kanıtlamaz. '
            +('Ayrı M11B pilotu etap özeti/izinli ayrıntı, ortak giriş ve görev akışını doğruladı; kapsamı `modul_ortak_baglanti.json` içindedir.' if data.get('modul_pilotu_sql_kaynagiyla_eslesiyor') else 'Güncel M11B pilot kanıtı ayrıca gerekir.'),'',
            'PLAN okumasındaki başlangıç planı (B0) '+('dolu.' if plan.get('baslangic_plani_dolu') else 'bu örnekte dolu kanıtlanmadı. ')
            +(' Ayrı pilotta dolu B0–B3, modül dışından onay ve ilk planın korunması geçti; bu genel web örneğiyle karıştırılmaz.' if data.get('modul_pilotu_sql_kaynagiyla_eslesiyor') else ' Dolu ilk plan ve revizyon kabulü ayrıca gerekir.'),'',
            '## Kaynak Ve Kanıt Dosyaları','',
            '- Normatif sınır: `tasarim/00_kararlar.md` (özellikle 95, 104, 129, 131, 140, 144, 151, 154) ve T18.',
            '- İşleyiş dayanağı: `../ortak_iskelet/03_saat_sunumu.html`, `05_beyaz_yaka_sunumu.html`, '
            '`06_gorev_atamasi_sunumu.html`. Sunumdaki akış ile sonradan alınan kararlar birlikte okunur; sunum kod kanıtı değildir.',
            '- Ürün yolları: `urun/veritabani/` numaralı SQL dosyaları, `istemci/irp_cekirdek`, `istemci/web`, `modul_platformu`, `moduller/M11B`.',
            '- Yeni gerçek SQL kanıtı: `codex/sonuclar/cekirdek_yetenekleri/sql_kaniti.json`. '
            'Yerel Auth/Storage/Realtime taklitleri gerçek servis kanıtı sayılmaz.',
            '- Önceki gerçek bulut/istemci kanıtları: `codex/sonuclar/tur23_SONUC.md`, '
            '`senaryo1_SONUC.md`, `web_son_duzeltmeler_SONUC.md`. Tarih/kapsamı satırda korunur; hepsi bu turda yeniden çalıştırılmadı.',
            '- `istemci6_SONUC.md` yalnız A sonucudur; gerçek Storage yükleme kabulü diye okunmaz.',
            '- Eski raporlar tarih/sürümle okunur: Tur 22 ilk motor eksikleri, sonraki `tur22_birlesim_SONUC.md` ile birlikte değerlendirilir.',
            '- Karşılaştırma: yayımlanmış paket kataloğu ve gelen üç modülün `istekler/` dosyaları.','',
            '## Çıktıların Kullanımı','',
            '`modul_kiti/cekirdek_yetenekleri.json` bütün okuma/eylem listesini, kaynak satırlarını ve kanıt kapsamını taşır. '
            'İlk envanterden sonraki değişiklikler T26/T27 ve satırların güncel kanıt kapsamıyla izlenir. '
            'Paket 1.1 ile ilk M11B bağlantısı, bütün gelen modüllerin kabulü anlamına gelmez.','',
            'Yeniden üretim: `python modul_kiti/yetenek_envanteri.py`. SQL kanıtının kaynağı değişmişse kanıt geçerli sayılmaz; '
            'yenileme mevcut ayrı gerçek SQL web sınamasında `bash istemci/mac_derle.sh web --tam-sinama` ile yapılır.','']
    lines+=['## Yetenek Satırlarının Kaynakları','']
    for row in data['yetenekler']:
        links=', '.join('['+Path(name).name+'](../'+name+')' for name in row['kaynaklar'])
        lines.append('- **'+row['kod']+'**: '+links)
    lines.append('')
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    data=inventory()
    (HERE/'cekirdek_yetenekleri.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'tasarim/25_cekirdek_yetenek_durumu.md').write_text(document(data))
    print('Yetenek envanteri: '+str(len(data['okumalar']))+' okuma, '+str(len(data['eylemler']))+' eylem; SQL kanıtı güncel: '+str(data['sql_kaniti_kaynakla_eslesiyor']))
