"""Audit static Payments messages and add Arabic without changing payment logic."""
import ast
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def localize_checkout(text):
    replacements = {
        '{% block title %} Payment {% endblock %}': '{% block title %} {{ _("Payment") }} {% endblock %}',
        '<title>Merchant Checkout Page</title>': '<title>{{ _("Merchant Checkout Page") }}</title>',
        '<h2>Please do not refresh this page...</h2>': '<h2>{{ _("Please do not refresh this page...") }}</h2>',
    }
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise ValueError('Pinned Paytm checkout template differs from the reviewed source')
        text = text.replace(old, new)
    return text


def messages(root):
    result = set((root / 'modules.txt').read_text().splitlines())
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix == '.json':
            document = json.loads(path.read_text())
            if document.get('doctype') == 'DocType':
                result.add(document['name'])
                for field in document.get('fields', []):
                    result.update(field[k] for k in ('label', 'description') if field.get(k))
                    if field.get('fieldtype') == 'Select':
                        result.update(filter(None, field.get('options', '').split('\n')))
        elif path.suffix == '.py':
            for node in ast.walk(ast.parse(path.read_text())):
                if (isinstance(node, ast.Call) and node.args and
                        ((isinstance(node.func, ast.Name) and node.func.id == '_') or
                         (isinstance(node.func, ast.Attribute) and node.func.attr == '_')) and
                        isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                    result.add(node.args[0].value)
        elif path.suffix in ('.html', '.js'):
            for match in re.finditer(r'''(?:__|_)\(\s*(["'])(.*?)\1''', path.read_text(), re.S):
                result.add(match[2])
    return result


def prepare(root, output):
    import hashlib
    import polib
    from localization import compile_catalogue
    checkout = root / 'payments/templates/pages/paytm_checkout.html'
    original_hash = hashlib.sha256(checkout.read_bytes()).hexdigest()
    checkout.write_text(localize_checkout(checkout.read_text()))
    catalogue = HERE / 'locale/payments.ar.po'
    entries = polib.pofile(str(catalogue))
    missing = messages(root / 'payments') - {e.msgid for e in entries if e.translated()}
    if missing:
        raise ValueError('Missing Arabic Payments messages: ' + repr(sorted(missing)))
    binary, count = compile_catalogue(catalogue)
    (output / 'payments.mo').write_bytes(binary)
    locale = root / 'payments/locale'
    locale.mkdir(exist_ok=True)
    (locale / 'ar.po').write_bytes(catalogue.read_bytes())
    return {'arabic_messages': count, 'catalogue_sha256': hashlib.sha256(catalogue.read_bytes()).hexdigest(),
            'source_overlays': {'payments/templates/pages/paytm_checkout.html': {
                'original_sha256': original_hash, 'localized_sha256': hashlib.sha256(checkout.read_bytes()).hexdigest()}}}


if __name__ == '__main__':
    import sys
    print(json.dumps(prepare(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
