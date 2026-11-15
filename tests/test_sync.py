import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_torneos import parse_listing, valid_tournament_title, normalize, FTM_HOME, FTM_CLUB

class ParsingTests(unittest.TestCase):
    def test_parses_homepage_only_absolute(self):
        html = '''<html><body><div><span>13/11/2026 - 29/11/2026</span><h3>II TORNEO NOA (ABSOLUTO)</h3><small>NOA</small></div>
        <div><span>13/11/2026 - 29/11/2026</span><h3>II TORNEO NOA (JUVENIL MASCULINO)</h3></div>
        <div><span>30/10/2026 - 15/11/2026</span><h3>IX TORNEO ABSOLUTO OTOÑO UCJC SPORTS CLUB</h3></div></body></html>'''
        records=parse_listing(html,FTM_HOME,'ftm_home')
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]['startDate'],'2026-11-13')
        self.assertFalse(records[0]['individualMaleVerified'])
        self.assertIsNone(records[0]['distanceKm'])
    def test_parses_club_rows(self):
        html='''<table><tr><th>Nombre torneo</th><th>Fechas</th></tr>
        <tr><td>MASTER SENIOR FTM 2026</td><td>28/12/2026 - 05/01/2027</td></tr>
        <tr><td><a href="/app/torneos/mensual/1234/">TORNEO ABSOLUTO XYZ 2026</a></td><td>01/12/2026 - 12/12/2026</td></tr></table>'''
        records=parse_listing(html,FTM_CLUB,'ftm_club')
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['sourceUrl'],'https://competicion.ftm.es/app/torneos/mensual/1234/')
        self.assertEqual(records[0]['startDate'],'2026-12-01')
    def test_no_fabricated_eligible(self):
        self.assertFalse(valid_tournament_title('CAMPEONATO DE MADRID ABSOLUTO POR EQUIPOS'))
        self.assertTrue(valid_tournament_title('TORNEO ABSOLUTO TENIS'))
        self.assertEqual(normalize('tórneo   absoluto'), 'TORNEO ABSOLUTO')

if __name__=='__main__':unittest.main()

class IntegrityTests(unittest.TestCase):
    def test_public_json_uses_only_explicit_fields(self):
        from sync_torneos import parse_public_json
        records = parse_public_json({'error':False,'data':[{'codigo':1234,'nombre':'TORNEO ABSOLUTO DE PRUEBA','fechaInicio':'01/12/2026','fechaFin':'12/12/2026','telefono':'privado'}]})
        self.assertEqual(len(records),1)
        self.assertFalse(records[0]['individualMaleVerified'])
        self.assertFalse(records[0]['distanceVerified'])
        self.assertEqual(records[0]['registration'],'unknown')
        self.assertNotIn('telefono',records[0])
        self.assertEqual(records[0]['sourceUrl'],'https://competicion.ftm.es/app/torneos/portada/1234')

    def test_api_failure_does_not_overwrite_snapshot(self):
        import argparse, tempfile
        from unittest.mock import patch
        import sync_torneos as sync
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'torneos.json'; output.write_text('previous valid snapshot')
            status=Path(tmp)/'status.json'
            with patch.object(sync,'OUTPUT',output),patch.object(sync,'STATUS',status),patch.object(sync,'fetch_public_tournaments',side_effect=RuntimeError('HTTP 403')),patch.object(sync,'fetch',return_value='<html></html>'):
                with self.assertRaises(RuntimeError):
                    sync.run(argparse.Namespace(fixture=None,dry_run=False))
            self.assertEqual(output.read_text(),'previous valid snapshot')
            import json
            self.assertFalse(json.loads(status.read_text())['success'])

    def test_rejects_unrecognized_api_response(self):
        from sync_torneos import parse_public_json
        for value in [{}, {'error':True,'data':[]}, {'error':False,'data':{}}]:
            with self.assertRaises(ValueError): parse_public_json(value)
