"""Üst kararla çelişen A1 satırının bağımsız, birebir yürütmesi.

Ana model bu satırı uygulamaz: karar 38 önceliklidir. C32 ORTA belge
tutarsızlığıdır; modelde veri kaybı varmış gibi raporlanmaz.
"""
from datetime import datetime,timedelta

def a1_altmis_gun_temizligi(sayaclar,bugun):
    return {g:n for g,n in sayaclar.items() if datetime.strptime(g,'%y%m%d').date() >= bugun-timedelta(days=60)}
