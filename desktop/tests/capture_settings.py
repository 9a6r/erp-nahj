"""Capture the real settings window under X11 (requires ImageMagick)."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from nahj_desktop.app import Nahj, GLib
from nahj_desktop import config

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--language', choices=('ar', 'en'), default='ar')
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as root:
    os.environ['XDG_CONFIG_HOME'] = root
    os.environ['XDG_DATA_HOME'] = root
    config.save({'server': '', 'language': args.language})
    app = Nahj()
    result = {'saved': False, 'attempts': 0}

    def capture():
        try:
            result['attempts'] += 1
            subprocess.run(['import', '-window', 'root', str(args.output.resolve())], check=True)
            colors = int(subprocess.check_output(['identify', '-format', '%k', str(args.output.resolve())]))
            if colors < 16 and result['attempts'] < 20:
                return True
            assert colors >= 16, 'Window did not render before capture timeout'
            result['saved'] = True
        except Exception:
            app.quit()
            raise
        app.quit()
        return False

    app.connect('activate', lambda *_: print('Renderer:', type(app.window.get_renderer()).__name__, 'Display:', app.window.get_display().get_name(), flush=True))
    app.connect('activate', lambda *_: GLib.timeout_add_seconds(5, capture))
    app.run([])
    assert result['saved'], 'Screenshot capture failed'
