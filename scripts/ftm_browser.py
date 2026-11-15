"""Lee el calendario y fichas públicas renderizadas de FTM, sin cuentas ni evasión.

Solo conserva hechos mínimos del torneo: nombre, fechas, club, modalidad, sede
explícita y estado de inscripción; no guarda jugadores, contactos, cuadros ni fotos.
"""
from __future__ import annotations
import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

CALENDAR = 'https://competicion.ftm.es/app/calendario/mensual'
TZ = ZoneInfo('Europe/Madrid')
DATE = r'\d{2}/\d{2}/\d{4}'
EXCLUDED = re.compile(r'EQUIPOS|DOBLES|PICKLEBALL|P[ÁA]DEL|PLAYA|SOCIAL', re.I)


def candidate_title(title: str) -> bool:
    return bool(re.search(r'ABSOLUT[OA]', title, re.I)) and not EXCLUDED.search(title)


def listing_candidates(html: str) -> list[dict]:
    """Asocia cada nombre con las fechas de su propio bloque, nunca por proximidad."""
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for row in soup.select('.lista_torneo'):
        link = row.select_one('.titulo a')
        date = row.select_one('.contenido .fecha')
        if not link or not date:
            continue
        name = link.get_text(' ', strip=True)
        if not candidate_title(name):
            continue
        match = re.fullmatch(rf'({DATE})\s*-\s*({DATE})', date.get_text(' ', strip=True))
        if not match:
            continue
        try:
            begin, end = [datetime.strptime(x, '%d/%m/%Y').date().isoformat() for x in match.groups()]
            if begin > end:
                continue
        except ValueError:
            continue
        result.append({'name': name, 'startDate': begin, 'endDate': end})
    return result


def parse_detail(html: str, url: str, now: datetime | None = None) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'competicion.ftm.es' or not re.fullmatch(r'/app/torneos/(?:mensual|portada|busqueda)/\d+/?', parsed.path):
        raise ValueError('La ficha no tiene una URL pública FTM reconocida')
    now = now or datetime.now(TZ)
    soup = BeautifulSoup(html, 'html.parser')
    general = soup.select_one('#general')
    if not general:
        raise ValueError('La ficha no contiene los datos generales renderizados')
    name_el = general.select_one('.nombre_torneo')
    name = name_el.get_text(' ', strip=True) if name_el else ''
    if not candidate_title(name):
        raise ValueError('La ficha no corresponde a un candidato de tenis absoluto')
    fields = {}
    for row in general.select('.row'):
        cells = row.find_all('div', recursive=False)
        if len(cells) == 2:
            label = cells[0].get_text(' ', strip=True).upper().rstrip(':')
            if label in {'FECHAS', 'CIERRE INSCRIPCIÓN', 'CLUB'}:
                fields[label] = cells[1].get_text(' ', strip=True)
    dates = re.findall(DATE, fields.get('FECHAS', ''))
    if len(dates) != 2:
        raise ValueError('La ficha no demuestra ambas fechas del torneo')
    begin, end = [datetime.strptime(x, '%d/%m/%Y').date().isoformat() for x in dates]
    if begin > end:
        raise ValueError('Fechas invertidas')
    registration = 'unknown'
    deadline = None
    periods = re.findall(rf'({DATE})(?:\s+(\d{{2}}:\d{{2}}))?', fields.get('CIERRE INSCRIPCIÓN', ''))
    if periods:
        day, hour = periods[-1]
        deadline = datetime.strptime(day + ' ' + (hour or '23:59'), '%d/%m/%Y %H:%M').replace(tzinfo=TZ)
        if deadline < now:
            registration = 'closed'
        elif general.select('a[href*="/torneos/inscripcion/"]'):
            registration = 'open'
    # La dirección administrativa del club NO se considera sede de juego.
    location = 'Sede de juego sin confirmar'
    observations = general.select_one('[data-ng-bind-html="torneo.observaciones"]')
    if observations:
        parts = [x.strip() for x in observations.stripped_strings if x.strip()]
        for i, text in enumerate(parts):
            if re.fullmatch(r'SEDE\s+DE\s+JUEGO\s*:', text, re.I):
                venue = []
                for part in parts[i+1:i+4]:
                    if re.search(r'https?://|@', part, re.I):
                        break
                    venue.append(part)
                if venue:
                    location = ' · '.join(venue)[:250]
                break
    notice = any('NOTIFICACI' in x.get_text(' ',strip=True).upper() for x in soup.select('.glyphicon-class'))
    return {'name': name, 'startDate': begin, 'endDate': end, 'sourceUrl': url,
            'club': fields.get('CLUB', 'Organizador sin confirmar'),
            'registration': registration,
            'registrationDeadline': deadline.isoformat(timespec='minutes') if deadline else None,
            'location': location, 'venueVerified': location != 'Sede de juego sin confirmar',
            'hasNotice': notice, 'checkedAt': now.isoformat(timespec='seconds')}


def male_absolute_verified(text: str) -> bool:
    return bool(re.search(r'\bAbsoluto\s+Individual\s+Masculino\b', text, re.I))


def fetch_tournaments() -> list[dict]:
    from playwright.sync_api import sync_playwright, expect
    result = []
    with sync_playwright() as engine:
        # Chromium estándar, contexto nuevo sin autenticación, sin modificaciones
        # de huella, proxies, credenciales ni técnicas para eludir bloqueos.
        browser = engine.chromium.launch()
        context = browser.new_context(locale='es-ES', timezone_id='Europe/Madrid')
        page = context.new_page()
        page.set_default_timeout(20000)
        page.set_default_navigation_timeout(35000)
        response = page.goto(CALENDAR, wait_until='domcontentloaded')
        if not response or response.status >= 400:
            raise RuntimeError('No se puede abrir el calendario público FTM')
        expect(page.locator('.caja_mes_calendario.activa')).to_be_visible()
        expect(page.locator('.lista_torneo').first).to_be_visible()
        boxes = page.locator('.caja_mes_calendario')
        active = next(i for i in range(boxes.count()) if 'activa' in (boxes.nth(i).get_attribute('class') or '').split())
        month_labels = [boxes.nth(i).inner_text() for i in [active-1, active, active+1] if 0 <= i < boxes.count()]
        candidates = []

        def select_month(label):
            target = page.locator('.caja_mes_calendario').filter(has_text=re.compile(r'\s*'.join(re.escape(part) for part in label.split())))
            if 'activa' not in (target.get_attribute('class') or '').split():
                with page.expect_response(lambda r: '/api/calendario.do' in r.url and r.request.method == 'POST') as pending:
                    target.click()
                reply = pending.value
                if reply.status != 200:
                    raise RuntimeError(f'El calendario FTM deniega el mes solicitado (HTTP {reply.status})')
                reply.finished()
            expect(target).to_have_class(re.compile(r'\bactiva\b'))
            expect(page.locator('.lista_torneo').first).to_be_visible()

        # Ventana explícita: mes anterior, actual y siguiente. Cobertura parcial.
        for month in month_labels:
            select_month(month)
            for candidate in listing_candidates(page.content()):
                candidate['month'] = month
                candidates.append(candidate)
        unique = {(x['name'], x['startDate']): x for x in candidates}
        if len(unique) > 20:
            raise RuntimeError('Más de 20 candidatos; revisar la cobertura antes de aumentar consultas')
        for candidate in unique.values():
            page.goto(CALENDAR, wait_until='domcontentloaded')
            expect(page.locator('.caja_mes_calendario.activa')).to_be_visible()
            expect(page.locator('.lista_torneo').first).to_be_visible()
            select_month(candidate['month'])
            page.get_by_role('link', name=candidate['name'], exact=True).click()
            expect(page.locator('#general .nombre_torneo')).to_have_text(candidate['name'])
            record = parse_detail(page.content(), page.url)
            if (record['startDate'], record['endDate']) != (candidate['startDate'],candidate['endDate']):
                raise ValueError('Las fechas del calendario y de la ficha no coinciden')
            page.get_by_role('button', name=re.compile('Pruebas y cuadros')).click()
            expect(page.locator('#pruebasycuadros')).to_be_visible()
            record['individualMaleVerified'] = male_absolute_verified(page.locator('#pruebasycuadros').inner_text())
            result.append(record)
        context.close()
        browser.close()
    return result
