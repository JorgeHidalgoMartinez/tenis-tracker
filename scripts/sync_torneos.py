#!/usr/bin/env python3
"""Sincronizador conservador de listados PÚBLICOS de la FTM.

No hay API externa documentada. Lee únicamente páginas públicas sin autenticación.
No extrae fichas de jugadores, cuadros personales, ni elude controles de acceso.
Si no consigue identificar registros con confianza, devuelve error sin modificar datos.

Uso: python scripts/sync_torneos.py [--dry-run] [--fixture ruta.html]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'torneos.json'
STATUS = ROOT / 'data' / 'sync-status.json'
FTM_API = 'https://competicion.ftm.es/app/api/calendario.do'
HEADERS = {'User-Agent': 'TenisTrackerPersonal/0.3 (https://github.com/JorgeHidalgoMartinez/tenis-tracker)', 'Accept': 'application/json,text/html'}
FTM_HOME = 'https://competicion.ftm.es/app/'
FTM_CLUB = 'https://competicion.ftm.es/clubes/club/1/torneos'
RFET_CALENDAR = 'https://www.rfet.es/es/calendarios.html'
DATE_PAIR = re.compile(r'(\d{2}/\d{2}/\d{4})\s*(?:-|–|—|al)\s*(\d{2}/\d{2}/\d{4})', re.I)
EXCLUDE = re.compile(r'VETERAN|JUVENIL|INFANTIL|ALEV[IÍ]N|DOBLES|EQUIPOS|PREVIA|FEMENINO|SENIOR|SUB.?1[0486]|SOCIAL', re.I)
TITLE = re.compile(r'ABSOLUT[OA]', re.I)
TIMEZONE = ZoneInfo('Europe/Madrid')


def normalize(x: str) -> str:
    x = unicodedata.normalize('NFD', x)
    x = ''.join(c for c in x if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', x).strip().upper()


def iso(text: str) -> str:
    return datetime.strptime(text, '%d/%m/%Y').date().isoformat()


def valid_tournament_title(x: str) -> bool:
    x = re.sub(r'\s+', ' ', x).strip()
    return (8 <= len(x) <= 140 and bool(TITLE.search(x)) and not EXCLUDE.search(x)
            and not DATE_PAIR.search(x) and not x.lower().startswith(('fecha', 'categoria')))


def canonical_href(href: str | None, base: str) -> str:
    if not href:
        return base
    url = urljoin(base, href)
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'competicion.ftm.es':
        return base
    return url


def make_record(title: str, start: str, end: str, source: str, url: str, evidence: str, raw_context: str='') -> dict:
    title = re.sub(r'\s+', ' ', unescape(title)).strip()
    short = re.sub('[^a-z0-9]+', '-', normalize(title).lower()).strip('-')
    cancelled = bool(re.search(r'\bCANCELAD[OA]\b', raw_context, re.I))
    gender_verified = bool(re.search(r'INDIVIDUAL\s+MASCULINO', raw_context, re.I))
    return {
        'id': f'ftm-{short[:65]}-{start.replace("-", "")}', 'name': title,
        'club': 'Organizador pendiente de identificar', 'startDate': start, 'endDate': end,
        'category': 'Absoluto', 'categoryVerified': True,
        'individualMaleVerified': gender_verified, 'registration': 'unknown',
        'status': 'cancelled' if cancelled else 'published', 'verification': source,
        'location': 'Sede de juego sin confirmar', 'distanceKm': None,
        'distanceVerified': False, 'surface': None,
        'sourceUrl': url, 'extraSourceUrl': None,
        'note': ('Marcado como cancelado en la misma fuente AVANZA.' if cancelled else
                 'Publicado en una página oficial FTM. Modalidad, sede y apertura de inscripciones pueden estar pendientes.'),
        'evidence': evidence
    }


def parse_listing(html: str, source_url: str, source: str) -> list[dict]:
    """Identifica solo títulos absolutos con fechas próximas explícitas.

    NO puede demostrar exhaustividad: las portadas pueden mostrar solo 5 torneos.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for x in soup(['script', 'style', 'nav', 'footer']):
        x.decompose()
    seen: dict[tuple[str, str], dict] = {}

    def add(title: str, pair: re.Match[str], link: str, context: str, reason: str):
        if not valid_tournament_title(title):
            return
        try:
            start, end = iso(pair.group(1)), iso(pair.group(2))
        except ValueError:
            return
        if start > end:
            return
        key = (normalize(title), start)
        candidate = make_record(title, start, end, source, link, reason, context)
        if key not in seen or (link != source_url and seen[key]['sourceUrl'] == source_url):
            seen[key] = candidate

    # 1. Filas de tabla estructuradas: tabla de torneos de un club.
    for row in soup.select('tr'):
        cells = row.find_all(['td','th'], recursive=False)
        if len(cells) < 2:
            continue
        names = [' '.join(c.stripped_strings) for c in cells]
        row_text = ' '.join(names)
        match = DATE_PAIR.search(row_text)
        if not match:
            continue
        title = next((s for s in names if valid_tournament_title(s)), '')
        a = row.find('a', href=True)
        add(title, match, canonical_href(a.get('href') if a else None, source_url), row_text,
            'Título y fechas extraídos de una fila del listado oficial FTM.')

    # Las tablas ya se procesaron por fila: evitar asociar títulos con la fecha de otra fila.
    for table in soup.find_all('table'):
        table.decompose()

    # 2. Portada AVANZA: nombre y rango de fechas se presentan en bloques adyacentes.
    tokens = [s.strip() for s in soup.stripped_strings if s.strip()]
    for i, title in enumerate(tokens):
        if not valid_tournament_title(title):
            continue
        # Solo fechas cercanas, sin cruzar otro título de torneo, minimiza falsos positivos.
        for j in range(i-1, max(-1, i-7), -1):
            if valid_tournament_title(tokens[j]):
                break
            m = DATE_PAIR.search(tokens[j])
            if m:
                context = ' '.join(tokens[max(0,j):min(len(tokens),i+3)])
                add(title, m, source_url, context,
                    'Título y fechas extraídos de la portada pública de la FTM (asociación por proximidad).')
                break
        else:
            # Hay portadas que ponen la fecha después del título.
            for j in range(i+1, min(len(tokens),i+5)):
                if valid_tournament_title(tokens[j]):
                    break
                m=DATE_PAIR.search(tokens[j])
                if m:
                    context = ' '.join(tokens[max(0,i-1):min(len(tokens),j+2)])
                    add(title, m, source_url, context,
                        'Título y fechas extraídos de la portada pública de la FTM (asociación por proximidad).')
                    break
    return list(seen.values())


def fetch(url: str) -> str:
    headers={'User-Agent': 'TenisTrackerPersonal/0.2 (public competitions; contact via GitHub repo owner)',
             'Accept': 'text/html,application/xhtml+xml'}
    r=requests.get(url,headers=headers,timeout=20,allow_redirects=True)
    r.raise_for_status()
    if urlparse(r.url).hostname not in {'competicion.ftm.es', 'www.rfet.es'}:
        raise ValueError(f'Redirección inesperada: {r.url}')
    if 'text/html' not in r.headers.get('content-type','text/html').lower():
        raise ValueError('Formato de respuesta no es HTML')
    return r.text


def parse_public_json(payload: dict) -> list[dict]:
    """Only the public tournament search response; never player or account data."""
    if not isinstance(payload, dict) or payload.get('error') is not False or not isinstance(payload.get('data'), list):
        raise ValueError('Respuesta FTM desconocida o error federativo; no se importan datos')
    found = []
    for row in payload['data']:
        if not isinstance(row, dict):
            continue
        title = str(row.get('nombre', '')).strip()
        if not valid_tournament_title(title):
            continue
        try:
            begin, end = iso(row['fechaInicio']), iso(row['fechaFin'])
            code = str(row['codigo'])
            if begin > end or not code.isdigit():
                continue
        except (KeyError, TypeError, ValueError):
            continue
        url = FTM_HOME + 'torneos/portada/' + code
        record = make_record(title, begin, end, 'ftm_api', url,
            'Nombre y fechas obtenidos del buscador público AVANZA; consulta HTTP sin autenticación.')
        record['id'] = 'ftm-' + code
        # No deducir modalidad, inscripción o sede de un nombre genérico.
        found.append(record)
    return found


def fetch_public_tournaments() -> list[dict]:
    # Ruta y parámetros observados en el JS público de AVANZA, versión 202611121406.
    # No es una API oficial documentada: puede cambiar sin aviso.
    params = {'accion': 'busquedaTorneos', 'start': 1, 'count': 10,
              'categorias': [], 'nombre': 'ABSOLUTO',
              'fechaInicio': (datetime.now(TIMEZONE) - timedelta(days=21)).strftime('%d/%m/%Y')}
    response = requests.post(FTM_API, json=params, headers=HEADERS, timeout=25, allow_redirects=False)
    response.raise_for_status()
    if response.is_redirect:
        raise ValueError('FTM redirige la consulta pública: no se sigue hacia autenticación')
    return parse_public_json(response.json())


def write_status(ok: bool, message: str, sources: list[dict]):
    STATUS.write_text(json.dumps({'checkedAt': datetime.now(TIMEZONE).isoformat(timespec='seconds'),
        'success': ok, 'message': message, 'sources': sources}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(args):
    found = []
    checks = []
    if args.fixture:
        page = Path(args.fixture).read_text(encoding='utf-8')
        found = parse_listing(page, FTM_HOME, 'ftm_home')
        print(f'[PRUEBA] {len(found)} candidatos en HTML de prueba')
    else:
        try:
            found = fetch_public_tournaments()
            checks.append({'source': 'FTM', 'success': bool(found), 'count': len(found)})
            print(f'[OK] Buscador público FTM: {len(found)} candidatos')
        except Exception as e:
            checks.append({'source': 'FTM', 'success': False, 'error': str(e)})
            print(f'[AVISO] FTM: {e}', file=sys.stderr)
        try:
            rfet = fetch(RFET_CALENDAR)
            soup = BeautifulSoup(rfet, 'html.parser')
            linked = any('ftm.es' in a.get('href', '') for a in soup.find_all('a', href=True))
            checks.append({'source': 'RFET', 'success': True, 'role': 'directorio territorial', 'ftmLinkFound': linked})
            print('[OK] RFET: directorio consultado; no se atribuyen torneos a esta fuente')
        except Exception as e:
            checks.append({'source': 'RFET', 'success': False, 'error': str(e)})
            print(f'[AVISO] RFET: {e}', file=sys.stderr)

    by_key={}
    for record in found:
        key=(normalize(record['name']),record['startDate'])
        # Priorizar registros completos con enlace FTM directo.
        if key not in by_key or (record['verification']=='ftm_home' and by_key[key]['verification']!='ftm_home'):
            by_key[key]=record
    verified=list(by_key.values())
    # Evitar que una página vacía o un cambio HTML borre datos útiles y se anuncie éxito.
    if not verified:
        message = 'Sin actualización: no se obtuvieron torneos verificables de FTM. Se conserva la última instantánea, si existe.'
        if not args.dry_run and not args.fixture:
            write_status(False, message, checks)
        raise RuntimeError(message)

    today=datetime.now(TIMEZONE)
    # Candidatos de páginas parciales, nunca inventar campos ausentes.
    data={
        'schemaVersion':1,
        'generatedAt':today.isoformat(timespec='seconds'),
        'generationMode':'extraccion_publica_automatica_parcial',
        'origin':{'name':'Rivas-Vaciamadrid','lat':40.3293,'lon':-3.5161,'radiusKm':100},
        'coverage':'Parcial: primera página (hasta 10 registros) del buscador público AVANZA; la RFET se consulta como directorio territorial. Ningún partido, inscripción o distancia se deduce de datos ausentes.',
        'sources':[
            {'label':'FTM AVANZA · portal oficial','url':FTM_HOME,'role':'primaria'},
            {'label':'FTM · torneos de la federación','url':FTM_CLUB,'role':'primaria'},
            {'label':'RFET · calendarios','url':RFET_CALENDAR,'role':'directorio'}
        ],
        'tournaments':sorted(verified,key=lambda t:(t['startDate'],t['name']))
    }
    print(json.dumps({'generatedAt':data['generatedAt'],'tournaments':len(verified),'names':[x['name'] for x in verified]},ensure_ascii=False,indent=2))
    if args.dry_run or args.fixture:
        return data
    write_status(True, f'{len(verified)} torneos obtenidos en una consulta real de FTM. Campos no demostrados pendientes.', checks)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from build import build
    build()
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true',help='Comprobar sin modificar archivos')
    parser.add_argument('--fixture',help='Probar sobre HTML de un archivo, sin red ni escritura')
    args=parser.parse_args()
    try:
        run(args)
    except Exception as exc:
        print(f'[ERROR] {exc}',file=sys.stderr)
        sys.exit(1)
