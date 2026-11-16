"""Inserta una instantánea en index.html para que también funcione como archivo local."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def build():
    data = json.loads((ROOT / 'data/torneos.json').read_text(encoding='utf-8'))
    template = (ROOT / 'template.html').read_text(encoding='utf-8')
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    player = json.loads((ROOT / 'data/player-public.json').read_text(encoding='utf-8'))
    player_json = json.dumps(player, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    personal_js = (ROOT / 'personal.js').read_text(encoding='utf-8').replace('__PLAYER_DATA__', player_json)
    output = template.replace('__EMBEDDED_DATA__', serialized).replace('__PERSONAL_CSS__', (ROOT / 'personal.css').read_text(encoding='utf-8')).replace('__PERSONAL_JS__', personal_js)
    (ROOT / 'index.html').write_text(output, encoding='utf-8')
if __name__ == '__main__':
    build()
