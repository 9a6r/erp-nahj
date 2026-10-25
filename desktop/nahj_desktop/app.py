"""GTK4 / WebKitGTK client. No native bridge is exposed to web content."""
import hashlib
import json
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gdk, Gio, GLib, WebKit
from . import config

CSS = b'''
window { background: #0c1524; color: #e7f1ff; }
headerbar { background: #101e33; color: #e7f1ff; box-shadow: none; }
.card { background: #14253c; border: 1px solid #2a4260; border-radius: 24px; padding: 36px; }
.hero-title { font-size: 34px; font-weight: 800; }
.subtitle { color: #a5bbd6; font-size: 15px; }
button { background-image: none; background-color: #192b43; color: #e0edfa; border: 1px solid #35516e; border-radius: 12px; padding: 10px 18px; }
button:hover { background-color: #243c58; }
button:disabled { opacity: .55; }
headerbar button { background: transparent; border-color: transparent; }
headerbar button:hover { background: #243c58; }
headerbar .title { font-size: 16px; }
dropdown popover contents { background: #14253c; color: #e0edfa; }
window { font-family: 'Noto Sans Arabic', sans-serif; }

button.suggested-action { background: #96c9ff; color: #0c1524; }
entry { background: #0e1c30; color: #e7f1ff; border: 1px solid #385578; border-radius: 12px; padding: 12px; }
.status { color: #a5d4ff; }
'''

class Nahj(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.nahj.Desktop')
        self.settings = config.load()
        self.web = None
        self.connect('activate', self.activate)

    def t(self, ar, en):
        return en if self.settings['language'] == 'en' else ar

    def activate(self, *_):
        if hasattr(self, 'window'):
            self.window.present()
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title='نهج · Nahj', default_width=1280, default_height=820)
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(self.layout)
        self.header = Gtk.HeaderBar()
        self.window.set_titlebar(self.header)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.layout.append(self.content)
        self.update_header()
        self.show_settings()
        self.window.present()
        if self.settings['server']:
            self.connect_server(None)

    def update_header(self):
        self.window.set_direction(Gtk.TextDirection.RTL if self.settings['language'] == 'ar' else Gtk.TextDirection.LTR)
        for name in ('settings_button', 'home_button', 'bank_button', 'reload_button'):
            old = getattr(self, name, None)
            if old:
                self.header.remove(old)
        actions = [('home_button', self.t('مساحة العمل', 'Workspace'), lambda *_: self.navigate('/app')),
                   ('bank_button', self.t('المعاملات البنكية', 'Banking'), lambda *_: self.navigate('/banking')),
                   ('reload_button', self.t('تحديث', 'Reload'), lambda *_: self.web.reload() if self.web else None),
                   ('settings_button', self.t('الإعدادات', 'Settings'), lambda *_: self.show_settings())]
        for name, label, callback in actions:
            button = Gtk.Button(label=label)
            button.connect('clicked', callback)
            setattr(self, name, button)
            self.header.pack_start(button)

    def clear(self):
        while child := self.content.get_first_child():
            self.content.remove(child)

    def show_settings(self):
        self.clear()
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, vexpand=True)
        card.add_css_class('card')
        card.set_size_request(500, -1)
        title = Gtk.Label(label=self.t('نهج، مساحة أعمالك', 'Nahj, your workspace'))
        title.add_css_class('hero-title'); card.append(title)
        subtitle = Gtk.Label(label=self.t('كل أعمالك في مكان هادئ وواضح.', 'A calm, clear place for your business.'))
        subtitle.add_css_class('subtitle'); card.append(subtitle)
        label = Gtk.Label(label=self.t('رابط خادم ERPNext', 'ERPNext server address'), xalign=0)
        card.append(label)
        self.address = Gtk.Entry(text=self.settings['server'], placeholder_text='https://erp.example.com')
        self.address.set_direction(Gtk.TextDirection.LTR)
        card.append(self.address)
        self.language = Gtk.DropDown.new_from_strings(['العربية', 'English'])
        self.language.set_selected(1 if self.settings['language'] == 'en' else 0)
        self.language.connect('notify::selected', self.change_language)
        card.append(self.language)
        note = Gtk.Label(label=self.t('أدخل رابط خادمك، ثم سجّل الدخول بحسابك.\nلا تحتاج إلى مفاتيح قاعدة البيانات أو توكن.', 'Enter your server address, then sign in.\nNo database keys or token required.'), wrap=True)
        note.add_css_class('subtitle'); card.append(note)
        self.status = Gtk.Label(wrap=True)
        self.status.add_css_class('status'); card.append(self.status)
        self.connect_button = Gtk.Button(label=self.t('فحص الاتصال وفتح التطبيق', 'Connect and open workspace'))
        self.connect_button.add_css_class('suggested-action')
        self.connect_button.connect('clicked', self.connect_server)
        card.append(self.connect_button)
        self.content.append(card)

    def change_language(self, dropdown, *_):
        self.settings['server'] = self.address.get_text()
        self.settings['language'] = 'en' if dropdown.get_selected() else 'ar'
        self.update_header()
        self.show_settings()

    def connect_server(self, *_):
        try:
            server = config.server_url(self.address.get_text())
        except ValueError:
            self.status.set_label(self.t('أدخل رابط HTTPS صحيحًا بدون مسار أو بيانات دخول. يسمح بـHTTP للخادم المحلي فقط.', 'Enter a valid HTTPS origin without a path or credentials. HTTP is allowed for localhost only.'))
            return
        self.connect_button.set_sensitive(False)
        self.address.set_sensitive(False)
        self.language.set_sensitive(False)
        self.status.set_label(self.t('جارٍ التحقق من الخادم…', 'Checking your server…'))
        def check():
            try:
                with urlopen(server + '/api/method/ping', timeout=12) as response:
                    if json.load(response).get('message') != 'pong':
                        raise ValueError('Not a Frappe server')
                GLib.idle_add(self.connected, server, None)
            except Exception:
                GLib.idle_add(self.connected, server, self.t('تعذّر الاتصال. راجع الرابط والشبكة وشهادة الخادم، ثم أعد المحاولة.', 'Connection failed. Check the address, network and server certificate, then retry.'))
        threading.Thread(target=check, daemon=True).start()

    def connected(self, server, error):
        self.connect_button.set_sensitive(True)
        self.address.set_sensitive(True)
        self.language.set_sensitive(True)
        if error:
            self.status.set_label(error)
            return False
        self.settings['server'] = server
        try:
            config.save(self.settings)
        except OSError:
            self.status.set_label(self.t('تعذر حفظ الإعدادات.', 'Could not save settings.'))
            return False
        if self.web:
            self.web.stop_loading()
        # A separate cookie/data store for each server, never a shared credential store.
        identity = hashlib.sha256(server.encode()).hexdigest()[:24]
        root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nahj' / identity
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        network = WebKit.NetworkSession.new(str(root), str(root / 'cache'))
        network.get_cookie_manager().set_persistent_storage(str(root / 'cookies.sqlite'), WebKit.CookiePersistentStorage.SQLITE)
        network.connect('download-started', self.download)
        self.web = WebKit.WebView(network_session=network)
        sheet = WebKit.UserStyleSheet.new(
            ":root, [data-theme] { --bg-color:#0c1524; --fg-color:#14253c; --navbar-bg:#101e33; "
            "--card-bg:#14253c; --control-bg:#192b43; --text-color:#e0edfa; --heading-color:#e0edfa; "
            "--text-muted:#aec4da; --border-color:#2a4260; --primary:#96c9ff; --primary-color:#96c9ff; } "
            "body { font-family: 'Noto Sans Arabic', system-ui, sans-serif; } "
            "@media(prefers-reduced-motion:reduce) { * { transition:none!important; animation:none!important; } }",
            WebKit.UserContentInjectedFrames.TOP_FRAME, WebKit.UserStyleLevel.USER,
            [server + "/*"], None)
        self.web.get_user_content_manager().add_style_sheet(sheet)
        self.web.get_settings().set_enable_developer_extras(False)
        self.web.connect('decide-policy', self.policy)
        self.web.connect('load-failed', self.load_failed)
        self.navigate('/banking')
        return False

    def navigate(self, path):
        if not self.web:
            return self.show_settings()
        self.clear()
        self.content.append(self.web)
        self.web.load_uri(self.settings['server'] + path + '?_lang=' + self.settings['language'])

    def policy(self, view, decision, kind):
        if kind not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        action = decision.get_navigation_action()
        uri = action.get_request().get_uri()
        target, origin = urlsplit(uri), urlsplit(self.settings['server'])
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            if kind == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
                decision.ignore(); view.load_uri(uri); return True
            return False
        decision.ignore()
        if target.scheme in ('https', 'http') and action.is_user_gesture():
            Gio.AppInfo.launch_default_for_uri(uri, None)
        return True

    def load_failed(self, view, event, uri, error):
        # Cancellation during normal navigation must not replace the new page.
        if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED) or error.code == 302:
            return False
        self.show_settings()
        self.status.set_label(self.t('تعذر تحميل الصفحة. تحقق من اتصالك وأعد المحاولة.', 'Page could not load. Check your connection and reconnect.'))
        return True

    def download(self, session, download):
        def choose(item, suggested):
            dialog = Gtk.FileChooserNative(title=self.t('حفظ الملف', 'Save file'), transient_for=self.window, action=Gtk.FileChooserAction.SAVE)
            dialog.set_current_name(Path(suggested).name)
            def response(chooser, result):
                if result == Gtk.ResponseType.ACCEPT:
                    item.set_destination(chooser.get_file().get_uri())
                    item.set_allow_overwrite(True)
                else:
                    item.cancel()
                chooser.destroy()
            dialog.connect('response', response)
            dialog.show()
            return True
        download.connect('decide-destination', choose)


def main():
    Nahj().run()
