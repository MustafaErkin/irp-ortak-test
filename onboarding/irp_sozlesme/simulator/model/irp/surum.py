"""Karar 48: iş içeriği özeti; hesap/izleme metaverisi dahil değildir (B36)."""
from hashlib import sha256
from .olay import kodla

META = {'surum','son_hesap_ani','son_olay','olusma_ani','kural_versiyonu'}

def is_alanlari(x):
    if isinstance(x, dict): return {k:is_alanlari(v) for k,v in x.items() if k not in META}
    if isinstance(x, list): return [is_alanlari(v) for v in x]
    return x

def ozet(x): return sha256(kodla(x).encode('utf-8')).hexdigest()

def liste_surumu(d,kisi): return ozet(d.listeler.get(kisi,[]))
