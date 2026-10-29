"""Exercise the actual GTK server settings without creating a database."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from nahj_desktop.app import Nahj, Gtk, GLib
from nahj_desktop import config


with tempfile.TemporaryDirectory() as directory:
    os.environ['XDG_CONFIG_HOME'] = directory
    os.environ['XDG_DATA_HOME'] = directory
    config.save({'server': '', 'language': 'ar'})
    app = Nahj()
    outcome = {'passed': False}

    def panel():
        widget = app.content.get_first_child().get_child()
        return widget.get_child() if isinstance(widget, Gtk.Viewport) else widget

    def exercise():
        try:
            app.show_server_settings()
            original = panel()
            original.mode.set_selected(2)
            expected = {'db_host': 'database.example.test', 'db_name': 'nahj_test',
                        'db_user': 'nahj_user', 'db_password': 'unsaved-secret',
                        'admin': 'unsaved-admin-secret', 'ca': '/chosen/ca.pem',
                        'destination': '/chosen/backups'}
            for key, value in expected.items():
                original.fields[key].set_text(value)
            language = original.controls[0]
            language.set_selected(1)
            current = panel()
            assert app.settings['language'] == 'en'
            assert current.mode.get_selected() == 2
            for key, value in expected.items():
                assert current.fields[key].get_text() == value, key
            assert 'unsaved-secret' not in config.config_path().read_text()
            assert 'unsaved-admin-secret' not in config.config_path().read_text()
            with patch.object(config, 'save', side_effect=OSError('read-only settings')):
                current.controls[0].set_selected(0)
            assert app.settings['language'] == 'en'
            assert current.controls[0].get_selected() == 1
            for key, value in expected.items():
                assert current.fields[key].get_text() == value
            app.server_operation = True
            app.show_settings()
            assert panel() is current, 'Active operation was hidden by settings navigation'
            assert app.window.emit('close-request') is True
            app.server_operation = False
            outcome['passed'] = True
            print('PASS: real GTK language switch preserves server fields without saving secrets; operation stays visible', flush=True)
        finally:
            app.quit()
        return False

    app.connect('activate', lambda *_: GLib.timeout_add(250, exercise))
    app.run([])
    assert outcome['passed']
