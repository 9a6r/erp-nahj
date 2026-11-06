"""Arabic user-facing lifecycle errors; retain unknown technical diagnostics."""
import re

ARABIC = {
    'Managed printing requires the configured local HTTP origin.': 'تتطلب الطباعة عنوان HTTP المحلي المحدد في إعداد الموقع.',
    'The managed HTTP port must be unprivileged and different from backend port 8000.': 'يجب أن يكون منفذ الموقع متاحًا للمستخدم العادي ومختلفًا عن منفذ الخدمة الداخلية 8000.',
    'A service command is required.': 'أمر تشغيل الخدمة مطلوب.',
    'Unsupported language': 'اللغة غير مدعومة.',
    'Site directory already exists; refusing to overwrite it.': 'مجلد الموقع موجود بالفعل؛ رُفضت الكتابة فوقه لحماية البيانات.',
    'Enter an Administrator password of at least 12 characters to initialize the site.': 'أدخل كلمة مرور لحساب Administrator تتكون من 12 حرفًا على الأقل لإنشاء الموقع.',
    'The base site installation is incomplete. Data was retained; restore or repair it before retrying.': 'تثبيت الموقع الأساسي غير مكتمل. البيانات محفوظة؛ استعد الموقع أو أصلحه قبل إعادة المحاولة.',
    'MariaDB connection is not encrypted; provisioning refused.': 'اتصال MariaDB غير مشفّر؛ رُفض إعداد الموقع.',
    'External database is not empty; provisioning refused.': 'قاعدة البيانات الخارجية ليست فارغة؛ رُفض إعداد الموقع لحماية بياناتها.',
    'MariaDB TLS is required.': 'يلزم اتصال مشفّر عبر TLS مع MariaDB.',
    'MariaDB 10.6 or later is required.': 'يلزم MariaDB بالإصدار 10.6 أو أحدث.',
    'Recovery target already exists; refusing to overwrite it.': 'وجهة الاستعادة موجودة بالفعل؛ رُفضت الكتابة فوقها لحماية البيانات.',
    'Partial backups and database downgrades are not supported.': 'النسخ الاحتياطية الجزئية والرجوع إلى إصدار أقدم لقاعدة البيانات غير مدعومين.',
    'Backup requires additional applications. Recovery remains stopped for inspection.': 'تتطلب النسخة تطبيقات إضافية. تظل الاستعادة متوقفة لحين الفحص.',
    'Backup metadata is too large.': 'حجم بيانات وصف النسخة الاحتياطية أكبر من المسموح.',
    'Invalid backup metadata.': 'بيانات وصف النسخة الاحتياطية غير صالحة.',
    'Unsafe attachment path or file type in backup.': 'تحتوي النسخة على مسار مرفق أو نوع ملف غير آمن.',
    'Select a backup folder containing manifest.json.': 'اختر مجلد النسخة الاحتياطية الذي يحتوي على manifest.json.',
    'Backup must contain only ordinary files, without symbolic links.': 'يجب أن تضم النسخة ملفات عادية فقط، دون روابط رمزية.',
    'Backup format or server image differs from this release. A tested migration is required.': 'صيغة النسخة أو صورة خادمها تختلف عن هذا الإصدار. يلزم نقل مختبر ومتوافق.',
    'Invalid backup site name.': 'اسم الموقع المسجل في النسخة الاحتياطية غير صالح.',
    'Invalid backup checksum manifest.': 'قائمة بصمات ملفات النسخة الاحتياطية غير صالحة.',
    'Backup files differ from the checksum manifest.': 'ملفات النسخة لا تطابق قائمة الملفات المسجلة في البصمات.',
    'Backup must contain exactly one public files archive.': 'يجب أن تحتوي النسخة على أرشيف واحد للملفات العامة.',
    'Encrypted or unsupported database backup. Decrypt a trusted copy with Frappe first.': 'نسخة القاعدة مشفرة أو بصيغة غير مدعومة. فك تشفير نسخة موثوقة بأدوات Frappe أولًا.',
    'Only MariaDB backups can be restored by this release.': 'يدعم هذا الإصدار استعادة قواعد MariaDB فقط.',
    'Duplicate attachment path in backup.': 'تتضمن النسخة مسار مرفق مكررًا.',
    'Automatic recovery requires a new local MariaDB site.': 'تتطلب الاستعادة التلقائية موقعًا محليًا جديدًا بقاعدة MariaDB.',
    'Recovery did not complete. Data was retained; do not resume it as a new installation.': 'لم تكتمل الاستعادة. البيانات محفوظة؛ لا تستكملها بوصفها تثبيتًا جديدًا.',
    'No completed recovery is waiting for activation.': 'لا يوجد موقع مستعاد مكتمل ينتظر التفعيل.',
    'Port 8000 is reserved for the application backend. Choose another local HTTP port.': 'المنفذ 8000 محجوز لخدمة التطبيق الداخلية. اختر منفذًا محليًا آخر.',
    'Select local MariaDB or external MariaDB.': 'اختر قاعدة MariaDB محلية أو خارجية.',
    'Enter a valid site hostname.': 'أدخل اسم موقع صالحًا بحروف إنجليزية صغيرة وأرقام ونقاط أو شرطات.',
    'Invalid local HTTP port.': 'رقم منفذ الموقع المحلي غير صالح.',
    'Local HTTP port must be between 1024 and 65535.': 'يجب أن يكون منفذ الموقع المحلي بين 1024 و65535.',
    'Enter a valid database host, name and user.': 'أدخل عنوان خادم قاعدة البيانات واسم القاعدة والمستخدم بصيغة صالحة.',
    'Invalid MariaDB port.': 'رقم منفذ MariaDB غير صالح.',
    'Select the CA certificate for the MariaDB server.': 'اختر شهادة الجهة المصدرة (CA) لخادم MariaDB.',
    'Cannot load the MariaDB CA certificate.': 'تعذر تحميل شهادة MariaDB؛ اختر ملف شهادة صالحًا.',
    'Podman/Podman Compose is missing. Install podman and podman-compose on Arch.': 'يلزم تثبيت podman وpodman-compose لتشغيل الخادم على Arch.',
    'Operation timed out. Services and data were retained; inspect status before retrying.': 'انتهت مهلة العملية. الخدمات والبيانات محفوظة؛ افحص الحالة قبل إعادة المحاولة.',
    'Another service operation is still running.': 'توجد عملية أخرى قيد التنفيذ؛ انتظر اكتمالها.',
    'No managed site is configured. Set up a site first.': 'لم يُضبط موقع محلي بعد، أو تعذر قراءة إعداده المحفوظ.',
    'Expected one running backend container. Start services and inspect status.': 'تعذر تحديد خدمة الموقع النشطة. شغّل الخدمات وافحص حالتها.',
    'Server image checksum does not match this release. Nothing was imported.': 'بصمة ملف الخادم لا تطابق هذا الإصدار؛ لم يُستورد الملف.',
    'Imported image identity does not match this release.': 'هوية صورة الخادم المستوردة لا تطابق هذا الإصدار.',
    'This server release requires an amd64 machine.': 'يتطلب هذا الخادم جهازًا بمعمارية x86_64 ‏(amd64).',
    'Choose an Administrator password of at least 12 characters.': 'اختر كلمة مرور لحساب Administrator تتكون من 12 حرفًا على الأقل.',
    'Enter the password for the existing empty MariaDB database.': 'أدخل كلمة مرور مستخدم قاعدة MariaDB الخارجية الفارغة.',
    'A site is already configured or partially initialized. Data was retained; do not overwrite it.': 'يوجد موقع محفوظ أو إعداد غير مكتمل. البيانات محفوظة؛ استخدم الاستكمال بدل إنشاء موقع فوقه.',
    'Run Nahj with rootless Podman as your normal desktop user.': 'شغّل نهج بحسابك العادي مع Podman دون صلاحيات root.',
    'Site initialization did not complete. Inspect the setup error; existing data has been preserved.': 'لم يكتمل إنشاء الموقع. راجع خطأ الإعداد؛ البيانات الموجودة محفوظة.',
    'ERPNext did not become ready within 300 seconds. Inspect service status; data was retained.': 'لم يستجب ERPNext خلال خمس دقائق. افحص حالة الخدمات؛ البيانات محفوظة.',
    'The original site initialization is still running. Wait for it to finish before resuming.': 'عملية إنشاء الموقع الأصلية ما زالت تعمل؛ انتظر اكتمالها قبل الاستكمال.',
    'Select an existing backup destination folder.': 'اختر مجلدًا موجودًا لحفظ النسخة الاحتياطية.',
    'This site uses another server image. Automatic upgrades or downgrades are not supported. Back up and arrange a tested migration; existing data was retained.': 'هذا الموقع يستخدم صورة خادم مختلفة. لا يُغيَّر إصداره تلقائيًا؛ احتفظ بنسخة احتياطية وخطّط لنقل مجرّب. بيانات الموقع محفوظة.',
    'This server release is still under validation. Select the verified local archive; automatic download is available after publication.': 'هذا الإصدار قيد التحقق. اختر ملف الخادم المحلي المطابق للبصمة؛ يتاح التنزيل التلقائي بعد النشر.',
    'The cached server image failed verification. Select a verified archive or remove the damaged download.': 'ملف الخادم المحفوظ لم يجتز فحص البصمة. اختر ملفًا سليمًا أو احذف التنزيل التالف.',
    'The partial download exceeds the expected image size.': 'حجم التنزيل الجزئي أكبر من الحجم المتوقع.',
    'The download server returned an unexpected byte range.': 'أعاد خادم التنزيل جزءًا غير متوافق مع موضع الاستكمال.',
    'Unexpected download response.': 'استجابة خادم التنزيل غير متوقعة.',
    'The download exceeds the expected image size.': 'حجم التنزيل أكبر من الحجم المتوقع.',
    'Download interrupted; retry to resume it.': 'انقطع التنزيل؛ أعد المحاولة لاستكماله.',
    'Downloaded image failed SHA256 verification. No services were started.': 'فشل التحقق من بصمة الملف المنزّل؛ لم تُشغّل أي خدمات.',
}


def translate_error(message):
    # Subprocess errors wrap helper exceptions and may include a traceback.
    # Translate known messages at their boundaries, preserving diagnostic names,
    # paths, exit codes and unknown third-party output verbatim.
    command = re.fullmatch(r'Command failed \((-?\d+)\): (.*)', message, re.DOTALL)
    if command:
        return f'فشل الأمر ({command[1]}): {translate_error(command[2])}'
    if '\n' in message:
        return '\n'.join(translate_error(line) for line in message.split('\n'))
    if message in ARABIC:
        return ARABIC[message]
    exception = re.fullmatch(r'([A-Za-z_][\w.]*(?:Error|Exception)): (.*)', message)
    if exception:
        return f'{exception[1]}: {translate_error(exception[2])}'
    for prefix, translated in (
        ('Command failed (', 'فشل الأمر ('),
        ('Incomplete backup: missing ', 'النسخة الاحتياطية غير مكتملة؛ الملف المطلوب غير موجود: '),
        ('Backup contains an empty file: ', 'تحتوي النسخة الاحتياطية على ملف فارغ: '),
        ('Backup checksum mismatch: ', 'بصمة الملف لا تطابق النسخة: '),
        ('Backup must contain exactly one ', 'يجب أن تحتوي النسخة على ملف واحد من النوع: '),
        ('Cannot read complete backup: ', 'تعذر قراءة النسخة كاملة: '),
    ):
        if message.startswith(prefix):
            return translated + message[len(prefix):]
    return message
