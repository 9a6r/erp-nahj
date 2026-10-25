PREFIX ?= /usr
install:
	install -dm755 $(DESTDIR)$(PREFIX)/share/nahj-desktop/nahj_desktop $(DESTDIR)$(PREFIX)/bin $(DESTDIR)$(PREFIX)/share/applications $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
	install -m644 nahj_desktop/*.py $(DESTDIR)$(PREFIX)/share/nahj-desktop/nahj_desktop/
	install -m755 nahj-desktop $(DESTDIR)$(PREFIX)/bin/
	install -m644 io.nahj.Desktop.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -m644 io.nahj.Desktop.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
