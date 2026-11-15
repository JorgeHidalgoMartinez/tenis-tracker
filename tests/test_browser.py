import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ftm_browser import listing_candidates, candidate_title, parse_detail, male_absolute_verified

class RenderedSourceTests(unittest.TestCase):
    def test_mixed_categories_are_not_lost(self):
        self.assertTrue(candidate_title('TORNEO ABSOLUTO FEMENINO Y MASCULINO'))
        self.assertTrue(candidate_title('TORNEO ABSOLUTO Y VETERANOS'))
        for title in ['CAMPEONATO ABSOLUTO POR EQUIPOS','CAMPEONATO ABSOLUTO PICKLEBALL','TORNEO JUVENIL']:
            self.assertFalse(candidate_title(title))

    def test_dates_belong_to_their_own_card(self):
        html='''<div class="lista_torneo"><div class="titulo"><a>TORNEO ABSOLUTO A</a></div><div class="contenido"><span class="fecha">01/12/2026 - 10/12/2026</span></div></div>
        <div class="lista_torneo"><div class="titulo"><a>TORNEO ABSOLUTO B</a></div><div class="contenido"><span class="fecha">20/12/2026 - 30/12/2026</span></div></div>'''
        rows=listing_candidates(html)
        self.assertEqual(rows[1]['startDate'],'2026-12-20')
        self.assertEqual(rows[0]['endDate'],'2026-12-10')

    def detail_html(self,venue=True):
        return '''<span class="glyphicon-class">NOTIFICACIÓN: SE SUSPENDE LA JORNADA</span>
        <div id="general"><h3 class="nombre_torneo">TORNEO ABSOLUTO DE PRUEBA</h3>
        <div class="row"><div>FECHAS:</div><div>Del 13/11/2026 al 29/11/2026</div></div>
        <div class="row"><div>CIERRE INSCRIPCIÓN:</div><div>10/10/2026 - 10/11/2026 22:00</div></div>
        <div class="row"><div>CLUB:</div><div>CLUB DE PRUEBA</div></div>
        <div class="row"><div>DIRECCIÓN:</div><div>DIRECCIÓN ADMINISTRATIVA</div></div>
        <div class="row"><div>MAIL:</div><div>privado@example.com</div></div>
        ''' + ('''<span data-ng-bind-html="torneo.observaciones"><h1>SEDE DE JUEGO:</h1><h2>PISTAS DE PRUEBA</h2><h2>CALLE DE PRUEBA 7</h2><h2>MADRID</h2></span>''' if venue else '') + '</div>'

    def test_detail_uses_explicit_venue_and_closed_deadline(self):
        now=datetime(2026,11,15,18,0,tzinfo=ZoneInfo('Europe/Madrid'))
        row=parse_detail(self.detail_html(),'https://competicion.ftm.es/app/torneos/mensual/123/',now)
        self.assertEqual(row['registration'],'closed')
        self.assertTrue(row['hasNotice'])
        self.assertIn('PISTAS DE PRUEBA',row['location'])
        self.assertNotIn('privado',str(row))
        self.assertNotIn('DIRECCIÓN ADMINISTRATIVA',str(row))
        self.assertNotIn('status',row)  # Un aviso de jornada no cancela el torneo.

    def test_club_address_is_not_a_verified_venue(self):
        row=parse_detail(self.detail_html(False),'https://competicion.ftm.es/app/torneos/mensual/123/')
        self.assertFalse(row['venueVerified'])
        self.assertEqual(row['location'],'Sede de juego sin confirmar')

    def test_male_modality_must_appear_explicitly(self):
        self.assertFalse(male_absolute_verified('Absoluto Individual Femenino Juvenil Individual Masculino'))
        self.assertTrue(male_absolute_verified('Absoluto Individual Masculino Final'))

    def test_rejects_missing_fields_and_non_official_urls(self):
        with self.assertRaises(ValueError):parse_detail('<html></html>','https://competicion.ftm.es/app/torneos/mensual/123/')
        with self.assertRaises(ValueError):parse_detail(self.detail_html(),'https://example.com/torneos/123')
