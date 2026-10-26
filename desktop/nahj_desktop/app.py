"""Native GTK4 workspace with isolated WebKit sessions per server."""
import hashlib
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, Gdk, Gio, GLib, WebKit
from . import config
from .connection import probe, ConnectionFailure
from .theme import CSS, WEB_CSS


class Nahj(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.nahj.Desktop')
        self.settings = config.load()
        self.web = None
        self.active_server = ''
        self.probe_generation = 0
        self.connect('activate', self.activate)
        self.connect('shutdown', lambda *_: self.cancel_probe())

    def t(self, ar, en):
        return en if self.settings['language'] == 'en' else ar

    def cancel_probe(self):
        self.probe_generation += 1

    def activate(self, *_):
        if hasattr(self, 'window'):
            self.window.present()
            return
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title='نهج · Nahj', default_width=1280, default_height=820)
        self.window.set_size_request(560, 400)
        self.header = Gtk.HeaderBar()
        self.window.set_titlebar(self.header)
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(self.layout)
        self.progress = Gtk.ProgressBar()
        self.progress.set_visible(False)
        self.layout.append(self.progress)
        self.error_banner = Gtk.Box(spacing=12)
        self.error_banner.add_css_class('error-banner')
        self.error_text = Gtk.Label(wrap=True, hexpand=True)
        self.error_banner.append(self.error_text)
        self.error_retry = Gtk.Button(icon_name='view-refresh-symbolic')
        self.error_retry.connect('clicked', lambda *_: self.reload())
        self.error_banner.append(self.error_retry)
        self.layout.append(self.error_banner)
        self.error_banner.set_visible(False)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.layout.append(self.content)
        for name, callback, keys in [
            ('reload', self.reload, ['<Primary>r']),
            ('back', lambda: self.web.go_back() if self.web else None, ['<Alt>Left']),
            ('forward', lambda: self.web.go_forward() if self.web else None, ['<Alt>Right']),
            ('settings', self.show_settings, ['<Primary>comma']),
        ]:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', lambda *_, fn=callback: fn())
            self.add_action(action)
            self.set_accels_for_action('app.' + name, keys)
        self.update_header()
        self.show_settings()
        self.window.present()
        if self.settings['server']:
            self.connect_server()

    def update_header(self):
        direction = Gtk.TextDirection.RTL if self.settings['language'] == 'ar' else Gtk.TextDirection.LTR
        self.window.set_direction(direction)
        for button in getattr(self, 'header_buttons', []):
            self.header.remove(button)
        self.header_buttons = []
        actions = [
            ('go-previous-symbolic', self.t('رجوع', 'Back'), lambda: self.web.go_back() if self.web else None),
            ('go-next-symbolic', self.t('تقدم', 'Forward'), lambda: self.web.go_forward() if self.web else None),
            ('go-home-symbolic', self.t('مساحة العمل', 'Workspace'), lambda: self.navigate('/desk')),
            ('x-office-spreadsheet-symbolic', self.t('المعاملات البنكية', 'Banking'), lambda: self.navigate('/banking')),
            ('view-refresh-symbolic', self.t('تحديث', 'Reload'), self.reload),
        ]
        for icon, label, callback in actions:
            button = Gtk.Button(icon_name=icon, tooltip_text=label)
            button.update_property([Gtk.AccessibleProperty.LABEL], [label])
            button.connect('clicked', lambda *_, fn=callback: fn())
            self.header.pack_start(button)
            self.header_buttons.append(button)
        button = Gtk.Button(icon_name='emblem-system-symbolic', tooltip_text=self.t('الإعدادات', 'Settings'))
        button.update_property([Gtk.AccessibleProperty.LABEL], [self.t('الإعدادات', 'Settings')])
        button.connect('clicked', lambda *_: self.show_settings())
        self.header.pack_end(button)
        self.header_buttons.append(button)
        self.error_retry.set_tooltip_text(self.t('إعادة المحاولة', 'Retry'))

    def clear(self):
        while child := self.content.get_first_child():
            self.content.remove(child)

    def show_settings(self, draft=None):
        self.cancel_probe()
        self.clear()
        self.progress.set_visible(False)
        self.error_banner.set_visible(False)
        scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(wrapper, 'set_margin_' + side)(24)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        card.add_css_class('card')
        card.set_size_request(440, -1)
        card.set_direction(self.window.get_direction())
        brand = Gtk.Label(label='N A H J')
        brand.add_css_class('brand-mark'); card.append(brand)
        title = Gtk.Label(label=self.t('مساحة أعمالك', 'Your workspace'))
        title.add_css_class('hero-title'); card.append(title)
        subtitle = Gtk.Label(label=self.t('أعمال مترابطة. تجربة واضحة.', 'Connected business. Clear perspective.'))
        subtitle.add_css_class('subtitle'); card.append(subtitle)
        label = Gtk.Label(label=self.t('خادم المؤسسة', 'Organization server'), xalign=1 if self.settings['language'] == 'ar' else 0)
        label.add_css_class('field-label'); card.append(label)
        self.address = Gtk.Entry(text=self.settings['server'] if draft is None else draft, placeholder_text='https://erp.example.com')
        self.address.set_direction(Gtk.TextDirection.LTR)
        self.address.set_input_purpose(Gtk.InputPurpose.URL)
        self.address.update_property([Gtk.AccessibleProperty.LABEL], [self.t('رابط خادم المؤسسة', 'Organization server URL')])
        self.address.connect('activate', self.connect_server)
        card.append(self.address)
        self.language = Gtk.DropDown.new_from_strings(['العربية', 'English'])
        self.language.update_property([Gtk.AccessibleProperty.LABEL], [self.t('لغة التطبيق', 'Application language')])
        self.language.set_selected(1 if self.settings['language'] == 'en' else 0)
        self.language.connect('notify::selected', self.change_language)
        card.append(self.language)
        self.graphics = Gtk.CheckButton(label=self.t('توافق الرسوميات للأجهزة الافتراضية', 'Graphics compatibility for virtual machines'))
        self.graphics.set_active(self.settings['graphics_compatibility'])
        self.graphics.set_tooltip_text(self.t('فعّله إذا ظهرت صفحات فارغة. يطبّق بعد إعادة تشغيل التطبيق.', 'Enable if pages appear blank. Applies after restarting the app.'))
        self.graphics_handler = self.graphics.connect('toggled', self.change_graphics)
        card.append(self.graphics)
        note = Gtk.Label(label=self.t('اتصل بمؤسستك وسجّل الدخول بحساب العمل.', 'Connect to your organization and sign in with your work account.'), wrap=True, max_width_chars=42)
        note.add_css_class('subtitle'); card.append(note)
        self.status = Gtk.Label(wrap=True, max_width_chars=42)
        self.status.add_css_class('status'); card.append(self.status)
        self.connect_button = Gtk.Button(label=self.t('اتصال وفتح مساحة العمل', 'Connect to workspace'))
        self.connect_button.add_css_class('suggested-action')
        self.connect_button.connect('clicked', self.connect_server)
        card.append(self.connect_button)
        if self.web:
            resume = Gtk.Button(label=self.t('العودة إلى العمل', 'Return to workspace'))
            resume.add_css_class('flat')
            resume.connect('clicked', lambda *_: self.show_web())
            card.append(resume)
        wrapper.append(card)
        scroll.set_child(wrapper)
        self.content.append(scroll)

    def change_graphics(self, checkbox):
        old = self.settings['graphics_compatibility']
        self.settings['graphics_compatibility'] = checkbox.get_active()
        try:
            config.save(self.settings)
            self.status.set_label(self.t('أعد تشغيل التطبيق لتطبيق إعداد الرسوميات.', 'Restart the app to apply the graphics setting.'))
        except OSError:
            self.settings['graphics_compatibility'] = old
            checkbox.handler_block(self.graphics_handler)
            checkbox.set_active(old)
            checkbox.handler_unblock(self.graphics_handler)
            self.status.set_label(self.t('تعذر حفظ الإعدادات.', 'Could not save settings.'))

    def change_language(self, dropdown, *_):
        draft = self.address.get_text()
        old = self.settings['language']
        self.settings['language'] = 'en' if dropdown.get_selected() else 'ar'
        try:
            config.save(self.settings)
        except OSError:
            self.settings['language'] = old
            self.status.set_label(self.t('تعذر حفظ الإعدادات.', 'Could not save settings.'))
            return
        self.update_header()
        self.show_settings(draft)

    def connect_server(self, *_):
        if not self.connect_button.get_sensitive():
            return
        try:
            server = config.server_url(self.address.get_text())
        except ValueError:
            self.status.set_label(self.t('أدخل رابط HTTPS لخادمك، مثل https://erp.example.com', 'Enter your HTTPS server address, such as https://erp.example.com'))
            self.status.add_css_class('error')
            return
        self.cancel_probe()
        generation = self.probe_generation
        for widget in (self.connect_button, self.address, self.language):
            widget.set_sensitive(False)
        self.status.remove_css_class('error')
        self.status.set_label(self.t('جارٍ الاتصال…', 'Connecting…'))
        def check():
            error = None
            try:
                probe(server)
            except ConnectionFailure as failure:
                error = str(failure)
            GLib.idle_add(self.connected, generation, server, error)
        threading.Thread(target=check, daemon=True).start()

    def connected(self, generation, server, error):
        if generation != self.probe_generation:
            return False
        for widget in (self.connect_button, self.address, self.language):
            widget.set_sensitive(True)
        errors = {
            'tls': ('شهادة الخادم غير موثوقة. راجع مسؤول النظام.', 'The server certificate is not trusted. Contact your administrator.'),
            'access': ('الخادم رفض الاتصال. راجع صلاحيات الوصول أو شبكة المؤسسة.', 'The server denied access. Check your organization network or access policy.'),
            'invalid': ('الرابط لا يشير إلى خادم Frappe متوافق.', 'This address does not identify a compatible Frappe server.'),
            'redirect': ('الخادم يعيد التوجيه إلى عنوان آخر. أدخل عنوانه النهائي.', 'The server redirects to another address. Enter its final address.'),
            'offline': ('تعذر الاتصال. تحقق من العنوان والشبكة ثم حاول مجددًا.', 'Could not connect. Check the address and network, then retry.'),
        }
        if error:
            self.status.set_label(self.t(*errors.get(error, errors['offline'])))
            self.status.add_css_class('error')
            return False
        updated = {**self.settings, 'server': server}
        web = self.web
        try:
            if not web or server != self.active_server:
                identity = hashlib.sha256(server.encode()).hexdigest()[:24]
                root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nahj' / identity
                root.mkdir(parents=True, exist_ok=True, mode=0o700)
                network = WebKit.NetworkSession.new(str(root), str(root / 'cache'))
                network.get_cookie_manager().set_persistent_storage(str(root / 'cookies.sqlite'), WebKit.CookiePersistentStorage.SQLITE)
                network.connect('download-started', self.download)
                web = WebKit.WebView(network_session=network, hexpand=True, vexpand=True)
                web.get_settings().set_default_font_family('Noto Sans Arabic')
                web.get_settings().set_sans_serif_font_family('Noto Sans Arabic')
                # Navigation policy already confines this view to the server origin.
                # WebKit match patterns reject explicit ports (common on local servers).
                sheet = WebKit.UserStyleSheet.new(WEB_CSS, WebKit.UserContentInjectedFrames.TOP_FRAME, WebKit.UserStyleLevel.USER, None, None)
                web.get_user_content_manager().add_style_sheet(sheet)
                web.connect('decide-policy', self.policy)
                web.connect('load-failed', self.load_failed)
                web.connect('load-changed', self.load_changed)
                web.connect('notify::estimated-load-progress', self.load_progress)
                web.connect('print', self.print_page)
                web.connect('web-process-terminated', self.process_terminated)
            config.save(updated)
        except (OSError, GLib.Error):
            self.status.set_label(self.t('تعذر تجهيز مساحة التطبيق. تحقق من المساحة المتاحة وصلاحيات مجلد المستخدم.', 'Could not prepare app storage. Check free space and your user folder permissions.'))
            self.status.add_css_class('error')
            return False
        self.settings = updated
        if self.web and server == self.active_server:
            self.show_web()
            return False
        if self.web:
            self.web.stop_loading()
        self.active_server = server
        self.web = web
        self.navigate('/desk')
        return False

    def show_web(self):
        if not self.web:
            return
        self.cancel_probe()
        self.clear()
        self.content.append(self.web)

    def navigate(self, path):
        if not self.web:
            return self.show_settings()
        self.show_web()
        self.web.load_uri(self.active_server + path + '?_lang=' + self.settings['language'])

    def reload(self):
        if self.web:
            self.show_web()
            self.web.reload()

    def load_changed(self, view, event):
        if view is not self.web:
            return
        if event == WebKit.LoadEvent.STARTED:
            self.error_banner.set_visible(False)
            self.progress.set_visible(True)
        elif event == WebKit.LoadEvent.FINISHED:
            self.progress.set_visible(False)

    def load_progress(self, view, *_):
        if view is self.web:
            self.progress.set_fraction(view.get_estimated_load_progress())

    def policy(self, view, decision, kind):
        if kind not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        action = decision.get_navigation_action()
        uri = action.get_request().get_uri()
        if uri.startswith('blob:' + self.active_server + '/'):
            return False
        target, origin = urlsplit(uri), urlsplit(self.active_server)
        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
            if kind == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
                decision.ignore(); view.load_uri(uri); return True
            return False
        decision.ignore()
        if target.scheme in ('https', 'http', 'mailto', 'tel') and action.is_user_gesture():
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except GLib.Error:
                self.show_error(self.t('تعذر فتح الرابط في تطبيق خارجي.', 'Could not open the link in an external application.'))
        elif target.scheme in ('https', 'http'):
            self.show_error(self.t('يتطلب تسجيل الدخول الخارجي استخدام متصفح المؤسسة.', 'External sign-in requires your organization browser.'))
        return True

    def show_error(self, message):
        self.error_text.set_label(message)
        self.error_banner.set_visible(True)
        self.progress.set_visible(False)

    def load_failed(self, view, event, uri, error):
        if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED) or error.code == 302:
            return False
        if view is self.web:
            self.show_error(self.t('تعذر تحميل الصفحة. تحقق من الشبكة وأعد المحاولة.', 'Could not load the page. Check your network and retry.'))
        return True

    def print_page(self, view, operation):
        operation.run_dialog(self.window)
        return True

    def process_terminated(self, view, reason):
        if view is self.web:
            self.show_error(self.t('توقفت صفحة العمل. اضغط إعادة المحاولة لتحميلها مجددًا.', 'The workspace page stopped. Select Retry to load it again.'))

    def download(self, session, download):
        def choose(item, suggested):
            dialog = Gtk.FileChooserNative(title=self.t('حفظ الملف', 'Save file'), transient_for=self.window, action=Gtk.FileChooserAction.SAVE)
            dialog.set_current_name(Path(suggested).name)
            def response(chooser, result):
                if result == Gtk.ResponseType.ACCEPT and chooser.get_file():
                    destination = chooser.get_file().get_path()
                    if destination:
                        item.set_destination(destination)
                        item.set_allow_overwrite(True)
                    else:
                        item.cancel()
                        self.show_error(self.t('اختر مجلدًا محليًا لحفظ الملف.', 'Choose a local folder to save the file.'))
                else:
                    item.cancel()
                chooser.destroy()
            dialog.connect('response', response)
            dialog.show()
            return True
        download.connect('decide-destination', choose)
        def failed(item, error):
            if not error.matches(WebKit.download_error_quark(), WebKit.DownloadError.CANCELLED_BY_USER):
                self.show_error(self.t('لم يكتمل تنزيل الملف. أعد المحاولة.', 'The file download did not finish. Please retry.'))
        download.connect('failed', failed)


def main():
    Nahj().run()
