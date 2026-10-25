# نهج لسطح المكتب — Nahj Desktop

عميل Linux أصلي خفيف نسبيًا يعتمد على GTK 4 وWebKitGTK الموجودين في النظام، دون شحن Chromium مستقل. يعمل مع خادم ERPNext/Frappe 17 حقيقي، محلي أو بعيد. لا يحوّل خادم ERPNext وقاعدة بياناته إلى برنامج يعمل دون خادم.

الواجهة عربية افتراضيًا، مع خيار English، وتصميم كحلي وأزرق مستوحى من أسلوب Vitreus الزجاجي. Vitreus الحالي يستخرج ألوان Glass من الخلفية؛ هذا التطبيق يستخدم لوحة زرقاء ثابتة، وليس نسخة رسمية من ثيم مسمى Blue.

## Arch Linux / Hyprland

```bash
sudo pacman -S --needed python python-gobject gtk4 webkitgtk-6.0 noto-fonts base-devel
cd desktop
./package.sh
cd dist
makepkg -si
nahj-desktop
```

ينشئ `package.sh` مصدر الحزمة وPKGBUILD مع SHA256 حقيقي. لم تُنشر حزمة AUR. WebKitGTK يستخدم Wayland أو X11 حسب جلسة النظام. لا يحتاج التطبيق إلى إعداد خاص في Hyprland ولا يتطلب blur أو مؤثرات compositor.

للتشغيل من المصدر، بعد تثبيت المكتبات:

```bash
cd desktop
/usr/bin/python3 -m nahj_desktop
```

Debian/Ubuntu: ثبّت `python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0 fonts-noto-core` ثم شغّل بنفس الأمر.

## الاتصال والاستخدام

1. أدخل أصل خادمك، مثل `https://erp.example.com`، ثم «فحص الاتصال وفتح التطبيق».
2. يسأل التطبيق `/api/method/ping` قبل حفظ الإعدادات. أدخل اسم المستخدم وكلمة المرور في صفحة دخول ERPNext الأصلية؛ لا يُطلب API token لاتصال واجهة المستخدم.
3. افتح المعاملات البنكية أو مساحة العمل من الشريط. يظل الحساب وقيود صلاحياته كما هما على الخادم.
4. إعدادات البنك ← التفضيلات ← اللغة تغيّر لغة الحساب بين العربية والإنجليزية وتعيد تحميل الصفحة باتجاه RTL/LTR. لغة غلاف الديسكتوب تُضبط في إعداداته بشكل مستقل.
5. تنزيلات التقارير تفتح نافذة اختيار مكان الحفظ. الروابط الخارجية التي يضغطها المستخدم تفتح في المتصفح؛ تنقلات تسجيل الدخول الخارجية التلقائية ليست مدعومة حاليًا. استخدم تسجيل دخول Frappe المباشر.

يسمح HTTP فقط لـlocalhost و127.0.0.1 و`.localhost`. الخادم البعيد يحتاج HTTPS بشهادة موثوقة. لا توجد معالجة تتجاوز أخطاء TLS. مفاتيح قواعد البيانات وتكاملات البنوك تُدار في إعدادات ERPNext الخاصة بكل تكامل على الخادم؛ إدخال رابط لا ينشئ قاعدة بيانات أو حساب خدمة تلقائيًا.

الإعدادات غير السرية في `$XDG_CONFIG_HOME/nahj/settings.json`، وجلسات الدخول في `$XDG_DATA_HOME/nahj/<server-hash>/`. لكل خادم مخزن جلسة مستقل. سجّل الخروج من داخل ERPNext لإبطال الجلسة. لا توجد واجهة JavaScript للوصول إلى وظائف الجهاز.

## البناء والتحقق

```bash
PYTHONPATH=. /usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=. dbus-run-session -- xvfb-run -a /usr/bin/python3 tests/smoke_gui.py
```

اختبار GUI يستخدم خادم HTTP محليًا مؤقتًا ويفحص النافذة، اللغة، حفظ الإعدادات، فحص الاتصال، تحميل WebKit والتنقل. أثناء التطوير نجح على Debian مع Xvfb؛ احتاجت حاوية الاختبار لتعطيل عزل WebKit داخلها لأن namespaces غير متاحة. التطبيق وشيفرة تشغيله **لا يعطلان العزل**. يلزم التحقق على جلسة Arch/Wayland فعلية قبل إصدار إنتاجي.

بناء واجهة البنك من Bench عبر الخطوات المعتادة. في بيئة Codex المُعدة يوجد `/workspace/setup-tools/refresh.sh`. اختبارات اللغة: `bench --site <site> run-tests --module erpnext.tests.test_banking_language --skip-before-tests --lightmode`.

التعريب يستفيد من كتالوجات Frappe/ERPNext العربية مع إضافات البنك. لم تُراجع كل شاشات ERPNext أو كل تنسيق طباعة يدويًا. الثيم المفصل يخص البنك وغلاف الديسكتوب، مع تلوين أساسي لباقي Desk. لا توجد قياسات ذاكرة أو FPS على جهاز Arch حقيقي حتى الآن.

لتطوير واجهة البنك من checkout مستقل: `cd banking && yarn install --frozen-lockfile && yarn build`. للتطوير الحي اضبط `FRAPPE_SITE_NAME` إلى اسم موقعك ثم `yarn dev`؛ `FRAPPE_WEBSERVER_PORT` اختياري (8000 افتراضيًا). يمكن تعيين `FRAPPE_BENCH_PATH` لقراءة منفذ Bench. بعد التثبيت أو تحديث كتالوج العربية، نفّذ من Bench:

```bash
bench --site <site> execute frappe.gettext.translate.compile_translations --kwargs '{"target_app":"erpnext","locale":"ar"}'
bench --site <site> clear-cache
```

في هذه الجلسة تعذّر بناء ملف حزمة Arch النهائي لأن المرايا `fastly.mirror.pkgbuild.com` و`geo.mirror.pkgbuild.com` أعادت 403 من سياسة الشبكة. مصدر الحزمة وPKGBUILD جاهزان للبناء على Arch.
