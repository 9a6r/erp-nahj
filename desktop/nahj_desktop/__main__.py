"""Command-line entry point for the desktop launcher."""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(prog='nahj-desktop', description='Nahj business workspace')
    parser.add_argument('--version', action='version', version='Nahj Desktop 0.2.0')
    parser.add_argument('--check', action='store_true', help='Check desktop runtime dependencies')
    args = parser.parse_args()
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('WebKit', '6.0')
        from gi.repository import Gtk, WebKit
    except (ImportError, ValueError):
        print('Missing desktop libraries. On Arch Linux run:\n'
              'sudo pacman -Syu --needed python python-gobject gtk4 webkitgtk-6.0 noto-fonts adwaita-icon-theme', file=sys.stderr)
        return 1
    if args.check:
        print(f'GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()} / '
              f'WebKitGTK {WebKit.get_major_version()}.{WebKit.get_minor_version()} available')
        return 0
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('Open Nahj from a graphical Linux session (Wayland or X11).', file=sys.stderr)
        return 1
    from .app import main as launch
    launch()
    return 0


if __name__ == '__main__':
    sys.exit(main())
