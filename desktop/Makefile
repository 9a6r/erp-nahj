PREFIX ?= /usr
install:
	install -dm755 $(DESTDIR)$(PREFIX)/share/nahj-desktop/nahj_desktop $(DESTDIR)$(PREFIX)/bin $(DESTDIR)$(PREFIX)/share/applications $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps $(DESTDIR)$(PREFIX)/share/doc/nahj-desktop $(DESTDIR)$(PREFIX)/share/licenses/nahj-desktop
	install -m644 nahj_desktop/*.py $(DESTDIR)$(PREFIX)/share/nahj-desktop/nahj_desktop/
	install -m755 nahj-desktop $(DESTDIR)$(PREFIX)/bin/
	install -m644 io.nahj.Desktop.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -m644 io.nahj.Desktop.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
	install -m644 README.md DEVELOPMENT.md $(DESTDIR)$(PREFIX)/share/doc/nahj-desktop/
	install -m644 $(if $(wildcard license.txt),license.txt,../license.txt) $(DESTDIR)$(PREFIX)/share/licenses/nahj-desktop/LICENSE
