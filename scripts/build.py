"""Inserta una instantánea en index.html para que también funcione como archivo local."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def build():
    data = json.loads((ROOT / 'data/torneos.json').read_text(encoding='utf-8'))
    template = (ROOT / 'template.html').read_text(encoding='utf-8')
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    (ROOT / 'index.html').write_text(template.replace('__EMBEDDED_DATA__', serialized), encoding='utf-8')
if __name__ == '__main__':
    build()
