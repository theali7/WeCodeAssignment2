import subprocess
from pathlib import Path
import tempfile
import unittest


class FrontendWiringTests(unittest.TestCase):
    def test_patch_is_fail_closed_and_uses_same_origin(self):
        script = Path(__file__).resolve().parents[1] / "scripts/prepare_frontend.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            bundle = root / "assets/index-DXabLyQE.js"
            bundle.write_text("var Ga=`https://oapnfhnvisujhrfdvklm.supabase.co`,Ka=`public`;")
            import sys
            result = subprocess.run([sys.executable, str(script), str(root)], capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("window.location.origin+`/api`", bundle.read_text())
            self.assertNotIn("supabase.co", bundle.read_text())
            second = subprocess.run([sys.executable, str(script), str(root)], capture_output=True)
            self.assertNotEqual(second.returncode, 0)
