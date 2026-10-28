"""Native bilingual controls for the real managed server lifecycle."""
import threading

from gi.repository import Gtk, GLib
from .server import Server, ServerError


class ServerPanel(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.app = app
        self.t = app.t
        self.controls = []
        self.fields = {}
        self.set_size_request(500, -1)
        self.add_css_class('card')
        self.append(Gtk.Label(label=self.t('إدارة نظام نهج', 'Manage Nahj server'), css_classes=['hero-title']))
        self.mode = Gtk.DropDown.new_from_strings([
            self.t('خادم ERPNext موجود', 'Existing ERPNext server'),
            self.t('نظام محلي كامل مع MariaDB', 'Complete local system with MariaDB'),
            self.t('خادم محلي مع MariaDB خارجية عبر TLS', 'Local server with external MariaDB over TLS'),
        ])
        self.mode.set_selected(1)
        self.append(self.mode)
        self.controls.append(self.mode)
        self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.append(self.form)
        self.field('archive', 'صورة الخادم ‎0.3.0‎ (ملف tar.gz)', 'Server 0.3.0 image (tar.gz file)')
        self.field('site', 'اسم الموقع', 'Site hostname', 'nahj.localhost')
        self.field('port', 'منفذ الواجهة المحلية', 'Local web port', '8088')
        self.field('admin', 'كلمة مرور Administrator الجديدة', 'New Administrator password', secret=True)
        self.external = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.form.append(self.external)
        self.field('db_host', 'عنوان MariaDB الخارجي', 'External MariaDB hostname', box=self.external)
        self.field('db_port', 'منفذ MariaDB', 'MariaDB port', '3306', box=self.external)
        self.field('db_name', 'اسم قاعدة بيانات فارغة مخصصة لنهج', 'Empty database dedicated to Nahj', box=self.external)
        self.field('db_user', 'مستخدم قاعدة البيانات', 'Database user', box=self.external)
        self.field('db_password', 'كلمة مرور قاعدة البيانات', 'Database password', secret=True, box=self.external)
        self.field('ca', 'مسار شهادة CA لقاعدة البيانات', 'Database CA certificate path', box=self.external)
        note = Gtk.Label(wrap=True, max_width_chars=58, label=self.t(
            'الاتصال الخارجي يتحقق من شهادة TLS واسم الخادم. يجب أن تكون القاعدة فارغة ومخصصة لهذا الموقع. لن تُحذف البيانات عند إيقاف الخدمات.',
            'External connections verify the TLS certificate and hostname. Use an empty database dedicated to this site. Stopping services retains all data.'))
        self.form.append(note)
        self.setup_button = self.button('إعداد الموقع لأول مرة', 'Set up a new site', self.setup, self.form)
        self.actions = Gtk.Box(spacing=8)
        self.append(self.actions)
        self.button('تشغيل', 'Start', lambda: self.operation(lambda server: server.start(), connect=True), self.actions)
        self.button('إيقاف', 'Stop', lambda: self.operation(lambda server: server.stop()), self.actions)
        self.button('الحالة', 'Status', lambda: self.operation(lambda server: server.status()), self.actions)
        self.field('destination', 'مجلد تصدير النسخة الاحتياطية', 'Backup destination folder', box=self)
        self.backup_button = self.button('نسخ القاعدة والملفات وإعداد الموقع', 'Back up database, files and site configuration', self.backup, self)
        self.spinner = Gtk.Spinner()
        self.append(self.spinner)
        self.status = Gtk.Label(wrap=True, selectable=True, max_width_chars=65, xalign=0)
        self.status.add_css_class('status')
        self.append(self.status)
        self.button('العودة إلى إعدادات الاتصال', 'Return to connection settings', app.show_settings, self)
        self.mode.connect('notify::selected', self.mode_changed)
        self.mode_changed()
        try:
            profile = Server().profile()
        except ServerError:
            profile = None
        if profile:
            self.mode.set_selected(2 if profile['mode'] == 'external' else 1)
            for key in self.fields:
                if key in profile:
                    self.fields[key].set_text(str(profile[key]))
            self.form.set_sensitive(False)
            self.mode.set_sensitive(False)
            self.status.set_label(self.t('الموقع المحفوظ: ', 'Saved site: ') + profile['site'])
        self.has_profile = bool(profile)

    def field(self, key, ar, en, value='', secret=False, box=None):
        box = box if box is not None else self.form
        label = self.t(ar, en)
        box.append(Gtk.Label(label=label, xalign=0, wrap=True))
        entry = Gtk.PasswordEntry(show_peek_icon=True) if secret else Gtk.Entry()
        entry.set_text(value)
        entry.set_direction(Gtk.TextDirection.LTR)
        entry.update_property([Gtk.AccessibleProperty.LABEL], [label])
        box.append(entry)
        self.fields[key] = entry
        self.controls.append(entry)

    def button(self, ar, en, callback, box):
        button = Gtk.Button(label=self.t(ar, en))
        button.connect('clicked', lambda *_: callback())
        box.append(button)
        self.controls.append(button)
        return button

    def mode_changed(self, *_):
        choice = self.mode.get_selected()
        if choice == 0:
            self.app.show_settings()
            return
        self.external.set_visible(choice == 2)

    def setup(self):
        values = {key: entry.get_text() for key, entry in self.fields.items()}
        values['mode'] = 'external' if self.mode.get_selected() == 2 else 'local'
        self.fields['admin'].set_text('')
        self.fields['db_password'].set_text('')
        self.operation(lambda server: server.setup(values, values['archive'], values['admin'], values['db_password']))

    def backup(self):
        destination = self.fields['destination'].get_text()
        self.operation(lambda server: server.backup(destination))

    def operation(self, action, connect=False):
        if getattr(self.app, 'server_operation', False):
            self.status.set_label(self.t('عملية أخرى قيد التنفيذ.', 'Another operation is running.'))
            return
        self.app.server_operation = True
        self.app.hold()
        for control in self.controls:
            control.set_sensitive(False)
        self.spinner.start()
        self.status.remove_css_class('error')
        self.status.set_label(self.t('جارٍ تنفيذ العملية…', 'Operation in progress…'))

        def progress(message):
            GLib.idle_add(self.status.set_label, self.t('التقدم: ', 'Progress: ') + message)

        def work():
            result, error = None, None
            try:
                result = action(Server(progress=progress))
            except Exception as failure:
                error = str(failure)
            GLib.idle_add(finished, result, error)

        def finished(result, error):
            self.app.server_operation = False
            self.app.release()
            self.spinner.stop()
            for control in self.controls:
                control.set_sensitive(True)
            try:
                Server().profile()
                self.form.set_sensitive(False)
                self.mode.set_sensitive(False)
            except ServerError:
                pass
            if error:
                self.status.add_css_class('error')
                self.status.set_label(self.t('تعذرت العملية؛ لم تُحذف البيانات. التفاصيل:\n', 'Operation failed; data was retained. Details:\n') + error)
            else:
                self.status.set_label(self.t('اكتملت العملية. ', 'Operation completed. ') + (str(result) if result else ''))
                if connect and result:
                    self.app.show_settings(str(result))
                    self.app.connect_server()
            return False

        threading.Thread(target=work, daemon=False).start()


def show(app):
    if getattr(app, 'server_operation', False):
        return
    app.cancel_probe()
    app.clear()
    app.progress.set_visible(False)
    app.error_banner.set_visible(False)
    scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
    panel = ServerPanel(app)
    panel.set_halign(Gtk.Align.CENTER)
    for side in ('top', 'bottom', 'start', 'end'):
        getattr(panel, 'set_margin_' + side)(24)
    scroll.set_child(panel)
    app.content.append(scroll)
