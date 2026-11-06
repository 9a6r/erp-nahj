const nahjArabic: Record<string, string> = {
    "Bank GL Account": "حساب البنك في دفتر الأستاذ",
    "For more information, click on the Bank Reconciliation Statement tab below.": "لمزيد من المعلومات، افتح تبويب كشف التسوية البنكية أدناه.",
    "Get Unpaid Invoices": "جلب الفواتير غير المسددة",
    "Other Charges / Deductions": "رسوم أو استقطاعات أخرى",
    "Resize column": "تغيير عرض العمود",
    "Select Invoices": "اختيار الفواتير",
    "Select all rows": "تحديد جميع الصفوف",
    "Select row": "تحديد الصف",
    "The following documents will be cancelled:": "سيتم إلغاء المستندات التالية:",
    "Unpaid invoices from {0} for {1}.": "فواتير غير مسددة من {0} بمبلغ {1}.",
    "breadcrumb": "مسار التنقّل",
    "Select a company": "اختر شركة",
    "Choose a company above to view its bank accounts and transactions.": "اختر الشركة من الأعلى لعرض حساباتها البنكية ومعاملاتها.",
    "Add Row": "إضافة صف",
    "Clearance Summary": "ملخص التسوية",
    "Click to change the closing balance as per statement": "اضغط لتعديل الرصيد الختامي حسب كشف الحساب",
    "Closing (statement)": "الرصيد الختامي (الكشف)",
    "Closing (system)": "الرصيد الختامي (النظام)",
    "Drag to reorder": "اسحب لإعادة الترتيب",
    "FY": "السنة المالية",
    "Import 1 transaction": "استيراد معاملة واحدة",
    "Importing 1 transaction": "جارٍ استيراد معاملة واحدة",
    "Importing {0} of {1} transactions": "جارٍ استيراد {0} من {1} معاملة",
    "Incorrectly Cleared": "تمت تسويتها بشكل غير صحيح",
    "Matched": "مطابق",
    "Matched date": "تاريخ المطابقة",
    "No results found": "لا توجد نتائج",
    "Payment Details": "تفاصيل الدفع",
    "Preferences": "التفضيلات",
    "Reconciliation Statement": "كشف التسوية",
    "Shortcut": "اختصار",
    "e.g. Last 3 weeks, Q1, May 2025": "مثلًا: آخر 3 أسابيع، الربع الأول، مايو 2025",

    "Nahj Blue": "نهج الأزرق",
    "A calm workspace, designed for clarity.": "مساحة عمل هادئة، مصممة للوضوح.",
    "Language": "اللغة",
    "Could not update language. Please try again.": "تعذر تغيير اللغة. حاول مرة أخرى.",
}
function _(txt: string, replace?: string[], context = null) {
    if (!txt) return txt;
    if (typeof txt != "string") return txt;

    let translated_text = "";

    const key = txt; // txt.replace(/\n/g, "");
    if (window.frappe) {
        if (context) {
            translated_text = window.frappe._messages[`${key}:${context}`];
        }

        if (!translated_text) {
            translated_text = window.frappe?._messages?.[key] || txt;
        }

    } else {
        translated_text = txt;
    }

    if (document.documentElement.lang.startsWith('ar') && nahjArabic[key]) {
        translated_text = nahjArabic[key]
    }
    if (replace && typeof replace === "object") {
        translated_text = format(translated_text, replace);
    }
    return translated_text;
};

function format(str: string, args: string[]) {
    if (str == undefined) return str;

    let unkeyed_index = 0;
    return str.replace(
        /\{(\w*)\}/g,
        function (match, key) {
            if (key === "") {
                key = unkeyed_index;
                unkeyed_index++;
            }
            if (key == +key) {
                return args[key] ?? match;
            }
            return ""
        }
    );
}
export default _;
