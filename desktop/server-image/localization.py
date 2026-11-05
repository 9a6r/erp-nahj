"""Validate and compile the Arabic catalogues used by the pinned server image."""
from collections import Counter
import gettext
import io
from pathlib import Path
import re

import polib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CATALOGUES = {
    'erpnext': REPO / 'erpnext/locale/ar.po',
    'frappe': HERE / 'locale/frappe.ar.po',
}
# Include anonymous/named placeholders, Jinja expressions and HTML attributes.
# Comparing multisets allows Arabic word order without losing repeated values.
TOKENS = re.compile(
    r'\{\{(?![\'\"]).*?\}\}|\{%.*?%\}|</?[a-zA-Z][^>]*>|'
    r'\{\d*\}|\{[a-zA-Z_]\w*\}|%\([^)]+\)[sdf]|%[sd]', re.DOTALL)


def compile_catalogue(path):
    catalogue = polib.pofile(str(path))
    errors = []
    seen = set()
    for entry in catalogue:
        if entry.obsolete:
            continue
        key = (entry.msgctxt, entry.msgid)
        if key in seen:
            errors.append(f'Duplicate message/context: {key!r}')
        seen.add(key)
        if entry.fuzzy or not entry.translated():
            errors.append(f'Untranslated or fuzzy: {entry.msgid!r}')
        targets = list(entry.msgstr_plural.values()) if entry.msgid_plural else [entry.msgstr]
        source = entry.msgid_plural or entry.msgid
        for target in targets:
            if Counter(TOKENS.findall(source)) != Counter(TOKENS.findall(target)):
                errors.append(f'Changed interpolation or markup: {entry.msgid!r}')
    if errors:
        raise ValueError(f'{path}:\n' + '\n'.join(errors))
    binary = catalogue.to_binary()
    translated = gettext.GNUTranslations(io.BytesIO(binary))
    for entry in catalogue:
        if entry.obsolete or entry.msgid_plural:
            continue
        actual = (translated.pgettext(entry.msgctxt, entry.msgid) if entry.msgctxt
                  else translated.gettext(entry.msgid))
        if actual != entry.msgstr:
            raise ValueError(f'Compiled translation lost: {entry.msgid!r}')
    return binary, len([entry for entry in catalogue if not entry.obsolete])


def image_files():
    result = {}
    bench = 'home/frappe/frappe-bench'
    for app, path in CATALOGUES.items():
        binary, _ = compile_catalogue(path)
        result[f'{bench}/apps/{app}/{app}/locale/ar.po'] = path.read_bytes()
        result[f'{bench}/assets/locale/ar/LC_MESSAGES/{app}.mo'] = binary
    return result


if __name__ == '__main__':
    for app, path in CATALOGUES.items():
        binary, count = compile_catalogue(path)
        print(f'PASS: {app}: {count} Arabic entries, no missing/fuzzy translations; '
              f'interpolation, markup and compiled gettext round-trip verified ({len(binary)} bytes)')
