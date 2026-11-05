# Arabic catalogues

`frappe.ar.po` is the Arabic catalogue from Frappe 16.54.0, commit
`2fcb9397a1f1da353b21e53d2f97ec56653acd02`, with Nahj's Arabic completions and
corrections. Frappe is MIT licensed; the original translator and project metadata
remain in the file. ERPNext's catalogue stays at `erpnext/locale/ar.po` under the
repository's GPL license. All translations are source text, not site data.

The pinned sources had 1,846 missing Frappe entries and 664 missing ERPNext
entries. These are filled, and misleading accounting/unit labels, repeated
English error messages and broken placeholders are corrected. Brand names,
program identifiers and executable examples intentionally retain their spelling.
Catalogue completeness is not a claim that every screen or external integration
has passed linguistic and visual review.

The builder validates every active entry, preserves message contexts and compiles
GNU gettext MO files. Both source PO and compiled MO files replace the upstream
copies in the image. Runtime assets reside under `frappe-bench/assets`; the managed
entrypoint links `sites/assets` there, including on a fresh or recovered site.
The compiled files are checked with Python's actual gettext loader. Rebuild and
pin the resulting image/archive identities whenever these sources change.

Run `python desktop/server-image/localization.py` after installing the hash-pinned
build requirements. The build fails on missing/fuzzy translations or changed
interpolation/HTML/Jinja tokens. Keep this catalogue tied to `upstream.json` when
upgrading Frappe; do not assume a newer upstream has the same message set.
