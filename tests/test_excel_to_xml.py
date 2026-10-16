"""Test de bout en bout de tools/excel_to_xml.py (mode fichier client libre) avec données fictives.
Usage : python3 -m unittest discover -s tests"""
import os, subprocess, sys, tempfile, unittest
from openpyxl import Workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "excel_to_xml.py")

class TestExcelToXml(unittest.TestCase):
    def test_production_from_client_sheet(self):
        with tempfile.TemporaryDirectory() as td:
            wb = Workbook(); ws = wb.active; ws.title = "Carte"
            ws.append(["Fiche client"]); ws.append(["Désignation", "Famille", "DLC (h)"])
            ws.append(["Soupe Œuf ", "Plats", 72]); ws.append(["Gaspacho", "Entrées", 48])
            src = os.path.join(td, "client.xlsx"); wb.save(src)
            out = os.path.join(td, "out")
            r = subprocess.run([sys.executable, SCRIPT, src, "--modules", "Production", "--sheet", "Carte",
                "--header-row", "2", "--map", '{"Name":"Désignation","Category":"Famille","DateLimit":"DLC (h)"}',
                "--out-dir", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            xml = open(os.path.join(out, "ProductsProduction.xml"), encoding="utf-8").read()
            self.assertIn("<Name>Soupe OEuf</Name>", xml)
            self.assertEqual(xml.count("<DefProductProduction>"), 2)
            self.assertIn("idempotence : OK", r.stdout)

    def test_missing_required_value_blocks_module(self):
        with tempfile.TemporaryDirectory() as td:
            wb = Workbook(); ws = wb.active; ws.title = "Service"
            ws.append(["Name", "TempMin", "TempMax"]); ws.append(["", 1, 2])
            src = os.path.join(td, "s.xlsx"); wb.save(src)
            r = subprocess.run([sys.executable, SCRIPT, src, "--modules", "Service", "--out-dir", os.path.join(td, "o")],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(os.path.join(td, "o", "ProductsService.xml")))

if __name__ == "__main__":
    unittest.main()
