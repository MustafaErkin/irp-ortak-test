"""İkinci tur rapor şeması, gerçek kanıt sayıları ve salt okunur kaynaklar."""
import ast,json,re,hashlib
from pathlib import Path
from collections import Counter
C=Path(__file__).resolve().parent
def oku(p): return json.loads((C/p).read_text('utf-8'))
def dogrula():
    s=oku('sonuc.json'); t=oku('test_sonuclari.json'); sim=oku('simulasyon/sonuc_v2.json')
    for a,b in [('toplam_test','toplam'),('gecen','gecen'),('kalan','kalan'),('atlanan','atlanan')]: assert s['ozet'][a]==t[b]
    assert t['toplam']==t['gecen']+t['kalan']+t['atlanan'] and t['beklenmeyen_hata']==t['xpass']==0
    assert all(x['hata_turu']=='AssertionError' and re.search(r'(C\d+|E\d+)',x['test']) for x in t['testler'] if x['sonuc']=='XFAIL')
    assert [x['no'] for x in s['tur1_durum']]==['C'+str(i) for i in range(1,21)]+['E'+str(i) for i in range(1,8)]+['B'+str(i) for i in range(1,26)]
    assert dict(Counter(x['durum'] for x in s['tur1_durum']))==s['ozet']['tur1']
    assert len(s['senaryolar'])==53 and len(s['degismezler'])==50
    assert {x['no'] for x in s['degismezler']}=={'I'+str(i) for i in range(1,51)}
    assert len(s['hatalar'])==sum(s['ozet']['yeni_hata'].values())
    assert len(s['belirsizlikler'])==s['ozet']['yeni_belirsizlik']
    assert len(s['tutarsizliklar'])==s['ozet']['yeni_tutarsizlik']
    for alan,harf,bas in [('hatalar','C',21),('belirsizlikler','B',26),('tutarsizliklar','E',8)]:
        assert [x['no'] for x in s[alan]]==[harf+str(i) for i in range(bas,bas+len(s[alan]))]
    sablon=(C.parent/'SONUC_SABLONU.md').read_text('utf-8'); rapor=(C/'SONUC.md').read_text('utf-8')
    assert re.findall(r'^## \d+\..*$',sablon,re.M)==re.findall(r'^## \d+\..*$',rapor,re.M)
    for l in sablon.splitlines():
        if l.startswith(('| No |','| Senaryo |')): assert l in rapor,l
    bek=json.loads(re.search(r'```json\s*(.*?)```',sablon,re.S)[1])
    def anahtar(a,b):
        if isinstance(b,dict):
            assert set(a)==set(b),(set(a),set(b))
            for k in b: anahtar(a[k],b[k])
        elif isinstance(b,list):
            for x in a: anahtar(x,b[0])
    anahtar(s,bek)
    for p in C.rglob('*.py'): ast.parse(p.read_text('utf-8'))
    damga=oku('kaynaklar_v2_sha256.json')
    assert all(hashlib.sha256((C.parent/p).read_bytes()).hexdigest()==v for p,v in damga.items()),'Kaynak degisti'
    k=oku('kapsama_v2.json'); assert set(k['kurallar'])=={str(i) for i in range(1,28)}; assert set(k['kararlar'])=={str(i) for i in range(1,38)}
    assert set(k['teknik'])=={'B'+str(i) for i in (3,4,5,8,9,11,12,15,19,21,23,24,25)}
    assert all(sim['degismezler'].values()) and all(x['esit'] for x in sim['karsilastirmalar'])
    assert all(x['sonuc']=='GECTI' for x in oku('simulasyon/denetim_v2.json').values())
    assert (C/'simulasyon/son_denetim_sha256.txt').read_text('ascii')==sim['son_hal_sha256']
    from irp.olay import EYLES
    assert set(oku('eylem_semalari.json'))==set(EYLES)
    print(f"Dogrulandi: {t['toplam']} test; 53 senaryo; 50 degismez; 52 eski bulgu; rapor/JSON semasi; kaynak SHA-256.")
    return True
if __name__=='__main__': dogrula()
