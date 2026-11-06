# Source integrity and feature scope

The reference is upstream **ERPNext 16.53.0**, commit
`9cd11b19575bfc34f092a24f6c8b368c4dd69481`, with Frappe **16.54.0**.
This is the stable 16 line; it does not claim parity with development 17 or
support downgrading a 17 database.

`python3 desktop/tests/audit_upstream.py` compares the committed Git trees:

| Original ERPNext source | Result |
| --- | ---: |
| App files retained | 5,360 / 5,360 |
| Byte-identical app files | 5,356 |
| Reviewed modified files | 4 |
| Deleted original files | 0 |
| Unchanged DocType definitions | 531 |
| Unchanged report definitions | 186 |
| Unchanged modules | 21 |

The four overlays are the Arabic catalogue, the authenticated banking language
preference, print-language amount-in-words, and translated printed item units.
Two app files are added: the item-unit print template and banking language tests.
The original root build manifests and licence are unchanged. The desktop client,
banking frontend and container orchestration are additional, separately visible
source. CI rejects deleted upstream files and changes outside this allowlist.
Allowlisting a file does not prove the correctness of every edit inside it.

All 21 original modules remain: Accounts, CRM, Buying, Projects, Selling, Setup,
Manufacturing, Stock, Support, Utilities, Assets, Portal, Maintenance, Regional,
ERPNext Integrations, Quality Management, Communication, Telephony, Bulk
Transaction, Subcontracting, and EDI. Permissions and company setup determine
what each user sees. Separately distributed apps such as HRMS and external
service subscriptions are not implied by retaining ERPNext's own source.

The server uses actual Frappe, MariaDB, Redis, workers and scheduler. Acceptance
tests create submitted accounting documents and stock movements, check balanced
ledger entries and access control, generate PDFs, send isolated SMTP and signed
webhook deliveries, and recover a real backup before and after a VM reboot.
These checks establish the exercised paths, not exhaustive correctness of every
original module or third-party service. Production use still requires testing
the company's configuration, provider accounts, permissions and recovery plan.

The print audit reproduced a real regression on an original Subcontracting
Receipt: it has `in_words` but no `set_total_in_words` method. The corrected print
hook checks whether that method exists and leaves this document's stored text
intact. The regression is also checked by the full server acceptance suite.

The native suite runs the actual `install.sh --with-server --yes` on a disposable
Arch/Zen account without subordinate ID ranges, checks the installed desktop
launcher, exercises GTK/WebKit on X11 and Wayland, and verifies package removal
preserves preferences. This is not a test of every GPU or the user's particular
Nahj Linux compositor.
