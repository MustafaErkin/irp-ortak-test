"""Modüllerin mevcut Python arka yüz bağımlılıklarını yalnız yerel çalışma alanına kurar."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'.runtime/python'

def hazirla():
    sys.path.insert(0,str(TARGET))
    if all(importlib.util.find_spec(n) for n in ('fastapi','uvicorn','psycopg_pool','httpx','fpdf')):
        return TARGET
    TARGET.mkdir(parents=True,exist_ok=True)
    lock=Path(__file__).with_name('requirements.lock')
    subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-cache-dir',
                    '--target',str(TARGET),'-r',str(lock if lock.exists() else Path(__file__).with_name('requirements.txt'))],check=True)
    return TARGET

if __name__=='__main__':
    hazirla()
