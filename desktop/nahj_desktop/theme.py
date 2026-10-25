"""Nahj Blue: deep-water surfaces, frosted edges and an ice-blue accent."""
CSS = b'''
window { background: #071b26; color: #e6f4f7; font-family: 'Noto Sans Arabic', sans-serif; }
headerbar { background: #0b2330; color: #e6f4f7; box-shadow: none; border-bottom: 1px solid #234451; }
headerbar .title { font-size: 15px; font-weight: 700; }
.card { background: linear-gradient(140deg, #123949, #0b2534); border: 1px solid #365967; border-radius: 24px; padding: 32px; box-shadow: 0 18px 48px #020d1644; }
.brand-mark { color: #9bd6e5; font-size: 14px; font-weight: 700; letter-spacing: 3px; }
.hero-title { font-size: 30px; font-weight: 800; }
.subtitle { color: #a7c4cd; font-size: 14px; }
.field-label { color: #d6eaf0; font-size: 13px; font-weight: 600; }
button { background-image: none; background-color: #163747; color: #e6f4f7; border: 1px solid #365967; border-radius: 12px; padding: 9px 16px; }
button:hover { background-color: #214b5d; }
button:disabled { opacity: .55; }
button:focus-visible, entry:focus-within { outline: 2px solid #9bd6e5; outline-offset: 2px; }
headerbar button { background: transparent; border-color: transparent; padding: 7px; }
headerbar button:hover { background: #214b5d; }
button.suggested-action { background: #9bd6e5; color: #071b26; border-color: #b4e5ef; font-weight: 700; }
button.suggested-action:hover { background: #b4e5ef; }
button.flat { background: transparent; border-color: transparent; }
entry { background: #091f2c; color: #e6f4f7; border: 1px solid #365967; border-radius: 12px; padding: 12px; }
dropdown popover contents { background: #123949; color: #e6f4f7; }
.status { color: #b4e5ef; font-size: 13px; }
.error { color: #ffb4ab; }
.error-banner { background: #3b2429; padding: 10px 18px; }
progressbar trough { background: transparent; min-height: 2px; }
progressbar progress { background: #9bd6e5; min-height: 2px; }
'''

WEB_CSS = '''
:root, [data-theme] {
 --bg-color:#071b26; --fg-color:#10303e; --navbar-bg:#0b2330;
 --card-bg:#10303e; --control-bg:#163747; --text-color:#e6f4f7;
 --heading-color:#e6f4f7; --text-muted:#a7c4cd; --border-color:#365967;
 --primary:#9bd6e5; --primary-color:#9bd6e5;
}
body { font-family:'Noto Sans Arabic',system-ui,sans-serif; }
@media(prefers-reduced-motion:reduce) {
 * { transition:none!important; animation:none!important; }
}
'''
